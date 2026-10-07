import numpy as np

from gems51.extras import tilt_angle_edge_feature


def test_tilt_edge_releases_coincident_zero_angle_edges_not_vertical_only_signal():
    h = w = 61
    horizontal = np.zeros((h, w), dtype=np.float32)
    vertical = np.zeros((h, w), dtype=np.float32)

    # A strong, persistent horizontal-gradient line with zero vertical-gradient
    # response has tilt angle near zero and should score above a VG-only line.
    horizontal[:, 20] = 10.0
    vertical[:, 42] = 10.0
    valid = np.ones((h, w), dtype=bool)

    score = tilt_angle_edge_feature(vertical, horizontal, valid, sigma=1.5)

    assert score[30, 20] > 0.9
    assert score[30, 42] < 0.001
    assert np.isfinite(score).all()
    assert np.nanmin(score) >= 0.0
    assert np.nanmax(score) <= 1.0


def test_tilt_edge_preserves_invalid_mask_and_flat_derivatives_have_no_edges():
    shape = (25, 31)
    valid = np.ones(shape, dtype=bool)
    valid[:, 0] = False
    horizontal = np.zeros(shape, dtype=np.float32)
    vertical = np.zeros(shape, dtype=np.float32)

    score = tilt_angle_edge_feature(vertical, horizontal, valid, sigma=2.0)

    assert np.isnan(score[:, 0]).all()
    assert np.isfinite(score[valid]).all()
    assert np.all(score[valid] == 0.0)


def test_tilt_edge_validates_shapes_and_fixed_scale_parameters():
    a = np.zeros((9, 11), dtype=np.float32)
    mask = np.ones(a.shape, dtype=bool)

    for kwargs in ({"sigma": 0.0}, {"sigma": 1.0, "tilt_tolerance_rad": 0.0}):
        try:
            tilt_angle_edge_feature(a, a, mask, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("non-positive fixed scale parameters must fail closed")

    try:
        tilt_angle_edge_feature(a, a[:, :-1], mask, sigma=1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("misaligned derivative arrays must fail closed")
