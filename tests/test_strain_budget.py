import numpy as np
import pandas as pd
import pytest

from gems51.strain_budget import (
    block_reduce_sum,
    horizontal_segment_tensor,
    trace_assignments,
)


def test_normal_fault_horizontal_tensor_uses_full_3d_projection():
    # East-west strike; the projected dip direction is north. For a 60-degree
    # normal fault, the horizontal term is L*u*cos(delta)/A, not L*u*cot(delta)/A.
    exx, eyy, exy = horizontal_segment_tensor(
        length_m=100.0,
        slip_m_yr=1e-3,
        dip_deg=60.0,
        strike_x=1.0,
        strike_y=0.0,
        is_strike_slip=False,
        area_m2=10_000.0,
        rate_convention="fault_plane",
    )
    expected = 100.0 * 1e-3 * np.cos(np.deg2rad(60.0)) / 10_000.0
    assert exx == pytest.approx(0.0, abs=1e-15)
    assert eyy == pytest.approx(expected)
    assert exy == pytest.approx(0.0, abs=1e-15)


def test_vertical_strike_slip_horizontal_shear_component():
    exx, eyy, exy = horizontal_segment_tensor(
        100.0, 1e-3, 90.0, 1.0, 0.0, True, 10_000.0
    )
    assert exx == pytest.approx(0.0, abs=1e-15)
    assert eyy == pytest.approx(0.0, abs=1e-15)
    assert exy == pytest.approx(100.0 * 1e-3 / (2.0 * 10_000.0))


def test_strike_slip_horizontal_projection_is_independent_of_dip():
    args = (100.0, 1e-3)
    strike_x = strike_y = 2**-0.5
    shallow_dip = horizontal_segment_tensor(
        *args, 60.0, strike_x, strike_y, True, 10_000.0,
    )
    vertical_dip = horizontal_segment_tensor(
        *args, 90.0, strike_x, strike_y, True, 10_000.0,
    )
    for shallow, vertical in zip(shallow_dip, vertical_dip):
        assert shallow == pytest.approx(vertical)


def test_horizontal_segment_tensor_exposes_vertical_rate_and_shear_sign():
    normal = horizontal_segment_tensor(
        100.0, 1e-3, 60.0, 1.0, 0.0, False, 10_000.0,
        rate_convention="vertical",
    )
    expected_vertical = 100.0 * 1e-3 / np.tan(np.deg2rad(60.0)) / 10_000.0
    assert normal[1] == pytest.approx(expected_vertical)

    right = horizontal_segment_tensor(
        100.0, 1e-3, 90.0, 2**-0.5, 2**-0.5, True, 10_000.0,
        strike_slip_sign=1.0,
    )
    left = horizontal_segment_tensor(
        100.0, 1e-3, 90.0, 2**-0.5, 2**-0.5, True, 10_000.0,
        strike_slip_sign=-1.0,
    )
    for r, l in zip(right, left):
        assert l == pytest.approx(-r)


def test_horizontal_segment_tensor_rejects_invalid_area_and_dip():
    with pytest.raises(ValueError, match="positive support area"):
        horizontal_segment_tensor(1, 1e-3, 60, 1, 0, False, 0)
    with pytest.raises(ValueError, match="dip"):
        horizontal_segment_tensor(1, 1e-3, 0, 1, 0, False, 1)


def test_trace_assignments_return_original_dataframe_index_labels():
    catalogue = np.zeros((12, 12), dtype=bool)
    catalogue[2, 2] = True
    catalogue[10, 10] = True
    df = pd.DataFrame(
        {"centroid_row": [2.0, 10.0], "centroid_col": [2.0, 10.0]},
        index=["fault-a", "fault-b"],
    )
    y, x, ids = trace_assignments(catalogue, df, step=1)
    assert list(zip(y, x)) == [(2, 2), (10, 10)]
    assert ids.tolist() == ["fault-a", "fault-b"]


def test_block_reduce_sum_uses_actual_partial_edge_tile_area():
    mask = np.ones((3, 5), dtype=float)
    counts = block_reduce_sum(mask, tile_px=2)
    np.testing.assert_array_equal(counts, np.array([[4, 4, 2], [2, 2, 1]], dtype=float))
