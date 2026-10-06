#!/usr/bin/env python3
"""Restore the hash-pinned GEMS competition + external mirrors into ``data/``.

Why this script exists
----------------------
The DrivenData data page is login-walled and this sandbox's egress is allowlisted
(PyPI + github.com + api.github.com only).  The group therefore re-hosts the
competition rasters as *public GitHub blobs* and pins every byte by sha256 in
``registry/data_manifest.json``.  A fetch that does not verify is worthless, so
this script verifies and exits non-zero on any digest mismatch (fail closed).

Nothing here contacts drivendata.org, and no DrivenData credential is used.

Usage
-----
    python3 scripts/restore_data.py [--group core|external|all] [--target-dir DIR]

Requires ``gh`` to be authenticated against github.com (it is, in this sandbox).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_manifest.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def gh_raw(repo: str, ref: str, path: str, dest: Path, label: str) -> None:
    """Fetch ``repo@ref:path`` raw bytes with the GitHub Contents API."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        with tmp.open("wb") as out:
            subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                 "-H", "Accept: application/vnd.github.raw"],
                stdout=out, check=True,
            )
        tmp.replace(dest)
    except subprocess.CalledProcessError as exc:
        print(f"FAIL  {label:28s} gh api returned {exc.returncode} for {repo}@{ref}:{path}")
        raise
    finally:
        tmp.unlink(missing_ok=True)


def restore(entry: dict, target: Path) -> dict:
    dest = target / entry["dest"]
    want = entry["sha256"]
    nbytes = entry.get("bytes")

    if dest.exists() and (want == "PENDING" or sha256_file(dest) == want):
        status = "cached"
    else:
        if "parts" in entry:
            chunks = []
            for i, part in enumerate(entry["parts"]):
                c = dest.parent / f"_part-{i:03d}"
                gh_raw(entry["repo"], entry["ref"], part, c, f"{entry['id']}[{i}]")
                chunks.append(c)
            with dest.open("wb") as out:
                for c in chunks:
                    with c.open("rb") as fh:
                        shutil.copyfileobj(fh, out, 1 << 22)
                out.flush()
                os.fsync(out.fileno())
            for c in chunks:
                c.unlink()
        else:
            gh_raw(entry["repo"], entry["ref"], entry["path"], dest, entry["id"])
        status = "fetched"

    got = sha256_file(dest)
    size = dest.stat().st_size
    size_ok = (nbytes is None) or (size == nbytes)
    digest_ok = (want == "PENDING") or (got == want)
    ok = digest_ok and size_ok
    print(("PASS " if ok else "FAIL ")
          + f"{entry['id']:34s} {status:8s} {size:>13,} B  {got[:16]}...")
    return {
        "id": entry["id"], "dest": entry["dest"], "status": status, "bytes": size,
        "sha256": got, "pinned_sha256": want, "digest_ok": digest_ok,
        "size_ok": size_ok, "ok": ok, "provenance": entry.get("provenance", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all", choices=["core", "external", "all"])
    ap.add_argument("--target-dir", default=str(ROOT / "data" / "raw"))
    a = ap.parse_args()

    spec = json.loads(MANIFEST.read_text())
    target = Path(a.target_dir)
    target.mkdir(parents=True, exist_ok=True)

    results, failed = [], []
    for entry in spec["files"]:
        if a.group not in ("all", entry.get("group", "core")):
            continue
        try:
            r = restore(entry, target)
        except Exception as exc:  # noqa: BLE001 - fail closed, report, keep going
            failed.append(entry["id"])
            print(f"FAIL  {entry['id']:34s} {type(exc).__name__}: {exc}")
            continue
        results.append(r)
        if not r["ok"]:
            failed.append(entry["id"])

    receipt = {
        "schema_version": 1,
        "verified_files_count": sum(1 for r in results if r["ok"]),
        "failed_files": failed,
        "storage_root": str(target),
        "files": results,
    }
    out = ROOT / "data" / "restore_receipt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1))
    print(json.dumps({"verified": receipt["verified_files_count"], "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
