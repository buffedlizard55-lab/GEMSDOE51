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
from .stack import _nc_deriv, lineament_bank
from .intersections import axial_intersection_score
from .features import COMPETITION_BANDS

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

    return g


def build_magnetic_gravity_intersections(stack, footprint: np.ndarray,
                                         scales=(4.0, 8.0)) -> dict:
    """High-angle co-located edges in TMI and isostatic gravity.

    The two source surfaces are robustly standardized competition bands, read
    from the prepared mirror. At each Gaussian scale, axial orientation
    discordance is weighted by both edge magnitudes (each scaled by its
    footprint 95th percentile). The returned operator is therefore high only
    where *both* independent potential-field surfaces have strong, nearly
    orthogonal boundaries. 100 m pixels make the scales 400 m and 800 m.

    No catalogue or holdout labels enter this transform. The feature is a
    prospectivity/structure proxy, not evidence that an edge is a fault.
    """
    from pathlib import Path

    names = [b[0] for b in COMPETITION_BANDS]
    shape = (len(names), *GRID.shape)
    z = np.memmap(Path(stack.dir) / "comp_z.dat", dtype=np.float32,
                  mode="r", shape=shape)
    tmi = z[names.index("tmi")]
    gravity = z[names.index("iso_grav_anom")]
    mt = np.isfinite(tmi) & footprint
    mg = np.isfinite(gravity) & footprint
    out = {}

    for sigma in scales:
        tx = _nc_deriv(tmi, mt, sigma, [0, 1])
        ty = _nc_deriv(tmi, mt, sigma, [1, 0])
        gx = _nc_deriv(gravity, mg, sigma, [0, 1])
        gy = _nc_deriv(gravity, mg, sigma, [1, 0])
        tm = np.hypot(tx, ty)
        gm = np.hypot(gx, gy)
        valid = (footprint & np.isfinite(tx) & np.isfinite(ty)
                 & np.isfinite(gx) & np.isfinite(gy) & np.isfinite(tm)
                 & np.isfinite(gm))
        if not valid.any():
            raise ValueError(f"no valid TMI/gravity gradients at sigma={sigma}")
        tscale = float(np.percentile(tm[valid], 95))
        gscale = float(np.percentile(gm[valid], 95))
        _, score = axial_intersection_score(tx, ty, gx, gy, tscale, gscale)
        score[~valid] = np.nan
        score[~footprint] = np.nan
        out[f"tmi_grav_xing_s{int(sigma * 100):03d}"] = score
        del tx, ty, gx, gy, tm, gm, valid, score

    del z
    return out


def _ncd(a, mask, sigma, order):
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
