#!/usr/bin/env python3
"""Locate, verify and index the competition rasters.

This script does NOT download anything (the competition data page is login-walled, and
from this sandbox every non-GitHub host returns HTTP 000 -- see IR-51-02).  It expects the
four core files to have been placed in `data/` (or `$GEMS_DATA_DIR`), e.g. by running
`bash scripts/download_competition_data.sh` on an unrestricted machine, and it verifies
them against the SHA-256 hashes published by the group's own mirror manifest.

It then writes `registry/data_manifest.json` with the measured grid facts, so that every
downstream number in this repository can be traced to a byte-level fact.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio

from gems51 import grid

ROOT = Path(__file__).resolve().parents[1]

CORE = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find(root: Path, name: str) -> Path | None:
    """Search the obvious placements, including the group's own mirror layout."""
    stem = str(root).rstrip("/")
    extra = Path(stem + "/.." if stem.endswith("data") else stem + "/data")
    for cand in (root / name, root / "bridge" / name, extra / name, extra / "bridge" / name):
        if cand.exists():
            return cand
    return None


def main() -> int:
    droot = grid.data_root()
    droot.mkdir(parents=True, exist_ok=True)
    report = {"data_root": str(droot), "files": {}, "grid": {}, "irregularities": []}

    for name, expect in CORE.items():
        p = find(droot, name)
        if p is None:
            report["files"][name] = {"present": False, "expected_sha256": expect}
            report["irregularities"].append(f"IR-51-02: {name} not found in {droot}")
            continue
        got = sha256_of(p)
        report["files"][name] = {
            "present": True,
            "path": str(p),
            "bytes": p.stat().st_size,
            "sha256": got,
            "expected_sha256": expect,
            "sha256_match": got == expect,
        }

    tf = find(droot, "training_features.tif")
    if tf:
        with rasterio.open(tf) as src:
            report["grid"] = {
                "source": str(tf),
                "count": src.count,
                "height": src.height,
                "width": src.width,
                "dtype": src.dtypes[0],
                "crs": str(src.crs),
                "res": [float(src.res[0]), float(src.res[1])],
                "transform": [float(v) for v in tuple(src.transform)[:6]],
                "nodata": float(src.nodata) if src.nodata is not None else None,
                "bands": {
                    str(i): {
                        "description": src.tags(i).get("description", ""),
                        "category": src.tags(i).get("data_category", ""),
                    }
                    for i in range(1, src.count + 1)
                },
            }

    ss = find(droot, "sample_submission.tif")
    ef = find(droot, "existing_faults.tif")
    if ss and ef:
        with rasterio.open(ss) as src:
            sample = src.read(1).astype(np.float32)
        cat = grid.read_catalogue(ef)
        report["format_facts"] = {
            "sample_submission_nodata": float(rasterio.open(ss).nodata)
            if rasterio.open(ss).nodata is not None
            else None,
            "footprint_valid_px": int(np.isfinite(sample).sum()),
            "sample_submission_nonzero_px": int((np.nan_to_num(sample) > 0).sum()),
            "catalogue_px": int(cat.sum()),
            "sample_submission_is_the_catalogue": bool(
                np.array_equal(np.nan_to_num(sample) > 0, cat)
            ),
            "catalogue_unique_values": [int(v) for v in np.unique(rasterio.open(ef).read(1))],
        }

    out = ROOT / "registry" / "data_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"[prepare_data] wrote {out}")
    print(f"  training_features present: {report['files']['training_features.tif']['present']}")
    print(f"  sha256 match            : {report['files']['training_features.tif'].get('sha256_match')}")
    if "format_facts" in report:
        ff = report["format_facts"]
        print(f"  catalogue px            : {ff['catalogue_px']}")
        print(f"  footprint valid px      : {ff['footprint_valid_px']}")
        print(f"  sample submission == catalogue: {ff['sample_submission_is_the_catalogue']}")
    for ir in report["irregularities"]:
        print(f"  !! {ir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
