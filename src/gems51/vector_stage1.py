"""Source-corrected, coarse tile Stage-1 strain-budget prior.

This module does not locate fault points.  It converts clipped official QFaults
trace segments to a 10 km horizontal strain tensor using Kreemer et al. (2000),
Eq. 3, then compares source-defined dilation and shear summaries with the
geodetic tile means.  Raw residuals are kept; only their equal-weight empirical
ranks define a broad allowed-domain prior.

Slip component, per-trace dip/rake, and the literal geodetic unit notation are
not fully resolved.  Callers must choose and record those assumptions rather
than silently infer them from a residual.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata


def _rank01(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Tie-aware empirical rank in [0,1], preserving NaN outside ``valid``."""
    a = np.asarray(values, dtype=np.float64)
    m = np.asarray(valid, dtype=bool) & np.isfinite(a)
    out = np.full(a.shape, np.nan, dtype=np.float64)
    if not m.any():
        return out
    selected = a[m]
    if selected.size == 1:
        out[m] = 0.5
    else:
        out[m] = (rankdata(selected, method="average") - 1.0) / (selected.size - 1.0)
    return out


def residual_rank_prior(
    observed_dilatation: np.ndarray,
    observed_shear: np.ndarray,
    predicted_dilatation_per_year: np.ndarray,
    predicted_shear_per_year: np.ndarray,
    valid_tiles: np.ndarray,
    *,
    geodetic_rate_scale: float = 1e-8,
) -> dict[str, np.ndarray | float]:
    """Return raw dilation/shear residuals and their equal-rank coarse prior.

    If a source raster value represents ``geodetic_rate_scale / year``, its
    numeric rate is ``observed * geodetic_rate_scale``.  Therefore a tensor
    rate in 1/year is expressed in source-raster numeric units by division by
    ``geodetic_rate_scale``.  The subtraction is performed on both documented
    scalar summaries, not on an unsupported full observed tensor.
    """
    arrays = [
        np.asarray(observed_dilatation, dtype=np.float64),
        np.asarray(observed_shear, dtype=np.float64),
        np.asarray(predicted_dilatation_per_year, dtype=np.float64),
        np.asarray(predicted_shear_per_year, dtype=np.float64),
        np.asarray(valid_tiles, dtype=bool),
    ]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays[1:]):
        raise ValueError("observed/predicted tile arrays and valid mask must match")
    if (not np.isfinite(geodetic_rate_scale)) or geodetic_rate_scale <= 0:
        raise ValueError("geodetic_rate_scale must be positive and finite")
    obs_d, obs_s, pred_d, pred_s, valid = arrays
    valid = valid & np.isfinite(obs_d) & np.isfinite(obs_s) & np.isfinite(pred_d) & np.isfinite(pred_s)
    r_dil = np.full(shape, np.nan, dtype=np.float64)
    r_shear = np.full(shape, np.nan, dtype=np.float64)
    r_dil[valid] = obs_d[valid] - pred_d[valid] / geodetic_rate_scale
    r_shear[valid] = obs_s[valid] - pred_s[valid] / geodetic_rate_scale
    rank_dil = _rank01(r_dil, valid)
    rank_shear = _rank01(r_shear, valid)
    score = np.full(shape, np.nan, dtype=np.float64)
    score[valid] = 0.5 * (rank_dil[valid] + rank_shear[valid])
    return {
        "dilatation_residual": r_dil,
        "shear_residual": r_shear,
        "rank_dilatation": rank_dil,
        "rank_shear": rank_shear,
        "prior_score": score,
        "geodetic_rate_scale": float(geodetic_rate_scale),
    }


def approved_pixel_mask(
    prior_score_tiles: np.ndarray,
    footprint: np.ndarray,
    *,
    tile_px: int = 100,
    q: float = 10.0,
) -> tuple[np.ndarray, float, float]:
    """Upsample a broad tile score and approve scores at/above quantile ``q``."""
    tiles = np.asarray(prior_score_tiles, dtype=np.float64)
    fp = np.asarray(footprint, dtype=bool)
    if tiles.ndim != 2 or fp.ndim != 2 or tile_px < 1:
        raise ValueError("2-D tile score/footprint and positive tile_px are required")
    if not 0.0 <= q < 100.0:
        raise ValueError("q must be in [0,100)")
    big = np.repeat(np.repeat(tiles, int(tile_px), axis=0), int(tile_px), axis=1)
    if big.shape[0] < fp.shape[0] or big.shape[1] < fp.shape[1]:
        raise ValueError("tile score grid does not cover the raster footprint")
    big = big[:fp.shape[0], :fp.shape[1]]
    valid = fp & np.isfinite(big)
    if not valid.any():
        raise ValueError("no finite Stage-1 tiles overlap the footprint")
    threshold = float(np.nanpercentile(big[valid], q))
    approved = valid & (big >= threshold)
    area_share = float(approved.sum() / max(int(fp.sum()), 1))
    return approved, threshold, area_share
