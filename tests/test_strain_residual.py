"""Unit tests for the H53-A fine-scale strain-residual ridge features."""
import numpy as np
import pytest

from gems51 import strain_budget as sb
from gems51.grid import GRID
from gems51.strain_residual import (BANDS, FINE_TILE_PX, feature_names,
                                    h53a_features, residual_tile_maps,
                                    upsample_tiles)


def _toy_inputs(tmp_path):
    rng = np.random.default_rng(0)
    footprint = np.zeros(GRID.shape, dtype=bool)
    footprint[500:1500, 500:1500] = True
    catalogue = np.zeros(GRID.shape, dtype=bool)
    # a few synthetic traces inside the footprint
    catalogue[700:900, 800] = True
    catalogue[1000, 700:1100] = True
    df = sb.load_slip_rates(_raw_dir(tmp_path))
    observations = {
        name: rng.normal(size=GRID.shape).astype(np.float32)
        for name in BANDS
    }
    return footprint, catalogue, df, observations


def _raw_dir(tmp_path):
    """A minimal slip-rate table with the real GDR column layout.

    Centroids sit on the synthetic catalogue traces so that
    ``strain_budget.trace_assignments`` can map pixels to trace rows.
    """
    import pandas as pd
    raw = tmp_path / "raw"
    (raw / "external").mkdir(parents=True)
    rows = []
    # vertical trace near (row 700-900, col 800); horizontal near (row 1000, col 700-1100)
    centroids = [(800, 800), (1000, 900)]
    for i in range(20):
        cy, cx = centroids[i % len(centroids)]
        rows.append(dict(
            trace_id=f"T{i:03d}", name=f"trace {i}",
            slip_rate=0.1 + 0.01 * i, recency="H",
            dip_direct="E", slip_sense=["N", "RL", "LL", ""][i % 4],
            map_scale=24000, full_length_m=1000.0 + 10.0 * i,
            clipped_length_m=900.0 + 10.0 * i,
            centroid_utm_x=500000.0 + 100.0 * i, centroid_utm_y=4500000.0,
            centroid_row=float(cy + (i // len(centroids))),
            centroid_col=float(cx), centroid_in_footprint=True,
        ))
    pd.DataFrame(rows).to_csv(raw / "external" / "gdr_qfaults_traces.csv",
                              index=False)
    return raw


def test_upsample_tiles_shape_and_values():
    tiles = np.arange(6, dtype=np.float64).reshape(2, 3)
    big = upsample_tiles(tiles, 4)
    assert big.shape[0] >= 8 and big.shape[1] >= 12
    assert big[0, 0] == 0.0 and big[3, 3] == 0.0
    assert big[4, 4] == 4.0 and big[7, 11] == 5.0


def test_residual_tile_maps_keys_and_finite(tmp_path):
    footprint, catalogue, df, obs = _toy_inputs(tmp_path)
    out = residual_tile_maps(catalogue, footprint, df, obs)
    for name in BANDS:
        assert name in out
        resid = out[name]
        assert resid.shape[0] == int(np.ceil(GRID.shape[0] / FINE_TILE_PX))
        # rank residuals are bounded in [-1, 1]
        finite = resid[np.isfinite(resid)]
        assert finite.size > 0
        assert np.nanmax(np.abs(finite)) <= 1.0 + 1e-9
    assert out["valid_tiles"].dtype == bool


def test_h53a_features_shape_finite_and_names(tmp_path):
    footprint, catalogue, df, obs = _toy_inputs(tmp_path)
    g = h53a_features(catalogue, footprint, df, obs)
    names = feature_names()
    assert sorted(g.keys()) == sorted(names)
    assert len(names) == 6
    for name, arr in g.items():
        assert arr.shape == GRID.shape
        assert arr.dtype == np.float32
        inside = arr[footprint]
        assert np.isfinite(inside).all(), name
        assert np.isnan(arr[~footprint]).all(), name
        # crest response is non-negative where finite
        assert (inside >= 0.0).all(), name


def test_h53a_features_change_with_catalogue(tmp_path):
    """The residual must respond to the fault budget, not be a constant."""
    footprint, catalogue, df, obs = _toy_inputs(tmp_path)
    g1 = h53a_features(catalogue, footprint, df, obs)
    catalogue2 = catalogue.copy()
    catalogue2[1200:1400, 1200:1400] = True  # add a far-away trace block
    g2 = h53a_features(catalogue2, footprint, df, obs)
    a = g1["h53a_geod_2ndinv_s15_crest"][footprint]
    b = g2["h53a_geod_2ndinv_s15_crest"][footprint]
    assert not np.allclose(a, b)


def test_h53a_features_missing_band_fails_closed(tmp_path):
    footprint, catalogue, df, obs = _toy_inputs(tmp_path)
    del obs["geod_shearrate"]
    with pytest.raises(KeyError):
        h53a_features(catalogue, footprint, df, obs)
