from types import SimpleNamespace

import numpy as np
import pytest

import gems51.submission as submission


def _small_grid(monkeypatch):
    monkeypatch.setattr(submission, "GRID", SimpleNamespace(shape=(2, 3)))


def test_encode_submission_array_writes_nan_only_outside(monkeypatch):
    _small_grid(monkeypatch)
    values = np.array([[0.0, 0.25, 0.5], [0.75, 1.0, 0.4]], dtype=np.float32)
    footprint = np.array([[True, True, False], [True, False, True]])
    out = submission.encode_submission_array(values, footprint)
    assert out.dtype == np.float32
    assert np.isnan(out[~footprint]).all()
    np.testing.assert_array_equal(out[footprint], values[footprint])


def test_encode_submission_array_fails_closed_on_invalid_predictions(monkeypatch):
    _small_grid(monkeypatch)
    footprint = np.array([[True, True, False], [True, False, True]])
    with pytest.raises(ValueError, match="finite"):
        submission.encode_submission_array(
            np.array([[0.0, np.nan, 0.5], [0.75, 1.0, 0.4]]), footprint
        )
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        submission.encode_submission_array(
            np.array([[0.0, 0.25, 0.5], [0.75, 1.0, 1.4]]), footprint
        )
