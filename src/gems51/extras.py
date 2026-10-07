"""Candidate-hypothesis feature groups (the things we have *not* tried before).

Each builder returns a dict  name -> (H, W) float32 grid, NaN outside the
footprint.  Groups are added to the baseline physical stack one at a time so the
holdout can attribute any change in DTI to that specific hypothesis.

Static groups do not depend on the catalogue and are computed once.
Catalogue-dependent groups must be recomputed per fold from ``fold.known`` only,
otherwise the held-out truth leaks into the model (IR-51-LEAK-01).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .grid import GRID
from .stack import lineament_bank

H, W = GRID.shape


def _edge_bank(field: np.ndarray, mask: np.ndarray, label: str, scales=(1.5, 4.0)):
    out = {}
    for s in scales:
        edge, crest, lin = lineament_bank(field, mask, s)
        t = int(s * 10)
        out[f"{label}_s{t:02d}_edge"] = edge
        out[f"{label}_s{t:02d}_crest"] = crest
        out[f"{label}_s{t:02d}_lin"] = lin
    return out


def cross_physics_edge_features(magnetic: np.ndarray, gravity: np.ndarray,
                                mask: np.ndarray, sigma: float = 2.0) -> dict[str, np.ndarray]:
    """Return edge-normal agreement and joint edge strength for two scalar fields.

    The normals are unoriented, so reversing the sign of one anomaly does not
    change its geological edge direction.  ``coedge`` is the geometric mean of
    robustly scaled gradient magnitudes multiplied by |cos(theta)|.  The scale
    denominators are the 95th percentiles of deterministic, evenly subsampled
    valid pixels; no labels or holdout truths enter the transform.
    """
    mask = np.asarray(mask, dtype=bool)
    mag = np.asarray(magnetic, dtype=np.float32)
    grav = np.asarray(gravity, dtype=np.float32)
    valid = mask & np.isfinite(mag) & np.isfinite(grav)
    gx_m = _ncd(mag, valid, sigma, [0, 1])
    gy_m = _ncd(mag, valid, sigma, [1, 0])
    gx_g = _ncd(grav, valid, sigma, [0, 1])
    gy_g = _ncd(grav, valid, sigma, [1, 0])
    norm_m = np.hypot(gx_m, gy_m)
    norm_g = np.hypot(gx_g, gy_g)
    denom = np.maximum(norm_m * norm_g, 1e-12)
    alignment = np.clip(np.abs(gx_m * gx_g + gy_m * gy_g) / denom, 0.0, 1.0)
    alignment[(norm_m <= 1e-8) | (norm_g <= 1e-8)] = 0.0

    def robust_p95(v):
        ok = valid & np.isfinite(v)
        vals = v[ok]
        if vals.size == 0:
            return 0.0
        stride = max(1, int(np.ceil(vals.size / 200_000)))
        return float(np.quantile(vals[::stride], 0.95))

    scale_m = robust_p95(norm_m)
    scale_g = robust_p95(norm_g)
    if scale_m <= 1e-12 or scale_g <= 1e-12:
        coedge = np.zeros(mag.shape, dtype=np.float32)
    else:
        em = np.clip(norm_m / scale_m, 0.0, 1.0)
        eg = np.clip(norm_g / scale_g, 0.0, 1.0)
        coedge = np.sqrt(em * eg) * alignment
    alignment = alignment.astype(np.float32)
    coedge = coedge.astype(np.float32)
    alignment[~valid] = np.nan
    coedge[~valid] = np.nan
    return {"alignment": alignment, "coedge": coedge}


def build_static(stack, footprint: np.ndarray) -> dict:
    """Hypothesis groups that use no catalogue information."""
    g = {}
    get = lambda n: np.asarray(stack.data[stack.names.index(n)], dtype=np.float32)

    # ---------------------------------------------------------------- H-E
    # Basin-bounding (range-front) faults.  A Great Basin range front is a step
    # in the depth-to-basement surface, a gravity gradient, and a resistivity
    # contrast between bedrock and basin fill -- three *independent* expressions
    # of the same buried structure.  A buried or blind range-front fault can be
    # almost invisible in topography while being obvious here, which is exactly
    # the class of structure a scarp-based catalogue misses.
    for src, lab in [("comp_depth_to_base_surf", "base"),
                     ("comp_cond_surf", "cond")]:
        f = get(src)
        m = np.isfinite(f) & footprint
        g.update(_edge_bank(f, m, lab, scales=(1.5, 4.0)))
    grav = get("comp_iso_grav_anom")
    m = np.isfinite(grav) & footprint
    g.update(_edge_bank(grav, m, "grav2", scales=(4.0,)))

    # depth-to-basement step *asymmetry*: a range front is a monotone step, so
    # the along-profile first derivative keeps one sign over kilometres.
    base = get("comp_depth_to_base_surf")
    m = np.isfinite(base) & footprint
    gx = _ncd(base, m, 3.0, [0, 1])
    gy = _ncd(base, m, 3.0, [1, 0])
    mag = np.hypot(gx, gy)
    # coherence of the step direction in a 9x9 window (|mean vector| / mean |vector|)
    ux = np.where(mag > 0, gx / np.maximum(mag, 1e-9), 0.0)
    uy = np.where(mag > 0, gy / np.maximum(mag, 1e-9), 0.0)
    ux = np.where(m, ux, 0.0); uy = np.where(m, uy, 0.0)
    wgt = np.where(m, mag, 0.0)
    k = np.ones((9, 9), np.float32)
    sx = ndi.convolve(ux * wgt, k, mode="nearest")
    sy = ndi.convolve(uy * wgt, k, mode="nearest")
    sw = ndi.convolve(wgt, k, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        coh = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
    coh[~(m.astype(bool))] = np.nan
    g["base_step_coh09"] = coh.astype(np.float32)

    # ---------------------------------------------------------------- H-X1
    # Cross-physics edge-normal concordance.  A buried fault/contact can produce
    # a magnetic edge and a density/gravity edge even where relief is weak.  The
    # *new* signal is not either edge magnitude by itself (both are already in
    # the base stack), but the local agreement of their unoriented edge normals.
    # Derivatives are computed from the rank-normalised competition bands so
    # feature scale is comparable and robust to the source units.  Two scales
    # (200 m and 500 m) are preregistered in knowledge/preregistration-2026-10-07.md.
    mag = get("comp_tmi")
    grav = get("comp_iso_grav_anom")
    common = footprint & np.isfinite(mag) & np.isfinite(grav)
    for sigma in (2.0, 5.0):
        feats = cross_physics_edge_features(mag, grav, common, sigma=sigma)
        suffix = f"s{int(sigma * 10):02d}"
        g[f"mg_alignment_{suffix}"] = feats["alignment"]
        g[f"mg_coedge_{suffix}"] = feats["coedge"]

    # ---------------------------------------------------------------- H-D
    # Scarp-facing coherence.  A through-going range-front fault has one facing
    # direction for kilometres; noise, drainages and dune fields do not.  We
    # measure |mean unit gradient| / mean |gradient| of the 1 m-DEM relief and of
    # detrended elevation over a 9x9 window -> high where a single scarp
    # dominates the window, regardless of how small that scarp is.
    for src, lab in [("lid_relief", "lidrel"), ("comp_det_elev", "detelev")]:
        f = get(src)
        m = np.isfinite(f) & footprint
        gx = _ncd(f, m, 2.0, [0, 1])
        gy = _ncd(f, m, 2.0, [1, 0])
        mag = np.hypot(gx, gy)
        ok = m & np.isfinite(mag) & (mag > 0)
        ux = np.where(ok, gx / np.maximum(mag, 1e-9), 0.0)
        uy = np.where(ok, gy / np.maximum(mag, 1e-9), 0.0)
        wgt = np.where(ok, mag, 0.0)
        sx = ndi.convolve(ux * wgt, k, mode="nearest")
        sy = ndi.convolve(uy * wgt, k, mode="nearest")
        sw = ndi.convolve(wgt, k, mode="nearest")
        with np.errstate(divide="ignore", invalid="ignore"):
            coh = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
        coh[~m] = np.nan
        g[f"{lab}_facecoh09"] = coh.astype(np.float32)
        # and the same at a longer 21x21 window -> tests *persistence*
        k21 = np.ones((21, 21), np.float32)
        sx = ndi.convolve(ux * wgt, k21, mode="nearest")
        sy = ndi.convolve(uy * wgt, k21, mode="nearest")
        sw = ndi.convolve(wgt, k21, mode="nearest")
        with np.errstate(divide="ignore", invalid="ignore"):
            coh21 = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
        coh21[~m] = np.nan
        g[f"{lab}_facecoh21"] = coh21.astype(np.float32)

    # ---------------------------------------------------------------- H-51-M
    # Cross-scale crest coincidence (session 2026-10-07, knowledge/02 §3 rank 2)
    _build_xscale(g, get, footprint)

    return g


def _rank_over(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1] over ``valid`` (monotone, 0 where invalid)."""
    v = a[valid]
    out = np.zeros(a.shape, np.float32)
    if v.size == 0:
        return out
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[valid] = (order.astype(np.float64) / max(1, v.size - 1)).astype(np.float32)
    return out


