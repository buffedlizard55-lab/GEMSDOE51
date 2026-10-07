#!/usr/bin/env python3
"""Run the current local format verifier on one GeoTIFF.

Usage: python scripts/check_submission.py path/to/candidate.tif
This verifies bytes against the local template and footprint only; it does not
predict acceptance by DrivenData. No candidate is currently cleared for upload.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import footprint  # noqa: E402
from gems51.submission import verify  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"FAIL: file not found: {path}")
        return 2
    try:
        report = verify(path, footprint())
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: local format verification could not complete: {exc}")
        return 1
    checks = report["checks"]
    for name, value in checks.items():
        if name in {"min_value", "max_value", "predicted_px", "total_mass", "nan_cells"}:
            continue
        print(f"  {'PASS' if value else 'FAIL'}  {name}: {value}")
    print(f"  file  {report['file']}")
    print(f"  sha256  {report['sha256']}")
    print("  note  local byte-level format checks only; portal acceptance is not inferred")
    print("LOCAL FORMAT CHECKS " + ("PASS" if checks["format_valid"] else "FAIL"))
    return 0 if checks["format_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
