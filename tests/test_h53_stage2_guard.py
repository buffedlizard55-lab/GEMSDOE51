from __future__ import annotations

import numpy as np
import pytest

from scripts.run_h53a_stage2_holdout import _sha256, _verify_fold_field_hashes


def _make_baseline_receipt(field_dir):
    rows = []
    for fold in range(6):
        row = {"fold": fold}
        for arm, offset, key in (
            ("HD", 10, "hd_field_sha256"),
            ("HH", 20, "hh_field_sha256"),
        ):
            path = field_dir / f"{arm}_fold{fold}.npy"
            np.save(path, np.full((3, 4), fold + offset, dtype=np.float32))
            row[key] = _sha256(path)
        rows.append(row)
    return {"per_fold": rows}


def test_stage2_guard_accepts_only_exact_audited_fold_fields(tmp_path):
    receipt = _make_baseline_receipt(tmp_path)

    _verify_fold_field_hashes(receipt, tmp_path, (3, 4))


def test_stage2_guard_rejects_changed_cached_field_bytes(tmp_path):
    receipt = _make_baseline_receipt(tmp_path)
    np.save(tmp_path / "HH_fold2.npy", np.full((3, 4), 999, dtype=np.float32))

    with pytest.raises(SystemExit, match="field hash failed"):
        _verify_fold_field_hashes(receipt, tmp_path, (3, 4))


def test_stage2_guard_rejects_incomplete_or_wrong_geometry_fields(tmp_path):
    receipt = _make_baseline_receipt(tmp_path)
    receipt["per_fold"].pop()
    with pytest.raises(SystemExit, match="six canonical fold"):
        _verify_fold_field_hashes(receipt, tmp_path, (3, 4))

    receipt = _make_baseline_receipt(tmp_path)
    np.save(tmp_path / "HD_fold5.npy", np.zeros((4, 3), dtype=np.float32))
    receipt["per_fold"][5]["hd_field_sha256"] = _sha256(tmp_path / "HD_fold5.npy")
    with pytest.raises(SystemExit, match="geometry/dtype"):
        _verify_fold_field_hashes(receipt, tmp_path, (3, 4))
