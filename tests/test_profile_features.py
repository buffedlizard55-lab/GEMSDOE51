import numpy as np
import pytest
from gems51.profile_features import profile_features


def test_constant_and_datum_invariance():
    y, x = np.indices((61, 61), dtype=np.float32)
    m = np.ones(x.shape, bool)
    for a in profile_features(x*0+3, m).values():
        assert np.nanmax(np.abs(a)) == 0
    a, b = profile_features(x, m), profile_features(x+20, m)
    for k in a:
        np.testing.assert_allclose(a[k][10:-10,10:-10], b[k][10:-10,10:-10], atol=1e-5)
        assert np.nanmin(a[k]) >= 0 and np.nanmax(a[k]) <= 1.00001


def test_missing_shoulders_not_evidence():
    y, x = np.indices((61, 61), dtype=np.float32)
    m = np.ones(x.shape, bool); m[:,30] = False
    for a in profile_features(x, m).values():
        assert np.isnan(a[:,30]).all()
        assert np.isnan(a[30,29])


def test_step_vs_symmetric_ridge():
    y, x = np.indices((101,101), dtype=np.float32)
    m = np.ones(x.shape,bool)
    step = np.tanh((x-50)/2)
    ridge = np.exp(-((x-50)/3)**2)
    a, b = profile_features(step,m), profile_features(ridge,m)
    assert a['p1_step_fraction'][50,50] > .95
    assert b['p1_step_fraction'][50,50] == 0


def test_parameters():
    with pytest.raises(ValueError):
        profile_features(np.ones((10,10)), np.ones((10,10),bool), offsets=(5,2))
