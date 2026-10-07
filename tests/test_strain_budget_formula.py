"""Unit tests for the Stage-1 moment-tensor formulas and sign conventions."""

import numpy as np
import pandas as pd
import pytest

from gems51.strain_budget import (
    BudgetConfig,
    assign_slip_rate,
    dip_slip_horizontal_amplitude,
    load_slip_rates,
    rotate_fault_tensor,
)


def test_dip_slip_rate_conventions_are_equivalent_for_same_physical_motion():
    length = 2500.0
    area = 1.0e8
    dip = 60.0
    total_rate = 2.0e-3
    vertical_rate = total_rate * np.sin(np.deg2rad(dip))

    from_fault_plane = dip_slip_horizontal_amplitude(
        length, total_rate, dip, area, "fault_plane"
    )
    from_vertical = dip_slip_horizontal_amplitude(
        length, vertical_rate, dip, area, "vertical"
    )
    assert from_fault_plane == pytest.approx(from_vertical)


def test_dip_slip_rate_conventions_have_the_documented_geometry_factors():
    length, rate, area, dip = 4.0, 3.0, 2.0, 60.0
    vertical = dip_slip_horizontal_amplitude(length, rate, dip, area, "vertical")
    total = dip_slip_horizontal_amplitude(length, rate, dip, area, "fault_plane")
    radians = np.deg2rad(dip)
    assert vertical == pytest.approx(length * rate / area / np.tan(radians))
    assert total == pytest.approx(length * rate * np.cos(radians) / area)
    with pytest.raises(ValueError):
        dip_slip_horizontal_amplitude(length, rate, dip, area, "unknown")


def test_left_and_right_lateral_senses_have_opposite_shear_signs():
    # A 45-degree fault has a non-zero xy shear component after rotation.
    angle = np.deg2rad(45.0)
    sx, sy = np.cos(angle), np.sin(angle)
    right = rotate_fault_tensor(sx, sy, 0.0, 1.0)
    left = rotate_fault_tensor(sx, sy, 0.0, -1.0)
    for right_component, left_component in zip(right, left):
        assert left_component == pytest.approx(-right_component)
    assert right[0] != pytest.approx(0.0)
    assert right[1] != pytest.approx(0.0)


def test_unknown_slip_sense_is_explicit_and_not_silently_called_known(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    pd.DataFrame(
        {
            "slip_rate": [2.0, 1.0],
            "slip_sense": ["Unspecified", "LL"],
            "centroid_row": [2.0, 8.0],
            "centroid_col": [2.0, 8.0],
            "dip_direct": ["NW", "SE"],
        }
    ).to_csv(external / "gdr_qfaults_traces.csv", index=False)
    df = load_slip_rates(tmp_path)
    assert df.loc[0, "dip_deg"] == 60.0
    assert not bool(df.loc[0, "sense_known"])
    assert bool(df.loc[1, "is_strike_slip"])
    assert df.loc[1, "strike_slip_sign"] == -1.0

    catalogue = np.zeros((12, 12), dtype=bool)
    catalogue[2, 2] = True
    catalogue[8, 8] = True
    result = assign_slip_rate(catalogue, df, BudgetConfig(max_assign_px=1.0))
    _, _, _, _, is_ss, sign, known, assigned, _ = result
    assert assigned.all()
    assert is_ss.tolist() == [False, True]
    assert sign.tolist() == [1.0, -1.0]
    assert known.tolist() == [False, True]
