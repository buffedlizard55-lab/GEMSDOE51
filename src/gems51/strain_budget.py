"""Stage 1: geodetic strain-budget deficit over broad tiles.

The hypothesis
--------------
Where the geodetic strain rate exceeds what the mapped faults' slip rates can
accommodate, the catalogue is likelier to be missing structures.  Used strictly
as a coarse first stage: it approves *tiles*, it never places a point.

Published moment-tensor summation (Kreemer et al. 2000, Eq. 3, *Earth Planets and Space* 52, 765–770):

    eps_dot_ij = (1 / (2 A)) * sum_k [ L_k * u_dot_k / sin(delta_k) ] * m_ij^k

where ``m_ij^k`` is the unit moment tensor defined by fault orientation and unit
slip vector, ``L_k`` is trace length, ``u_dot_k`` is slip rate, and ``delta_k``
is dip. Public source:
https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf

For ``m_ij = s_i n_j + s_j n_i``, the 2-D horizontal components under pure-mode
assumptions are:

* Pure strike slip on a vertical plane, with total along-strike rate:
  ``eps_dot_sn = L * u_dot / (2 A)``; right- and left-lateral senses have
  opposite shear signs.
* Pure dip slip with total fault-plane rate: horizontal normal component
  ``L * u_dot * cos(delta) / A``.
* If the tabulated rate is instead vertical displacement ``u_dot_v``, total
  dip-slip rate is ``u_dot_v / sin(delta)`` and that component is
  ``L * u_dot_v * cot(delta) / A``.

The GDR/QFaults table has ``slip_rate``, ``slip_sense`` and ``dip_direct`` but no
numeric dip angle or rake. ``dip_direct`` is an azimuth/direction of dip, **not**
a dip angle. The rate convention (total fault-plane slip versus vertical
displacement) is not established by the local CSV or its source metadata, so
``BudgetConfig.rate_convention`` supports both. Pure normal and pure
strike-slip motion, 60° normal-fault dip, 90° strike-slip dip, nearest-centroid
rate assignment, and the treatment of missing slip sense are explicit
assumptions—not measurements. Values are converted from the source table's
rate field using the documented working unit (mm/yr) to m/yr; their physical
interpretation is not independently verified here.

The geodetic layers are highly correlated but satisfy no exact algebraic
identity, so the precise invariant convention behind ``geod_2ndinv`` cannot be
recovered. Stage 1 is therefore a coarse-tile ranking diagnostic in quantile
space, never an absolute geodetic calibration or fine-scale point placer. See
``evidence/stage1_formula_audit.json`` for the paired convention sensitivity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi

from .grid import GRID

H_PX, W_PX = GRID.shape
PIXEL_M = 100.0
MU = 30e9            # Pa, crustal shear modulus (cancels; kept for transparency)
H_SEIS = 15_000.0    # m, seismogenic thickness (sensitivity: 10 km and 20 km)
DIP_BY_SENSE = {"N": 60.0, "RL": 90.0, "LL": 90.0}
DIP_DEFAULT = 60.0   # "Unspecified" -> Basin and Range normal faulting


@dataclass
class BudgetConfig:
    tile_px: int = 100          # 100 px = 10 km
    h_seis_m: float = H_SEIS
    dip_default: float = DIP_DEFAULT
    max_assign_px: float = 60.0  # nearest-trace slip-rate assignment radius
    invariant: str = "II"       # "II" : sqrt(exx^2 + eyy^2 + 2 exy^2)
    rate_convention: str = "vertical"  # "vertical" or "fault_plane"; source convention unresolved
    assume_unknown_normal: bool = True  # explicit Basin-and-Range fallback for missing sense


# ------------------------------------------------------------------ inputs
def load_slip_rates(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "external" / "gdr_qfaults_traces.csv")
    df["slip_rate_m_yr"] = df["slip_rate"].astype(float) * 1e-3   # working assumption: mm/yr -> m/yr
    sense = df["slip_sense"].fillna("").astype(str).str.strip().str.upper()
    df["slip_sense_clean"] = sense
    df["dip_deg"] = sense.map(DIP_BY_SENSE).fillna(DIP_DEFAULT)
    df["is_strike_slip"] = sense.isin(["RL", "LL"])
    df["strike_slip_sign"] = np.where(sense == "LL", -1.0, 1.0)
    df["sense_known"] = sense.isin(["N", "RL", "LL"])
    return df


def assign_slip_rate(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig):
    """Per-catalogue-pixel working rate, dip proxy, mode/sign, and assignment flag.

    Geometry comes from the catalogue raster. Rates and senses are transferred
    from the nearest CSV centroid; cells beyond ``max_assign_px`` receive the
    regional median rate and default dip/mode only when ``assume_unknown_normal``
    is enabled. This transfer is approximate: the CSV has centroids, not trace
    geometries, and the default is recorded in the returned metadata.
    """
    ys, xs = np.nonzero(catalogue)
    cy = df["centroid_row"].to_numpy(float)
    cx = df["centroid_col"].to_numpy(float)
    ok = np.isfinite(cy) & np.isfinite(cx)
    cy, cx = cy[ok], cx[ok]
    sr = df["slip_rate_m_yr"].to_numpy(float)[ok]
    dip = df["dip_deg"].to_numpy(float)[ok]
    ss = df["is_strike_slip"].to_numpy(bool)[ok]
    sign = df["strike_slip_sign"].to_numpy(float)[ok]
    known = df["sense_known"].to_numpy(bool)[ok]

    # brute-force nearest centroid over ~61 k x 1.1 k pairs = 68 M, done in strips
    best_d = np.full(ys.size, np.inf)
    best_i = np.full(ys.size, -1, dtype=np.int64)
    step = 4096
    for a in range(0, ys.size, step):
        b = min(a + step, ys.size)
        d = (ys[a:b, None] - cy[None, :]) ** 2 + (xs[a:b, None] - cx[None, :]) ** 2
        j = np.argmin(d, axis=1)
        best_i[a:b] = j
        best_d[a:b] = d[np.arange(b - a), j]
    best_d = np.sqrt(best_d)

    med = float(np.nanmedian(sr))
    assigned = best_d <= cfg.max_assign_px
    nearest = np.maximum(best_i, 0)
    srate = np.where(assigned, sr[nearest], med)
    dipv = np.where(assigned, dip[nearest], cfg.dip_default)
    ssv = np.where(assigned, ss[nearest], False)
    sgn = np.where(assigned, sign[nearest], 1.0)
    known_sense = np.where(assigned, known[nearest], False)
    return (ys, xs, srate.astype(float), dipv.astype(float), ssv.astype(bool),
            sgn.astype(float), known_sense.astype(bool), assigned,
            float(np.sqrt(np.median(best_d ** 2))))


def strike_orientation(catalogue: np.ndarray, sigma_grad: float = 2.0,
                       sigma_int: float = 3.0):
    """Local strike direction (unit vector) at every catalogue pixel.

    Standard steerable-filter structure tensor: the dominant gradient direction
    of a smoothed trace indicator is perpendicular to the trace, so the strike is
    that direction rotated by 90 degrees.
    """
    I = ndi.gaussian_filter(catalogue.astype(np.float32), sigma_grad, mode="nearest")
    gy, gx = np.gradient(I)
    Jxx = ndi.gaussian_filter(gx * gx, sigma_int, mode="nearest")
    Jyy = ndi.gaussian_filter(gy * gy, sigma_int, mode="nearest")
    Jxy = ndi.gaussian_filter(gx * gy, sigma_int, mode="nearest")
    theta = 0.5 * np.arctan2(2.0 * Jxy, (Jxx - Jyy))     # direction of max gradient
    strike = theta + np.pi / 2.0                          # rotate 90 deg -> along-strike
    sx, sy = np.cos(strike), np.sin(strike)
    return sx, sy


def tile_index(catalogue_pixels_yx, tile_px: int):
    ty = np.asarray(catalogue_pixels_yx[0]) // tile_px
    tx = np.asarray(catalogue_pixels_yx[1]) // tile_px
    nt_y = int(np.ceil(H_PX / tile_px))
    nt_x = int(np.ceil(W_PX / tile_px))
    return ty * nt_x + tx, (nt_y, nt_x)


# ------------------------------------------------------------------ Kostrov
def dip_slip_horizontal_amplitude(length_m, rate_m_yr, dip_deg, area_m2,
                                  rate_convention: str = "vertical"):
    """Horizontal tensor component for a pure normal-fault segment.

    The `vertical` convention treats the input as vertical displacement rate;
    `fault_plane` treats it as total dip-slip rate. The source convention is not
    resolved, so both are testable and recorded.
    """
    d = np.deg2rad(np.asarray(dip_deg, dtype=np.float64))
    if rate_convention == "vertical":
        geom = 1.0 / np.tan(d)   # u_total = u_vertical / sin(dip)
    elif rate_convention == "fault_plane":
        geom = np.cos(d)
    else:
        raise ValueError("rate_convention must be 'vertical' or 'fault_plane'")
    return np.asarray(length_m) * np.asarray(rate_m_yr) * geom / float(area_m2)


def rotate_fault_tensor(strike_x, strike_y, normal_component, shear_component):
    """Rotate the local (normal, strike-shear) tensor into horizontal x/y."""
    sx = np.asarray(strike_x, dtype=np.float64)
    sy = np.asarray(strike_y, dtype=np.float64)
    c1 = np.asarray(normal_component, dtype=np.float64)
    c12 = np.asarray(shear_component, dtype=np.float64)
    nx, ny = -sy, sx
    exx = c1 * nx * nx + c12 * 2.0 * nx * sx
    eyy = c1 * ny * ny + c12 * 2.0 * ny * sy
    exy = c1 * nx * ny + c12 * (nx * sy + ny * sx)
    return exx, eyy, exy


def kostrov_tiles(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig):
    """Approximate fault-accommodated horizontal tensor per tile, in nanostrain/yr.

    Uses the published Kreemer et al. (2000) Eq. (3) under pure-mode and rate-
    convention assumptions documented at module top. Returns tensor components,
    trace length, assigned-pixel counts, moment-rate proxy, tile shape, and audit
    metadata. This is a broad prior, not a calibrated physical measurement.
    """
    if cfg.rate_convention not in ("vertical", "fault_plane"):
        raise ValueError("rate_convention must be 'vertical' or 'fault_plane'")
    (ys, xs, srate, dip, is_ss, ss_sign, sense_known,
     assigned, med_d) = assign_slip_rate(catalogue, df, cfg)
    sx, sy = strike_orientation(catalogue)
    A_tile = (cfg.tile_px * PIXEL_M) ** 2
    # A cell traversed at azimuth (sx,sy) contributes 100--141 m of trace.
    sxs = sx[ys, xs]; sys_ = sy[ys, xs]
    L = PIXEL_M / np.maximum(np.maximum(np.abs(sxs), np.abs(sys_)), 1e-6)
    L = np.clip(L, PIXEL_M, PIXEL_M * np.sqrt(2.0))

    d = np.deg2rad(dip)
    normal_mode = (~is_ss) & (sense_known | cfg.assume_unknown_normal)
    # For a pure strike-slip fault the source sense sets the sign. RL and LL
    # have opposite unit moment tensors; both are not accumulated with one sign.
    ess = L * srate / (2.0 * A_tile)
    enn = dip_slip_horizontal_amplitude(L, srate, dip, A_tile,
                                        cfg.rate_convention)

    # Rotate the segment-frame tensor into x/y. `s_hat` is along strike and
    # `n_hat=(-sy,sx)` is its horizontal perpendicular. For pure normal motion,
    # n*n^T is invariant to the unobserved dip-direction sign; dip_direct remains
    # directional metadata and is never read as a dip angle.
    c1 = np.where(normal_mode, enn, 0.0)              # E_nn, pure normal
    c12 = np.where(is_ss, ess * ss_sign, 0.0)        # E_sn, signed RL/LL
    exx, eyy, exy = rotate_fault_tensor(sxs, sys_, c1, c12)

    tid, tshape = tile_index((ys, xs), cfg.tile_px)
    n_tiles = tshape[0] * tshape[1]
    def agg(v):
        return np.bincount(tid, weights=v, minlength=n_tiles)
    exx_t = agg(exx) * 1e9
    eyy_t = agg(eyy) * 1e9
    exy_t = agg(exy) * 1e9
    len_t = agg(np.full(ys.size, L))
    npix_t = np.bincount(tid, minlength=n_tiles)
    assigned_t = agg(assigned.astype(float))
    # Keep the scalar moment-rate proxy consistent with the selected convention.
    total_rate = srate.copy()
    if cfg.rate_convention == "vertical":
        total_rate = np.where(normal_mode, srate / np.maximum(np.sin(d), 1e-9), srate)
    total_rate = np.where(normal_mode | is_ss, total_rate, 0.0)
    mom_t = agg(L * total_rate * (cfg.h_seis_m / np.sin(d)))
    meta = dict(tile_px=cfg.tile_px, tile_shape=list(tshape), h_seis_m=cfg.h_seis_m,
                median_centroid_distance_px=med_d,
                frac_catalogue_px_with_slip_rate=float(assigned.mean()),
                frac_catalogue_px_with_known_sense=float(sense_known.mean()),
                rate_convention=cfg.rate_convention,
                assume_unknown_normal=bool(cfg.assume_unknown_normal),
                dip_assumptions={"normal_deg": cfg.dip_default, "strike_slip_deg": 90.0},
                regional_median_slip_rate_mm_yr=float(np.nanmedian(df["slip_rate"])),
                total_mapped_trace_km=float(len_t.sum() / 1000.0))
    return (exx_t.reshape(tshape), eyy_t.reshape(tshape), exy_t.reshape(tshape),
            len_t.reshape(tshape), npix_t.reshape(tshape),
            assigned_t.reshape(tshape), mom_t.reshape(tshape), tshape, meta)


def invariant(exx, eyy, exy, kind: str = "II"):
    if kind == "II":
        return np.sqrt(exx ** 2 + eyy ** 2 + 2.0 * exy ** 2)
    if kind == "max":                      # engineering max shear / 2
        return np.sqrt(((exx - eyy) / 2.0) ** 2 + exy ** 2)
    raise ValueError(kind)


def block_reduce_sum(a: np.ndarray, tile_px: int, pad_value=0.0):
    """Sum of ``a`` over tile_px x tile_px blocks, padded at the right/bottom edge."""
    nt_y = int(np.ceil(a.shape[0] / tile_px))
    nt_x = int(np.ceil(a.shape[1] / tile_px))
    py, px = nt_y * tile_px, nt_x * tile_px
    b = np.full((py, px), pad_value, dtype=np.float64)
    b[:a.shape[0], :a.shape[1]] = a
    return (b.reshape(nt_y, tile_px, nt_x, tile_px)
             .sum(axis=(1, 3)))


def observed_tiles(field: np.ndarray, footprint: np.ndarray, tile_px: int):
    """Tile mean of an observed layer, NaN where the tile has no valid pixel."""
    good = footprint & np.isfinite(field)
    v = np.where(good, field, 0.0).astype(np.float64)
    s = block_reduce_sum(v, tile_px)
    c = block_reduce_sum(good.astype(np.float64), tile_px)
    with np.errstate(invalid="ignore", divide="ignore"):
        return s / np.where(c > 0, c, np.nan)


def quantile_map(a: np.ndarray, mask: np.ndarray | None = None):
    """Empirical CDF of the finite values, mapped back to the input shape."""
    out = np.full(a.shape, np.nan)
    m = np.isfinite(a) if mask is None else (np.isfinite(a) & mask)
    if m.sum() < 2:
        return out
    v = a[m]
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(v.size)
    ranks[order] = np.arange(1, v.size + 1)
    out[m] = ranks / v.size
    return out
