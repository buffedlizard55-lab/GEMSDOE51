"""Regression tests for the *current* submission state (manifest <-> bytes).

These tests are cheap but they guard the exact class of failure the user reported
from the portal ("Predicted values must be in range [0, 1]"): they re-open the
declared submission artifact and re-check the properties the manifest claims,
rather than trusting that the receipt is still true after later edits.

They are skipped automatically when the manifest declares no recommended
candidate, so the repository can be checked out at an earlier state.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "submission_manifest.json"
DOWNLOADS = ROOT / "docs" / "downloads"


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip("no submission manifest in this checkout")
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def candidate(manifest: dict) -> dict:
    record = manifest.get("recommended_upload_candidate")
    if not record:
        pytest.skip("manifest declares no recommended upload candidate")
    return record


def test_candidate_bytes_match_the_manifest_sha256(candidate: dict) -> None:
    path = DOWNLOADS / candidate["file"]
    assert path.is_file(), path
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == candidate["sha256"]
    assert path.stat().st_size == candidate["bytes"]


def test_candidate_is_linked_from_the_index(candidate: dict) -> None:
    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert f'href="downloads/{candidate["file"]}"' in index
    assert "RECOMMENDED UPLOAD CANDIDATE" in index


def test_candidate_declared_gates_are_internally_consistent(candidate: dict) -> None:
    checks = candidate["format"]["checks"]
    assert checks["format_valid"] is True
    assert checks["single_band"] is True
    assert checks["dtype_float32"] is True
    assert checks["crs_epsg_32611"] is True
    assert checks["transform_matches_template"] is True
    assert checks["shape_matches_template"] is True
    # the encoding that the reported portal error is about
    assert checks["values_outside_0_1"] == 0
    assert checks["nan_cells"] == 0
    assert checks["min_value"] >= 0.0 and checks["max_value"] <= 1.0
    # stage 1 stays coarse and non-dominant
    s1 = candidate["stage1_dominance"]
    assert s1["emitted_share_inside_approved"] == 1.0
    assert s1["lift_over_area_share"] < 1.5
    # uniqueness against the locally held prior corpus
    prewrite = candidate["uniqueness"]["prewrite"]
    assert prewrite["max_jaccard"] <= prewrite["limits"]["jaccard"] == 0.50
    assert prewrite["max_containment"] <= prewrite["limits"]["containment"] == 0.60
    assert prewrite["verdict"] == "PASS"
    assert candidate["uniqueness"]["staged"]["verdict"] == "PASS"
    assert candidate["uniqueness"]["reference_count"] >= 20


def test_candidate_raster_is_finite_and_in_range(candidate: dict) -> None:
    rasterio = pytest.importorskip("rasterio")
    path = DOWNLOADS / candidate["file"]
    with rasterio.open(path) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.crs is not None and src.crs.to_epsg() == 32611
        arr = src.read(1)
    assert arr.shape == (3730, 3292)
    assert np.isfinite(arr).all(), "a NaN or Inf would fail a naive range check"
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    positives = int((arr > 0).sum())
    assert positives == candidate["format"]["checks"]["predicted_px"] == candidate["geometry_audit"]["dots"]


def test_candidate_support_never_nearest_neighbour_closer_than_the_declared_spacing(candidate: dict) -> None:
    """Unit dots at >= 2.4 px separation: closer dots share kernel credit and waste mass."""
    rasterio = pytest.importorskip("rasterio")
    path = DOWNLOADS / candidate["file"]
    with rasterio.open(path) as src:
        arr = src.read(1)
    ys, xs = np.nonzero(arr > 0)
    assert ys.size == candidate["geometry_audit"]["dots"]
    if ys.size < 2:
        pytest.skip("degenerate single-dot artifact")
    rng = np.random.default_rng(0)
    idx = rng.choice(ys.size, size=min(4000, ys.size), replace=False)
    pts = np.stack([ys[idx], xs[idx]], 1).astype(np.float64)
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    np.fill_diagonal(d, np.inf)
    assert d.min() >= 2.4 - 1e-6


def test_manifest_readiness_state_is_known_and_not_overclaiming(manifest: dict) -> None:
    readiness = manifest["submission_readiness"]
    assert readiness["status"] in {
        "PORTAL_ACCEPTED",
        "NOT_YET_PORTAL_VALIDATED",
        "LOCAL_GATES_PASSED_NOT_PORTAL_TESTED",
        "BLOCKED_NOT_FOR_UPLOAD",
    }
    if manifest.get("recommended_upload_candidate") and readiness["status"] in {
        "NOT_YET_PORTAL_VALIDATED",
        "LOCAL_GATES_PASSED_NOT_PORTAL_TESTED",
    }:
        # An unvalidated candidate must never be described as accepted anywhere in the index.
        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8").lower()
        assert "portal-validated submission file" not in index
        assert "not yet portal-validated" in index


def test_no_archived_candidate_is_linked_from_the_site(candidate: dict) -> None:
    """The site must only expose the current candidate plus the audit/research records."""
    manifest = json.loads(MANIFEST.read_text())
    allowed = set()
    for record in [manifest.get("primary") or {}] + list(manifest.get("artifacts", [])) + \
            list(manifest.get("research_only_artifacts", [])) + [candidate]:
        for key in ("file", "zip"):
            if record.get(key):
                allowed.add(Path(record[key]).name)
    assert Path(candidate["file"]).name in allowed
    for page in (ROOT / "docs").glob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "archive/submissions/" not in text or 'href="archive/submissions/' not in text
