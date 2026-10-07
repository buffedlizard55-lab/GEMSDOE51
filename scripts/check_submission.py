#!/usr/bin/env python3
"""Run the current local format verifier on one GeoTIFF.

Usage: python scripts/check_submission.py path/to/candidate.tif
This verifies bytes against the local template and footprint only; it does not
predict acceptance by DrivenData.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import footprint  # noqa: E402
from gems51.submission import verify  # noqa: E402


def _passes(name: str, value: object, checks: dict) -> bool:
    """Interpret count-valued and alternative footprint checks."""
    if name in {"values_outside_0_1", "global_invalid_cells"}:
        return value == 0
    if name in {"outside_footprint_zeros", "outside_footprint_nan", "nodata_tag_is_nan"}:
        # The current contract accepts either finite zero outside or explicit
        # NaN/NoData outside; this diagnostic is not a failure when the NaN
        # alternative is the one present on disk.
        return bool(checks.get("outside_footprint_zeros")) or bool(checks.get("outside_footprint_nan"))
    return bool(value)


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
        if name in {"min_value", "max_value", "predicted_px", "total_mass", "nan_cells", "global_invalid_cells", "all_cells_finite_in_range"}:
            continue
        display = value
        if name == "outside_footprint_zeros" and not value and checks.get("outside_footprint_nan"):
            display = "False (NaN outside is the accepted alternative)"
        print(f"  {'PASS' if _passes(name, value, checks) else 'FAIL'}  {name}: {display}")
    print(f"  file  {report['file']}")
    print(f"  sha256  {report['sha256']}")
    print("  note  local byte-level format checks only; portal acceptance is not inferred")
    print("LOCAL FORMAT CHECKS " + ("PASS" if checks["format_valid"] else "FAIL"))
    return 0 if checks["format_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
