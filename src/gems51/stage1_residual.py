"""Componentwise geodetic-minus-fault strain residuals for coarse Stage 1.

This module deliberately stops at a broad-tile prior. It does not turn a scalar
residual into a fine-scale fault location. The source uses a separate unit-scale
factor (e.g. 1e-8 strain/yr per geodetic unit), while ``vector_budget`` returns
physical yr^-1 tensor components.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
from scipy.stats import rankdata

from .vector_budget import clip_segment


def component_residual(observed_source_units: np.ndarray,
                       modeled_rate_per_year: np.ndarray,
                       unit_factor: float) -> np.ndarray:
    """Subtract a modeled physical scalar rate from a source-unit observation.

    ``observed_source_units * unit_factor`` is the observed physical rate in
    yr^-1. The returned residual remains in the geodetic source's numeric units,
    so it can be interpreted and ranked without mixing unit conventions.
    """
    obs = np.asarray(observed_source_units, dtype=np.float64)
    modeled = np.asarray(modeled_rate_per_year, dtype=np.float64)
    if obs.shape != modeled.shape:
        raise ValueError("observed and modeled arrays must have identical shapes")
    if not np.isfinite(unit_factor) or unit_factor <= 0:
        raise ValueError("unit_factor must be finite and positive")
    out = np.full(obs.shape, np.nan, dtype=np.float64)
    valid = np.isfinite(obs) & np.isfinite(modeled)
    out[valid] = obs[valid] - modeled[valid] / float(unit_factor)
    return out


def positive_empirical_rank(values: np.ndarray,
                            valid: np.ndarray | None = None) -> np.ndarray:
    """Rank the positive part of a residual to [0, 1], leaving invalid cells NaN.

    Exact ties receive average ranks. A constant valid field maps to zero, so a
    physically uninformative constant residual cannot masquerade as a gradient.
    """
    values = np.asarray(values, dtype=np.float64)
    mask = np.isfinite(values)
    if valid is not None:
        valid = np.asarray(valid, dtype=bool)
        if valid.shape != values.shape:
            raise ValueError("valid mask must match values")
        mask &= valid
    out = np.full(values.shape, np.nan, dtype=np.float32)
    if not mask.any():
        return out
    selected = np.maximum(values[mask], 0.0)
    if selected.size <= 1 or float(selected.max()) <= float(selected.min()):
        out[mask] = 0.0
        return out
    ranks = rankdata(selected, method="average")
    out[mask] = ((ranks - 1.0) / (selected.size - 1.0)).astype(np.float32)
    return out


def combined_deficit_rank(dilatation_residual: np.ndarray,
                          shear_residual: np.ndarray,
                          valid: np.ndarray | None = None) -> np.ndarray:
    """Preregistered equal-weight combination of positive dilation/shear ranks."""
    dil = np.asarray(dilatation_residual)
    shr = np.asarray(shear_residual)
    if dil.shape != shr.shape:
        raise ValueError("dilatation and shear residuals must have identical shapes")
    valid_mask = np.isfinite(dil) & np.isfinite(shr)
    if valid is not None:
        valid = np.asarray(valid, dtype=bool)
        if valid.shape != dil.shape:
            raise ValueError("valid mask must match residual arrays")
        valid_mask &= valid
    q_dil = positive_empirical_rank(dil, valid_mask)
    q_shr = positive_empirical_rank(shr, valid_mask)
    out = np.full(dil.shape, np.nan, dtype=np.float32)
    out[valid_mask] = 0.5 * (q_dil[valid_mask] + q_shr[valid_mask])
    return out


def approved_domain(score: np.ndarray, footprint: np.ndarray,
                    lower_percentile: float = 10.0) -> tuple[np.ndarray, float]:
    """Approve score >= fixed lower quantile; return mask and threshold.

    A q10 threshold is the broadest tested domain (nominally 90% approved).
    Ties can make the realized approved area larger than 90%; that is reported,
    not broken with a label-informed tie rule.
    """
    score = np.asarray(score, dtype=np.float64)
    footprint = np.asarray(footprint, dtype=bool)
    if score.shape != footprint.shape:
        raise ValueError("score and footprint must have identical shapes")
    if not 0.0 <= lower_percentile < 100.0:
        raise ValueError("lower_percentile must be in [0, 100)")
    valid = footprint & np.isfinite(score)
    if not valid.any():
        raise ValueError("no finite score pixels in footprint")
    threshold = float(np.nanpercentile(score[valid], lower_percentile))
    approved = valid & (score >= threshold)
    return approved, threshold


def records_intersecting_block(segments: Iterable[Mapping],
                               bounds_rc: tuple[int, int, int, int],
                               buffer_px: int = 12,
                               transform: tuple[float, float, float, float, float, float]
                               = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
                               pixel_m: float = 100.0) -> set[int]:
    """Return source record IDs whose actual segment intersects a buffered block.

    ``bounds_rc`` is ``(row_start, row_stop, col_start, col_stop)`` with stop
    indices exclusive. The rectangular block is transformed to projected map
    coordinates; every intersecting source record is excluded as a whole before
    building a held-out Stage-1 fault budget.
    """
    r0, r1, c0, c1 = map(int, bounds_rc)
    if r1 <= r0 or c1 <= c0 or buffer_px < 0 or pixel_m <= 0:
        raise ValueError("invalid block bounds, buffer, or pixel size")
    a, b, x_origin, d, e, y_origin = map(float, transform)
    if b != 0.0 or d != 0.0 or a <= 0.0 or e >= 0.0:
        raise ValueError("records_intersecting_block requires north-up, unrotated grid")
    if not np.isclose(a, pixel_m) or not np.isclose(abs(e), pixel_m):
        raise ValueError("pixel_m must match the grid transform resolution")
    pad = float(buffer_px) * float(pixel_m)
    xmin = x_origin + c0 * pixel_m - pad
    xmax = x_origin + c1 * pixel_m + pad
    ymax = y_origin - r0 * pixel_m + pad
    ymin = y_origin - r1 * pixel_m - pad
    found: set[int] = set()
    for row in segments:
        rid = int(row["record_id"])
        x0, y0 = float(row["x0"]), float(row["y0"])
        x1, y1 = float(row["x1"]), float(row["y1"])
        # Cheap envelope rejection avoids invoking exact clipping for most lines.
        if (max(x0, x1) < xmin or min(x0, x1) > xmax
                or max(y0, y1) < ymin or min(y0, y1) > ymax):
            continue
        if clip_segment(x0, y0, x1, y1, xmin, ymin, xmax, ymax) is not None:
            found.add(rid)
    return found
