#!/usr/bin/env python3
"""Recompute a candidate's support-uniqueness gate against the current local inventory.

Unlike a builder's original pre-write gate, this audit includes every TIFF currently
under docs/downloads/, the three checked-in local priors, and any freshly fetched sibling
TIFFs under .cache/siblings/. It records each comparison payload's sha256 and byte count so
that adding a later artifact cannot silently make an older gate look current.

This script checks byte identity, binary support Jaccard, and support containment only; it
does not establish global uniqueness, geological validity, holdout promotion, or portal
acceptance. Run after a sibling refresh and after changes to public candidate TIFFs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems51.uniqueness import run_gate  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", help="path to candidate TIFF")
    ap.add_argument("--template", default=str(ROOT / "data" / "sample_submission.tif"))
    ap.add_argument("--siblings", default=str(ROOT / ".cache" / "siblings"))
    ap.add_argument("--out", default="", help="JSON receipt path (default: evidence/ timestamped)")
    args = ap.parse_args()

    candidate = Path(args.candidate)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if not candidate.is_file() or candidate.suffix.lower() not in {".tif", ".tiff"}:
        raise SystemExit(f"REFUSING: candidate TIFF does not exist: {candidate}")
    with rasterio.open(args.template) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(candidate) as ds:
        values = ds.read(1)
    if values.shape != footprint.shape:
        raise SystemExit("REFUSING: candidate and template shapes differ")
    support = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0) > 0

    paths: dict[str, Path] = {}
    for p in sorted((ROOT / "data" / "prior").glob("*.tif")):
        paths[f"local:{p.name}"] = p
    for p in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        if p.resolve() != candidate.resolve():
            paths[f"downloads:{p.name}"] = p
    for p in sorted(Path(args.siblings).glob("*.tif")):
        paths[f"sibling:{p.name}"] = p

    result = run_gate(candidate, paths, support, footprint)
    gate = result.as_dict()
    inventory = [
        {"label": label, "file": str(path), "bytes": path.stat().st_size,
         "sha256": sha256(path)}
        for label, path in sorted(paths.items()) if path.is_file()
    ]
    receipt = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate": str(candidate.relative_to(ROOT) if candidate.is_relative_to(ROOT) else candidate),
        "candidate_sha256": sha256(candidate),
        "candidate_support_px": int(support.sum()),
        "footprint_px": int(footprint.sum()),
        "comparison_count": len(inventory),
        "scope": "current local data/prior, docs/downloads and supplied .cache/siblings; not a global proof",
        "comparison_inventory": inventory,
        "gate": gate,
    }
    if args.out:
        dest = Path(args.out)
        if not dest.is_absolute():
            dest = ROOT / dest
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = ROOT / "evidence" / f"uniqueness_current_{candidate.stem}_{stamp}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=1))
    worst_j = max(gate["support_jaccard"].values(), default=0.0)
    worst_c = max(gate["support_containment"].values(), default=0.0)
    print(f"{gate['verdict']} — {len(inventory)} artifacts; "
          f"worst Jaccard {worst_j:.6f}; worst containment {worst_c:.6f}")
    print("receipt:", dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest)
    return 0 if gate["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
