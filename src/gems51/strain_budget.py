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
  n    = unit normal to the fault plane (horizontal)
  m    = unit slip direction

Substituting W_k and V into (1) removes mu and H:

  strike-slip segment (m = s_hat, n perpendicular to strike):
        eps_dot_sn = L_k * sdot_k / (2 * A_tile * sin(delta))                  (3)
  dip-slip segment (horizontal projection of slip is cos(delta) along n):
        eps_dot_nn = L_k * sdot_k * cot(delta) / A_tile                        (4)

and the horizontal tensor is assembled by rotating (3) and (4) into the (x, y)
frame with the strike of each segment.  This is what ``kostrov_tiles`` computes.

Unit convention: slip rates in the INGENIOUS/GDR compilation are mm/yr; we
convert to m/yr and report strain rate in nanostrain/yr (1e-9 /yr).

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
    df["slip_rate_m_yr"] = df["slip_rate"].astype(float) * 1e-3   # mm/yr -> m/yr
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
def kostrov_tiles(catalogue: np.ndarray, df: pd.DataFrame, cfg: BudgetConfig):
    """Fault-accommodated horizontal strain-rate tensor per tile, in nanostrain/yr.

    Returns ``(exx, eyy, exy, tiles_shape, meta)`` where each array is on the
    coarse tile grid.
    """
    ys, xs, srate, dip, is_ss, assigned, med_d = assign_slip_rate(catalogue, df, cfg)
    sx, sy = strike_orientation(catalogue)
    A_tile = (cfg.tile_px * PIXEL_M) ** 2
    # length of the trace inside one raster cell: a cell traversed at azimuth
    # (sx, sy) carries 1/max(|sx|,|sy|) cells of trace, i.e. between 100 m and
    # 141.4 m.  Using a flat 100 m would under-count diagonal traces by up to 29%.
    sxs = sx[ys, xs]; sys_ = sy[ys, xs]
    L = PIXEL_M / np.maximum(np.maximum(np.abs(sxs), np.abs(sys_)), 1e-6)
    L = np.clip(L, PIXEL_M, PIXEL_M * np.sqrt(2.0))

    d = np.deg2rad(dip)
    # per-segment tensor-strain contribution, in 1/yr, already divided by A_tile
    ess = np.where(is_ss, L * srate / (2.0 * A_tile * np.sin(d)), 0.0)   # (3)
    enn = np.where(is_ss, 0.0, L * srate / (A_tile * np.tan(d)))          # (4) cot = 1/tan

    # rotate the segment frame (s_hat, n_hat) into (x, y)
    #   s_hat = (sx, sy);  n_hat = (-sy, sx)
    #   eps_ij = ess * (s_i n_j + n_i s_j) / 2? -- see note below; we build the
    #   tensor directly from the two segment-frame components.
    #
    # In the segment frame the tensor is [[0, ess], [ess, 0]] (strike-slip) or
    # [[enn, 0], [0, 0]] (dip-slip, n = e1 axis).  Rotating a 2x2 tensor with
    # R = [[sx, -sy], [sy, sx]] (columns are s_hat and n_hat):
    #   E = R @ Eseg @ R.T
    c1 = np.where(is_ss, 0.0, enn)   # Eseg_11 (along n_hat)
    c2 = 0.0                          # Eseg_22 (along s_hat)
    c12 = np.where(is_ss, ess, 0.0)   # Eseg_12
    # E = c1 * n n^T + c2 * s s^T + c12 * (n s^T + s n^T)
    nx, ny = -sys_, sxs
    exx = c1 * nx * nx + c12 * 2.0 * nx * sxs
    eyy = c1 * ny * ny + c12 * 2.0 * ny * sys_
    exy = c1 * nx * ny + c12 * (nx * sys_ + ny * sxs)

    tid, tshape = tile_index((ys, xs), cfg.tile_px)
    n_tiles = tshape[0] * tshape[1]
    def agg(v):
        return np.bincount(tid, weights=v, minlength=n_tiles)
    exx_t = agg(exx) * 1e9      # -> nanostrain/yr
    eyy_t = agg(eyy) * 1e9
    exy_t = agg(exy) * 1e9
    len_t = agg(np.full(ys.size, L))                 # metres of mapped trace per tile
    npix_t = np.bincount(tid, minlength=n_tiles)
    assigned_t = agg(assigned.astype(float))
    mom_t = agg(L * srate * (cfg.h_seis_m / np.sin(d)))   # mu*A*sdot/mu [m^2 * m/yr]
    meta = dict(tile_px=cfg.tile_px, tile_shape=list(tshape), h_seis_m=cfg.h_seis_m,
                median_centroid_distance_px=med_d,
                frac_catalogue_px_with_slip_rate=float(assigned.mean()),
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
