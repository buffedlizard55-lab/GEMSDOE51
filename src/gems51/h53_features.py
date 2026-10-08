"""H53-A finite-lag cross-physics edge features.

The operator tests whether a gravity edge lies a bounded, non-zero distance
along either side of a detrended-elevation edge normal.  It is a structural
hypothesis, not a fault detector by itself; coincident lithologic contacts and
interpolation artifacts remain plausible alternatives.

The output layer names and scales are frozen in
``registry/preregistration_h53.json``.  It uses no labels, catalogue distance,
or holdout state.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

from .stack import _nc_deriv


def _rank_nonzero(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Tie-aware empirical rank of positive finite magnitudes; zero is no edge."""
    a = np.asarray(values, dtype=np.float32)
    m = np.asarray(valid, dtype=bool) & np.isfinite(a)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    out[m] = 0.0
    nz = m & (a > 0.0)
    if not nz.any():
        return out
    selected = a[nz].astype(np.float64)
    if selected.size == 1 or float(selected.max()) == float(selected.min()):
        out[nz] = 1.0 if selected.size == 1 else 0.5
        return out
    r = rankdata(selected, method="average")
    out[nz] = ((r - 1.0) / (selected.size - 1.0)).astype(np.float32)
    return out


def _unit_gradient(field: np.ndarray, valid: np.ndarray, sigma: float):
    """Mask-normalized x/y gradients, magnitude, and unoriented unit normal."""
    gx = _nc_deriv(field, valid, sigma, [0, 1])
    gy = _nc_deriv(field, valid, sigma, [1, 0])
    mag = np.hypot(gx, gy).astype(np.float32)
    ok = np.asarray(valid, dtype=bool) & np.isfinite(gx) & np.isfinite(gy) & np.isfinite(mag)
    ux = np.zeros(mag.shape, dtype=np.float32)
    uy = np.zeros(mag.shape, dtype=np.float32)
    nz = ok & (mag > 1e-12)
    np.divide(gx, mag, out=ux, where=nz)
    np.divide(gy, mag, out=uy, where=nz)
    mag[~ok] = np.nan
    return ux, uy, mag, ok


def finite_lag_edge_features(
    detrended_elevation: np.ndarray,
    isostatic_gravity: np.ndarray,
    valid: np.ndarray,
    *,
    sigmas: tuple[float, ...] = (2.0, 5.0),
    max_lag_px: int = 8,
) -> dict[str, np.ndarray]:
    """Compute the six preregistered H53-A fields.

    For each sigma (2 and 5 pixels in the frozen experiment):

    * rank nonzero gradient magnitudes over valid footprint cells;
    * calculate a zero-lag geometric-mean edge response weighted by the
      absolute cosine of the two edge-normal directions;
    * search both signs of the elevation-gradient normal at lags 1..8 pixels;
      retain the largest similarly oriented gravity-edge response and the
      signed winning lag divided by 8.

    The signed direction is relative to the gradient of the fixed elevation
    product (toward increasing detrended elevation is positive).  It is not a
    geologic fault dip or a tectonic displacement sign.  Missing input samples
    remain missing; invalid interpolation samples are ignored.  Feature
    magnitudes and lag scalars are bounded in [0,1] and [-1,1], respectively.
    """
    z = np.asarray(detrended_elevation, dtype=np.float32)
    g = np.asarray(isostatic_gravity, dtype=np.float32)
    m = np.asarray(valid, dtype=bool)
    if z.ndim != 2 or z.shape != g.shape or z.shape != m.shape:
        raise ValueError("elevation, gravity, and valid mask must be matching 2-D arrays")
    if not sigmas or any(not np.isfinite(s) or s <= 0 for s in sigmas):
        raise ValueError("sigmas must be a non-empty sequence of positive finite values")
    if isinstance(max_lag_px, bool) or int(max_lag_px) != max_lag_px or max_lag_px < 1:
        raise ValueError("max_lag_px must be a positive integer")

    common = m & np.isfinite(z) & np.isfinite(g)
    safe_z = np.where(common, z, 0.0).astype(np.float32)
    safe_g = np.where(common, g, 0.0).astype(np.float32)
    outputs: dict[str, np.ndarray] = {}
    rows, cols = np.indices(z.shape, dtype=np.float32)

    for sigma in sigmas:
        suffix = f"s{int(round(float(sigma) * 10)):02d}"
        ux, uy, zm, zok = _unit_gradient(safe_z, common, float(sigma))
        vx, vy, gm, gok = _unit_gradient(safe_g, common, float(sigma))
        base_valid = common & zok & gok & np.isfinite(zm) & np.isfinite(gm)
        zr = _rank_nonzero(zm, base_valid)
        gr = _rank_nonzero(gm, base_valid)

        zero = np.zeros(z.shape, dtype=np.float32)
        dot0 = np.abs(ux * vx + uy * vy)
        zero[base_valid] = np.sqrt(np.maximum(zr[base_valid] * gr[base_valid], 0.0)) * dot0[base_valid]
        zero[~common] = np.nan

        best = np.zeros(z.shape, dtype=np.float32)
        best_lag = np.zeros(z.shape, dtype=np.float32)
        # Interpolation buffers are zero-filled only for sampling; ``common``
        # is sampled separately so nodata edges cannot become positive evidence.
        gr_safe = np.nan_to_num(gr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        vx_safe = np.where(base_valid, vx, 0.0).astype(np.float32)
        vy_safe = np.where(base_valid, vy, 0.0).astype(np.float32)
        valid_sample = base_valid.astype(np.float32)

        for distance in range(1, int(max_lag_px) + 1):
            for side in (-1, 1):
                coords = np.stack((rows + side * distance * uy,
                                   cols + side * distance * ux), axis=0)
                sampled_valid = ndi.map_coordinates(
                    valid_sample, coords, order=0, mode="constant", cval=0.0,
                    prefilter=False,
                ) >= 0.5
                sampled_rank = ndi.map_coordinates(
                    gr_safe, coords, order=1, mode="constant", cval=0.0,
                    prefilter=False,
                )
                sampled_x = ndi.map_coordinates(
                    vx_safe, coords, order=1, mode="constant", cval=0.0,
                    prefilter=False,
                )
                sampled_y = ndi.map_coordinates(
                    vy_safe, coords, order=1, mode="constant", cval=0.0,
                    prefilter=False,
                )
                sampled_norm = np.hypot(sampled_x, sampled_y)
                alignment = np.zeros(z.shape, dtype=np.float32)
                orient_valid = sampled_valid & (sampled_norm > 1e-8)
                np.divide(
                    np.abs(ux * sampled_x + uy * sampled_y),
                    sampled_norm,
                    out=alignment,
                    where=orient_valid,
                )
                np.clip(alignment, 0.0, 1.0, out=alignment)
                response = np.sqrt(np.maximum(zr * sampled_rank, 0.0)) * alignment
                response[~(base_valid & orient_valid)] = 0.0
                update = response > best
                best[update] = response[update]
                best_lag[update] = np.float32(side * distance / float(max_lag_px))
                del coords, sampled_valid, sampled_rank, sampled_x, sampled_y
                del sampled_norm, alignment, response, update

        best[~common] = np.nan
        best_lag[~common] = np.nan
        outputs[f"h53_zero_coedge_{suffix}"] = zero
        outputs[f"h53_offset_coedge_{suffix}"] = best
        outputs[f"h53_signed_lag_{suffix}"] = best_lag
        del ux, uy, zm, zok, vx, vy, gm, gok, base_valid, zr, gr
        del zero, best, best_lag, gr_safe, vx_safe, vy_safe, valid_sample

    return outputs
