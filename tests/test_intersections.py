import numpy as np

from gems51.intersections import axial_intersection_score


def test_axial_orientation_is_sign_invariant_and_crosses_at_right_angle():
    one = np.ones((2, 3), dtype=np.float32)
    zero = np.zeros_like(one)

    parallel, parallel_score = axial_intersection_score(one, zero, -one, zero, 1, 1)
    perpendicular, cross_score = axial_intersection_score(one, zero, zero, one, 1, 1)

    assert np.allclose(parallel, 0)
    assert np.allclose(parallel_score, 0)
    assert np.allclose(perpendicular, 1)
    assert np.allclose(cross_score, 1)


def test_crossing_score_requires_two_edges_and_scales_with_strength():
    one = np.ones((1, 1), dtype=np.float32)
    zero = np.zeros_like(one)

    _, score = axial_intersection_score(one, zero, zero, one, 2, 1)
    _, no_edge = axial_intersection_score(zero, zero, zero, one, 1, 1)

    assert np.allclose(score, np.sqrt(0.5))
    assert np.allclose(no_edge, 0)
