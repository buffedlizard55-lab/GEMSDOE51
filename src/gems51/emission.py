"""Emission: turn a continuous rank field into a legal, budgeted dot raster.

WHY THIS IS THE RIGHT OBJECTIVE, DERIVED FROM THE PUBLISHED METRIC
------------------------------------------------------------------
With the published definitions (page 967) and T = TP_w, S = sum_x p(x),
M = sum_x p(x) * max_g k(d(x,g)), G = |truth|, the identity

    FP_w = S - M        and        FN_w = |G| - T

is exact, so

    DTI = T / ( 0.2*(T + S - M) + 0.8*|G| )            (derived here, algebraically)

(which reproduces the owner group's independently reported identity).  Two consequences
drive the emission rule:

  1. Mass that is *masked* (on a mapped fault) does not enter S at all, while T can still
     rise -> such mass has strictly positive expected value at zero cost.  This is the
     official masking statement, used as published.
  2. For unmasked mass, a unit added at kernel weight w changes the denominator by
     0.2*(1 - w) and, if it becomes the argmax for some truth pixel, raises T.
     The break-even condition for accepting a pixel of *new* credit is therefore
     w > 0.2*DTI  (the "credit bar"), and this repository evaluates it explicitly.

The selector below is a greedy maximum-expected-coverage packing with a non-maximum
suppression ring of 3 px (the kernel radius), because the metric pays for covering
DISTINCT truth pixels, not for covering them thickly: once a truth pixel has a
prediction at distance 0, extra mass on it earns no further T and still costs 0.2.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def nms_mask(field: np.ndarray, radius_px: int) -> np.ndarray:
    """Index map choosing one representative per (2r+1)^2 window, by max field value."""
    size = 2 * radius_px + 1
    mx = ndimage.maximum_filter(field, size=size, mode="nearest")
    return field >= mx - 1e-12


def greedy_pack(
    field: np.ndarray,
    eligible: np.ndarray,
    budget: int,
    *,
    suppression_px: int = 3,
    w_est: np.ndarray | None = None,
) -> np.ndarray:
    """Pick `budget` pixels maximising sum of expected kernel credit.

    field      : ranking score (higher = more likely near a real fault)
    eligible   : boolean eligibility mask (stage-1 approved tiles & valid footprint)
    w_est      : optional per-pixel expected kernel weight; defaults to `field`-derived
    Returns a boolean selection mask.
    """
    if w_est is None:
        w_est = field
    cand = np.logical_and(eligible, np.isfinite(field) & (field > 0))
    n_cand = int(cand.sum())
    if n_cand == 0 or budget <= 0:
        return np.zeros_like(cand)

    # Greedy max-coverage: iteratively take the global max, then suppress a disc of
    # radius `suppression_px` around it (the kernel is 3 px, so a second dot inside
    # that disc cannot reach a truth pixel the first one did not already reach at a
    # larger weight).
    work = np.where(cand, w_est.astype(np.float32), -np.inf).copy()
    picked = np.zeros_like(cand)
    r = int(suppression_px)
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    disc = (yy * yy + xx * xx) <= r * r
    offs = np.argwhere(disc) - r
    for _ in range(int(budget)):
        idx = int(np.argmax(work))
        if not np.isfinite(work.flat[idx]):
            break
        y, x = divmod(idx, work.shape[1])
        picked[y, x] = True
        for dy, dx in offs:
            ny, nx = y + dy, x + dx
            if 0 <= ny < work.shape[0] and 0 <= nx < work.shape[1]:
                work[ny, nx] = -np.inf
    return picked


def pack_by_threshold(field: np.ndarray, eligible: np.ndarray, budget: int,
                      *, suppression_px: int = 3) -> np.ndarray:
    """Cheap alternative to `greedy_pack`: keep the top-`budget` peak pixels after NMS."""
    peaks = nms_mask(field, suppression_px)
    cand = np.logical_and.reduce([eligible, peaks, np.isfinite(field), field > 0])
    if budget <= 0:
        return np.zeros_like(cand)
    vals = field[cand]
    n = int(cand.sum())
    if n <= budget:
        return cand
    thr = np.partition(vals, n - budget)[n - budget]
    return np.logical_and(cand, field >= thr)


def to_values(
    picked: np.ndarray,
    core: np.ndarray,
    shell: np.ndarray,
    *,
    core_value: float = 1.0,
    shell_gain: float = 1.0,
    dot_value: float = 1.0,
    field: np.ndarray | None = None,
    grad_min: float = 0.42,
    grad_max: float = 1.0,
) -> np.ndarray:
    """Compose the final float raster in [0, 1].

    core  : mapped-fault pixels -> `core_value` (masked, therefore free)
    shell : near-catalogue annulus weight in [0, 1] -> scaled by `shell_gain`
    picked: selected novel dots, graded in [grad_min, grad_max] by the ranking field so
            that higher-confidence dots carry more probability mass.
    """
    out = np.zeros(core.shape, dtype=np.float32)
    if field is None:
        out[picked] = dot_value
    else:
        v = field[picked]
        if v.size:
            lo, hi = float(np.min(v)), float(np.max(v))
            if hi > lo:
                g = grad_min + (grad_max - grad_min) * (v - lo) / (hi - lo)
            else:
                g = np.full_like(v, grad_max)
            out[picked] = g.astype(np.float32)
    np.maximum(out, (shell * shell_gain).astype(np.float32), out=out)
    out[core] = np.maximum(out[core], core_value)
    np.clip(out, 0.0, 1.0, out=out)
    return out


def weighted_sample(
    field: np.ndarray,
    eligible: np.ndarray,
    budget: int,
    *,
    seed: int = 0,
    power: float = 1.0,
) -> np.ndarray:
    """Sample `budget` pixels without replacement, probability proportional to `field**power`.

    WHY THIS EXISTS, AND WHY IT IS THE SHIPPED RULE
    -----------------------------------------------
    The published metric's credit term is `TP_w = SUM over TRUTH pixels g of
    max_x p(x)k(d(x,g))`.  It is a sum over the *truth*, not over the predictions.  A dot
    therefore earns its best credit once, whether it is the only dot within 3 px of a truth
    pixel or one of twenty.  Concentrating dots on the top of a ranking leaves large parts of
    the map uncovered and each covered truth pixel is worth at most 1; spreading dots
    guarantees that a *larger number of distinct truth pixels* collect credit.

    Measured consequence (leave-one-trace-out holdout, 4 draws, matched 44,090-dot budget,
    `evidence/holdout_spread.json`): top-of-ranking peak packing LOSES to uniform random
    despite having a higher per-dot credit density, while field-weighted sampling -- which
    keeps uniform coverage but biases the draw toward the detector's high-responses ground --
    beats both.  Breadth of coverage is the binding constraint; the field sets the bias.
    """
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(eligible.ravel())
    if idx.size == 0 or budget <= 0:
        return np.zeros_like(eligible)
    w = np.clip(field.ravel()[idx], 0.0, None).astype(np.float64)
    if power != 1.0:
        w = np.power(w, power)
    if not np.isfinite(w).all() or w.sum() <= 0:
        w = np.ones_like(w)
    w = w / w.sum()
    n = min(int(budget), idx.size)
    pick = rng.choice(idx, size=n, replace=False, p=w)
    picked = np.zeros_like(eligible)
    picked.ravel()[pick] = True
    return picked