def _build_xscale(g: dict, get, footprint: np.ndarray) -> None:
    """H-51-M — cross-scale crest coincidence (session 2026-10-07).

    A fine crest (sigma 1.5 px) that sits exactly on the axis of the coarse
    crest (sigma 4 px) marks the trace of a through-going structure; an
    asymmetric scarp displaces the single-scale response off-axis, so the
    positional agreement of the two scales is a localisation signal no shipped
    feature carries.  Implemented as Q(fine crest) * exp(-d/1.5) where d is the
    distance to the top-2% coarse-crest set, plus the symmetric rank-min
    agreement min(Q_fine, Q_coarse).
    """
    det = get("comp_det_elev")
    m = np.isfinite(det) & footprint
    _e, crest15, _l = lineament_bank(det, m, 1.5)
    _e, crest40, _l2 = lineament_bank(det, m, 4.0)
    m15 = m & np.isfinite(crest15)
    m40 = m & np.isfinite(crest40)
    thr = np.nanpercentile(crest40[m40], 98.0)
    d40 = ndi.distance_transform_edt(~(m40 & (crest40 >= thr))).astype(np.float32)
    q15 = _rank_over(crest15, m15)
    q40 = _rank_over(crest40, m40)
    near = np.exp(-d40 / 1.5).astype(np.float32)
    g["xscale_coincide_det"] = (q15 * near).astype(np.float32)
    g["xscale_minrank_det"] = np.minimum(q15, q40).astype(np.float32)

    lid = get("lid_relief")
    ml = np.isfinite(lid) & footprint
    _e, lcrest15, _l3 = lineament_bank(lid, ml, 1.5)
    ml15 = ml & np.isfinite(lcrest15)
    ql15 = _rank_over(lcrest15, ml15)
    g["xscale_coincide_lid"] = (ql15 * near).astype(np.float32)


