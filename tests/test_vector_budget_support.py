import numpy as np
import pandas as pd

from gems51.grid import GRID
from gems51.vector_budget import budget_prepared, prepare_segments_in_support


def _rows(*records):
    return pd.DataFrame(records, columns=[
        "record_id", "x0", "y0", "x1", "y1", "slip_mm_yr", "sense"
    ])


def test_source_segments_are_clipped_to_valid_cells_and_actual_tile_area():
    footprint = np.zeros(GRID.shape, dtype=bool)
    footprint[0, 0] = True
    footprint[0, 2] = True
    x0, y0 = GRID.transform[2], GRID.transform[5]
    y = y0 - 50.0
    rows = _rows((17, x0 + 50, y, x0 + 250, y, 1.0, "N"))

    prepared = prepare_segments_in_support(rows, footprint, tile_px=2)
    tensor, meta = budget_prepared(prepared, convention="fault_plane")

    # Of the 200 m source segment, the central 100 m pixel is outside support.
    assert meta["supported_source_length_m"] == 100.0
    assert meta["used_length_m"] == 100.0
    assert prepared.area_by_tile_m2[0, 0] == 10_000.0
    assert prepared.area_by_tile_m2[0, 1] == 10_000.0
    assert tensor.shape == (3, *prepared.tile_shape)
    assert np.count_nonzero(tensor) == 2  # one positive normal term in each tile
    assert prepared.meta["support_area_m2"] == 20_000.0


def test_unknown_sense_is_geometry_only_and_reported_not_imputed():
    footprint = np.zeros(GRID.shape, dtype=bool)
    footprint[0, :3] = True
    x0, y0 = GRID.transform[2], GRID.transform[5]
    y = y0 - 50.0
    rows = _rows((22, x0 + 50, y, x0 + 250, y, 0.8, ""))
    prepared = prepare_segments_in_support(rows, footprint, tile_px=2)

    tensor, meta = budget_prepared(prepared, convention="vertical")
    assert prepared.meta["unknown_sense_segment_rows"] == 1
    assert prepared.meta["unknown_sense_unique_records"] == 1
    assert meta["omitted_unknown_sense_segments"] == 1
    assert meta["omitted_unknown_sense_length_m"] == 200.0
    assert not tensor.any()
    assert prepared.rasterize_records([22]).sum() == 3


def test_segment_on_pixel_boundary_is_counted_once_if_either_side_is_valid():
    footprint = np.zeros(GRID.shape, dtype=bool)
    footprint[0, 1] = True
    x0, y0 = GRID.transform[2], GRID.transform[5]
    x = x0 + 100.0
    rows = _rows((31, x, y0 - 10, x, y0 - 90, 1.0, "N"))

    prepared = prepare_segments_in_support(rows, footprint, tile_px=1)
    assert prepared.meta["supported_source_length_m"] == 80.0
    assert prepared.pixel_row.tolist() == [0]
    assert prepared.pixel_col.tolist() == [1]


def test_source_budget_exclusion_and_rate_component_sensitivity():
    footprint = np.zeros(GRID.shape, dtype=bool)
    footprint[0, 0] = True
    x0, y0 = GRID.transform[2], GRID.transform[5]
    rows = _rows((42, x0, y0 - 50, x0 + 100, y0 - 50, 1.0, "N"))
    prepared = prepare_segments_in_support(rows, footprint, tile_px=1)

    plane, _ = budget_prepared(prepared, convention="fault_plane")
    vertical, _ = budget_prepared(prepared, convention="vertical")
    omitted, excluded_meta = budget_prepared(prepared, excluded=[42], convention="fault_plane")

    np.testing.assert_allclose(plane[1, 0, 0], 5e-6, rtol=1e-12)
    np.testing.assert_allclose(vertical[1, 0, 0] / plane[1, 0, 0],
                               (1 / np.tan(np.deg2rad(60))) / np.cos(np.deg2rad(60)))
    assert not omitted.any()
    assert excluded_meta["used_trace_records"] == 0
