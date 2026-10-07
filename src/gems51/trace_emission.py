"""Strike-coherent trace emission (STE) — turning a pixel-wise belief field into dots
that sit *on a line* instead of *inside a blob*.

Why this module exists
----------------------
Every detector in this repository scores pixels independently, so its output is a
field of blobs.  The scored object, however, is a *fault trace*: a thin, locally
straight, kilometre-scale curve.  Two consequences follow directly from the
official metric (page 967, verbatim in ``gems51.metric``):

    DTI = TP_w / (alpha*(TP_w + FP_w) + beta*|G|),  alpha = 0.2, beta = 0.8

1.  ``TP_w`` is a sum over the *truth* and takes the maximum over nearby
    predictions, so a second dot on the same 3-px neighbourhood of a truth pixel
    earns (almost) nothing while costing a full unit of mass.  Dots must be
    spread *along* a trace, never stacked across it.
2.  A dot placed on the crest of a correct lineament earns kernel credit from
    the truth pixels at distance 0, 1 and 2 px along the trace
    (1 + 2/3 + 1/3 on each side).  A dot placed 2 px off the crest earns at
    most k(2) = 1/3 from the nearest truth pixel.  Localisation across strike is
    therefore worth up to a factor of ~3 in credit per unit mass.

The incumbent emission rule (``gems51.emission.nms_dots``) applies *isotropic*
non-maximum suppression: it takes the global top pixel and blanks a disc of
radius 2.4 px.  On a blobby field that places dots on the shoulders of blobs and
spends several dots across the width of one structure.  This module replaces it
with three steps that are each standard practice in linear-feature extraction:

    (a) **Ridge / vesselness filtering** of the belief field at several scales.
        Frangi, Niessen, Vincken & Viergever (1998), "Multiscale vessel
        enhancement filtering", MICCAI 1998, LNCS 1496, 130-137,
        doi:10.1007/BFb0056195.  A 2-D bright ridge has Hessian eigenvalues
        lambda_1 << 0 (across strike) and lambda_2 ~ 0 (along strike); the
        vesselness response rewards exactly that anisotropy.

    (b) **Along-strike line integration** (a local Radon / line-accumulator
        step).  Deans, *The Radon Transform and Some of Its Applications*
        (Wiley, 1983); the discrete-orientation line-accumulator form used here
        is the standard "line detector" of Vanderbrug, "Line detection in
        satellite imagery", IEEE Trans. Geoscience Electronics 14(1), 37-44
        (1976), doi:10.1109/TGE.1976.294466.  Continuity over kilometres is the
        single strongest prior that separates a mapped fault from noise and it
        is a property no pixel-wise classifier can express.

    (c) **Across-strike non-maximum suppression** — the thinning step of Canny,
        "A computational approach to edge detection", IEEE TPAMI 8(6), 679-698
        (1986), doi:10.1109/TPAMI.1986.4767851 — followed by greedy spacing of
        dots *along* the surviving crest at the kernel support R = 3 px.

Nothing here is tuned by hand: every parameter is swept on the spatially blocked
holdout by ``scripts/run_emission_geometry.py`` and the winning setting is the
one written into the submission builder.

All public functions are pure NumPy/SciPy and operate on a single float32 grid
with NaN outside the footprint.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "normalised_gaussian",
    "ridge_response",
    "line_accumulate",
    "strike_coherent_score",
    "across_strike_thin",
    "spaced_dots",
    "emit",
]


# --------------------------------------------------------------------------- #
# low level
# --------------------------------------------------------------------------- #
def normalised_gaussian(a: np.ndarray, mask: np.ndarray, sigma: float,
                        order=(0, 0)) -> np.ndarray:
    """Normalised-convolution Gaussian (derivative) filter.

    Knutsson & Westin (1993), "Normalized and differential convolution",
    CVPR 1993, 515-523, doi:10.1109/CVPR.1993.341081.  Convolving ``a*mask`` and
    ``mask`` separately and dividing gives the local weighted least-squares
    estimate, instead of smearing zeros across data gaps.
    """
    a0 = np.where(mask, np.nan_to_num(a, nan=0.0), 0.0).astype(np.float32)
    num = ndi.gaussian_filter(a0, sigma, order=order, mode="nearest")
    den = ndi.gaussian_filter(mask.astype(np.float32), sigma, order=0, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    out[den < 0.2] = 0.0
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def ridge_response(field: np.ndarray, mask: np.ndarray, sigma: float,
                   beta: float = 0.5):
    """2-D Frangi vesselness of a *bright* ridge, plus its along-strike direction.

    Returns ``(v, theta)`` where ``v`` in [0, 1] is the ridge response and
    ``theta`` is the orientation of the ridge axis in radians (the eigenvector
    of the Hessian eigenvalue with the smaller magnitude).

    Frangi et al. 1998 (doi:10.1007/BFb0056195), equations (13)-(15) in 2-D:
        R_B = |lambda_2| / |lambda_1|      (blobness; 0 on an ideal line)
        S   = sqrt(lambda_1^2 + lambda_2^2) (structureness; 0 on flat background)
        V   = 0                                   if lambda_1 > 0
              exp(-R_B^2 / 2 beta^2) * (1 - exp(-S^2 / 2 c^2))  otherwise
    with ``c`` set, as Frangi recommends, to half the maximum Hessian norm of
    the image so the filter is scale-free with respect to the belief field's
    arbitrary units.
    """
    s2 = float(sigma) ** 2
    fxx = s2 * normalised_gaussian(field, mask, sigma, order=(0, 2))
    fyy = s2 * normalised_gaussian(field, mask, sigma, order=(2, 0))
    fxy = s2 * normalised_gaussian(field, mask, sigma, order=(1, 1))

    tr = fxx + fyy
    det = fxx * fyy - fxy * fxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    e1 = tr / 2.0 + disc          # algebraically larger eigenvalue
    e2 = tr / 2.0 - disc          # algebraically smaller eigenvalue

    # order by |.| : lam1 is the large-magnitude one (across strike)
    swap = np.abs(e2) >= np.abs(e1)
    lam1 = np.where(swap, e2, e1)
    lam2 = np.where(swap, e1, e2)

    rb = np.abs(lam2) / (np.abs(lam1) + 1e-12)
    s = np.sqrt(lam1 * lam1 + lam2 * lam2)
    inside = s[mask]
    c = 0.5 * float(np.percentile(inside, 99.5)) if inside.size else 1.0
    c = max(c, 1e-9)
    v = np.exp(-(rb * rb) / (2.0 * beta * beta)) * (1.0 - np.exp(-(s * s) / (2.0 * c * c)))
    v = np.where(lam1 < 0, v, 0.0)            # bright ridge only
    v = np.where(mask, v, 0.0).astype(np.float32)

    # eigenvector for lam1 (across-strike normal); the ridge axis is perpendicular.
    # For [[fxx, fxy],[fxy, fyy]] an eigenvector of eigenvalue L is (fxy, L - fxx).
    nx = fxy
    ny = lam1 - fxx
    nrm = np.hypot(nx, ny) + 1e-12
    nx, ny = nx / nrm, ny / nrm
    theta = np.arctan2(nx, -ny)               # rotate the normal by 90 deg
    return v, theta.astype(np.float32)


def _line_offsets(length: int, k: int, n_orient: int) -> list[tuple[int, int]]:
    """Integer (dy, dx) offsets of a straight segment of ``length`` px, orientation k."""
    r = length // 2
    ang = np.pi * k / n_orient
    dy, dx = float(np.sin(ang)), float(np.cos(ang))
    seen = []
    for t in np.linspace(-r, r, 4 * r + 1):
        off = (int(round(t * dy)), int(round(t * dx)))
        if off not in seen:
            seen.append(off)
    return seen


def line_accumulate(v: np.ndarray, length: int = 9, n_orient: int = 12):
    """Max over orientations of the mean of ``v`` along a straight segment.

    This is the discrete line-accumulator of Vanderbrug (1976)
    (doi:10.1109/TGE.1976.294466): a pixel scores high only if the ridge
    response stays high for ``length`` pixels in *some* single direction.
    Implemented as shift-and-add (one pass per sample point) rather than a dense
    convolution, because the line kernel is 1-D sparse inside a 2-D window.

    Returns ``(acc, best_angle)`` with ``best_angle`` in radians.
    """
    v = np.ascontiguousarray(v, dtype=np.float32)
    best = np.full(v.shape, -np.inf, dtype=np.float32)
    arg = np.zeros(v.shape, dtype=np.int8)
    acc = np.empty(v.shape, dtype=np.float32)
    for k in range(n_orient):
        offs = _line_offsets(length, k, n_orient)
        acc[:] = 0.0
        for dy, dx in offs:
            # shift v by (dy, dx) with zero padding; edge effects are immaterial
            # because the footprint boundary is already masked out of v
            ys0, ys1 = max(0, dy), min(v.shape[0], v.shape[0] + dy)
            xs0, xs1 = max(0, dx), min(v.shape[1], v.shape[1] + dx)
            acc[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx] += v[ys0:ys1, xs0:xs1]
        acc /= float(len(offs))
        better = acc > best
        np.copyto(best, acc, where=better)
        np.copyto(arg, np.int8(k), where=better)
    ang = (np.pi * arg.astype(np.float32) / n_orient).astype(np.float32)
    return np.maximum(best, 0.0).astype(np.float32), ang


def strike_coherent_score(field: np.ndarray, mask: np.ndarray,
                          sigmas=(1.0, 2.0, 3.5), line_len: int = 9,
                          n_orient: int = 12, w_cont: float = 0.5):
    """Combine belief, multi-scale ridgeness and along-strike continuity.

    ``score = rank(field) ** (1 - w_cont) * rank(continuity) ** w_cont``

    Rank (empirical-CDF) transforms are used so the geometric blend is
    scale-free: the belief field and the continuity accumulator have
    incomparable units, and a rank blend is the only combination that does not
    silently weight one by its variance.

    Returns ``(score, theta)`` where theta is the along-strike angle used by the
    thinning step.
    """
    f = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    v = np.zeros(f.shape, dtype=np.float32)
    th = np.zeros(f.shape, dtype=np.float32)
    for s in sigmas:
        vi, ti = ridge_response(f, mask, s)
        take = vi > v
        v = np.where(take, vi, v)
        th = np.where(take, ti, th)
    acc, ang = line_accumulate(v, length=line_len, n_orient=n_orient)
    # the accumulator's own winning orientation is a more robust strike estimate
    # than the single-pixel Hessian where the ridge is weak
    theta = np.where(acc > 0, ang, th).astype(np.float32)

    rf = _rank01(f, mask)
    ra = _rank01(acc, mask)
    w = float(np.clip(w_cont, 0.0, 1.0))
    score = (rf ** (1.0 - w)) * (ra ** w)
    score = np.where(mask, score, 0.0).astype(np.float32)
    return score, theta


def _rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Empirical-CDF transform to (0, 1] computed on ``mask``; 0 elsewhere."""
    out = np.zeros(a.shape, dtype=np.float32)
    v = a[mask]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float32)
    ranks[order] = (np.arange(1, v.size + 1, dtype=np.float32) / v.size)
    out[mask] = ranks
    return out


