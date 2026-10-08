import numpy as np

from gems51.extras import conductive_ribbon_group


def _fields(shape=(121, 121)):
    y, x = np.mgrid[:shape[0], :shape[1]]
    # Smooth gradients make the axial orientation well-defined at both frozen
    # scales without relying on a sparse, thresholded edge mask.
    structural = np.sin(x.astype(np.float32) / 30.0)
    return {
        "comp_cond_surf": structural.copy(),
        "comp_depth_to_base_surf": structural.copy(),
        "comp_iso_grav_anom": 2.0 * structural,
        "comp_tmi": 0.5 * structural,
    }, x, y


def _build(fields, footprint=None):
    if footprint is None:
        footprint = np.ones_like(next(iter(fields.values())), dtype=bool)
    return conductive_ribbon_group(lambda name: fields[name], footprint)["h53_k2x_min_s2s5"]


def test_h53_k2x_rewards_cross_edge_not_along_edge_conductivity_gradient():
    fields, x, y = _fields()
    across = _build(fields)
    along_fields = dict(fields)
    along_fields["comp_cond_surf"] = np.sin(y.astype(np.float32) / 30.0)
    along = _build(along_fields)

    # The three independent structural gradients have an x-normal / y-tangent
    # axis. At a location with non-zero gradients, only the x-directed
    # conductivity change has positive cross-edge-minus-along-edge energy.
    row, col = 60, 90
    assert across[row, col] > 0.5
    assert along[row, col] < 1e-5
    assert across[row, col] > along[row, col]


def test_h53_k2x_is_invariant_to_positive_layer_rescaling():
    fields, _, _ = _fields()
    baseline = _build(fields)
    scaled = {
        "comp_cond_surf": 13.0 * fields["comp_cond_surf"],
        "comp_depth_to_base_surf": 0.07 * fields["comp_depth_to_base_surf"],
        "comp_iso_grav_anom": 4.2 * fields["comp_iso_grav_anom"],
        "comp_tmi": 0.2 * fields["comp_tmi"],
    }
    result = _build(scaled)
    valid = np.isfinite(baseline) & np.isfinite(result)
    assert valid.any()
    np.testing.assert_allclose(result[valid], baseline[valid], rtol=2e-5, atol=2e-6)


def test_h53_k2x_flat_fields_are_zero_and_missing_support_stays_missing():
    shape = (41, 37)
    fields = {name: np.zeros(shape, dtype=np.float32) for name in (
        "comp_cond_surf", "comp_depth_to_base_surf", "comp_iso_grav_anom", "comp_tmi"
    )}
    flat = _build(fields)
    assert np.isfinite(flat).all()
    assert np.all(flat == 0.0)

    fields["comp_cond_surf"][:, :4] = np.nan
    mask = np.ones(shape, dtype=bool)
    out = _build(fields, mask)
    assert np.isnan(out[:, :4]).all()
    assert np.isfinite(out[:, 8:-8]).all()
    assert np.all((out[np.isfinite(out)] >= 0.0) & (out[np.isfinite(out)] <= 1.0))
