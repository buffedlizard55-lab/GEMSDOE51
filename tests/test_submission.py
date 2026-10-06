"""Format, gate and emission-contract tests.

These are the tests that protect the *deliverable*: if any of them fails, the file that would be
uploaded to the competition portal is not legal, not unique, or not the rule that was promoted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import requires_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SUBMISSION = ROOT / "docs" / "downloads" / "gemsdoe51-strainbudget-s1-v1.tif"
RECEIPT = ROOT / "evidence" / "submission_receipt.json"


def test_receipt_exists_and_is_self_consistent():
    assert RECEIPT.exists(), "evidence/submission_receipt.json is missing"
    r = json.loads(RECEIPT.read_text())
    assert r["dtype"] == "float32"
    assert r["count"] == 1
    assert r["crs"] == "EPSG:32611"
    assert r["nodata"] is None, "a nodata tag can trip the portal's [0,1] range check"
    assert r["n_nan"] == 0 and r["all_finite"] is True
    assert r["n_below0"] == 0 and r["n_above1"] == 0
    assert r["n_positive"] > 0
    assert len(r["sha256"]) == 64


@pytest.mark.skipif(not SUBMISSION.exists(), reason="shipped raster not present")
def test_shipped_raster_satisfies_the_format_contract():
    import rasterio

    with rasterio.open(SUBMISSION) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == 32611
        assert tuple(ds.shape) == (3730, 3292)
        assert ds.nodatavals[0] is None or 0.0 <= float(ds.nodatavals[0]) <= 1.0
        a = ds.read(1)
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0


@pytest.mark.skipif(not SUBMISSION.exists(), reason="shipped raster not present")
def test_shipped_raster_matches_the_receipt_digest():
    import hashlib

    r = json.loads(RECEIPT.read_text())
    assert hashlib.sha256(SUBMISSION.read_bytes()).hexdigest() == r["sha256"]


def test_uniqueness_gate_contract(tmp_path):
    """The gate must reject a copy of a prior submission and accept a disjoint one."""
    from gems51 import grid, submission

    prior = np.zeros(grid.SHAPE, bool)
    prior[100:140, 100:140] = True
    same = prior.copy()
    disjoint = np.zeros(grid.SHAPE, bool)
    disjoint[1000:1040, 1000:1040] = True

    import rasterio
    from rasterio.transform import from_origin

    prior_dir = tmp_path / "scored"
    prior_dir.mkdir()
    with rasterio.open(prior_dir / "prior.tif", "w", driver="GTiff", height=grid.SHAPE[0],
                       width=grid.SHAPE[1], count=1, dtype="float32",
                       crs="EPSG:32611", transform=from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(prior.astype("float32"), 1)

    r_same = submission.uniqueness_gate(same, scored_dir=prior_dir)
    assert not r_same["passed"] and r_same["max_jaccard"] == 1.0
    r_new = submission.uniqueness_gate(disjoint, scored_dir=prior_dir)
    assert r_new["passed"] and r_new["max_jaccard"] == 0.0


@requires_data
def test_build_emission_respects_the_off_catalogue_rule_and_the_rule_switch():
    """Thin dots must stay inside the candidate mask; the lattice branch must be reachable."""
    from gems51 import detector, grid, submission

    fp = grid.footprint()
    # pick a 120x120 window with the largest footprint coverage (searched, not assumed)
    best, win = -1.0, None
    for r0 in range(0, grid.SHAPE[0] - 120, 200):
        for c0 in range(0, grid.SHAPE[1] - 120, 200):
            w = (slice(r0, r0 + 120), slice(c0, c0 + 120))
            frac = float(fp[w].mean())
            if frac > best:
                best, win = frac, w
    approved = np.zeros(grid.SHAPE, bool)
    approved[win] = fp[win]
    belief = np.zeros(grid.SHAPE, np.float32)
    belief[win] = np.linspace(0, 1, 120)[:, None]

    mask, info = submission.build_emission(belief, approved, rule="thin", density=0.05, spacing=3.0)
    cand = submission.candidate_mask(approved)
    assert info["rule"] == "thin_dots_belief_priority" and info["promoted"] is True
    assert mask.sum() > 0
    assert (mask & ~cand).sum() == 0, "a dot escaped the candidate mask"
    assert info["emitted_inside_candidate_fraction"] == 1.0

    lat, linfo = submission.build_emission(belief, approved, rule="lattice", quantile=0.9,
                                           spacing=3)
    assert linfo["rule"] == "coverage_lattice_not_promoted" and linfo["promoted"] is False
    assert (lat & ~cand).sum() == 0

    with pytest.raises(ValueError):
        submission.build_emission(belief, approved, rule="nonsense")


def test_stage_dominance_gate_flags_a_densified_tile_mask(monkeypatch):
    """A mask that fills its approved tiles must fail; a sparse selective one must pass.

    `grid.tiles()` tiles the whole competition footprint, so this test would need the 557 MB
    organiser raster just to count tiles.  The footprint is therefore stubbed to an all-true grid:
    the gate's arithmetic (fill fraction, tile concentration) is what is under test here, and it
    never reads any raster value.  Nothing about the shipped file changes.
    """
    from gems51 import grid, submission

    monkeypatch.setattr(grid, "footprint", lambda *a, **k: np.ones(grid.SHAPE, bool))

    approved = np.zeros(grid.SHAPE, bool)
    approved[0:300, 0:300] = True
    dense = approved.copy()                     # the failure mode: stage 1's footprint, densified
    r_dense = submission.stage_dominance_check(dense, approved, approved)
    assert r_dense["verdict"] != "fine-scale selectivity present"

    sparse = np.zeros(grid.SHAPE, bool)
    sparse[::4, ::4] = True
    sparse &= approved
    r_sparse = submission.stage_dominance_check(sparse, approved, approved)
    assert r_sparse["fill_fraction"] < 0.25
    assert r_sparse["coverage_in_approved"] == 1.0
