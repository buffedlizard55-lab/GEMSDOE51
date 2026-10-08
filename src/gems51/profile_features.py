"""Catalogue-independent odd/even topographic normal profiles (P1).

Features are hypotheses, not displacement or slip-rate measurements. Sampling
uses only image values and is invariant to adding a constant datum. Invalid
shoulders yield NaN rather than fabricated evidence.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def profile_features(elevation, mask, sigma=2.0, offsets=(2.0, 5.0)):
    z = np.asarray(elevation, dtype=np.float32)
    valid = np.asarray(mask, dtype=bool) & np.isfinite(z)
    if z.ndim != 2 or valid.shape != z.shape:
        raise ValueError("elevation and mask must be matching 2D arrays")
    if sigma <= 0 or len(offsets) != 2 or not 0 < offsets[0] < offsets[1]:
        raise ValueError("positive sigma and two increasing positive offsets required")
    den = ndi.gaussian_filter(valid.astype(np.float32), sigma, mode="nearest")
    smooth = ndi.gaussian_filter(
        np.where(valid, z, 0), sigma, mode="nearest"
    ) / np.maximum(den, 1e-8)
    # Differentiate the quotient, NOT a derivative numerator divided by support.
    gy, gx = np.gradient(smooth)
    mag = np.hypot(gx, gy)
    nx = gx / np.maximum(mag, 1e-8)
    ny = gy / np.maximum(mag, 1e-8)
    yy, xx = np.indices(z.shape, dtype=np.float32)
    good = valid & (den > 0.99)
    odd, even = [], []
    for d in offsets:
        samples = []
        for sign in (-1, 1):
            coords = [yy + sign * d * ny, xx + sign * d * nx]
            support = ndi.map_coordinates(
                valid.astype(np.float32), coords, order=1, mode="constant", cval=0
            )
            sample = ndi.map_coordinates(
                np.where(valid, z, 0), coords, order=1, mode="constant", cval=0
            )
            good &= support > 0.999
            samples.append(sample)
        lo, hi = samples
        odd.append((hi - lo) * 0.5)
        even.append((hi + lo) * 0.5 - z)
    scale = np.abs(odd[1]) + np.abs(even[1]) + 1e-6
    values = {
        "p1_step_fraction": np.abs(odd[1]) / scale,
        "p1_near_far_agreement": np.maximum(odd[0] * odd[1], 0)
        / (odd[0] ** 2 + odd[1] ** 2 + 1e-12)
        * 2,
        "p1_even_fraction": np.abs(even[0]) / (np.abs(odd[0]) + np.abs(even[0]) + 1e-6),
    }
    for k, v in values.items():
        v[mag < 1e-8] = 0
        values[k] = np.where(good, v, np.nan).astype(np.float32)
    return values
