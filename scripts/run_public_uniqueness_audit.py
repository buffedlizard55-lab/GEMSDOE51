#!/usr/bin/env python3
"""Re-run the candidate uniqueness gate against a reproducible public artifact corpus.

The historical 211-file study directory referenced by docs/uniqueness_gate.json
is not present in this checkout. This script reconstructs a fresh corpus from all
`.tif` files indexed under `docs/downloads/` and `submissions/` in the pinned
54-repository public inventory, deduplicates exact Git blobs, verifies every
fetched blob against its indexed Git SHA, and then invokes the full pixel-level
uniqueness gate. Downloads live only in a temporary directory under /tmp.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "registry" / "sibling_tiff_inventory.json"
CHECKER = ROOT / "scripts" / "run_uniqueness_gate.py"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def eligible(path: str) -> bool:
    low = path.lower()
    return low.endswith((".tif", ".tiff")) and (
        path.startswith("docs/downloads/") or path.startswith("submissions/")
    )


def fetch_one(args):
    index, rec, tempdir = args
    repo, branch, path = rec["repo"], rec["branch"], rec["path"]
    filename = f"{index:04d}-{rec['git_blob_sha'][:12]}.tif"
    dest = Path(tempdir) / filename
    endpoint = (f"repos/buffedlizard55-lab/{repo}/contents/"
                f"{quote(path, safe='/')}?ref={quote(branch, safe='')}")
    last_error = None
    for attempt in range(3):
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
        except Exception as exc:  # noqa: BLE001 - external network/process boundary
            last_error = f"{type(exc).__name__}: {exc}"
    return {"ok": False, "record": rec, "error": last_error or "download failed"}


def canonical_source(rec):
    return f"{rec['repo']}:{rec['path']}"


def rewrite_paths(obj, temp_to_source):
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key == "path" and isinstance(value, str) and value in temp_to_source:
                src = temp_to_source[value]
                result[key] = canonical_source(src)
                result["source_url"] = (
                    f"https://github.com/buffedlizard55-lab/{src['repo']}/blob/"
                    f"{src['branch']}/{quote(src['path'], safe='/')}"
                )
            else:
                result[key] = rewrite_paths(value, temp_to_source)
        return result
    if isinstance(obj, list):
        return [rewrite_paths(v, temp_to_source) for v in obj]
    return obj


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default="evidence/uniqueness_gate_public_downloads.json")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    candidate = Path(args.candidate).resolve()
    if not candidate.exists():
        raise SystemExit(f"candidate not found: {candidate}")

    inventory = json.loads(INVENTORY.read_text())
    all_records = []
    for repo_record in inventory.get("repos", []):
        repo = repo_record["repo"]
        branch = repo_record.get("branch") or "main"
        for f in repo_record.get("tifs", []):
            if eligible(f.get("path", "")):
                all_records.append({
                    "repo": repo, "branch": branch, "path": f["path"],
                    "size": int(f["size"]), "git_blob_sha": f["sha"],
                })

    # Dedupe exact bytes, retaining all aliases for provenance. Exclude this exact
    # candidate path only; a same-byte artifact in another repository remains a
    # genuine byte-identity failure and must not be hidden by deduplication.
    by_sha = {}
    for rec in all_records:
        by_sha.setdefault(rec["git_blob_sha"], []).append(rec)
    candidate_data = candidate.read_bytes()
    candidate_git_sha = git_blob_sha(candidate_data)
    unique_records = []
    for sha, aliases in by_sha.items():
        usable = [r for r in aliases
                  if not (Path(r["path"]).name == candidate.name
                          and r["repo"] == "GEMSDOE51")]
        if usable:
            rep = dict(usable[0])
            rep["aliases"] = usable
            unique_records.append(rep)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gemsdoe51-public-tifs-") as tmp:
        tasks = [(i, rec, tmp) for i, rec in enumerate(unique_records)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            downloaded = list(pool.map(fetch_one, tasks))
        successful = [r for r in downloaded if r["ok"]]
        failed = [{"source": canonical_source(r["record"]),
                   "error": r["error"], "expected_git_blob_sha": r["record"]["git_blob_sha"]}
                  for r in downloaded if not r["ok"]]

        checker_out = Path(tmp) / "checker.json"
        refs = [r["path"] for r in successful]
        cmd = [sys.executable, str(CHECKER), "--candidate", str(candidate),
               "--out", str(checker_out)]
        if refs:
            cmd += ["--refs", *refs]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if not checker_out.exists():
            raise RuntimeError("uniqueness checker did not write output:\n" + proc.stdout + proc.stderr)
        report = json.loads(checker_out.read_text())
        temp_to_source = {r["path"]: r["record"] for r in successful}
        report = rewrite_paths(report, temp_to_source)

        # Do not call an incomplete fetch a pass.
        checker_verdict = report.get("verdict")
        report["checker_verdict"] = checker_verdict
        report["verdict"] = "INCOMPLETE" if failed else checker_verdict
        report["audit"] = {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "candidate_path": str(candidate.relative_to(ROOT)
                                   if candidate.is_relative_to(ROOT) else candidate),
            "candidate_git_blob_sha": candidate_git_sha,
            "historical_gate_note": "The historical n=211 input directory from docs/uniqueness_gate.json is absent; this is an independently rebuilt public-artifact corpus, not a bit-for-bit replay of that missing list.",
            "inventory": str(INVENTORY.relative_to(ROOT)),
            "inventory_repositories": len(inventory.get("repos", [])),
            "selection": "All unique-by-Git-blob `.tif`/`.tiff` payloads indexed under docs/downloads/ and submissions/ across the public 54-repository inventory. Non-submission TIFs elsewhere in those repos are out of scope.",
            "indexed_path_count": len(all_records),
            "unique_payload_count_before_candidate_exclusion": len(by_sha),
            "candidate_exact_path_excluded": candidate.name,
            "unique_payload_count_after_exclusion": len(unique_records),
            "downloaded_and_sha_verified": len(successful),
            "download_errors": failed,
            "checker_returncode": proc.returncode,
            "checker_stdout": proc.stdout[-3000:],
            "checker_stderr": proc.stderr[-3000:],
            "reference_manifest": [
                {
                    "git_blob_sha": r["record"]["git_blob_sha"],
                    "bytes": r["bytes"],
                    "representative": canonical_source(r["record"]),
                    "source_url": (
                        f"https://github.com/buffedlizard55-lab/{r['record']['repo']}/blob/"
                        f"{r['record']['branch']}/{quote(r['record']['path'], safe='/')}"
                    ),
                    "aliases": [canonical_source(a) for a in r["record"]["aliases"]],
                }
                for r in successful
            ],
        }
        out_path.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({
        "verdict": report["verdict"],
        "checker_verdict": report["checker_verdict"],
        "n_references_fetched": len(successful),
        "n_download_errors": len(failed),
        "n_compared": report.get("n_compared", 0),
        "n_skipped": len(report.get("skipped", [])),
        "output": str(out_path),
    }, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
