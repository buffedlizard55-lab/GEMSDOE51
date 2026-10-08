#!/usr/bin/env python3
"""Re-run support uniqueness against the pinned public artifact corpus.

The historical 211-file study directory referenced by docs/uniqueness_gate.json
is not present in this checkout. This script reconstructs the corpus from all
`.tif`/`.tiff` files indexed under `docs/downloads/` and `submissions/` in the
pinned 54-repository inventory, deduplicates exact Git blobs, verifies each
fetched blob against its indexed Git SHA and byte count, and calls the current
``gems51.uniqueness.run_gate`` directly. It does not call the retired
``scripts/run_uniqueness_gate.py``. Downloads live only in a temporary directory.

A complete inventory pass is bounded public-artifact evidence, not a global
novelty proof or a submission recommendation. Unreadable/mismatched-grid refs
fail closed as INCOMPLETE; all candidate metric thresholds remain unchanged.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems51.uniqueness import run_gate  # noqa: E402

INVENTORY = ROOT / "registry" / "sibling_tiff_inventory.json"
TEMPLATE = ROOT / "data" / "sample_submission.tif"


def git_blob_sha(data: bytes) -> str:
    """Git's SHA-1 blob identifier (the registry's pinned identity)."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def eligible(path: str) -> bool:
    return path.lower().endswith((".tif", ".tiff")) and (
        path.startswith("docs/downloads/") or path.startswith("submissions/")
    )


