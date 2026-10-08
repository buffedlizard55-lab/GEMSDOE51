"""K2-08 basement-edge-conditioned conductive-ribbon operator.

The operator is intentionally separate from H-E's single-field edge banks and
H-H's conductivity-weighted endpoint bridges. It estimates an independent
basement-edge axis, contrasts conductivity at that axis against two flanks, and
measures whether the signed cross-edge contrast persists along the axis.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def normalized_gradient(field: np.ndarray, valid: np.ndarray, sigma: float):
    """Mask-normalized Gaussian first derivatives in (row, column) coordinates."""
    field = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(field)
    if field.ndim != 2 or field.shape != valid.shape:
        raise ValueError("field and valid mask must be same-shaped 2-D arrays")
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma must be positive and finite")
    safe = np.where(valid, field, 0.0).astype(np.float32)
    mask_f = valid.astype(np.float32)
    den = ndi.gaussian_filter(mask_f, sigma, order=0, mode="nearest")
    gx_num = ndi.gaussian_filter(safe, sigma, order=(0, 1), mode="nearest")
    gy_num = ndi.gaussian_filter(safe, sigma, order=(1, 0), mode="nearest")
    gx = np.full(field.shape, np.nan, dtype=np.float32)
    gy = np.full(field.shape, np.nan, dtype=np.float32)
    good = valid & (den >= 0.2)
    np.divide(gx_num, den, out=gx, where=good)
    np.divide(gy_num, den, out=gy, where=good)
    return gx, gy


def conditioned_ribbon_features(basement: np.ndarray,
                                conductivity: np.ndarray,
                                support: np.ndarray,
                                sigma: float,
                                edge_threshold: float,
                                along_offsets=(-5.0, -2.5, 0.0, 2.5, 5.0),
                                cross_half_width: float | None = None) -> dict[str, np.ndarray]:
    """Compute raw K2 ribbon contrast and signed along-edge persistence.

    At each supported basement-edge centre, let ``n`` be the normalized
    basement-depth gradient and ``t`` its tangent. For each tangent offset j,

        d_j = C(x+j*t) - 0.5 * [C(x+j*t+w*n) + C(x+j*t-w*n)].

    The contrast channel is median(|d_j|); the persistence channel is
    |mean(d_j)| / (mean(|d_j|) + 1e-12). They accept either conductive or
    resistive polarity. Bilinear conductivity samples are valid only if the
    entire interpolation neighborhood lies in the common support.

    ``edge_threshold`` is determined outside this function from a deterministic,
    label-free sample of basement-gradient magnitudes. Off-edge, valid pixels are
    zero; invalid footprint pixels and edge pixels whose samples cross a gap are
    NaN.
    """
    basement = np.asarray(basement, dtype=np.float32)
    conductivity = np.asarray(conductivity, dtype=np.float32)
    support = np.asarray(support, dtype=bool)
    if basement.ndim != 2 or basement.shape != conductivity.shape or basement.shape != support.shape:
        raise ValueError("basement, conductivity and support must be equal-shaped 2-D arrays")
    if not np.isfinite(edge_threshold) or edge_threshold < 0:
        raise ValueError("edge_threshold must be finite and nonnegative")
    if cross_half_width is None:
        cross_half_width = 1.5 * float(sigma)
    if not np.isfinite(cross_half_width) or cross_half_width <= 0:
        raise ValueError("cross_half_width must be positive and finite")
    offsets = np.asarray(tuple(along_offsets), dtype=np.float32)
    if offsets.size == 0 or not np.isfinite(offsets).all():
        raise ValueError("along_offsets must contain finite offsets")

    valid = support & np.isfinite(basement) & np.isfinite(conductivity)
    gx, gy = normalized_gradient(basement, valid, sigma)
    magnitude = np.hypot(gx, gy)
    edge = valid & np.isfinite(magnitude) & (magnitude >= edge_threshold) & (magnitude > 1e-12)
    nx = np.zeros(basement.shape, dtype=np.float32)
    ny = np.zeros(basement.shape, dtype=np.float32)
    np.divide(gx, magnitude, out=nx, where=edge)
    np.divide(gy, magnitude, out=ny, where=edge)
    # A tangent in (column, row) image coordinates, perpendicular to the normal.
    tx, ty = -ny, nx

    safe_cond = np.where(valid, conductivity, 0.0).astype(np.float32)
    valid_f = valid.astype(np.float32)
    height, width = basement.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    deltas = np.zeros((offsets.size, height, width), dtype=np.float32)
    all_samples_valid = np.ones((height, width), dtype=bool)

    def sample(field, sample_y, sample_x):
        coords = [sample_y.astype(np.float32), sample_x.astype(np.float32)]
        values = ndi.map_coordinates(field, coords, order=1, mode="constant", cval=0.0)
        coverage = ndi.map_coordinates(valid_f, coords, order=1, mode="constant", cval=0.0)
        return values, coverage >= (1.0 - 1e-5)

    for i, offset in enumerate(offsets):
        cy = yy + offset * ty
        cx = xx + offset * tx
        centre, centre_ok = sample(safe_cond, cy, cx)
        plus, plus_ok = sample(safe_cond, cy + cross_half_width * ny,
                               cx + cross_half_width * nx)
        minus, minus_ok = sample(safe_cond, cy - cross_half_width * ny,
                                 cx - cross_half_width * nx)
        valid_samples = centre_ok & plus_ok & minus_ok
        all_samples_valid &= valid_samples
        deltas[i] = centre - 0.5 * (plus + minus)

    mean_abs = np.mean(np.abs(deltas), axis=0)
    mean_signed = np.mean(deltas, axis=0)
    contrast = np.median(np.abs(deltas), axis=0).astype(np.float32)
    persistence = (np.abs(mean_signed) / (mean_abs + 1e-12)).astype(np.float32)

    contrast_out = np.zeros(basement.shape, dtype=np.float32)
    persistence_out = np.zeros(basement.shape, dtype=np.float32)
    contrast_out[edge] = contrast[edge]
    persistence_out[edge] = persistence[edge]
    invalid_edge = edge & ~all_samples_valid
    contrast_out[invalid_edge] = np.nan
    persistence_out[invalid_edge] = np.nan
    contrast_out[~valid] = np.nan
    persistence_out[~valid] = np.nan
    return dict(contrast=contrast_out, persistence=persistence_out, edge_mask=edge)


def average_tie_rank01(values: np.ndarray, selected: np.ndarray) -> np.ndarray:
    """Average-tie ranks on selected cells; non-selected valid cells get zero."""
    from scipy.stats import rankdata

    values = np.asarray(values, dtype=np.float32)
    selected = np.asarray(selected, dtype=bool) & np.isfinite(values)
    out = np.zeros(values.shape, dtype=np.float32)
    if not selected.any():
        return out
    v = values[selected]
    if v.size == 1 or float(v.max()) == float(v.min()):
        out[selected] = 0.5
        return out
    out[selected] = ((rankdata(v, method="average") - 1.0) / (v.size - 1.0)).astype(np.float32)
    return out
