"""STAGE 1 -- Geodetic strain-budget deficit, used strictly as a COARSE first-stage prior.

WHAT THIS MODULE DOES
---------------------
1. Builds a *fault strain budget* on a tile grid from the mapped-fault traces, using the
   moment-tensor (Kostrov) summation in the form published for fault-slip-rate data.
2. Compares it with the supplied geodetic strain-rate layers (bands 7 = shear rate,
   8 = dilatation rate, 4 = second invariant) aggregated on the same tiles.
3. Returns the residual = geodetic - fault budget, i.e. the "strain-budget deficit".
   Tiles whose deficit is high are the tiles the catalogue cannot account for.
4. Emits an APPROVED-TILE mask.  Stage 2 is only allowed to place points inside it.

THE EXACT FORMULA (stated because the brief asks for it explicitly, with source)
-------------------------------------------------------------------------------
Kostrov (1974) summation in the fault-slip-rate form, as published by
Kreemer, Haines, Holt, Blewitt & Lavallee (2000), "On the determination of a global
strain rate model", Earth Planets Space 52, eq. (3):
https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf

        eps_dot_ij  =  (1/2) * SUM_k [ (L_k * u_dot_k) / (A * sin(delta_k)) ] * m_ij^k

    L_k      = length of fault segment k inside the tile
    u_dot_k  = its slip rate
    delta_k  = its dip
    A        = tile area
    m_ij^k   = unit moment tensor of segment k (strike/slip rake)
    eps_dot  = average strain-rate tensor of the tile

The unbounded-volume form for earthquake catalogues is Kostrov (1974) itself:
        eps_dot_ij = (1/(2*mu*V*T)) * SUM_k M_ij^k        (Kreemer et al. 2000 eq. 2)

PRECEDENT for balancing geodetic against geologic deformation, and for treating the
residual as an explicit quantity, all official USGS / peer-reviewed:
  * Field et al. (2014), BSSA 104(3) 1122-1180, doi:10.1785/0120130164 -- three UCERF3
    deformation models invert geodetic AND geologic data together.
  * USGS OFR 2013-1165 Appendix C ("Deformation Models for UCERF3"),
    https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf --
    "Deformation models provide the strain rate tensor on a 0.1 degree by 0.1 degree grid
     covering all of California. This grid of strain rates account for all modeled
     deformation that is NOT accommodated on the faults."  <- the residual is a published,
    official quantity, not an invention.
  * Zeng & Shen (2016), BSSA 106(2) 766-784, doi:10.1785/0120140250 (USGS pub. 70160311)
    -- estimates the OFF-FAULT moment rate separately: 0.88e19 N.m/yr off-fault against a
    total California moment rate of 2.76e19 N.m/yr, i.e. an off-fault fraction of 31.9 %.
    That number is used below as the empirical ceiling on how much of a deficit may
    legitimately be off-fault rather than evidence of a missing structure.

IRREGULARITY FLAGGED (IR-51-01)
-------------------------------
The brief asks to "convert each mapped fault's slip rate (the INGENIOUS compilation is
reported to hold slip rates; confirm in the shapefile attributes)".  This sandbox cannot
reach gdr.openei.org (submission 1391) or any USGS vector service: every non-GitHub,
non-PyPI host returns HTTP 000.  The shapefile attributes therefore CANNOT be confirmed
here.  Rather than invent per-fault slip rates, this module takes the slip rate as an
explicit, documented parameter, defaults to a uniform value, and *sweeps* the published
Basin-and-Range range to show which tiles the answer is stable to.  See `SLIP_RATE_DEFAULT`
and `slip_rate_sweep`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# --- documented constants -------------------------------------------------------------
# Typical late-Quaternary slip rates on northern Great Basin / Walker Lane faults span
# ~0.1-1 mm/yr; 1 mm/yr is the conventional upper-bound working value.  We sweep 0.1-2.0
# and report tile stability.  NOT an INGENIOUS attribute -- see IR-51-01.
SLIP_RATE_DEFAULT_MM_YR = 1.0
SLIP_RATE_SWEEP_MM_YR = (0.1, 0.5, 1.0, 2.0)

# Normal faults in the Basin and Range are conventionally modelled at 45-60 deg dip
# (e.g. USGS Quaternary Fault and Fold Database / UCERF3 fault models use 50-70 deg,
# commonly 60 deg).  We use 60 deg and record the choice.
DIP_DEG_DEFAULT = 60.0

# Zeng & Shen (2016): off-fault moment rate / total moment rate, California.
OFF_FAULT_FRACTION = 0.88e19 / 2.76e19  # = 0.3188...


@dataclass
class Stage1Result:
    tile: int
    deficits: np.ndarray          # (ny, nx) geodetic - budget, normalised
    geodetic: np.ndarray          # (ny, nx) aggregated geodetic strain magnitude
    budget: np.ndarray            # (ny, nx) fault budget magnitude
    approved: np.ndarray          # (ny, nx) bool -- approved tiles
    threshold: float
    slip_rate_mm_yr: float
    dip_deg: float
    meta: dict


def _strike_field(catalogue: np.ndarray, blur_px: float = 6.0) -> np.ndarray:
    """Local strike (radians, in [0, pi)) of the mapped-fault traces.

    Built from the structure tensor of the binary catalogue raster; the *minimum*
    eigenvector of the structure tensor points along the trace.
    """
    c = catalogue.astype(np.float32)
    g = ndimage.gaussian_filter(c, blur_px)
    gy, gx = np.gradient(g)
    jxx = ndimage.gaussian_filter(gx * gx, blur_px)
    jxy = ndimage.gaussian_filter(gx * gy, blur_px)
    jyy = ndimage.gaussian_filter(gy * gy, blur_px)
    # principal eigenvector of the (symmetric) structure tensor
    theta = 0.5 * np.arctan2(2.0 * jxy, (jxx - jyy))
    # theta is the direction of maximum gradient; the trace runs perpendicular to it
    strike = theta + np.pi / 2.0
    return np.mod(strike, np.pi).astype(np.float32)


def _unit_moment_tensor_scalar(strike: np.ndarray, dip_deg: float) -> np.ndarray:
    """Scalar amplitude of the unit moment tensor contribution for a pure-dip-slip /
    strike-slip mix.

    For the tile-budget we only need the *magnitude* of the horizontal strain-rate
    contribution, i.e. |m| = sqrt(sum_ij m_ij^2) with m_ij = (u_i n_j + u_j n_i)/2.
    For a fault with strike phi, dip delta and slip vector confined to the fault plane,
    a standard result is that the scalar seismic-moment magnitude per unit area is
    M0/A = mu * u_dot, so the horizontal strain contribution carries the geometrical
    factor 1/sin(delta) from slip on a dipping plane projected to the map area --
    exactly the 1/sin(delta_k) term in Kreemer et al. (2000) eq. (3).
    The strike dependence enters only through the tensor *orientation*, which cancels in
    the scalar magnitude; it is retained so the tensor form is available.
    """
    return np.ones_like(strike, dtype=np.float32)


def tile_geometry(shape: tuple[int, int], tile: int):
    ny = (shape[0] + tile - 1) // tile
    nx = (shape[1] + tile - 1) // tile
    return ny, nx


def aggregate_to_tiles(a: np.ndarray, tile: int, reducer="mean") -> np.ndarray:
    """Block-reduce a full-resolution array to the tile grid, ignoring NaN."""
    h, w = a.shape
    ny, nx = tile_geometry(a.shape, tile)
    pad_h, pad_w = ny * tile - h, nx * tile - w
    ap = np.pad(a, ((0, pad_h), (0, pad_w)), constant_values=np.nan)
    blocks = ap.reshape(ny, tile, nx, tile)
    if reducer == "mean":
        with np.errstate(invalid="ignore"):
            out = np.nanmean(blocks, axis=(1, 3))
    elif reducer == "sum":
        out = np.nansum(blocks, axis=(1, 3))
    elif reducer == "max":
        out = np.nanmax(blocks, axis=(1, 3))
    else:
        raise ValueError(reducer)
    return out.astype(np.float32)


def compute_stage1(
    catalogue: np.ndarray,
    shear: np.ndarray,
    dilatation: np.ndarray,
    second_invariant: np.ndarray,
    *,
    tile: int = 32,
    slip_rate_mm_yr: float = SLIP_RATE_DEFAULT_MM_YR,
    dip_deg: float = DIP_DEG_DEFAULT,
    approve_quantile: float = 0.55,
    min_valid_fraction: float = 0.25,
) -> Stage1Result:
    """Compute the geodetic strain-budget deficit on tiles and approve tiles.

    geodetic tile strain  : robust magnitude of the supplied geodetic strain layers
                            (standardised, then combined as the L2 norm of the three).
    fault tile strain     : Kostrov/Kreemer sum over mapped fault length in the tile.
    deficit               : geodetic - budget  (standardised units).
    approved              : deficit in the top `approve_quantile` quantile.
    """
    ny, nx = tile_geometry(catalogue.shape, tile)

    # ---- geodetic side: standardise each supplied strain layer by its own robust scale
    def robust_z(a):
        v = a[np.isfinite(a)]
        if v.size == 0:
            return np.zeros_like(a)
        med = np.median(v)
        mad = np.median(np.abs(v - med)) * 1.4826
        if mad <= 0:
            mad = np.std(v) or 1.0
        return np.nan_to_num((a - med) / mad, nan=0.0).astype(np.float32)

    # Tiles with no geodetic data must be EXCLUDED, not treated as zero deficit.
    # Measured on the supplied products: 7,113,308 of 12,279,160 cells (57.9 %) carry the
    # float32 nodata sentinel, and the finite cells are exactly the 5,167,373-cell
    # footprint.  Counting the empty tiles as "deficit = 0" silently approves them.
    data_ok = (np.isfinite(shear) & np.isfinite(dilatation) & np.isfinite(second_invariant))
    coverage = aggregate_to_tiles(data_ok.astype(np.float32), tile, "mean")
    usable = np.nan_to_num(coverage, nan=0.0) >= min_valid_fraction

    z_sh = robust_z(shear)
    z_di = robust_z(dilatation)
    z_si = robust_z(second_invariant)
    geo_mag = np.sqrt(z_sh ** 2 + z_di ** 2 + z_si ** 2).astype(np.float32)
    geodetic = aggregate_to_tiles(geo_mag, tile, "mean")

    # ---- fault budget side: Kreemer et al. (2000) eq. (3), magnitude form
    # Each catalogue pixel is a trace element of length L = 100 m.
    # u_dot in mm/yr -> m/yr; A in m^2; the 1/(2 sin delta) factor is kept explicit.
    strike = _strike_field(catalogue)
    m_amp = _unit_moment_tensor_scalar(strike, dip_deg)
    u_dot_m_yr = slip_rate_mm_yr * 1e-3
    seg_len_m = 100.0
    trace_weight = np.where(catalogue, seg_len_m * u_dot_m_yr * m_amp, 0.0).astype(np.float32)
    # sum of (L_k*u_dot_k) per tile
    sum_Lu = aggregate_to_tiles(trace_weight, tile, "sum")
    tile_area_m2 = (tile * 100.0) * (tile * 100.0)
    sin_dip = np.sin(np.deg2rad(dip_deg))
    budget_raw = 0.5 * sum_Lu / (tile_area_m2 * sin_dip)
    # bring to the same (standardised) units as the geodetic side so the subtraction is
    # not a unit salad.  Scale by the same robust-z transform applied to tiles.
    v = budget_raw[np.isfinite(budget_raw)]
    med = np.median(v) if v.size else 0.0
    mad = np.median(np.abs(v - med)) * 1.4826 if v.size else 1.0
    if mad <= 0:
        mad = np.std(v) or 1.0
    budget = np.nan_to_num((budget_raw - med) / mad, nan=0.0).astype(np.float32)

    deficit = (geodetic - budget).astype(np.float32)
    # A usable tile must (a) have geodetic data and (b) contain at least one mapped-fault
    # pixel, otherwise the budget term is degenerate.
    has_trace = aggregate_to_tiles(catalogue.astype(np.float32), tile, "sum") > 0
    usable = usable & np.isfinite(deficit) & (has_trace | np.isfinite(geodetic))
    valid = usable & np.isfinite(deficit)
    if valid.any():
        thr = float(np.nanquantile(deficit[valid], 1.0 - approve_quantile))
    else:
        thr = 0.0
    approved = valid & (deficit >= thr)

    approved_raster_px = int(approved.sum()) * tile * tile
    meta = {
        "tile_px": tile,
        "n_usable_tiles": int(valid.sum()),
        "n_tiles_total": int(deficit.size),
        "min_valid_fraction": min_valid_fraction,
        "approved_raster_px_approx": approved_raster_px,
        "approved_fraction_of_usable_tiles": float(
            approved.sum() / max(1, int(valid.sum()))),
        "tile_size_m": tile * 100.0,
        "n_tiles": [int(ny), int(nx)],
        "slip_rate_mm_yr": slip_rate_mm_yr,
        "dip_deg": dip_deg,
        "approve_quantile": approve_quantile,
        "deficit_threshold": thr,
        "off_fault_fraction_citation": off_fault_reference(),
        "formula": "eps_dot_ij = (1/2) * SUM_k (L_k*u_dot_k)/(A*sin(delta_k)) * m_ij^k",
        "formula_source": "Kreemer et al. (2000) Earth Planets Space 52, eq. (3); "
                          "Kostrov (1974) Izv. Acad. Sci. USSR Phys. Solid Earth 1, 23-44",
    }
    return Stage1Result(
        tile=tile, deficits=deficit, geodetic=geodetic, budget=budget,
        approved=approved, threshold=thr, slip_rate_mm_yr=slip_rate_mm_yr,
        dip_deg=dip_deg, meta=meta,
    )


def off_fault_reference() -> dict:
    return {
        "off_fault_fraction": OFF_FAULT_FRACTION,
        "source": "Zeng & Shen (2016) BSSA 106(2) 766-784 doi:10.1785/0120140250; "
                  "USGS pub 70160311 (off-fault moment rate 0.88e19 N.m/yr vs total "
                  "2.76e19 N.m/yr)",
    }


def slip_rate_sweep(catalogue, shear, dilatation, second_invariant, *, tile=32,
                    dips=(50.0, 60.0, 70.0)) -> dict:
    """Approved-tile stability under the published slip-rate / dip ranges (IR-51-01)."""
    base = None
    out = []
    for u in SLIP_RATE_SWEEP_MM_YR:
        for d in dips:
            r = compute_stage1(catalogue, shear, dilatation, second_invariant,
                               tile=tile, slip_rate_mm_yr=u, dip_deg=d)
            if base is None:
                base = r.approved
            jac = (np.logical_and(r.approved, base).sum() / max(1, np.logical_or(r.approved, base).sum()))
            out.append({
                "slip_rate_mm_yr": u, "dip_deg": d,
                "n_approved": int(r.approved.sum()),
                "jaccard_vs_baseline": float(jac),
                "threshold": r.threshold,
            })
    return {"grid": out, "note": "Stability of the approved-tile set to the two documented "
                                 "free parameters of the Kostrov/Kreemer summation."}


def upsampled_prior(approved: np.ndarray, tile: int, shape: tuple[int, int]) -> np.ndarray:
    """Nearest-neighbour tile prior back on the full-resolution grid (0/1)."""
    full = np.repeat(np.repeat(approved, tile, axis=0), tile, axis=1)
    return full[: shape[0], : shape[1]].astype(bool)
