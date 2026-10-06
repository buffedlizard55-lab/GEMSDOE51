#!/usr/bin/env python3
"""Restore and SHA-256 verify every file in registry/data_manifest.json.  FAILS CLOSED.

Usage:
    python3 scripts/fetch_data.py [--group core|external|scored|work|all] [--dest DIR]

Why this exists: DrivenData requires a login, so the organizer's bytes cannot be downloaded
unattended from this environment.  The sibling repositories mirror them as public GitHub blobs and
pin every byte with sha256; this script fetches those mirrors and refuses to keep anything whose
digest or size does not match the pin.  The mirrors are NOT organizer-authenticated -- see
registry/irregularities.json IR-51-DATA-01 -- so the only thing that makes them usable is that
every byte is checked here, and the check is reported in data/restore_receipt.json.

Requires: `gh` authenticated for github.com (or GH_TOKEN in the environment).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        with tmp.open("wb") as out:
            subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                 "-H", "Accept: application/vnd.github.raw"],
                stdout=out, check=True)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def restore_entry(entry: dict, root: Path) -> dict:
    dest = root / entry["dest"]
    if dest.exists() and sha256_file(dest) == entry["sha256"] and \
            dest.stat().st_size == entry["bytes"]:
        status = "present"
    else:
        if "parts" in entry:
            tmp = dest.with_suffix(".assembling")
            with tmp.open("wb") as out:
                for part in entry["parts"]:
                    p = root / "raw_parts" / Path(part).name
                    fetch(entry["repo"], entry["ref"], part, p)
                    with p.open("rb") as src:
                        shutil.copyfileobj(src, out, 1 << 20)
                    p.unlink()
            got = sha256_file(tmp)
            if got != entry["sha256"]:
                tmp.unlink(missing_ok=True)
                raise SystemExit(f"HASH MISMATCH for {entry['id']}: {got} != {entry['sha256']}")
            tmp.replace(dest)
        else:
            fetch(entry["repo"], entry["ref"], entry["path"], dest)
            got = sha256_file(dest)
            if got != entry["sha256"]:
                dest.unlink(missing_ok=True)
                raise SystemExit(f"HASH MISMATCH for {entry['id']}: {got} != {entry['sha256']}")
        status = "restored"
    if dest.stat().st_size != entry["bytes"]:
        raise SystemExit(f"SIZE MISMATCH for {entry['id']}: {dest.stat().st_size} != {entry['bytes']}")
    return dict(id=entry["id"], dest=entry["dest"], group=entry["group"], status=status,
                bytes=dest.stat().st_size, sha256=entry["sha256"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group", default="all", choices=["core", "external", "scored", "work", "all"])
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest.json"))
    ap.add_argument("--dest", default=None)
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text())
    root = Path(args.dest) if args.dest else Path(str(ROOT / ".cache" / "gems_data"))
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for e in man["files"]:
        if args.group in ("all", e["group"]):
            r = restore_entry(e, root)
            results.append(r)
            print(f"{r['status']:>8}  {e['dest']:70s} sha256={r['sha256'][:12]}...", flush=True)
    receipt = dict(schema_version=1, verified_files_count=len(results), storage_root=str(root),
                   manifest=str(args.manifest), files=results)
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(results)} files; receipt written to data/restore_receipt.json")


if __name__ == "__main__":
    sys.exit(main())
