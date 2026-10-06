"""Emission -- turning a belief field into a submission mask with the budget rule explicit.

Why the rule is not "emit every pixel above a threshold"
--------------------------------------------------------
The published metric is a ratio whose denominator is

    D = alpha (TP_w + FP_w) + beta |G|,      alpha = 0.2, beta = 0.8.

Every unit of emitted mass that is not the best cover of a ground-truth pixel contributes ~1 to
FP_w and therefore ~alpha = 0.2 to D, while a ground-truth pixel that stays uncovered contributes
beta = 0.8.  Recall is therefore four times as expensive as precision, and emitting mass
"just in case" is *cheap but not free*.  The exact marginal rule follows from the theorem in
`metric.py`:

    a dot of unit mass that lands on a pixel at kernel distance k from the nearest truth pixel,
    raising the best credit of a single truth pixel by dT = k with own cost dF = 1 - k, improves
    the score iff   k > alpha * DTI          (the "credit bar", metric.marginal_bar)

and in general (metric.py eq. T1)    dT (alpha F + beta K) > alpha T dF.

What is implemented here
------------------------
`ExpectedBudgetPacker` ranks candidate dots by *credit density* -- expected kernel-matched belief
divided by expected cost -- and then picks the prefix of that ranking that maximises the
*expected* DTI under a documented point-process model of the hidden truth:

    b(x)          = belief that pixel x is a hidden fault pixel (from Stage B; probability scale)
    credit(x)     = sum_y b(y) k(|x - y|)       (matched filter; 1 kernel radius support)
    cost(x)       = 1 - b(x)                    (expected mass that misses the truth)
    T_pred(S)     = sum_y b(y) max_{x in S, |x-y|<=R} k(|x-y|)     (redundancy-aware)
    F_pred(S)     = sum_{x in S} cost(x)
    K_pred        = sum_x b(x)
    DTI_pred(S)   = T_pred / (alpha (T_pred + F_pred) + beta K_pred)

The prefix maximising DTI_pred is emitted (`choose_prefix`).  This makes the model's own
trade-off explicit and auditable rather than a tuned threshold, and it is the piece that the
sibling repositories' greedy coverage arms (their A1/A2/A3 arms) do not do: they optimise mass or
credit, not the published ratio, and they do not expose the fixed point at which extra mass stops
paying.

Assumptions stated openly (nothing here is a measured score):
  * the truth is modelled as independent Bernoulli(b(x)) pixels -- the hidden faults are neither
    independent nor Bernoulli, so DTI_pred is a ranking instrument, not a prediction of the
    leaderboard;
  * cost(x) = 1 - b(x) ignores the partial credit of a dot that lands 1-2 px off a fault;
  * the model is calibrated only against the visible catalogue (proxy truth).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import convolve

from . import grid, metric


def kernel_stamp() -> np.ndarray:
    r = int(np.ceil(metric.RADIUS_PX))
    k = np.zeros((2 * r + 1, 2 * r + 1), dtype=np.float32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k[dy + r, dx + r] = float(metric.kernel(np.hypot(dy, dx)))
    return k


def credit_field(belief: np.ndarray) -> np.ndarray:
    """Matched-filter credit c(x) = sum_y b(y) k(|x-y|)."""
    b = np.nan_to_num(belief, nan=0.0).astype(np.float32)
    return convolve(b, kernel_stamp(), mode="constant")


@dataclass
class Packing:
    rows: np.ndarray
    cols: np.ndarray
    counts: np.ndarray
    t_pred: np.ndarray
    f_pred: np.ndarray
    dti_pred: np.ndarray
    best_count: int
    spacing_px: float


class ExpectedBudgetPacker:
    """Greedy credit-density packing with redundancy-aware prefix selection."""

    def __init__(self, spacing_px: float = 2.8, n_prefix: int = 60, max_dots: int = 400_000):
        self.spacing = float(spacing_px)
        self.n_prefix = int(n_prefix)
        self.max_dots = int(max_dots)

    def _order(self, belief: np.ndarray, candidate: np.ndarray):
        b = np.nan_to_num(belief, nan=0.0).astype(np.float32)
        credit = credit_field(belief)
        cost = np.clip(1.0 - b, 1e-3, 1.0)
        score = np.where(candidate, credit / cost, -np.inf)
        flat = np.flatnonzero(np.isfinite(score) & candidate)
        if flat.size == 0:
            return np.array([], int), np.array([], int), b
        order = flat[np.argsort(-score.ravel()[flat], kind="stable")]
        return order, score, b

    def pack(self, belief: np.ndarray, candidate: np.ndarray) -> Packing:
        order, _score, b = self._order(belief, candidate)
        if order.size == 0:
            empty = np.array([], int)
            return Packing(empty, empty, np.array([0]), np.array([0.0]), np.array([0.0]),
                           np.array([0.0]), 0, self.spacing)
        cell = max(1, int(np.floor(self.spacing)))
        md2 = self.spacing ** 2
        occupied: dict[tuple[int, int], list[tuple[int, int]]] = {}
        rows, cols = [], []
        width = grid.SHAPE[1]
        for idx in order:
            if len(rows) >= self.max_dots:
                break
            rr, cc = divmod(int(idx), width)
            key = (rr // cell, cc // cell)
            ok = True
            for a in (-1, 0, 1):
                for c2 in (-1, 0, 1):
                    for (tr, tc) in occupied.get((key[0] + a, key[1] + c2), ()):
                        if (rr - tr) ** 2 + (cc - tc) ** 2 < md2:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                continue
            occupied.setdefault(key, []).append((rr, cc))
            rows.append(rr)
            cols.append(cc)
        rows = np.array(rows, dtype=np.int32)
        cols = np.array(cols, dtype=np.int32)
        return self._prefix_curve(rows, cols, b)

    def _prefix_curve(self, rows, cols, b) -> Packing:
        n = rows.size
        if n == 0:
            z = np.array([0])
            return Packing(rows, cols, z, z.astype(float), z.astype(float), z.astype(float), 0,
                           self.spacing)
        steps = np.unique(np.linspace(1, n, min(self.n_prefix, n)).astype(int))
        t_pred, f_pred, dti = [], [], []
        k_stamp = kernel_stamp()
        r = int(np.ceil(metric.RADIUS_PX))
        for m in steps:
            mask = np.zeros(grid.SHAPE, bool)
            mask[rows[:m], cols[:m]] = True
            best = convolve(mask.astype(np.float32), k_stamp, mode="constant")
            np.clip(best, 0.0, 1.0, out=best)
            T = float((b * best).sum())
            F = float(np.clip(1.0 - b[rows[:m], cols[:m]], 0.0, 1.0).sum())
            K = float(b.sum())
            D = metric.ALPHA * (T + F) + metric.BETA * K
            t_pred.append(T)
            f_pred.append(F)
            dti.append(T / (D + metric.EPS) if D > 0 else 0.0)
        dti = np.array(dti)
        best_i = int(np.argmax(dti))
        return Packing(rows, cols, steps, np.array(t_pred), np.array(f_pred), dti,
                       int(steps[best_i]), self.spacing)


def prune_below_bar(mask: np.ndarray, belief: np.ndarray, dti_pred: float) -> np.ndarray:
    """Remove dots whose matched-filter credit is below the credit bar alpha*DTI_pred."""
    bar = metric.marginal_bar(dti_pred)
    credit = credit_field(belief)
    keep = mask & (credit >= bar)
    return keep


def to_values(mask: np.ndarray) -> np.ndarray:
    """Binary mask -> float32 raster on the submission grid (zeros elsewhere)."""
    v = np.zeros(grid.SHAPE, dtype=np.float32)
    v[mask] = 1.0
    return v
