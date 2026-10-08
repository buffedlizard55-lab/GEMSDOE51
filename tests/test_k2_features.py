import numpy as np

from gems51.k2_features import average_tie_rank01, conditioned_ribbon_features


def _ridge(sign=1.0):
    h, w = 64, 64
    y, x = np.mgrid[:h, :w]
    base = np.broadcast_to((x >= 32).astype(np.float32), (h, w)).copy()
    cond = sign * np.exp(-0.5 * ((x - 32.0) / 2.0) ** 2).astype(np.float32)
    return base, cond


def test_ribbon_contrast_is_polarity_agnostic_and_persists_along_independent_edge():
    base, conductive = _ridge(+1.0)
    _, resistive = _ridge(-1.0)
    support = np.ones(base.shape, bool)
    kwargs = dict(support=support, sigma=2.0, edge_threshold=0.01,
                  along_offsets=(-5, -2.5, 0, 2.5, 5), cross_half_width=3.0)
    positive = conditioned_ribbon_features(base, conductive, **kwargs)
    negative = conditioned_ribbon_features(base, resistive, **kwargs)
    center = (32, 32)
    assert positive["edge_mask"][center]
    assert positive["contrast"][center] > 0.1
    assert positive["persistence"][center] > 0.95
    np.testing.assert_allclose(positive["contrast"][center], negative["contrast"][center], rtol=0.02)
    np.testing.assert_allclose(positive["persistence"][center], negative["persistence"][center], rtol=0.02)


def test_ribbon_operator_respects_missing_sample_footprint_and_rank_ties():
    base, cond = _ridge(+1.0)
    support = np.ones(base.shape, bool)
    support[32, 35] = False
    result = conditioned_ribbon_features(base, cond, support, sigma=2.0,
                                         edge_threshold=0.01, cross_half_width=3.0)
    assert np.isnan(result["contrast"][32, 32])
    assert np.isnan(result["persistence"][32, 32])
    assert np.isnan(result["contrast"][32, 35])
    assert result["contrast"][0, 0] == 0.0

    ranked = average_tie_rank01(np.array([0.0, 4.0, 4.0, 8.0]),
                                np.array([False, True, True, True]))
    np.testing.assert_allclose(ranked, [0.0, 0.25, 0.25, 1.0])
