import numpy as np

from gems51.physical_stage1 import observed_tile_mean, physical_residual_prior, rank01
from gems51.vector_budget import PreparedSegments


def test_tile_mean_and_average_tie_ranks():
    values = np.array([[1.0, 3.0], [5.0, 7.0]])
    support = np.array([[True, True], [False, True]])
    np.testing.assert_allclose(observed_tile_mean(values, support, tile_px=2), [[11.0 / 3.0]])
    ranks = rank01(np.array([1.0, 1.0, 3.0]), np.ones(3, bool))
    np.testing.assert_allclose(ranks, [0.25, 0.25, 1.0])


def test_physical_prior_uses_dilation_and_shear_scenarios_and_is_broad():
    prepared = PreparedSegments(
        tile_px=2,
        tile_shape=(2, 2),
        area_by_tile_m2=np.full((2, 2), 40_000.0),
        record_id=np.array([7], dtype=np.int32),
        source_segment_index=np.array([0], dtype=np.int32),
        pixel_row=np.array([0], dtype=np.int32),
        pixel_col=np.array([0], dtype=np.int32),
        tile_id=np.array([0], dtype=np.int32),
        length_m=np.array([100.0]),
        strike_x=np.array([1.0]),
        strike_y=np.array([0.0]),
        rate_mm_yr=np.array([1.0]),
        sense_code=np.array([0], dtype=np.int8),
        meta={"tile_m": 200.0},
    )
    observed_dilatation = np.arange(16, dtype=float).reshape(4, 4)
    observed_shear = np.flipud(observed_dilatation) / 2.0
    support = np.ones((4, 4), dtype=bool)

    result = physical_residual_prior(
        prepared,
        observed_dilatation,
        observed_shear,
        support,
        approved_quantile=10.0,
        geodetic_scales=(1e-9, 1e-8),
        rate_conventions=("fault_plane", "vertical"),
    )

    assert result["scenario_count"] == 4
    assert set(result["scenario_results"]) == {
        "fault_plane_1e-09", "fault_plane_1e-08", "vertical_1e-09", "vertical_1e-08"
    }
    assert result["score"].shape == (2, 2)
    assert result["approved_tiles"].sum() >= 3
    assert result["approved_area_fraction"] >= 0.75
    assert np.isfinite(result["scenario_results"]["fault_plane_1e-09"]
                       ["dilation_residual_per_year"]["median"])
    assert result["interpretation"].endswith("broad tile prior only")


def test_prior_drops_excluded_trace_rows_from_tensor():
    prepared = PreparedSegments(
        tile_px=2,
        tile_shape=(2, 2),
        area_by_tile_m2=np.full((2, 2), 40_000.0),
        record_id=np.array([7], dtype=np.int32),
        source_segment_index=np.array([0], dtype=np.int32),
        pixel_row=np.array([0], dtype=np.int32),
        pixel_col=np.array([0], dtype=np.int32),
        tile_id=np.array([0], dtype=np.int32),
        length_m=np.array([100.0]),
        strike_x=np.array([1.0]),
        strike_y=np.array([0.0]),
        rate_mm_yr=np.array([1.0]),
        sense_code=np.array([0], dtype=np.int8),
        meta={"tile_m": 200.0},
    )
    values = np.arange(16, dtype=float).reshape(4, 4)
    support = np.ones((4, 4), dtype=bool)
    all_rows = physical_residual_prior(prepared, values, values, support,
                                       excluded_records=(), geodetic_scales=(1e-9,),
                                       rate_conventions=("fault_plane",))
    held_out = physical_residual_prior(prepared, values, values, support,
                                       excluded_records=[7], geodetic_scales=(1e-9,),
                                       rate_conventions=("fault_plane",))
    assert all_rows["scenario_results"]["fault_plane_1e-09"]["budget"]["used_length_m"] == 100.0
    assert held_out["scenario_results"]["fault_plane_1e-09"]["budget"]["used_length_m"] == 0.0
