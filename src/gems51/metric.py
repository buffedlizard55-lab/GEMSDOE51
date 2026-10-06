"""Distance-Weighted Tversky Index (DTI) for the DOE GEMS Prize Challenge.

VERBATIM SOURCE (read in full, twice, on 2026-10-06):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

Published definition (competition problem description, "Performance metric"):

    k(d) = (1 - d/R)_+ = max(1 - d/R, 0),          R = 300 m  (= 3 px at 100 m)

    TP_w = sum_{g in G} max_{x : d(x,g) <= R}  p(x) k(d(x,g))
    FP_w = sum_{x : p(x) > 0}  p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x : d(x,g) <= R} p(x) k(d(x,g))]

    DTI(alpha, beta) = TP_w / (TP_w + alpha FP_w + beta FN_w + eps),  alpha=0.2, beta=0.8.

Two exact identities are used throughout this repository and are unit-tested:

  (I1)  FN_w = |G| - TP_w              (substituted straight into the definition)
  (I2)  T + F = sum_x p(x) - (sum_x p(x) k(d_g(x))) + (sum_g p_best(x_g)) ...
        In the *dotted* regime used here (binary mass, no mutual coverage), the closed form
        T = sum_g p_best, F = sum_x p(x)(1 - k_near(x)), K = |G| gives
        DTI = T / (0.2(T + F) + 0.8 K)  -- the "budget" form, tested in tests/test_metric.py.

MARGINAL-INCLUSION THEOREM (derived here, tested numerically in tests/test_metric.py).
Add one unit of mass whose realised kernel credit against the *current* best is dT and whose own
uncovered distance weight is dF.  Writing D = alpha(T+F) + beta K,

    DTI' > DTI  <=>  (T + dT) D > T (D + alpha(dT + dF))
                <=>  dT (D - alpha T) > alpha T dF
                <=>  dT (alpha F + beta K) > alpha T dF.                       (T1)

For a dot that lands on a pixel at kernel distance k from the nearest ground-truth pixel and
covers exactly one ground-truth pixel (dT = k, dF = 1 - k), (T1) reduces to

    k > alpha * DTI   (equivalently dT/dF > alpha*T/(alpha*F + beta*K)).          (T2)

Equation (T2) is the "credit bar": alpha*DTI.  It is used in emission.py as the pruning rule and
reported in the site.  NOTE ON PRIOR ART: an earlier expression alpha*s/(1-alpha*s) appears in the
sibling repositories GEMSDOE28/GEMSDOE32 (their file `src/gems32/metric.py`, irregularity
IR-32-BAR-01) and is NOT used here; (T1) is the general form and (T2) is the special case.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA: float = 0.2
BETA: float = 0.8
RADIUS_PX: float = 3.0          # 300 m / 100 m pixel
EPS: float = 1e-12

__all__ = [
    "ALPHA", "BETA", "RADIUS_PX", "EPS", "kernel", "dti_from_components",
    "evaluate", "evaluate_binary", "evaluate_bruteforce", "marginal_bar",
    "marginal_gain_components", "CreditAudit", "credit_audit",
]


def kernel(d, radius: float = RADIUS_PX):
    """Triangular kernel k(d) = max(1 - d/R, 0); d and radius in pixels."""
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


def _shift(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Return ``out`` with ``out[y, x] = arr[y - dy, x - dx]`` (zero fill outside)."""
    out = np.zeros_like(arr)
    h, w = arr.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    if ys0 < ys1 and xs0 < xs1:
        out[ys0:ys1, xs0:xs1] = arr[max(0, -dy):min(h, h - dy),
                                    max(0, -dx):min(w, w - dx)]
    return out


def _offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = float(kernel(np.hypot(dy, dx), radius))
            if k > 0.0:
                out.append((dy, dx, k))
    return out


_OFFS = _offsets()


def _check(pred, truth, valid):
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth)
    if pred.ndim != 2:
        raise ValueError("prediction must be a 2-D grid")
    if truth.shape != pred.shape:
        raise ValueError("prediction and truth must be equal-shaped 2-D grids")
    if valid is None:
        valid = np.ones(pred.shape, bool)
    else:
        valid = np.asarray(valid, bool)
        if valid.shape != pred.shape:
            raise ValueError("valid mask grid mismatch")
    inside = pred[valid]
    if inside.size and (not np.isfinite(inside).all()):
        raise ValueError("predictions inside the scored domain must be finite")
    if inside.size and ((inside < 0.0).any() or (inside > 1.0).any()):
        raise ValueError("predictions inside the scored domain must lie in [0, 1]")
    return pred, truth, valid


def _clean(pred, truth, valid):
    """Zero the prediction and truth outside the scored domain."""
    p = np.where(valid & np.isfinite(pred), pred, 0.0).astype(np.float64)
    g = valid & (np.asarray(truth) > 0)
    return p, g