def fetch_one(args):
    index, rec, tempdir = args
    endpoint = (f"repos/buffedlizard55-lab/{rec['repo']}/contents/"
                f"{quote(rec['path'], safe='/')}?ref={quote(rec['branch'], safe='')}")
    dest = Path(tempdir) / f"{index:04d}-{rec['git_blob_sha'][:12]}.tif"
    last_error = None
    for _ in range(3):
        try:
            proc = subprocess.run(
                ["gh", "api", "-H", "Accept: application/vnd.github.raw", endpoint],
                cwd=ROOT, capture_output=True, timeout=120,
            )
            if proc.returncode:
                last_error = proc.stderr.decode("utf-8", "replace")[:500]
                continue
            data = proc.stdout
            actual = git_blob_sha(data)
            if actual != rec["git_blob_sha"]:
                last_error = f"Git blob SHA mismatch: expected {rec['git_blob_sha']}, got {actual}"
                continue
            if len(data) != rec["size"]:
                last_error = f"byte size mismatch: expected {rec['size']}, got {len(data)}"
                continue
            dest.write_bytes(data)
            return {"ok": True, "path": str(dest), "bytes": len(data),
                    "git_blob_sha": actual, "record": rec}
        except Exception as exc:  # noqa: BLE001 - process/network boundary
            last_error = f"{type(exc).__name__}: {exc}"
    # The manifest includes historical paths removed from repository branches.
    # Recover their immutable Git object by the already-pinned blob SHA instead
    # of treating a legitimate 404 as missing corpus coverage.
    try:
        blob = subprocess.run(
            ["gh", "api", f"repos/buffedlizard55-lab/{rec['repo']}/git/blobs/{rec['git_blob_sha']}"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        if blob.returncode == 0:
            payload = json.loads(blob.stdout)
            data = base64.b64decode(payload["content"])
            actual = git_blob_sha(data)
            if actual == rec["git_blob_sha"] and len(data) == rec["size"]:
                dest.write_bytes(data)
                return {"ok": True, "path": str(dest), "bytes": len(data),
                        "git_blob_sha": actual, "record": rec,
                        "recovered_by_immutable_blob": True}
            last_error = (f"immutable blob mismatch: expected {rec['git_blob_sha']} / "
                          f"{rec['size']} bytes, got {actual} / {len(data)} bytes")
        else:
            last_error = blob.stderr.decode("utf-8", "replace")[:500]
    except Exception as exc:  # noqa: BLE001 - process/network boundary
        last_error = f"immutable blob lookup failed: {type(exc).__name__}: {exc}"
    return {"ok": False, "record": rec, "error": last_error or "download failed"}


def canonical_source(rec: dict) -> str:
    return f"{rec['repo']}:{rec['path']}"


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default="evidence/uniqueness_gate_public_downloads.json")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--template", default=str(TEMPLATE))
    args = ap.parse_args()
    candidate = Path(args.candidate).resolve()
    if not candidate.is_file():
        raise SystemExit(f"candidate not found: {candidate}")
    if candidate.suffix.lower() not in {".tif", ".tiff"}:
        raise SystemExit(f"candidate must be a TIFF: {candidate}")

    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    all_records = []
    for repo_record in inventory.get("repos", []):
        repo = repo_record["repo"]
        branch = repo_record.get("branch") or "main"
        for record in repo_record.get("tifs", []):
            if eligible(record.get("path", "")):
                all_records.append(dict(
                    repo=repo, branch=branch, path=record["path"],
                    size=int(record["size"]), git_blob_sha=record["sha"],
                ))

    # Deduplicate only identical Git blobs; retain aliases so provenance is visible.
    by_sha: dict[str, list[dict]] = {}
    for record in all_records:
        by_sha.setdefault(record["git_blob_sha"], []).append(record)
    unique_records = []
    for sha, aliases in by_sha.items():
        usable = [r for r in aliases
                  if not (r["repo"] == "GEMSDOE51"
                          and Path(r["path"]).name == candidate.name)]
        if usable:
            rep = dict(usable[0])
            rep["aliases"] = usable
            unique_records.append(rep)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(args.template) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(candidate) as src:
        candidate_values = src.read(1)
        candidate_shape = (src.height, src.width)
    if candidate_shape != footprint.shape:
        raise SystemExit("candidate raster shape differs from the registered template")
    candidate_support = np.nan_to_num(candidate_values, nan=0.0,
                                      posinf=0.0, neginf=0.0) > 0

    with tempfile.TemporaryDirectory(prefix="gemsdoe51-public-tifs-") as tmp:
        tasks = [(i, rec, tmp) for i, rec in enumerate(unique_records)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            downloaded = list(pool.map(fetch_one, tasks))
        successful = [record for record in downloaded if record["ok"]]
        failed = [dict(source=canonical_source(record["record"]),
                       error=record["error"],
                       expected_git_blob_sha=record["record"]["git_blob_sha"])
                  for record in downloaded if not record["ok"]]

        valid_paths: dict[str, Path] = {}
        invalid = []
        excluded_noncompetition_grid = []
        for item in successful:
            ref = Path(item["path"])
            try:
                with rasterio.open(ref) as src:
                    shape = (src.height, src.width)
                    count = src.count
                    src.read(1, out_shape=(min(src.height, 32), min(src.width, 32)))
                if shape != candidate_shape:
                    mismatch = dict(source=canonical_source(item["record"]),
                                    reason="different raster shape",
                                    shape=list(shape), expected_shape=list(candidate_shape))
                    # The pinned inventory contains one explicitly named toy
                    # format fixture, not a competition prediction raster. It
                    # is reported, but excluded from same-grid support checks.
                    if Path(item["record"]["path"]).name == "GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif":
                        mismatch["scope_decision"] = "excluded: explicit NOT_SUBMISSION format fixture; incompatible 32x48 grid"
                        excluded_noncompetition_grid.append(mismatch)
                    else:
                        invalid.append(mismatch)
                    continue
                if count < 1:
                    invalid.append(dict(source=canonical_source(item["record"]),
                                        reason="no readable raster band"))
                    continue
                valid_paths[canonical_source(item["record"])] = ref
            except Exception as exc:  # noqa: BLE001
                invalid.append(dict(source=canonical_source(item["record"]),
                                    reason=f"unreadable TIFF: {exc}"))

        # Include current local priors/artifacts, excluding the candidate itself.
        local_paths: dict[str, Path] = {}
        for root in (ROOT / "data" / "prior", ROOT / "data" / "refs",
                     ROOT / "docs" / "downloads", ROOT / "submissions",
                     ROOT / "archive" / "submissions"):
            if not root.exists():
                continue
            for ref in root.rglob("*.tif"):
                if ref.resolve() != candidate:
                    local_paths[_relative(ref)] = ref
        prior_paths = {**local_paths, **valid_paths}
        report = run_gate(candidate, prior_paths, candidate_support, footprint).as_dict()
        # Fail closed on any unverified or incomparable inventory item.
        coverage_complete = (not failed and not invalid
                             and len(successful) == len(unique_records)
                             and len(valid_paths) + len(excluded_noncompetition_grid) == len(unique_records))
        support_gate_verdict = report["verdict"]
        verdict = support_gate_verdict if coverage_complete else "INCOMPLETE"
        report.update(
            verdict=verdict,
            support_gate_verdict=support_gate_verdict,
            coverage_complete=coverage_complete,
            invalid_references=invalid,
            excluded_noncompetition_grid=excluded_noncompetition_grid,
            download_errors=failed,
            audit=dict(
                generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                candidate_path=_relative(candidate),
                candidate_git_blob_sha=git_blob_sha(candidate.read_bytes()),
                inventory=str(INVENTORY.relative_to(ROOT)),
                inventory_repositories=len(inventory.get("repos", [])),
                indexed_path_count=len(all_records),
                unique_payload_count_before_candidate_exclusion=len(by_sha),
                unique_payload_count_after_candidate_exclusion=len(unique_records),
                downloaded_and_git_sha_verified=len(successful),
                pixel_comparisons=len(report.get("support_jaccard", {})),
                local_comparison_count=len(local_paths),
                historical_gate_note=(
                    "The historical n=211 directory is unavailable. This is a rebuilt "
                    "public-artifact corpus, not a bit-for-bit replay of that list."
                ),
                selection=(
                    "Unique-by-Git-blob .tif/.tiff under docs/downloads/ and submissions/ "
                    "in the pinned 54-repository inventory; non-submission TIFs elsewhere "
                    "are outside scope. The explicitly named GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif "
                    "(32x48) is reported separately and excluded from same-grid support comparison."
                ),
                reference_manifest=[dict(
                    git_blob_sha=item["record"]["git_blob_sha"],
                    bytes=item["bytes"],
                    representative=canonical_source(item["record"]),
                    source_url=(
                        f"https://github.com/buffedlizard55-lab/{item['record']['repo']}/blob/"
                        f"{item['record']['branch']}/{quote(item['record']['path'], safe='/')}"
                    ),
                    aliases=[canonical_source(alias) for alias in item["record"]["aliases"]],
                ) for item in successful],
            ),
        )
        out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "verdict": report["verdict"],
        "checker_verdict": report["verdict"],
        "coverage_complete": coverage_complete,
        "n_references_expected": len(unique_records),
        "n_references_fetched": len(successful),
        "n_download_errors": len(failed),
        "n_invalid_references": len(invalid),
        "n_compared": len(report.get("support_jaccard", {})),
        "output": _relative(out_path),
    }, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
