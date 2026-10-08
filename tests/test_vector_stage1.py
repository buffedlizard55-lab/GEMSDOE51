import numpy as np
import pandas as pd
import pytest

from gems51.vector_stage1 import approved_pixel_mask, residual_rank_prior
from scripts.h53a_pipeline import random_prediction, record_ids_intersecting_block
from gems51.grid import GRID


def test_residual_prior_uses_finite_ranked_absolute_residuals_and_equal_weight():
    obs_d = np.array([[0.0, 1.0, 2.0, np.nan]])
    obs_s = np.array([[3.0, 2.0, 1.0, 0.0]])
    pred_d = np.zeros_like(obs_d)
    pred_s = np.zeros_like(obs_s)
    valid = np.ones_like(obs_d, dtype=bool)

    result = residual_rank_prior(
        obs_d,
        obs_s,
        pred_d,
        pred_s,
        valid,
        geodetic_rate_scale=1.0,
    )
    np.testing.assert_allclose(result["dilatation_residual"][0, :3], [0, 1, 2])
    np.testing.assert_allclose(result["rank_dilatation"][0, :3], [0, 0.5, 1])
    np.testing.assert_allclose(result["rank_shear"][0, :3], [1, 0.5, 0])
    np.testing.assert_allclose(result["prior_score"][0, :3], [0.5, 0.5, 0.5])
    assert np.isnan(result["prior_score"][0, 3])


def test_residual_prior_converts_tensor_units_and_rejects_bad_scale():
    values = np.array([[2.0]])
    result = residual_rank_prior(values, values, np.array([[1e-8]]),
                                 np.array([[2e-8]]), np.ones_like(values, bool),
                                 geodetic_rate_scale=1e-8)
    assert result["dilatation_residual"][0, 0] == pytest.approx(1.0)
    assert result["shear_residual"][0, 0] == pytest.approx(0.0)
    with pytest.raises(ValueError, match="positive and finite"):
        residual_rank_prior(values, values, values, values,
                            np.ones_like(values, bool), geodetic_rate_scale=0)


def test_approved_mask_is_coarse_quantile_and_footprint_scoped():
    tiles = np.arange(4, dtype=np.float64).reshape(2, 2)
    footprint = np.ones((4, 4), dtype=bool)
    footprint[0, 0] = False
    mask, threshold, area = approved_pixel_mask(tiles, footprint, tile_px=2, q=50)
    # Quantiles are footprint-pixel weighted after upsampling the four tiles.
    assert threshold == pytest.approx(2.0)
    assert mask[2:, :].all()
    assert not mask[:2, :2].any()
    assert not mask[0, 0]
    assert area == pytest.approx(mask.sum() / footprint.sum())


def test_random_prediction_has_exact_mass_without_replacement():
    allowed = np.zeros((4, 5), dtype=bool)
    allowed[1:3, 1:4] = True
    a = random_prediction(allowed, 5, seed=7)
    b = random_prediction(allowed, 5, seed=7)
    assert a.sum() == 5
    assert np.array_equal(a, b)
    assert np.all(~a | allowed)
    with pytest.raises(ValueError, match="only"):
        random_prediction(allowed, int(allowed.sum()) + 1, seed=7)


def test_whole_record_intersection_uses_entire_block_rectangle():
    # A 1-pixel block at raster [100, 100] has a 100 m by 100 m UTM rectangle.
    block = np.zeros(GRID.shape, dtype=bool)
    block[100, 100] = True
    west = 243350.0 + 100 * 100
    north = 4508550.0 - 100 * 100
    records = pd.DataFrame([
        # record 11 crosses the block interior
        [11, west - 500, north - 50, west + 500, north - 50],
        # record 12 misses north of the block
        [12, west - 500, north + 500, west + 500, north + 500],
        # record 13 touches the right edge and continues through the block
        [13, west + 50, north - 50, west + 150, north - 50],
    ], columns=["record_id", "x0", "y0", "x1", "y1"])
    assert record_ids_intersecting_block(records, block) == [11, 13]
