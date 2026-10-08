#!/usr/bin/env python3
"""Independent final-byte, mask, ZIP and decision verification (no training data)."""

import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems51.grid import footprint
from gems51.submission import verify


def main():
    record = json.loads((ROOT / "evidence/p1_artifact_20261007.json").read_text())
    hold = json.loads((ROOT / "evidence/p1_holdout_20261007.json").read_text())
    tile = json.loads((ROOT / "evidence/p1_stage1_tiles_20261007.json").read_text())
    fp = footprint()
    path = ROOT / "docs/downloads" / record["file"]
    report = verify(path, fp)
    assert (
        report["checks"]["all_cells_finite_in_range"]
        and report["checks"]["format_valid"]
    )
    assert report["nodata"] is None
    assert report["sha256"] == record["sha256"]
    with rasterio.open(path) as s:
        arr = s.read(1)
    support = arr > 0
    ap = (
        np.repeat(
            np.repeat(np.array(tile["approved_tiles"], bool), 100, axis=0), 100, axis=1
        )[: fp.shape[0], : fp.shape[1]]
        & fp
    )
    assert hashlib.sha256(ap.tobytes()).hexdigest() == tile["mask_sha256"]
    assert not np.any(support & ~ap)
    assert support.sum() == 44069
    assert np.isin(arr, [0, 1]).all()
    assert np.all(arr[~fp] == 0)
    with zipfile.ZipFile(path.with_suffix(".zip")) as z:
        assert z.namelist() == [path.name]
        assert hashlib.sha256(z.read(path.name)).hexdigest() == record["sha256"]
    candidate = np.mean([r["scores"]["candidate_gated"]["dti"] for r in hold["rows"]])
    assert abs(candidate - hold["summary"]["candidate_gated"]) < 1e-12
    assert (
        record["status"] == "NOT_FOR_SUBMISSION"
        and not hold["promoted"]
        and not hold["slot_used"]
    )
    report["approved_points"] = int((support & ap).sum())
    report["zip_identical"] = True
    report["recommend_submission"] = False
    (ROOT / "evidence/p1_final_verification_20261007.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(
        "PASS: final bytes, global range, grid, ZIP, coarse-mask confinement, holdout arithmetic and no-submit status"
    )


if __name__ == "__main__":
    main()
