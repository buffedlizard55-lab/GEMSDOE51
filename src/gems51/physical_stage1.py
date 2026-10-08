"""Physical dilation/shear residual prior for broad spatial tiles.

This module is deliberately separate from the legacy rank-space second-invariant
prior in ``gems51.stage1``. It sums source fault vectors with
``vector_budget.budget_prepared``, derives source-defined dilation/shear from the
summed tensor, converts supplied geodetic scalar values under explicit scale
scenarios, and subtracts corresponding physical scalar terms. The output is a
rank-ensemble tile prior only; it is not a calibrated tensor inversion or a
fine-scale fault locator.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

from .vector_budget import PreparedSegments, budget_prepared, summaries


GEODETIC_SCALES_PER_YEAR = (1e-9, 1e-8)
RATE_CONVENTIONS = ("fault_plane", "vertical")


def _tile_sums(values: np.ndarray, mask: np.ndarray, tile_px: int):
    values = np.asarray(values, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool) & np.isfinite(values)
    h, w = values.shape
    ny = (h + tile_px - 1) // tile_px
    nx = (w + tile_px - 1) // tile_px
    ph, pw = ny * tile_px, nx * tile_px
    sums = np.zeros((ph, pw), dtype=np.float64)
    counts = np.zeros((ph, pw), dtype=np.float64)
    sums[:h, :w] = np.where(mask, values, 0.0)
    counts[:h, :w] = mask
    return (sums.reshape(ny, tile_px, nx, tile_px).sum(axis=(1, 3)),
            counts.reshape(ny, tile_px, nx, tile_px).sum(axis=(1, 3)))


def observed_tile_mean(values: np.ndarray, support: np.ndarray, tile_px: int) -> np.ndarray:
    """Mean observed scalar in each tile on one common finite geodetic support."""
    values = np.asarray(values, dtype=np.float64)
    support = np.asarray(support, dtype=bool)
    if values.shape != support.shape:
        raise ValueError("observed values and support must have the same shape")
    if int(tile_px) != tile_px or tile_px <= 0:
        raise ValueError("tile_px must be a positive integer")
    sums, counts = _tile_sums(values, support, int(tile_px))
    out = np.full(sums.shape, np.nan, dtype=np.float64)
    np.divide(sums, counts, out=out, where=counts > 0)
    return out


def rank01(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Average-tie empirical rank in [0,1]; invalid cells remain NaN."""
    values = np.asarray(values, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(values)
    if values.shape != valid.shape:
        raise ValueError("rank input and validity mask must have the same shape")
    out = np.full(values.shape, np.nan, dtype=np.float64)
    n = int(valid.sum())
    if not n:
        return out
    if n == 1:
        out[valid] = 0.5
        return out
    ranks = rankdata(values[valid], method="average")
    out[valid] = (ranks - 1.0) / (n - 1.0)
    return out


def _residual_stats(residual: np.ndarray, valid: np.ndarray) -> dict:
    v = np.asarray(residual, dtype=np.float64)[np.asarray(valid, dtype=bool)]
    if not v.size:
        return dict(n_tiles=0)
    return dict(
        n_tiles=int(v.size),
        min=float(np.min(v)),
        p10=float(np.percentile(v, 10)),
        median=float(np.median(v)),
        p90=float(np.percentile(v, 90)),
        max=float(np.max(v)),
        positive_fraction=float(np.mean(v > 0.0)),
    )


def physical_residual_prior(prepared: PreparedSegments,
                            observed_dilatation: np.ndarray,
                            observed_shear: np.ndarray,
                            support: np.ndarray,
                            excluded_records=(),
                            approved_quantile: float = 10.0,
                            geodetic_scales=GEODETIC_SCALES_PER_YEAR,
                            rate_conventions=RATE_CONVENTIONS,
                            normal_dip_deg: float = 60.0) -> dict:
    """Build a physical scalar-residual prior from dilation and shear scenarios.

    For each rate-component convention and each plausible geodetic unit scale,
    the signed residuals are

        R_D = scale * observed_dilatation - fault_tensor_dilatation
        R_S = scale * observed_shear      - fault_tensor_scalar_shear.

    Both residuals are ranked over the same eligible tiles. Their ranks are
    averaged within scenario and then across scenarios. No second-invariant
    residual enters this prior.
    """
    dil = np.asarray(observed_dilatation, dtype=np.float64)
    shear_obs = np.asarray(observed_shear, dtype=np.float64)
    support = np.asarray(support, dtype=bool)
    if dil.shape != shear_obs.shape or dil.shape != support.shape:
        raise ValueError("dilation, shear and common support must have equal shapes")
    if not (0.0 <= approved_quantile <= 100.0):
        raise ValueError("approved_quantile must be in [0, 100]")
    excluded_records = tuple(excluded_records)
    rate_conventions = tuple(rate_conventions)
    geodetic_scales = tuple(float(x) for x in geodetic_scales)
    if not rate_conventions or not geodetic_scales:
        raise ValueError("at least one rate convention and unit scale are required")
    if tuple(prepared.area_by_tile_m2.shape) != tuple(prepared.tile_shape):
        raise ValueError("prepared tile area and shape disagree")
    if int(np.ceil(dil.shape[0] / prepared.tile_px)) != prepared.tile_shape[0] or \
       int(np.ceil(dil.shape[1] / prepared.tile_px)) != prepared.tile_shape[1]:
        raise ValueError("prepared tile grid does not match observation grid and tile size")

    obs_dil = observed_tile_mean(dil, support, prepared.tile_px)
    obs_shear = observed_tile_mean(shear_obs, support, prepared.tile_px)
    tile_valid = ((prepared.area_by_tile_m2 > 0.0)
                  & np.isfinite(obs_dil) & np.isfinite(obs_shear))
    if not tile_valid.any():
        raise ValueError("no tiles have common finite geodetic support")

    scenario_results = {}
    scenario_scores = []
    for convention in rate_conventions:
        tensor, budget_meta = budget_prepared(
            prepared, excluded=excluded_records, convention=convention,
            normal_dip_deg=normal_dip_deg,
        )
        if tensor.shape[1:] != obs_dil.shape:
            raise ValueError("fault tensor tiles and observed tiles do not match")
        fault_scalar = summaries(*tensor)
        for scale in geodetic_scales:
            scale = float(scale)
            if not np.isfinite(scale) or scale <= 0:
                raise ValueError("geodetic unit scales must be positive and finite")
            rd = obs_dil * scale - fault_scalar["dilatation"]
            rs = obs_shear * scale - fault_scalar["shear"]
            valid = tile_valid & np.isfinite(rd) & np.isfinite(rs)
            rd_rank = rank01(rd, valid)
            rs_rank = rank01(rs, valid)
            scenario_score = 0.5 * (rd_rank + rs_rank)
            scenario_scores.append(scenario_score)
            key = f"{convention}_{scale:.0e}"
            scenario_results[key] = dict(
                rate_convention=convention,
                observed_strain_scale_per_year=scale,
                dilation_residual_per_year=_residual_stats(rd, valid),
                shear_residual_per_year=_residual_stats(rs, valid),
                budget=budget_meta,
            )

    score_stack = np.stack(scenario_scores, axis=0)
    score = np.full(obs_dil.shape, np.nan, dtype=np.float64)
    score[tile_valid] = np.mean(score_stack[:, tile_valid], axis=0)
    threshold = float(np.nanpercentile(score[tile_valid], approved_quantile))
    approved_tiles = tile_valid & (score >= threshold)

    pixel_tiles = np.repeat(np.repeat(approved_tiles, prepared.tile_px, axis=0),
                            prepared.tile_px, axis=1)
    pixel_tiles = pixel_tiles[:support.shape[0], :support.shape[1]]
    approved = pixel_tiles & support
    return dict(
        score=score,
        tile_valid=tile_valid,
        approved_tiles=approved_tiles,
        approved_mask=approved,
        threshold=threshold,
        approved_area_fraction=float(approved.sum() / max(int(support.sum()), 1)),
        approved_tile_fraction=float(approved_tiles.sum() / max(int(tile_valid.sum()), 1)),
        observed_dilatation_tiles=obs_dil,
        observed_shear_tiles=obs_shear,
        scenario_results=scenario_results,
        scenario_count=int(len(scenario_results)),
        rate_conventions=list(rate_conventions),
        geodetic_scales_per_year=[float(x) for x in geodetic_scales],
        excluded_trace_records=int(len(set(excluded_records))),
        normal_dip_deg=float(normal_dip_deg),
        tile_px=int(prepared.tile_px),
        tile_m=float(prepared.meta["tile_m"]),
        interpretation="signed physical dilation/shear residual ranks, averaged over unresolved rate-component and geodetic-unit scenarios; broad tile prior only",
    )