def _ncd(a, mask, sigma, order):
    from .stack import _nc_deriv
    return _nc_deriv(a, mask, sigma, order)


def build_catalogue_dependent(stack, footprint: np.ndarray, known: np.ndarray) -> dict:
    """Hypothesis groups that use only the *known* catalogue of this fold.

    H-C: continuation beyond a mapped trace tip.  The organizer confirmed that
    "new fault" includes newly mapped geometry of an existing fault system
    (https://community.drivendata.org/t/where-do-you-draw-the-line/11536), so the
    corridor just beyond the endpoint of a mapped trace is a priori the single
    cheapest place to look for an unmapped one.
    """
    g = {}
    # trace tips = catalogue pixels with exactly one 8-neighbour catalogue pixel
    nb = ndi.convolve(known.astype(np.float32), np.ones((3, 3), np.float32),
                      mode="constant") - 1.0
    tips = known & (nb <= 1.0)
    d_tip = ndi.distance_transform_edt(~tips).astype(np.float32)
    g["d_tip"] = np.log1p(d_tip).astype(np.float32)
    return g


def tips_of(known: np.ndarray) -> np.ndarray:
    nb = ndi.convolve(known.astype(np.float32), np.ones((3, 3), np.float32),
                      mode="constant") - 1.0
    return known & (nb <= 1.0)
