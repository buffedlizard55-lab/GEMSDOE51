import numpy as np
import pytest

from gems51.h53_features import finite_lag_edge_features


def test_finite_lag_operator_detects_offset_and_zero_lag_control():
    h = w = 96
    rows, cols = np.mgrid[:h, :w]
    # A single vertical edge in elevation and a parallel gravity edge four
    # pixels east; broad constant backgrounds keep the gradients interpretable.
    elevation = (cols >= 40).astype(np.float32)
    gravity = (cols >= 44).astype(np.float32)
    valid = np.ones((h, w), dtype=bool)

    result = finite_lag_edge_features(
        elevation,
        gravity,
        valid,
        sigmas=(2.0,),
        max_lag_px=8,
    )
    zero = result["h53_zero_coedge_s20"]
    offset = result["h53_offset_coedge_s20"]
    lag = result["h53_signed_lag_s20"]

    # The offset response should be strongest near the elevation edge, while
    # the winning signed lag points toward increasing elevation's normal.
    roi = (slice(30, 66), slice(38, 42))
    assert np.nanmax(offset[roi]) > np.nanmax(zero[roi])
    row, col = np.unravel_index(np.nanargmax(offset[roi]), offset[roi].shape)
    assert lag[30 + row, 38 + col] > 0
    assert np.nanmin(offset) >= 0.0
    assert np.nanmax(offset) <= 1.0
    assert np.nanmin(lag) >= -1.0
    assert np.nanmax(lag) <= 1.0


def test_invalid_support_stays_missing_and_feature_names_are_stable():
    h = w = 40
    rows, cols = np.mgrid[:h, :w]
    valid = np.ones((h, w), dtype=bool)
    valid[:5, :] = False
    valid[15:18, 18:21] = False
    elevation = (cols >= 20).astype(np.float32)
    gravity = (cols >= 23).astype(np.float32)
    elevation[~valid] = np.nan
    gravity[~valid] = np.nan

    result = finite_lag_edge_features(elevation, gravity, valid, sigmas=(2.0, 5.0))
    assert list(result) == [
        "h53_zero_coedge_s20",
        "h53_offset_coedge_s20",
        "h53_signed_lag_s20",
        "h53_zero_coedge_s50",
        "h53_offset_coedge_s50",
        "h53_signed_lag_s50",
    ]
    for layer in result.values():
        assert np.isnan(layer[~valid]).all()
        assert np.isfinite(layer[valid]).all()


def test_constant_inputs_have_no_edge_or_lag():
    x = np.ones((24, 25), dtype=np.float32)
    result = finite_lag_edge_features(x, x.copy(), np.ones_like(x, dtype=bool), sigmas=(2.0,))
    assert np.all(result["h53_zero_coedge_s20"] == 0)
    assert np.all(result["h53_offset_coedge_s20"] == 0)
    assert np.all(result["h53_signed_lag_s20"] == 0)


def test_rejects_mismatched_inputs_and_invalid_lag():
    x = np.zeros((10, 10), dtype=np.float32)
    with pytest.raises(ValueError, match="matching 2-D"):
        finite_lag_edge_features(x, x[:8], np.ones_like(x, dtype=bool))
    with pytest.raises(ValueError, match="positive integer"):
        finite_lag_edge_features(x, x, np.ones_like(x, dtype=bool), max_lag_px=0)