def across_strike_thin(score: np.ndarray, theta: np.ndarray, mask: np.ndarray,
                       step: float = 1.0) -> np.ndarray:
    """Canny-style non-maximum suppression *across* the local strike.

    Keep a pixel only if its score is >= the bilinearly interpolated score at
    +/- ``step`` px along the across-strike normal.  Canny 1986
    (doi:10.1109/TPAMI.1986.4767851).
    """
    H, W = score.shape
    # strike direction is (cos th, sin th) in (x, y); the across-strike normal
    # is that vector rotated by 90 degrees, i.e. (-sin th, cos th).
    nx = (-np.sin(theta) * step).astype(np.float32)
    ny = (np.cos(theta) * step).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    keep = np.ones(score.shape, bool)
    for sgn in (+1.0, -1.0):
        sy = np.clip(yy + sgn * ny, 0, H - 1)
        sx = np.clip(xx + sgn * nx, 0, W - 1)
        samp = ndi.map_coordinates(score, [sy, sx], order=1, mode="nearest")
        keep &= score >= samp
    return keep & mask


def spaced_dots(score: np.ndarray, candidate: np.ndarray, n_dots: int,
                spacing: float = 3.0):
    """Greedy highest-score-first selection with a circular exclusion of ``spacing`` px.

    Applied to an already-thinned crest, the circular exclusion becomes an
    *along-trace* spacing, which is what the metric wants: with spacing equal to
    the kernel support R = 3 px the dots tile the trace with no overlap of their
    credit cones and no gap that earns zero.
    """
    H, W = score.shape
    cand = np.asarray(candidate, bool) & np.isfinite(score)
    idx = np.flatnonzero(cand.ravel())
    if idx.size == 0 or n_dots <= 0:
        return np.zeros(0, np.int32), np.zeros(0, np.int32)
    vals = score.ravel()[idx]
    order = idx[np.argsort(vals, kind="stable")[::-1]]

    # Work in a padded occupancy buffer so the inner loop needs no bounds checks.
    r = int(np.ceil(spacing))
    PW = W + 2 * r
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    nb = (dy * dy + dx * dx) <= spacing * spacing
    flat_offs = (dy[nb].astype(np.int64) * PW + dx[nb].astype(np.int64))

    blocked = np.zeros((H + 2 * r) * PW, dtype=bool)
    # map an unpadded flat index to the padded one
    pad_idx = (order // W + r) * PW + (order % W + r)

    ys = np.empty(n_dots, np.int32)
    xs = np.empty(n_dots, np.int32)
    taken = 0
    order_list = order.tolist()
    pad_list = pad_idx.tolist()
    for i in range(len(order_list)):
        p = pad_list[i]
        if blocked[p]:
            continue
        f = order_list[i]
        ys[taken] = f // W
        xs[taken] = f % W
        taken += 1
        blocked[p + flat_offs] = True
        if taken >= n_dots:
            break
    return ys[:taken], xs[:taken]


def emit(field: np.ndarray, candidate: np.ndarray, n_dots: int,
         sigmas=(1.0, 2.0, 3.5), line_len: int = 9, n_orient: int = 12,
         w_cont: float = 0.5, spacing: float = 3.0, thin: bool = True,
         thin_step: float = 1.0, score_mask: np.ndarray | None = None):
    """Full strike-coherent emission.

    ``field``      belief field (NaN outside footprint)
    ``candidate``  bool grid of pixels that are legal to emit on
    ``n_dots``     mass budget
    ``score_mask`` domain on which the ridge/continuity transforms are computed
                   (defaults to the finite part of ``field``); pass the footprint
                   so the transforms are not truncated at the candidate boundary.

    Returns ``(ys, xs, score, theta)``.
    """
    dom = np.isfinite(field) if score_mask is None else np.asarray(score_mask, bool)
    score, theta = strike_coherent_score(field, dom, sigmas=sigmas, line_len=line_len,
                                         n_orient=n_orient, w_cont=w_cont)
    cand = np.asarray(candidate, bool) & dom
    if thin:
        crest = across_strike_thin(score, theta, dom, step=thin_step)
        cand_thin = cand & crest
        # never let thinning starve the budget
        if int(cand_thin.sum()) >= n_dots:
            cand = cand_thin
    ys, xs = spaced_dots(score, cand, n_dots, spacing=spacing)
    return ys, xs, score, theta
