"""Structural-intersection features from independent geophysical edge fields.

The operator is intentionally static (no catalogue inputs): it measures whether
strong magnetic and gravity boundaries meet at a high angle, a geometry that can
mark transfer/intersection zones. It is a structural proxy, not a fault label.
"""
from __future__ import annotations

import numpy as np


def axial_intersection_score(gx_a, gy_a, gx_b, gy_b, scale_a: float, scale_b: float,
                             eps: float = 1e-8):
    """Return (angle-discordance, edge-strength-weighted crossing score).

    Gradient orientation is axial: reversing either gradient does not change the
    lineament orientation. ``angle_discordance`` is 0 for parallel edges and 1
    for perpendicular edges. The weighted score is zero when either gradient is
    zero and otherwise scales discordance by both normalized edge magnitudes.
    ``scale_a`` and ``scale_b`` are robust magnitude scales (e.g. footprint p95).
    """
    ax, ay, bx, by = (np.asarray(v, dtype=np.float32)
                      for v in (gx_a, gy_a, gx_b, gy_b))
    ma = np.hypot(ax, ay)
    mb = np.hypot(bx, by)
    denom = np.maximum(ma * mb, eps)
    alignment = np.abs((ax * bx + ay * by) / denom)
    discordance = np.clip(1.0 - alignment, 0.0, 1.0)
    sa = np.clip(ma / max(float(scale_a), eps), 0.0, 1.0)
    sb = np.clip(mb / max(float(scale_b), eps), 0.0, 1.0)
    strength = np.sqrt(sa * sb)
    score = discordance * strength
    score[(ma <= eps) | (mb <= eps)] = 0.0
    return discordance.astype(np.float32), score.astype(np.float32)
