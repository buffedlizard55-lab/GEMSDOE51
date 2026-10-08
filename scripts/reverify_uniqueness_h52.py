#!/usr/bin/env python3
"""Re-run the support-uniqueness gate for an already-built H52 artifact.

Why this exists
---------------
The full builder (``scripts/build_submission_h52.py``) retrains the belief field and
needs ``data/prepared/`` (multi-GB, deliberately not in Git).  When the *only* thing
that has to change is the set of comparison artifacts - e.g. after an interim build of
the same emission is pruned because it duplicated the shipped one - the gate can be
re-measured on its own, against freshly fetched sibling bytes, without retraining.

What it re-measures (and what it refuses to fake)
-------------------------------------------------
* byte-sha256 identity, support Jaccard and support containment against
  ``data/prior/*.tif``, the current ``docs/downloads/*.tif`` and ``.cache/siblings/*.tif``
  (the sibling TIFFs are re-fetched from GitHub by ``/tmp/fetch_siblings.py``-style API
  calls and their digests are recorded in the receipt);
* the Stage-1 dominance block is *carried over* from the original build receipt and
  labelled as carried, because it depends on the Stage-1 approved mask that can only be
  recomputed with ``data/prepared/``.  It is not affected by which comparison artifacts
  are present, so carrying it changes no number;
* the format block is re-verified from the written bytes and must be identical to the
  original receipt, otherwise this script refuses.

Usage
-----
    .venv/bin/python scripts/reverify_uniqueness_h52.py \
        --checks docs/downloads/<name>-checks.json \
        --prune <duplicate-file-name.tif>
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

from gems51.submission import verify  # noqa: E402
from gems51.uniqueness import run_gate  # noqa: E402

DOCS = ROOT / "docs" / "downloads"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def footprint_from_template(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return np.isfinite(ds.read(1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checks", required=True, help="the build receipt to update in place")
    ap.add_argument("--template", default=str(ROOT / "data" / "sample_submission.tif"),
                    help="competition template whose finite mask defines the footprint")
    ap.add_argument("--prune", default="", help="comma-separated file names to delete first")
    ap.add_argument("--reason", default="", help="why the pruned files are not distinct artifacts")
    ap.add_argument("--siblings", default=str(ROOT / ".cache" / "siblings"))
    ap.add_argument("--max-jaccard", type=float, default=0.50)
    ap.add_argument("--max-containment", type=float, default=0.60)
    args = ap.parse_args()

    checks_path = Path(args.checks)
    rec = json.loads(checks_path.read_text())
    name = rec["name"]
    tif = DOCS / f"{name}.tif"
    if not tif.is_file():
        raise SystemExit(f"REFUSING: candidate {tif} is missing")
    old_gate = rec["uniqueness"]

    footprint = footprint_from_template(Path(args.template))
    print(f"footprint from {Path(args.template).name}: {int(footprint.sum()):,} px, "
          f"shape {footprint.shape}")
    with rasterio.open(tif) as ds:
        support = ds.read(1) > 0
    if support.shape != footprint.shape:
        raise SystemExit("REFUSING: candidate shape != footprint shape")

    # ------------------------------------------------------------------ prune duplicates
    pruned = []
    for raw in [s for s in args.prune.split(",") if s.strip()]:
        p = DOCS / raw.strip()
        if not p.is_file():
            raise SystemExit(f"REFUSING: asked to prune {p.name}, which does not exist")
        entry = dict(file=p.name, bytes=p.stat().st_size, sha256=sha256_file(p),
                     jaccard_vs_candidate=old_gate["support_jaccard"].get(f"downloads:{p.name}"),
                     containment_vs_candidate=old_gate["support_containment"].get(
                         f"downloads:{p.name}"))
        p.unlink()
        twin_zip = p.with_suffix(".zip")
        if twin_zip.is_file():
            entry["zip"] = dict(file=twin_zip.name, bytes=twin_zip.stat().st_size,
                                sha256=sha256_file(twin_zip))
            twin_zip.unlink()
        old_receipt = p.with_name(p.stem + "-checks.json")
        if old_receipt.is_file():
            entry["checks_receipt"] = old_receipt.name
            old_receipt.unlink()
        pruned.append(entry)
        print(f"pruned {entry['file']} (sha256 {entry['sha256'][:16]}...)")

    # ------------------------------------------------------------------ comparison set
    prior_paths = {}
    for p in sorted((ROOT / "data" / "prior").glob("*.tif")):
        prior_paths[f"local:{p.name}"] = p
    for p in sorted(DOCS.glob("*.tif")):
        if p.name != tif.name:
            prior_paths[f"downloads:{p.name}"] = p
    sib_dir = Path(args.siblings)
    for p in sorted(sib_dir.glob("*.tif")):
        prior_paths[f"sibling:{p.name}"] = p
    sib_digests = {p.name: sha256_file(p) for p in sorted(sib_dir.glob("*.tif"))}
    print(f"comparison set: {len(prior_paths)} artifacts "
          f"({len(sib_digests)} sibling bytes re-fetched)")

    gate = run_gate(tif, prior_paths, support, footprint,
                    max_jaccard=args.max_jaccard, max_containment=args.max_containment)
    new = gate.as_dict()

    # ------------------------------------------------------------------ carried blocks
    new["stage1_dominance"] = old_gate["stage1_dominance"]
    new["stage1_dominance"]["carried_from_original_build_receipt"] = True
    new["notes"] = list(new.get("notes", [])) + [
        "Stage-1 dominance block carried unchanged from the original build receipt: it depends "
        "on the Stage-1 approved mask, which can only be recomputed with data/prepared/ "
        "(not in Git). Pruning comparison artifacts cannot change it.",
    ]
    for entry in pruned:
        new["notes"].append(
            f"pruned {entry['file']} before this gate run: it was an interim build of the same "
            f"emission (support Jaccard {entry['jaccard_vs_candidate']:.4f}, containment "
            f"{entry['containment_vs_candidate']:.4f} against this candidate), not a distinct "
            f"submission - see the gate_rerun block of this receipt for its sha256")

    fmt = verify(tif, footprint)
    old_fmt = rec.get("format", {})
    if old_fmt.get("sha256") and old_fmt["sha256"] != fmt["sha256"]:
        raise SystemExit("REFUSING: the candidate bytes changed since the build receipt")
    rec["format"] = fmt
    rec["uniqueness"] = new
    rec["gate_rerun"] = dict(
        utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        reason=args.reason or "re-gate after pruning duplicate comparison artifacts",
        footprint_source=Path(args.template).name, footprint_px=int(footprint.sum()),
        pruned=pruned, comparison_set_size=len(prior_paths),
        sibling_digests=sib_digests,
        verdict=new["verdict"],
    )
    checks_path.write_text(json.dumps(rec, indent=1))

    print("\nuniqueness verdict:", new["verdict"])
    worst_j = max(new["support_jaccard"].values())
    worst_c = max(new["support_containment"].values())
    print(f"worst Jaccard {worst_j:.4f} (limit {args.max_jaccard}), "
          f"worst containment {worst_c:.4f} (limit {args.max_containment})")
    return 0 if str(new["verdict"]).startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
