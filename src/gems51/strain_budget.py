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

For a pure dip-slip segment, the horizontal projections of the full unit normal
and slip direction have magnitudes ``sin(delta)`` and ``cos(delta)``.  Their
product cancels the ``sin(delta)`` in the prefactor, giving the horizontal
extension/contraction component

        eps_dot_nn = L_k * u_dot_k * cos(delta_k) / A_tile                    (4)

The tensor is rotated from the local strike/dip frame into projected x/y axes.
This projection is explicitly approximate for this project: fault rakes and
per-trace dips are not supplied in the table used here, so normal/unspecified
traces use a documented 60-degree dip and the two lateral classes use a vertical
fault assumption.  The current implementation uses raster-trace local strike
and nearest-centroid slip-rate assignment; it is not a full geodetic inversion.

Unit convention is provisional: the locally mirrored CSV's `slip_rate` field is
interpreted as mm/yr and converted to m/yr, but the retained NBMG service schema
for `SLIPRTNUM` does not state units and the accompanying GDR field-definition file
has not been audited locally. Raw nanostrain/yr values are therefore not
source-validated. The current quantile-rank Stage-1 comparison is invariant to a
uniform rate rescaling, but not to mixed units, categorical encodings, or
record-specific attribute errors.

What we can and cannot verify
-----------------------------
The three geodetic layers shipped with the competition are mutually consistent
to r = 0.993 but satisfy **no exact algebraic identity** (tested: sqrt(dil^2 +
shear^2), sqrt((dil^2+shear^2)/2), |dil| + |shear| all miss by >30% in places),
so they were gridded/smoothed independently and the exact invariant convention
used for ``geod_2ndinv`` is not recoverable from the data.  We therefore state
the deficit in **quantile (rank) space**, which is invariant to any monotone
rescaling of either side.  The raw nanostrain/yr numbers are reported too, and
compared, but no absolute claim rests on them.
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


# ------------------------------------------------------------------ inputs
def load_slip_rates(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "external" / "gdr_qfaults_traces.csv")
    # Provisional unit interpretation; the mirrored SLIPRTNUM source field's
    # unit must be checked against the GDR text field-definition file.
    df["slip_rate_m_yr"] = df["slip_rate"].astype(float) * 1e-3   # assumed mm/yr -> m/yr
    df["dip_deg"] = df["slip_sense"].map(DIP_BY_SENSE).fillna(DIP_DEFAULT)
    df["is_strike_slip"] = df["slip_sense"].isin(["RL", "LL"])
    return df


