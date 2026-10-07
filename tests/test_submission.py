from types import SimpleNamespace

import numpy as np
import pytest

import gems51.submission as submission
from gems51.grid import GRID, footprint


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


def test_repository_footprint_comes_from_sample_submission():
    mask = footprint()
    assert mask.shape == GRID.shape
    assert mask.dtype == np.bool_
    assert 0 < int(mask.sum()) < mask.size


def test_check_submission_reports_zero_out_of_range_values_as_pass(monkeypatch, capsys, tmp_path):
    import scripts.check_submission as cli

    candidate = tmp_path / "candidate.tif"
    candidate.touch()
    monkeypatch.setattr(cli, "footprint", lambda: np.ones((1, 1), dtype=bool))
    monkeypatch.setattr(cli, "verify", lambda _path, _mask: {
        "checks": {"values_outside_0_1": 0, "format_valid": True},
        "file": "candidate.tif",
        "sha256": "test",
    })
    monkeypatch.setattr(cli.sys, "argv", ["check_submission.py", str(candidate)])

    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "PASS  values_outside_0_1: 0" in output
    assert "LOCAL FORMAT CHECKS PASS" in output


@pytest.mark.parametrize('outside', [-9999, np.inf, -np.inf, 1.01])
def test_invalid_outside_rejected(monkeypatch, outside):
    _small_grid(monkeypatch)
    with pytest.raises(ValueError, match='outside'):
        submission.encode_submission_array(np.zeros((2,3)), np.ones((2,3),bool), outside)


def test_zero_encoded_tiff_is_globally_finite(tmp_path, monkeypatch):
    from rasterio.transform import Affine
    monkeypatch.setattr(submission, 'GRID', SimpleNamespace(shape=(16,16), epsg=32611,
        transform=(100.,0.,243350.,0.,-100.,4508550.)))
    fp=np.zeros((16,16),bool);fp[2:14,2:14]=True
    a=np.zeros((16,16),np.float32);a[8,8]=1
    rec=submission.write_tif(tmp_path/'a.tif',a,fp)
    assert rec['checks']['all_cells_finite_in_range']
    assert rec['checks']['global_invalid_cells']==0
    assert rec['nodata'] is None
    with pytest.raises(ValueError, match='NoData'):
        submission.write_tif(tmp_path/'bad.tif',a,fp,nodata=-9999)
