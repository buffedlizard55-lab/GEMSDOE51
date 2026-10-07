"""Tests for the preregistered H-H endpoint/relay operator."""

import numpy as np

from gems51.extras import _paired_bridge


def test_paired_bridge_requires_offset_endpoints_and_connects_the_relay():
    a = np.full((40, 40), np.nan, dtype=np.float32)
    b = np.full((40, 40), np.nan, dtype=np.float32)
    a[20, 10] = 1.0
    b[20, 20] = 1.0

    bridge = _paired_bridge(a, b, min_px=3.0, max_px=20.0)

    assert np.isfinite(bridge[20, 15])
    assert bridge[20, 15] > 0


def test_paired_bridge_rejects_coincident_endpoints():
    a = np.full((20, 20), np.nan, dtype=np.float32)
    b = np.full((20, 20), np.nan, dtype=np.float32)
    a[10, 10] = 1.0
    b[10, 10] = 1.0

    bridge = _paired_bridge(a, b, min_px=3.0, max_px=20.0)

    assert not np.isfinite(bridge).any()
