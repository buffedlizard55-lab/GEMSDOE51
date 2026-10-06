#!/usr/bin/env python3
"""Verify a submission raster against the competition format contract and its receipt.

    python3 scripts/check_submission.py docs/downloads/gemsdoe51-strainbudget-s1-v1.tif

Exit code 0 = the file satisfies every rule the portal checks, and (if a receipt exists for it) its
sha256 matches the receipt.  Exit code 1 = at least one rule failed, printed with the reason.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
EPSG = 32611
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
SHAPE = (3730, 3292)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    fails: list[str] = []

    def ok(cond: bool, msg: str) -> None:
        print(("  PASS  " if cond else "  FAIL  ") + msg)
        if not cond:
            fails.append(msg)

    with rasterio.open(path) as ds:
        ok(ds.count == 1, f"single band (found {ds.count})")
        ok(ds.dtypes[0] == "float32", f"dtype float32 (found {ds.dtypes[0]})")
        ok(ds.crs is not None and ds.crs.to_epsg() == EPSG, f"EPSG:{EPSG} (found {ds.crs})")
        ok(tuple(ds.shape) == SHAPE, f"shape {SHAPE} (found {ds.shape})")
        tf = ds.transform
        got = (tf.a, tf.b, tf.c, tf.d, tf.e, tf.f)
        ok(all(abs(a - b) < 1e-6 for a, b in zip(got, TRANSFORM)),
           f"transform {TRANSFORM} (found {tuple(round(v, 6) for v in got)})")
        nod = ds.nodatavals[0]
        ok(nod is None or (0.0 <= float(nod) <= 1.0),
           f"nodata tag absent or inside [0,1] (found {nod})")
        a = ds.read(1)

    a = np.asarray(a)
    ok(np.isfinite(a).all(), "all cells finite (no NaN, no sentinel)")
    ok(float(a.min()) >= 0.0 and float(a.max()) <= 1.0,
       f"values inside [0,1] (min {float(a.min())}, max {float(a.max())})")
    n_pos = int((a > 0).sum())
    print(f"  note  {n_pos:,} emitting pixels, {float((a > 0).mean()) * 100:.3f}% of the grid")

    receipt = ROOT / "evidence" / "submission_receipt.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"  note  sha256 {digest}")
    if receipt.exists():
        r = json.loads(receipt.read_text())
        if Path(r.get("path", "")).name == path.name:
            ok(digest == r.get("sha256"), "sha256 matches evidence/submission_receipt.json")
            ok(n_pos == r.get("n_positive"), "emitting-pixel count matches the receipt")
        else:
            print("  note  receipt exists but describes a different filename; digest not compared")

    print(("ALL CHECKS PASSED" if not fails else f"{len(fails)} CHECK(S) FAILED"))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