def assign_slip_rate(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig):
    """Per-catalogue-pixel slip rate (m/yr), dip (deg) and strike-slip flag.

    Geometry comes from the catalogue *raster* (exact, 100 m per pixel).  Slip
    rate comes from the INGENIOUS/GDR attribute table by nearest trace centroid.
    Pixels with no trace centroid inside ``max_assign_px`` get the regional
    median and are flagged, so their contribution can be switched off in a
    sensitivity run.
    """
    ys, xs = np.nonzero(catalogue)
    cy = df["centroid_row"].to_numpy(float)
    cx = df["centroid_col"].to_numpy(float)
    ok = np.isfinite(cy) & np.isfinite(cx)
    cy, cx = cy[ok], cx[ok]
    sr = df["slip_rate_m_yr"].to_numpy(float)[ok]
    dip = df["dip_deg"].to_numpy(float)[ok]
    ss = df["is_strike_slip"].to_numpy(bool)[ok]

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
    srate = np.where(assigned, sr[np.maximum(best_i, 0)], med)
    dipv = np.where(assigned, dip[np.maximum(best_i, 0)], cfg.dip_default)
    ssv = np.where(assigned, ss[np.maximum(best_i, 0)], False)
    return ys, xs, srate.astype(float), dipv.astype(float), ssv.astype(bool), \
        assigned, float(np.sqrt(np.median(best_d ** 2)))


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
                              is_strike_slip, area_m2):
    """Kreemer-eq.-(3) horizontal tensor contribution for pure-slip segments.

    All quantities may be NumPy arrays and are broadcast together. ``strike_y``
    is in projected map coordinates (north-positive); ``area_m2`` is the actual
    cell/tile support area. Returns ``(exx, eyy, exy)`` in 1/yr.
    """
    length = np.asarray(length_m, dtype=np.float64)
    slip = np.asarray(slip_m_yr, dtype=np.float64)
    dip = np.deg2rad(np.asarray(dip_deg, dtype=np.float64))
    sx = np.asarray(strike_x, dtype=np.float64)
    sy = np.asarray(strike_y, dtype=np.float64)
    ss = np.asarray(is_strike_slip, dtype=bool)
    area = np.asarray(area_m2, dtype=np.float64)
    if np.any(area <= 0.0):
        raise ValueError("fault strain tensor requires positive support area")
    if np.any((dip <= 0.0) | (dip > np.pi / 2.0)):
        raise ValueError("dip must be in (0, 90] degrees")

    # Eq. (3): strike-slip tensor has unit off-diagonal local component; for a
    # dip-slip tensor, the horizontal projections contribute sin(dip)*cos(dip).
    shear = np.where(ss, length * slip / (2.0 * area * np.maximum(np.sin(dip), 1e-12)), 0.0)
    normal = np.where(~ss, length * slip * np.cos(dip) / area, 0.0)
    nx, ny = -sy, sx  # horizontal dip direction, perpendicular to strike
    exx = normal * nx * nx + 2.0 * shear * nx * sx
    eyy = normal * ny * ny + 2.0 * shear * ny * sy
    exy = normal * nx * ny + shear * (nx * sy + ny * sx)
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
    """Fault-accommodated horizontal tensor per tile, in nanostrain/yr.

    ``area_mask`` defines the area over which observed tile means are computed
    (normally the competition footprint). Partial edge tiles use their actual
    support area rather than the nominal full-tile area.

    Returns ``(exx, eyy, exy, trace_len, n_trace_px, assigned_px, moment_area_rate,
    tiles_shape, meta)``; the first three arrays are on the coarse tile grid.
    """
    if catalogue.shape != (H_PX, W_PX):
        raise ValueError(f"catalogue shape {catalogue.shape} != {(H_PX, W_PX)}")
    if area_mask is None:
        area_mask = np.ones(catalogue.shape, dtype=bool)
    else:
        area_mask = np.asarray(area_mask, dtype=bool)
        if area_mask.shape != catalogue.shape:
            raise ValueError("area_mask and catalogue must have identical shapes")

    ys, xs, srate, dip, is_ss, assigned, med_d = assign_slip_rate(catalogue, df, cfg)
    sx, sy_image = strike_orientation(catalogue)
    # Raster rows increase southward, whereas projected UTM y increases northward.
    sxs = sx[ys, xs]
    sys_ = -sy_image[ys, xs]
    # A cell traversed at azimuth (sx, sy) carries 100..141.4 m of trace.
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

    exx, eyy, exy = horizontal_segment_tensor(
        L, srate, dip, sxs, sys_, is_ss, segment_area)

    def agg(v):
        return np.bincount(tid, weights=v, minlength=n_tiles)
    exx_t = agg(exx) * 1e9      # -> nanostrain/yr
    eyy_t = agg(eyy) * 1e9
    exy_t = agg(exy) * 1e9
    len_t = agg(np.full(ys.size, L))
    npix_t = np.bincount(tid, minlength=n_tiles)
    assigned_t = agg(assigned.astype(float))
    dip_rad = np.deg2rad(dip)
    mom_t = agg(L * srate * (cfg.h_seis_m / np.maximum(np.sin(dip_rad), 1e-12)))
    finite_area = area_by_tile[area_by_tile > 0]
    meta = dict(tile_px=cfg.tile_px, tile_shape=list(tshape), h_seis_m=cfg.h_seis_m,
                median_centroid_distance_px=med_d,
                frac_catalogue_px_with_slip_rate=float(assigned.mean()) if assigned.size else 0.0,
                regional_median_slip_rate_assumed_mm_yr=float(np.nanmedian(df["slip_rate"]))
                if len(df) else float("nan"),
                total_mapped_trace_km=float(len_t.sum() / 1000.0),
                area_mask_px=int(area_mask.sum()),
                slip_rate_unit_assumption="mm/yr (provisional; verify GDR field definition)",
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
