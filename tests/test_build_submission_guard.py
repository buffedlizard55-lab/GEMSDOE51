from scripts import build_submission
from scripts.build_submission import matches_recorded_uniqueness_failure, prior_rasters


def _manifest():
    return {
        "status": "NO_ELIGIBLE_CANDIDATE",
        "decision": {
            "h_d_soft_w020": {
                "uniqueness": {"promotion": "FAIL_UNIQUENESS"},
                "config": {
                    "arm": "H_D",
                    "gate_mode": "soft",
                    "gate_weight": 0.20,
                    "ratio": 3.47,
                    "g_hidden_estimate": 12700,
                    "stage1_q": 50.0,
                    "tile_px": 100,
                    "nms_radius": 2.4,
                    "excl_radius": 2.0,
                },
            }
        },
    }


def _config():
    return {
        "arm": "H_D",
        "gate_mode": "soft",
        "gate_weight": 0.20,
        "ratio": 3.47,
        "g_hidden_estimate": 12700,
        "stage1_q": 50.0,
        "tile_px": 100,
        "nms_radius": 2.4,
        "excl_radius": 2.0,
    }


def test_unchanged_failed_candidate_is_recognized():
    assert matches_recorded_uniqueness_failure(_config(), _manifest())


def test_different_candidate_is_not_mislabeled_as_same_failure():
    config = _config()
    config["gate_weight"] = 0.10
    assert not matches_recorded_uniqueness_failure(config, _manifest())


def test_no_recorded_failure_does_not_block_build():
    manifest = _manifest()
    manifest["decision"]["h_d_soft_w020"]["uniqueness"]["promotion"] = "PASS"
    assert not matches_recorded_uniqueness_failure(_config(), manifest)


def test_prior_rasters_preserves_nested_paths_and_duplicate_basenames(tmp_path, monkeypatch):
    old = tmp_path / "archive" / "submissions" / "2026-01-01" / "candidate.tif"
    newer = tmp_path / "archive" / "submissions" / "2026-01-02" / "candidate.tif"
    old.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    newer.write_bytes(b"new")
    monkeypatch.setattr(build_submission, "ROOT", tmp_path)

    found = prior_rasters()

    assert set(found) == {
        "archive/submissions/2026-01-01/candidate.tif",
        "archive/submissions/2026-01-02/candidate.tif",
    }