def evaluate(pred, truth, valid=None) -> dict:
    """Exact DTI for a soft or binary prediction.  Returns components + score."""
    pred, truth, valid = _check(pred, truth, valid)
    p, g = _clean(pred, truth, valid)
    H, W = p.shape
    n_truth = int(g.sum())
    if n_truth == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0, coverage=0.0)
    best = np.zeros(p.shape, dtype=np.float64)
    for dy, dx, k in _OFFS:
        # best[y, x] = max over offsets of p[y + dy, x + dx] * k   (credit for truth at (y, x))
        np.maximum(best, _shift(p, -dy, -dx) * k, out=best)
    np.clip(best, 0.0, 1.0, out=best)
    tp = float(best[g].sum())
    fn = float(n_truth) - tp
    d_g = distance_transform_edt(~g)
    fp = float((p * (1.0 - kernel(d_g))).sum())
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n_truth,
                dti=dti_from_components(tp, fp, fn), coverage=tp / n_truth)


def evaluate_binary(pred_bool, truth, valid=None) -> dict:
    """Fast exact DTI for a binary {0,1} prediction (EDT identity), same convention."""
    pred_bool = np.asarray(pred_bool, bool)
    truth = np.asarray(truth, bool)
    if pred_bool.shape != truth.shape:
        raise ValueError("prediction and truth must be equal-shaped grids")
    valid_ = np.ones(pred_bool.shape, bool) if valid is None else np.asarray(valid, bool)
    p = pred_bool & valid_
    g = truth & valid_
    n_truth = int(g.sum())
    if n_truth == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0, coverage=0.0)
    if not p.any():
        return dict(tp=0.0, fp=0.0, fn=float(n_truth), n_truth=n_truth, dti=0.0, coverage=0.0)
    d_p = distance_transform_edt(~p)
    tp = float(kernel(d_p[g]).sum())
    fn = float(n_truth) - tp
    d_g = distance_transform_edt(~g)
    fp = float((1.0 - kernel(d_g[p])).sum())
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n_truth,
                dti=dti_from_components(tp, fp, fn), coverage=tp / n_truth)


def evaluate_bruteforce(pred, truth, radius: float = RADIUS_PX) -> dict:
    """Literal transcription of the published equations, O(|G|*|P|).  Test oracle only."""
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, bool)
    gs = np.argwhere(truth)
    xs = np.argwhere(pred > 0)
    tp = fn = 0.0
    for g in gs:
        best = 0.0
        for x in xs:
            d = float(np.hypot(*(x - g)))
            if d <= radius:
                best = max(best, pred[tuple(x)] * max(1.0 - d / radius, 0.0))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for x in xs:
        kmin = 0.0
        for g in gs:
            kmin = max(kmin, max(1.0 - float(np.hypot(*(x - g))) / radius, 0.0))
        fp += pred[tuple(x)] * (1.0 - kmin)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=float(len(gs)),
                dti=dti_from_components(tp, fp, fn))


def dti_from_components(tp: float, fp: float, fn: float) -> float:
    """DTI from the three published components (alpha=0.2, beta=0.8)."""
    return float(tp / (tp + ALPHA * fp + BETA * fn + EPS))


def marginal_bar(current_dti: float) -> float:
    """Credit bar alpha*DTI, the special case (T2) of the theorem (T1)."""
    return ALPHA * float(current_dti)


def marginal_gain_components(d_tp: float, d_fp: float, tp: float, fp: float,
                             n_truth: float) -> float:
    """Exact change in DTI of adding (d_tp, d_fp) to a state (tp, fp, n_truth).

    Sign test uses the general theorem (T1).  Returned as the actual delta so callers can rank.
    """
    d0 = ALPHA * (tp + fp) + BETA * n_truth
    d1 = ALPHA * (tp + d_tp + fp + d_fp) + BETA * n_truth
    return float((tp + d_tp) / (d1 + EPS) - tp / (d0 + EPS))


@dataclass(frozen=True)
class CreditAudit:
    n_emitted: int
    total_mass: float
    redundancy_fraction: float
    mean_self_kernel: float
    mean_nearest_truth_px: float = float("nan")


def credit_audit(mask, truth=None) -> CreditAudit:
    """Structure audit of an emission mask, optionally against a truth set."""
    m = np.asarray(mask, dtype=np.float64)
    pos = m > 0
    n = int(pos.sum())
    if n == 0:
        return CreditAudit(0, 0.0, 0.0, 0.0)
    best = np.zeros(m.shape)
    for dy, dx, k in _OFFS:
        if dy == 0 and dx == 0:
            continue                       # own pixel: 1.0 * mask, no information
        np.maximum(best, _shift(m, -dy, -dx) * k, out=best)
    red = np.clip(best, 0.0, 1.0)
    d_truth = float("nan")
    if truth is not None:
        g = np.asarray(truth, bool)
        d_truth = float(distance_transform_edt(~g)[pos].mean()) if g.any() else float("nan")
    return CreditAudit(n_emitted=n, total_mass=float(m.sum()),
                       redundancy_fraction=float((red[pos] > 0).mean()),
                       mean_self_kernel=float(red[pos].mean()),
                       mean_nearest_truth_px=d_truth)
