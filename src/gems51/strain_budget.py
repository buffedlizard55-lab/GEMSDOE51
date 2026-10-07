"""Stage 1: geodetic strain-budget deficit over broad tiles.

The hypothesis
--------------
Where the geodetic strain rate exceeds what the mapped faults' slip rates can
accommodate, the catalogue is likelier to be missing structures.  Used strictly
as a coarse first stage: it approves *tiles*, it never places a point.

The formula (Kostrov summation)
-------------------------------
Kostrov (1974), "Seismic moment and long-term deformation of the lithosphere",
Izvestiya, Academy of Sciences USSR, Physics of the Solid Earth -- restated in the
form used by modern geodetic/geologic deformation budgets, e.g.
  * Ward, S.N. (1998), "On the consistency of earthquake moment rates, geological
    fault data, and space geodetic strain", Geophys. J. Int. 134, 172-186;
  * Stevens, V.L. & Avouac, J.-P. (2015), "Interseismic coupling on the main
    Himalayan thrust", J. Geophys. Res. 120, 5828-5848, eq. (1);
  * Field, E.H. et al. (2014), "Uniform California Earthquake Rupture Forecast,
    Version 3 (UCERF3) -- The Time-Independent Model", Bull. Seismol. Soc. Am.
    104(3), 1122-1180, doi:10.1785/0120130164 -- which is the precedent the
    hypothesis cites for balancing geodetic and geologic deformation and for
    modelling off-fault strain explicitly.

        eps_dot_ij  =  (1 / (2 * mu * V)) * sum_k  Mdot_ij^(k)                 (1)
        Mdot_ij^(k) =  mu * A_k * sdot_k * ( n_i m_j + n_j m_i )               (2)

  A_k  = L_k * W_k            fault area           [m^2]
  L_k  = surface trace length of segment k in the tile [m]
  W_k  = H / sin(delta)       down-dip width        [m]   (H = seismogenic thickness)
  V    = A_tile * H           volume of the tile    [m^3]
  mu   = shear modulus        [Pa]  -- cancels out of (1) when W_k = H/sin(delta)
  n    = unit normal to the complete (3-D) fault plane
  m    = unit slip direction

Kreemer et al. (2000), eq. (3), write the horizontal strain-rate components as

        eps_dot_ij = (1/2) sum_k [L_k * u_dot_k / (A_tile * sin(delta_k))] m_ij^k

where ``m_ij^k = n_i m_j + n_j m_i`` is the unit moment tensor.  For a vertical
pure strike-slip segment, the strike-normal component is

        eps_dot_sn = L_k * u_dot_k / (2 * A_tile)                             (3)

For pure dip slip, the horizontal projections of the full unit normal and slip
direction have magnitudes ``sin(delta)`` and ``cos(delta)``. If ``u_dot`` is the
total fault-plane slip rate, their product cancels the ``sin(delta)`` denominator,
giving ``eps_dot_nn = L*u_dot_plane*cos(delta)/A_tile``. If the source rate is
vertical displacement, then ``u_dot_plane = u_dot_vertical/sin(delta)`` and the
horizontal component becomes ``L*u_dot_vertical*cot(delta)/A_tile``. The source
component convention is unresolved; ``BudgetConfig.rate_convention`` exposes both
assumptions and defaults to ``vertical``. Right- and left-lateral strike slip use
opposite shear signs.

The tensor is rotated from the local strike/dip frame into projected x/y axes.
This projection is explicitly approximate for this project: fault rakes and
per-trace dips are not supplied in the table used here, so normal/unknown traces
use a documented 60-degree dip fallback and the two lateral classes use a vertical
fault assumption. Unknown-sense contributions can be treated as normal only by an
explicit configurable fallback. The implementation uses raster-trace local strike
and nearest-centroid slip-rate assignment; it is not a full geodetic inversion.

Source audit update (2026-10-07)
--------------------------------
The official v2 shapefile field definitions now verify SLIPRT2023 as mm/year
and SLIPRTNUM as its numeric portion. All 1,126 mirrored records match the
source DBF by record index/name/rate/sense. Slip component and per-trace dip
remain assumptions. See registry/official and evidence/official_attribute_audit_20261007.json.

The official geodetic README defines II=sqrt(e1^2+e2^2), dilation=e1+e2,
and shear=min(abs(e1),abs(e2)) for opposite-signed eigenvalues, otherwise zero.
The earlier inference that no scalar identity exists was incorrect: under that
convention II^2=dilation^2+2*shear*(abs(dilation)+shear). Interpolation can still
break exact equality. The legacy rank-space prior below is kept unchanged for
frozen holdout reproducibility. It is NOT a physical dilation/shear subtraction.
The new vector_budget module and audit_official_budget.py use actual clipped
source trace lengths and source-matched scalar summaries for a separate audit.
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
    # Units verified against official v2 DBF and field definitions.
    # Slip component (vertical vs fault-plane) remains an assumption.
    df["slip_rate_m_yr"] = df["slip_rate"].astype(float) * 1e-3   # working mm/yr -> m/yr
    sense = df["slip_sense"].fillna("").astype(str).str.strip().str.upper()
    df["slip_sense_clean"] = sense
    df["dip_deg"] = sense.map(DIP_BY_SENSE).fillna(DIP_DEFAULT)
    df["is_strike_slip"] = sense.isin(["RL", "LL"])
    # This sign convention is explicit and testable; it is not a geologic
    # polarity inferred from dip_direct (which is a direction label, not an angle).
    df["strike_slip_sign"] = np.where(sense == "LL", -1.0, 1.0)
    df["sense_known"] = sense.isin(["N", "RL", "LL"])
    return df


def assign_slip_rate(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig):
    """Per-catalogue-pixel working rate, dip proxy, mode/sign, and assignment flag.

    Geometry comes from the catalogue raster. Rates and senses are transferred
    from the nearest CSV centroid; cells beyond ``max_assign_px`` receive the
    regional median rate and default dip/mode. This is approximate: the CSV has
    centroids, not trace geometries, and the fallback is recorded in metadata.
    """
    ys, xs = np.nonzero(catalogue)
    if ys.size == 0:
        empty = np.empty(0, dtype=np.float64)
        return ys, xs, empty, empty, empty.astype(bool), empty, empty.astype(bool), \
            empty.astype(bool), float("nan")
    cy = df["centroid_row"].to_numpy(float)
    cx = df["centroid_col"].to_numpy(float)
    ok = np.isfinite(cy) & np.isfinite(cx)
    cy, cx = cy[ok], cx[ok]
    sr = df["slip_rate_m_yr"].to_numpy(float)[ok]
    dip = df["dip_deg"].to_numpy(float)[ok]
    ss = df["is_strike_slip"].to_numpy(bool)[ok]
    sign = df["strike_slip_sign"].to_numpy(float)[ok]
    known = df["sense_known"].to_numpy(bool)[ok]
    if not sr.size:
        raise ValueError("no finite trace centroids with slip attributes are available")

    # Brute-force nearest centroid in strips; the public table has about 1.1k rows.
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


def trace_assignments(catalogue: np.ndarray, df: pd.DataFrame, step: int = 4096):
    """Map each positive catalogue pixel to its nearest trace-centroid row ID.

    This deterministic approximation is used to remove whole attribute rows
    whose assigned pixels overlap a held-out fold. It returns original DataFrame
    index labels, not positions, so a caller can safely filter ``df``.
    """
    ys, xs = np.nonzero(catalogue)
    if ys.size == 0:
        return ys, xs, np.empty(0, dtype=np.asarray(df.index).dtype)
    cy = df["centroid_row"].to_numpy(float)
    cx = df["centroid_col"].to_numpy(float)
    row_ids = np.asarray(df.index)
    ok = np.isfinite(cy) & np.isfinite(cx)
    cy, cx, row_ids = cy[ok], cx[ok], row_ids[ok]
    if not row_ids.size:
        raise ValueError("no finite trace centroids are available")
    assigned = np.empty(ys.size, dtype=row_ids.dtype)
    for start in range(0, ys.size, step):
        stop = min(start + step, ys.size)
        d2 = ((ys[start:stop, None] - cy[None, :]) ** 2
              + (xs[start:stop, None] - cx[None, :]) ** 2)
        nearest = np.argmin(d2, axis=1)
        assigned[start:stop] = row_ids[nearest]
    return ys, xs, assigned


def horizontal_segment_tensor(length_m, slip_m_yr, dip_deg, strike_x, strike_y,
                              is_strike_slip, area_m2, strike_slip_sign=1.0,
                              rate_convention="fault_plane"):
    """Kreemer-eq.-(3) horizontal tensor contribution for pure-slip segments.

    Normal-fault rate convention is explicit (the utility defaults to total
    fault-plane slip for backward compatibility); RL/LL sense is supplied by
    ``strike_slip_sign``. All quantities may be NumPy arrays and broadcast.
    ``strike_y`` is projected north-positive and ``area_m2`` is actual support
    area. Returns ``(exx, eyy, exy)`` in 1/yr.
    """
    length = np.asarray(length_m, dtype=np.float64)
    slip = np.asarray(slip_m_yr, dtype=np.float64)
    dip = np.deg2rad(np.asarray(dip_deg, dtype=np.float64))
    sx = np.asarray(strike_x, dtype=np.float64)
    sy = np.asarray(strike_y, dtype=np.float64)
    ss = np.asarray(is_strike_slip, dtype=bool)
    ss_sign = np.asarray(strike_slip_sign, dtype=np.float64)
    area = np.asarray(area_m2, dtype=np.float64)
    if np.any(area <= 0.0):
        raise ValueError("fault strain tensor requires positive support area")
    if np.any((dip <= 0.0) | (dip > np.pi / 2.0)):
        raise ValueError("dip must be in (0, 90] degrees")

    # Eq. (3): horizontal projection of the strike-slip plane normal contributes
    # sin(dip), cancelling the denominator in Eq. (3); the shear coefficient is
    # therefore L*u/(2*A), independent of dip. Dip-slip uses its own projection.
    if rate_convention not in ("vertical", "fault_plane"):
        raise ValueError("rate_convention must be 'vertical' or 'fault_plane'")
    shear = np.where(ss, length * slip * ss_sign / (2.0 * area), 0.0)
    normal = np.where(~ss, dip_slip_horizontal_amplitude(
        length, slip, np.rad2deg(dip), area, rate_convention), 0.0)
    nx, ny = -sy, sx  # horizontal dip direction, perpendicular to strike
    exx = normal * nx * nx + 2.0 * shear * nx * sx
    eyy = normal * ny * ny + 2.0 * shear * ny * sy
    exy = normal * nx * ny + shear * (nx * sy + ny * sx)
    return exx, eyy, exy


def dip_slip_horizontal_amplitude(length_m, rate_m_yr, dip_deg, area_m2,
                                  rate_convention: str = "vertical"):
    """Horizontal tensor component for a pure normal-fault segment.

    ``vertical`` treats the source rate as vertical displacement, yielding
    L*u_vertical*cot(dip)/A. ``fault_plane`` treats it as total dip-slip rate,
    yielding L*u_plane*cos(dip)/A. Source semantics remain unresolved, so both
    conventions are explicit, testable assumptions.
    """
    d = np.deg2rad(np.asarray(dip_deg, dtype=np.float64))
    area = np.asarray(area_m2, dtype=np.float64)
    if np.any(area <= 0.0):
        raise ValueError("fault strain tensor requires positive support area")
    if np.any((d <= 0.0) | (d > np.pi / 2.0)):
        raise ValueError("dip must be in (0, 90] degrees")
    if rate_convention == "vertical":
        geom = 1.0 / np.tan(d)
    elif rate_convention == "fault_plane":
        geom = np.cos(d)
    else:
        raise ValueError("rate_convention must be 'vertical' or 'fault_plane'")
    return np.asarray(length_m, dtype=np.float64) * np.asarray(rate_m_yr, dtype=np.float64) * geom / area


def rotate_fault_tensor(strike_x, strike_y, normal_component, shear_component):
    """Rotate local (normal, strike-shear) components into projected x/y axes."""
    sx = np.asarray(strike_x, dtype=np.float64)
    sy = np.asarray(strike_y, dtype=np.float64)
    c1 = np.asarray(normal_component, dtype=np.float64)
    c12 = np.asarray(shear_component, dtype=np.float64)
    nx, ny = -sy, sx
    exx = c1 * nx * nx + c12 * 2.0 * nx * sx
    eyy = c1 * ny * ny + c12 * 2.0 * ny * sy
    exy = c1 * nx * ny + c12 * (nx * sy + ny * sx)
    return exx, eyy, exy


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
def kostrov_tiles(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig,
                  area_mask: np.ndarray | None = None):
    """Approximate fault-accommodated horizontal tensor per broad tile.

    Uses the Kreemer et al. (2000) Eq. (3) moment-tensor sum, with explicit
    rate-component, missing-sense, dip, centroid-assignment, and trace-geometry
    assumptions. Partial edge tiles use actual valid support area. This is a
    coarse prior, not a calibrated geodetic inversion or fine-scale placer.
    """
    if catalogue.shape != (H_PX, W_PX):
        raise ValueError(f"catalogue shape {catalogue.shape} != {(H_PX, W_PX)}")
    if cfg.rate_convention not in ("vertical", "fault_plane"):
        raise ValueError("rate_convention must be 'vertical' or 'fault_plane'")
    if area_mask is None:
        area_mask = np.ones(catalogue.shape, dtype=bool)
    else:
        area_mask = np.asarray(area_mask, dtype=bool)
        if area_mask.shape != catalogue.shape:
            raise ValueError("area_mask and catalogue must have identical shapes")

    (ys, xs, srate, dip, is_ss, ss_sign, sense_known,
     assigned, med_d) = assign_slip_rate(catalogue, df, cfg)
    sx, sy_image = strike_orientation(catalogue)
    # Raster rows increase southward while projected UTM northing increases northward.
    sxs = sx[ys, xs]
    sys_ = -sy_image[ys, xs]
    L = PIXEL_M / np.maximum(np.maximum(np.abs(sxs), np.abs(sys_)), 1e-6)
    L = np.clip(L, PIXEL_M, PIXEL_M * np.sqrt(2.0))

    area_by_tile = block_reduce_sum(area_mask.astype(np.float64), cfg.tile_px) * PIXEL_M ** 2
    tid, tshape = tile_index((ys, xs), cfg.tile_px)
    if tuple(area_by_tile.shape) != tuple(tshape):
        raise RuntimeError("tile area and trace aggregation grids disagree")
    n_tiles = tshape[0] * tshape[1]
    area_flat = area_by_tile.reshape(-1)
    segment_area = area_flat[tid]
    if np.any(segment_area <= 0.0):
        raise ValueError("catalogue traces fall in tiles with zero support area")

    d = np.deg2rad(dip)
    normal_mode = (~is_ss) & (sense_known | bool(cfg.assume_unknown_normal))
    # Eq. (3), after horizontal projection. RL/LL use opposite shear signs.
    ess = L * srate / (2.0 * segment_area)
    enn = dip_slip_horizontal_amplitude(L, srate, dip, segment_area,
                                        cfg.rate_convention)
    c1 = np.where(normal_mode, enn, 0.0)
    c12 = np.where(is_ss, ess * ss_sign, 0.0)
    exx, eyy, exy = rotate_fault_tensor(sxs, sys_, c1, c12)

    def agg(v):
        return np.bincount(tid, weights=v, minlength=n_tiles)
    exx_t = agg(exx) * 1e9
    eyy_t = agg(eyy) * 1e9
    exy_t = agg(exy) * 1e9
    len_t = agg(np.full(ys.size, L))
    npix_t = np.bincount(tid, minlength=n_tiles)
    assigned_t = agg(assigned.astype(float))
    total_rate = srate.copy()
    if cfg.rate_convention == "vertical":
        total_rate = np.where(normal_mode, srate / np.maximum(np.sin(d), 1e-9), srate)
    total_rate = np.where(normal_mode | is_ss, total_rate, 0.0)
    mom_t = agg(L * total_rate * (cfg.h_seis_m / np.maximum(np.sin(d), 1e-9)))
    finite_area = area_by_tile[area_by_tile > 0]
    meta = dict(tile_px=cfg.tile_px, tile_shape=list(tshape), h_seis_m=cfg.h_seis_m,
                median_centroid_distance_px=med_d,
                frac_catalogue_px_with_slip_rate=float(assigned.mean()) if assigned.size else 0.0,
                frac_catalogue_px_with_known_sense=float(sense_known.mean()) if sense_known.size else 0.0,
                rate_convention=cfg.rate_convention,
                assume_unknown_normal=bool(cfg.assume_unknown_normal),
                dip_assumptions={"normal_deg": cfg.dip_default, "strike_slip_deg": 90.0},
                regional_median_slip_rate_mm_yr=float(np.nanmedian(df["slip_rate"])) if len(df) else float("nan"),
                total_mapped_trace_km=float(len_t.sum() / 1000.0),
                area_mask_px=int(area_mask.sum()),
                slip_rate_unit_assumption="mm/yr (provisional; verify source field definition)",
                tile_area_m2_min=float(finite_area.min()) if finite_area.size else 0.0,
                tile_area_m2_max=float(finite_area.max()) if finite_area.size else 0.0)
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
