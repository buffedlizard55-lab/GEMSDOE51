"""The historical blend writer must fail closed until explicit gates pass."""
from __future__ import annotations

import json

import pytest

from scripts.build_submission_hh_blend import require_build_authorization


def _manifest(*, readiness="CLEARED_FOR_NEW_BUILD", status="PROMOTED",
              all_inside=True, nondominant=True):
    return {
        "submission_readiness": {"status": readiness},
        "candidate_screen": {
            "status": status,
            "holdout_q10_domain": {"all_points_inside_approved": all_inside},
            "stage1_non_dominance_pass": nondominant,
        },
    }


def _write(tmp_path, payload):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_current_manifest_blocks_the_historical_writer():
    with pytest.raises(SystemExit, match="not CLEARED_FOR_NEW_BUILD"):
        require_build_authorization()


def test_explicit_promotion_without_q10_confinement_is_blocked(tmp_path):
    path = _write(tmp_path, _manifest(all_inside=False))
    with pytest.raises(SystemExit, match="every emitted Stage-2 point"):
        require_build_authorization(path)


def test_all_required_manifest_gates_allow_preflight(tmp_path):
    expected = _manifest()
    path = _write(tmp_path, expected)
    assert require_build_authorization(path) == expected
