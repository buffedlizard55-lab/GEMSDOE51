"""Official Distance-Weighted Tversky Index (DTI) for the DOE GEMS Prize Challenge.

Source of the equations (verbatim, fetched 2026-10-06):
    https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

Published formulation
---------------------
    k(d)   = max(1 - d/R, 0),                        R = 300 m = 3 px at 100 m
    TP_w   = sum_{g in G} max_{x : d(x,g) <= R}  p(x) * k(d(x,g))
    FP_w   = sum_{x : p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FN_w   = sum_{g in G} [1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g))]  = |G| - TP_w
    DTI(a,b) = TP_w / (TP_w + a*FP_w + b*FN_w + eps),  a = 0.2, b = 0.8

Two algebraic identities used throughout this repository (both proved in
``tests/test_metric.py``):

    (I1)  FN_w = |G| - TP_w                       (immediate from the definitions)
    (I2)  DTI  = TP_w / ( a*(TP_w + FP_w) + b*|G| + eps )
          because TP + a FP + b(|G| - TP) = (1-b) TP + a FP + b|G| and 1-b = a.

(I2) is a useful budget identity, but ``TP_w + FP_w`` is an effective
weighted cost, not the raw number of emitted pixels. For an added prediction,
let ``c`` be its incremental weighted true-positive credit and ``f`` its
incremental weighted false-positive cost. The exact condition for improving
the current score is

    c * (1 - a*DTI) > a*DTI*f

The familiar ``c > a*DTI`` is only the special case ``c + f = 1`` (one unit of
effective weighted cost, e.g. one isolated unit-valued prediction affecting only
one previously uncovered truth pixel). Redundant or overlapping predictions,
or one prediction covering several truth pixels, need the general condition.

Known-fault masking
-------------------
DrivenData staff (chrisk-dd) confirmed on 2026-09-16 that known USGS/INGENIOUS
fault pixels are excluded from evaluation, and that the Final Prize Round
re-scoring masks them too:
    https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516
and on 2026-09-23 that "new fault" means *any* fault pixel not already captured
by USGS/INGENIOUS, explicitly including newly mapped geometry (continuations,
splays, parallel strands) of an existing fault system:
    https://community.drivendata.org/t/where-do-you-draw-the-line/11536

We implement masking as a boolean ``known`` grid: those cells are removed from
the scored domain for *both* the truth set and the prediction mass.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA: float = 0.2
BETA: float = 0.8
RADIUS_PX: float = 3.0
EPS: float = 1e-12


def kernel(d, radius: float = RADIUS_PX):
    """Triangular kernel k(d) = max(1 - d/R, 0); d in pixels (1 px = 100 m)."""
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


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


def _prepare(pred, truth, valid, known):
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth)
    if pred.ndim != 2 or pred.shape != truth.shape:
        raise ValueError("prediction and truth must be equal-shaped 2-D grids")
    valid = np.ones(pred.shape, bool) if valid is None else np.asarray(valid, bool)
    known = np.zeros(pred.shape, bool) if known is None else np.asarray(known, bool)
    active = valid & ~known
    if active.sum() == 0:
        raise ValueError("empty scored domain")
    vals = pred[active]
    if not np.isfinite(vals).all() or (vals < 0).any() or (vals > 1).any():
        raise ValueError("predictions inside the scored domain must be finite and in [0, 1]")
    p = np.where(active, pred, 0.0)
    g = active & (truth > 0)
    return p, g, active


def dti(pred, truth, valid=None, known=None, alpha=ALPHA, beta=BETA, radius=RADIUS_PX):
    """Exact DTI for arbitrary soft predictions in [0, 1].

    Returns a dict with tp, fp, fn, n_truth, dti, coverage, mass.
    """
    p, g, active = _prepare(pred, truth, valid, known)
    H, W = p.shape
    n = int(g.sum())
    mass = float(p.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0,
                    dti=0.0, coverage=0.0, mass=mass)
    yy, xx = np.nonzero(g)
    credit = np.zeros(n, dtype=np.float64)
    # exact: max over the (2*ceil(R)+1)^2 neighbourhood of each truth pixel
    for dy, dx, k in _offsets(radius):
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        if not ok.any():
            continue
        credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    fn = float(n) - tp
    d = distance_transform_edt(~g)
    fp = float((p * (1.0 - kernel(d, radius))).sum())
    dti_v = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(dti_v),
                coverage=tp / n, mass=mass)


def dti_binary(pred_bool, truth, valid=None, known=None, alpha=ALPHA, beta=BETA, radius=RADIUS_PX):
    """Fast exact DTI for binary {0,1} predictions (Euclidean distance transforms)."""
    pb = np.asarray(pred_bool, bool)
    truth = np.asarray(truth, bool)
    valid_ = np.ones(pb.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pb.shape, bool) if known is None else np.asarray(known, bool)
    active = valid_ & ~known_
    p = pb & active
    g = truth & active
    n = int(g.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0,
                    dti=0.0, coverage=0.0, mass=float(p.sum()))
    if not p.any():
        return dict(tp=0.0, fp=0.0, fn=float(n), n_truth=n,
                    dti=0.0, coverage=0.0, mass=0.0)
    dp = distance_transform_edt(~p)
    tp = float(kernel(dp[g], radius).sum())
    fn = float(n) - tp
    dg = distance_transform_edt(~g)
    fp = float((1.0 - kernel(dg[p], radius)).sum())
    d = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(d), coverage=tp / n, mass=float(p.sum()))


def dti_bruteforce(pred, truth, valid=None, known=None, alpha=ALPHA, beta=BETA, radius=RADIUS_PX):
    """Literal O(|G|*|P|) transcription of the published equations — for unit tests only."""
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, bool)
    valid_ = np.ones(pred.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pred.shape, bool) if known is None else np.asarray(known, bool)
    active = valid_ & ~known_
    pred = np.where(active, pred, 0.0)
    g = np.argwhere(active & truth)
    xs = np.argwhere(pred > 0)
    tp = fn = 0.0
    for gy, gx in g:
        best = 0.0
        for xy, xx in xs:
            dd = float(np.hypot(xy - gy, xx - gx))
            if dd <= radius:
                best = max(best, pred[xy, xx] * float(kernel(dd, radius)))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for xy, xx in xs:
        best = 0.0
        for gy, gx in g:
            best = max(best, float(kernel(float(np.hypot(xy - gy, xx - gx)), radius)))
        fp += pred[xy, xx] * (1.0 - best)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=float(len(g)),
                dti=float(tp / (tp + alpha * fp + beta * fn + EPS)),
                coverage=tp / max(len(g), 1), mass=float(pred.sum()))


def breakeven_credit_bar(dti_value: float, alpha: float = ALPHA) -> float:
    """Special-case threshold c=alpha*DTI when an increment adds one unit to TP+FP.

    For a general prediction, use the exact paired changes (delta_tp, delta_fp):
    it improves DTI iff delta_tp*(1-alpha*DTI) > alpha*DTI*delta_fp.
    """
    return alpha * float(dti_value)


def marginal_dti_improves(dti_value: float, delta_tp: float, delta_fp: float,
                          alpha: float = ALPHA) -> bool:
    """Exact first-step test for whether a prediction increment raises DTI.

    ``delta_tp`` and ``delta_fp`` are the changes in the competition's weighted
    TP and FP terms; adding one prediction does not generally add one unit to
    either term.
    """
    d = float(dti_value)
    c = float(delta_tp)
    f = float(delta_fp)
    return c * (1.0 - alpha * d) > alpha * d * f


def implied_truth_size(tp: float, fp: float, dti_value: float, alpha=ALPHA, beta=BETA):
    """Invert identity (I2) for |G| given a measured (tp, fp, dti)."""
    return (tp * (1.0 - beta * dti_value) / (alpha * dti_value)) - tp - fp \
        if dti_value > 0 else float("nan")
