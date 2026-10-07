"""Inventory-context features: what the *visible* fault inventory implies about the next fault.

Motivation
----------
Every shipped feature in this repository is catalogue-independent.  That is the
right design for the *proxy* instrument (``gems51.holdout``), because there the
held-out truth **is** catalogue, so any function of the catalogue hands the
answer over — IR-51-LEAK-01.  It is the wrong design for the real task.  In the
real task the scorer's known set is the public USGS/INGENIOUS catalogue and the
truth is the faults that catalogue *missed*; the organizer states that "new
fault" explicitly includes newly mapped geometry (continuations, splays,
parallel strands) of an existing fault system
(https://community.drivendata.org/t/where-do-you-draw-the-line/11536).  Distance
to the nearest mapped trace, distance to a mapped *tip*, and the orientation of
the nearby trace are therefore informative, non-leaking inputs **whenever they
are computed from a known set that excludes the fold's own truth pixels**.

This module computes exactly those inputs from a caller-supplied ``known`` mask.
It contains no scoring, no thresholding and no catalogue of its own, so the same
function is honest under both instruments in this repository:

* ``gems51.holdout`` — pass ``known = catalogue & ~held_out_block``;
* off-catalogue A/B — pass ``known = A``.

Operators and sources
---------------------
* Euclidean distance transforms (``scipy.ndimage.distance_transform_edt``).
* Trace tips: a known pixel with at most one 8-connected known neighbour — the
  same definition already used for the H-C group in ``gems51.extras``.
* Local trace azimuth from the **structure tensor** of the known mask,
  J = G_sigma * (grad I)(grad I)^T, whose eigenvector of smaller eigenvalue is
  the line direction (Bigün & Granlund, "Optimal orientation detection of
  linear symmetry", CVPR 1987, doi:10.1109/CVPR.1987.289354; the same operator
  family used by Frangi et al. 1998, doi:10.1007/BFb0056195).
* Orientation agreement is computed in the doubled-angle representation
  ``cos 2Δ = cos2φ1 cos2φ2 + sin2φ1 sin2φ2``, which is invariant to the
  arbitrary sign of an eigenvector and to the π ambiguity of a line direction.
  The returned alignment is ``cos²Δ = (1 + cos 2Δ)/2`` in [0, 1] (1 = parallel).

Nothing here is a probability.  The features are rank-free continuous inputs to
the same gradient-boosted detector used everywhere else in the package.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

TWO_PI = 2.0 * np.pi


def tips_of(known: np.ndarray) -> np.ndarray:
    """Known pixels with at most one 8-connected known neighbour (trace ends)."""
    n = ndi.convolve(known.astype(np.float32), np.ones((3, 3), np.float32),
                     mode="constant") - 1.0
    return np.asarray(known, bool) & (n <= 1.0)


def _double_angle_orientation(field: np.ndarray, valid: np.ndarray,
                              sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Structure-tensor orientation of a scalar image, in doubled-angle form.

    Returns ``(cos2phi, sin2phi, coherence)`` where ``phi`` is the local
    *gradient* orientation (the line direction is ``phi + pi/2``) and
    ``coherence = (l1 - l2) / (l1 + l2)`` in [0, 1] is the linearity of the
    neighbourhood (0 = isotropic, 1 = a perfect line).
    """
    a = np.where(valid, np.nan_to_num(field, nan=0.0), 0.0).astype(np.float32)
    m = valid.astype(np.float32)
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1), mode="nearest")
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0), mode="nearest")
    w = ndi.gaussian_filter(m, sigma, order=0, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        gx = gx / np.maximum(w, 1e-6)
        gy = gy / np.maximum(w, 1e-6)
    gxx = ndi.gaussian_filter(gx * gx, sigma * 2.0, mode="nearest")
    gxy = ndi.gaussian_filter(gx * gy, sigma * 2.0, mode="nearest")
    gyy = ndi.gaussian_filter(gy * gy, sigma * 2.0, mode="nearest")
    tr = gxx + gyy
    disc = np.sqrt(np.maximum((gxx - gyy) ** 2 / 4.0 + gxy * gxy, 0.0))
    l1, l2 = tr / 2.0 + disc, tr / 2.0 - disc
    norm = np.maximum(l1 + np.abs(l2), 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        cos2 = (gxx - gyy) / np.maximum(2.0 * disc, 1e-12)
        sin2 = gxy / np.maximum(disc, 1e-12)
    cos2 = np.where(valid, np.nan_to_num(cos2), np.nan).astype(np.float32)
    sin2 = np.where(valid, np.nan_to_num(sin2), np.nan).astype(np.float32)
    coh = np.where(valid, (l1 - np.abs(l2)) / norm, np.nan).astype(np.float32)
    return cos2, sin2, np.clip(coh, 0.0, 1.0)


def tip_rays(known: np.ndarray, footprint: np.ndarray, length_px: int = 60,
             half_width_px: int = 0, min_neighbours: int = 1) -> np.ndarray:
    """Binary corridor of the mapped-trace directions *extrapolated beyond tips*.

    For every tip of ``known`` the local trace azimuth (structure tensor of the
    mask itself, ``sigma`` = 3 px) is resolved into the one of the two possible
    senses that points away from the mapped trace, then ``length_px`` steps are
    painted from the tip along that sense.  The result is the set of pixels a
    continuation of a mapped fault would occupy if it kept its strike — the
    corridor in which the organizer's definition of a "new fault" lives.

    Bias, stated explicitly: the corridor is straight.  A real continuation can
    curve, so this is a *feature*, never a hard mask; the detector decides how
    much to trust it and the holdout decides whether the detector was right.
    """
    known = np.asarray(known, bool)
    known = np.asarray(known, bool)
    footprint = np.asarray(footprint, bool)
    out = np.zeros(known.shape, bool)
    tips = tips_of(known) & footprint
    ys, xs = np.nonzero(tips)
    if ys.size == 0:
        return out
    cos2, sin2, _ = _double_angle_orientation(known.astype(np.float32), footprint, 3.0)
    # gradient direction -> line direction: rotate by +90 degrees in doubled angle
    lcos = -np.nan_to_num(cos2[ys, xs])
    lsin = -np.nan_to_num(sin2[ys, xs])
    ang = 0.5 * np.arctan2(lsin, lcos)
    dy, dx = np.sin(ang), np.cos(ang)
    H, W = known.shape
    t = np.arange(1.0, float(length_px) + 1.0, 1.0)
    for sgn in (1.0, -1.0):
        # the outward sense is the one whose 3 px and 6 px probes are both outside
        # the mapped mask; a normal tip has exactly one such sense.
        outside = np.ones(ys.size, bool)
        for step in (3.0, 6.0):
            py = ys + sgn * dy * step
            px = xs + sgn * dx * step
            inside = (py < 0) | (py >= H) | (px < 0) | (px >= W)
            iy = np.clip(np.round(py).astype(np.int64), 0, H - 1)
            ix = np.clip(np.round(px).astype(np.int64), 0, W - 1)
            probe = known[iy, ix] & ~inside
            outside &= ~probe
        keep = outside
        if not keep.any():
            continue
        py = (ys[keep][:, None] + sgn * dy[keep][:, None] * t[None, :]).ravel()
        px = (xs[keep][:, None] + sgn * dx[keep][:, None] * t[None, :]).ravel()
        iy = np.round(py).astype(np.int64)
        ix = np.round(px).astype(np.int64)
        okf = (iy >= 0) & (iy < H) & (ix >= 0) & (ix < W)
        out[iy[okf], ix[okf]] = True
        if half_width_px > 0:
            for oy in range(-half_width_px, half_width_px + 1):
                for ox in range(-half_width_px, half_width_px + 1):
                    if oy == 0 and ox == 0:
                        continue
                    jy, jx = iy + oy, ix + ox
                    okj = okf & (jy >= 0) & (jy < H) & (jx >= 0) & (jx < W)
                    out[jy[okj], jx[okj]] = True
        del py, px
    out &= footprint
    del min_neighbours
    return out


def inventory_features(known: np.ndarray, footprint: np.ndarray,
                       relief: np.ndarray | None = None,
                       tip_length_px: int = 60) -> dict[str, np.ndarray]:
    """The inventory-context feature group.

    Parameters
    ----------
    known : bool (H, W)
        The inventory the model is allowed to see: the full catalogue when
        building a submission, ``catalogue & ~held_out`` inside a proxy fold,
        ``A`` inside the off-catalogue A/B instrument.  It must never contain a
        scored truth pixel.
    footprint : bool (H, W)
        Competition data area.  Everything outside is NaN.
    relief : float32 (H, W), optional
        A scalar surface used for the orientation-agreement feature (the 1 m-DEM
        relief band is used in the shipped arm).  When absent the feature is NaN.

    Returns
    -------
    dict of float32 (H, W) with NaN outside ``footprint``:

    ``inv_d``            log1p Euclidean distance to the nearest known pixel (px)
    ``inv_dens21``       known-pixel fraction in a 2.1 km window
    ``inv_dens101``      known-pixel fraction in a 10.1 km window (system scale)
    ``inv_d_tip``        log1p distance to the nearest mapped trace tip
    ``inv_tip_ray``      exp(-d_ray / 4): "this pixel is on a mapped strike extension"
    ``inv_d_tip_ray``    log1p distance to the extrapolated-tip corridor
    ``inv_az_align``     cos^2 of the angle between the local relief lineament and
                         the local mapped-trace azimuth (1 = parallel)
    ``inv_tip_support``  tip corridor strength times scarp support (continuation
                         that also has a surface expression)
    """
    known = np.asarray(known, bool) & np.asarray(footprint, bool)
    foot = np.asarray(footprint, bool)
    out: dict[str, np.ndarray] = {}

    d = ndi.distance_transform_edt(~known).astype(np.float32)
    out["inv_d"] = np.where(foot, np.log1p(d), np.nan).astype(np.float32)
    del d

    for size, name in ((21, "inv_dens21"), (101, "inv_dens101")):
        dens = ndi.uniform_filter(known.astype(np.float32), size=size, mode="constant")
        out[name] = np.where(foot, dens, np.nan).astype(np.float32)
        del dens

    tips = tips_of(known) & foot
    d_tip = ndi.distance_transform_edt(~tips).astype(np.float32)
    out["inv_d_tip"] = np.where(foot, np.log1p(d_tip), np.nan).astype(np.float32)
    del d_tip

    rays = tip_rays(known, foot, length_px=tip_length_px)
    if rays.any():
        d_ray = ndi.distance_transform_edt(~rays).astype(np.float32)
        out["inv_tip_ray"] = np.where(foot, np.exp(-d_ray / 4.0), np.nan).astype(np.float32)
        out["inv_d_tip_ray"] = np.where(foot, np.log1p(d_ray), np.nan).astype(np.float32)
        del d_ray
    else:
        out["inv_tip_ray"] = np.where(foot, 0.0, np.nan).astype(np.float32)
        out["inv_d_tip_ray"] = np.where(foot, 0.0, np.nan).astype(np.float32)
    del rays

    if relief is not None:
        r = np.asarray(relief, dtype=np.float32)
        m_known = known | (ndi.binary_dilation(known, np.ones((5, 5), bool)))
        kcos2, ksin2, _ = _double_angle_orientation(known.astype(np.float32), foot, 3.0)
        rcos2, rsin2, _ = _double_angle_orientation(r, foot & np.isfinite(r), 3.0)
        dot = kcos2 * rcos2 + ksin2 * rsin2            # cos 2*delta
        align = 0.5 * (1.0 + np.nan_to_num(dot, nan=0.0))
        align = np.where(foot & np.isfinite(kcos2) & np.isfinite(rcos2), align, np.nan)
        out["inv_az_align"] = align.astype(np.float32)
        del kcos2, ksin2, rcos2, rsin2, dot
        support = np.where(foot & np.isfinite(r), r, np.nan)
        finite = np.isfinite(support)
        if finite.any():
            v = support[finite]
            q = np.percentile(v, [5, 95])
            sc = np.clip((support - q[0]) / max(q[1] - q[0], 1e-9), 0.0, 1.0)
        else:
            sc = np.zeros_like(support)
        out["inv_tip_support"] = (np.nan_to_num(out["inv_tip_ray"]) * np.nan_to_num(sc)).astype(np.float32)
        out["inv_tip_support"] = np.where(foot, out["inv_tip_support"], np.nan).astype(np.float32)
        del support, sc, m_known
    else:
        nan = np.where(foot, np.nan, np.nan).astype(np.float32)
        out["inv_az_align"] = nan.copy()
        out["inv_tip_support"] = nan.copy()

    for k, v in out.items():
        v[~foot] = np.nan
        out[k] = v.astype(np.float32)
    return out


FEATURE_NAMES = ("inv_d", "inv_dens21", "inv_dens101", "inv_d_tip", "inv_tip_ray",
                 "inv_d_tip_ray", "inv_az_align", "inv_tip_support")
