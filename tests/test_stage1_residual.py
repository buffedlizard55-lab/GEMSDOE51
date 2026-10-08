import numpy as np
import pytest

from gems51.stage1_residual import (
    approved_domain,
    combined_deficit_rank,
    component_residual,
    positive_empirical_rank,
    records_intersecting_block,
)


def test_component_residual_preserves_documented_unit_scenarios():
    observed = np.array([5.0, 5.0])
    modeled = np.array([1e-8, 1e-8])
    np.testing.assert_allclose(component_residual(observed, modeled, 1e-8), [4.0, 4.0])
    np.testing.assert_allclose(component_residual(observed, modeled, 1e-9), [-5.0, -5.0])
    with pytest.raises(ValueError, match="unit_factor"):
        component_residual(observed, modeled, 0.0)
    with pytest.raises(ValueError, match="identical shapes"):
        component_residual(observed, modeled[:1], 1e-8)


def test_positive_rank_drops_negative_deficit_and_handles_constant_fields():
    values = np.array([-3.0, 0.0, 1.0, 4.0])
    rank = positive_empirical_rank(values)
    assert rank[0] == rank[1] < rank[2]
    assert rank[2] < rank[3]
    np.testing.assert_array_equal(positive_empirical_rank(np.array([-1.0, -1.0])), [0, 0])


def test_combined_prior_is_equal_weight_and_keeps_invalid_cells_nan():
    dil = np.array([0.0, 1.0, 2.0, np.nan])
    shear = np.array([3.0, 2.0, 1.0, 4.0])
    valid = np.array([True, True, True, True])
    out = combined_deficit_rank(dil, shear, valid)
    assert np.isfinite(out[:3]).all()
    assert np.isnan(out[3])
    # The symmetric middle tile has equal average rank despite opposite component order.
    assert out[1] == pytest.approx(0.5)


def test_q10_domain_is_a_fixed_lower_tail_gate():
    score = np.arange(100, dtype=np.float32).reshape(10, 10)
    footprint = np.ones_like(score, dtype=bool)
    approved, threshold = approved_domain(score, footprint, 10.0)
    assert threshold == pytest.approx(9.9)
    assert approved.sum() == 90
    assert not approved[0, 0]
    assert approved[-1, -1]


def test_record_exclusion_uses_geometry_and_buffer_in_map_units():
    transform = (100.0, 0.0, 0.0, 0.0, -100.0, 1000.0)
    segments = [
        {"record_id": 1, "x0": -500, "y0": 750, "x1": 1000, "y1": 750},
        {"record_id": 2, "x0": -500, "y0": 250, "x1": 1000, "y1": 250},
        {"record_id": 3, "x0": -500, "y0": 400, "x1": 1000, "y1": 400},
    ]
    # Block rows 0:5, cols 0:5 spans x=[0,500], y=[500,1000]. With a
    # one-pixel buffer, record 1 crosses the block and record 3 touches its edge.
    assert records_intersecting_block(segments, (0, 5, 0, 5), 1, transform) == {1, 3}
    with pytest.raises(ValueError, match="invalid block"):
        records_intersecting_block(segments, (5, 0, 0, 5), 1, transform)
