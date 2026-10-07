import numpy as np

from gems51.extras import cross_physics_edge_features


def test_cross_physics_alignment_detects_coincident_parallel_edges():
    h = w = 41
    yy, xx = np.mgrid[:h, :w]
    magnetic = (xx >= 20).astype(np.float32)
    same_edge = (xx >= 20).astype(np.float32)
    perpendicular_edge = (yy >= 20).astype(np.float32)
    mask = np.ones((h, w), dtype=bool)

    aligned = cross_physics_edge_features(magnetic, same_edge, mask, sigma=2.0)
    perpendicular = cross_physics_edge_features(magnetic, perpendicular_edge, mask, sigma=2.0)
    # The step intersection has two perpendicular normals, while the parallel
    # case has the same unoriented normal. Both have nonzero edge magnitude.
    assert aligned["alignment"][20, 20] > 0.95
    assert perpendicular["alignment"][20, 20] < 0.05
    assert aligned["coedge"][20, 20] > perpendicular["coedge"][20, 20]


def test_cross_physics_alignment_is_invariant_to_anomaly_sign():
    h = w = 31
    yy, xx = np.mgrid[:h, :w]
    field = (xx >= 15).astype(np.float32)
    out = cross_physics_edge_features(field, -field, np.ones((h, w), bool), sigma=2.0)
    assert out["alignment"][15, 15] > 0.95
    assert out["coedge"][15, 15] > 0.9


def test_cross_physics_features_mask_invalid_pixels_and_handle_flat_fields():
    h = w = 15
    mask = np.ones((h, w), dtype=bool)
    mask[:, 0] = False
    zeros = np.zeros((h, w), dtype=np.float32)
    out = cross_physics_edge_features(zeros, zeros, mask, sigma=1.0)
    assert np.isnan(out["alignment"][:, 0]).all()
    assert np.isnan(out["coedge"][:, 0]).all()
    assert np.all(out["alignment"][mask] == 0.0)
    assert np.all(out["coedge"][mask] == 0.0)
    assert np.isfinite(out["alignment"][mask]).all()
