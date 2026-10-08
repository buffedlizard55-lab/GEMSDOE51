#!/usr/bin/env python3
"""Post-run instrument recompute for the R1 receipt (preregistration Amendment A1).

The running harness was frozen with the original instrument check (base vs the
archived hh_blend numbers).  The archived field files were never committed, so
Amendment A1 (knowledge/preregistration-2026-10-08.md section 6) anchors the
check on evidence/p1_holdout_20261007.json baseline_ungated instead.  This
script appends that recomputation to the receipt's summary without touching
the raw per-fold values.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "evidence" / "r1_holdout_20261008.json"
P1 = ROOT / "evidence" / "p1_holdout_20261007.json"
TOL = 1e-5


def main() -> int:
    doc = json.loads(RECEIPT.read_text())
    p1 = json.loads(P1.read_text())
    p1_rows = {int(r["fold"]): r for r in p1["rows"]}
    folds = sorted(int(k) for k in doc["per_fold"])
    if folds != [0, 1, 2, 3, 4, 5]:
        raise SystemExit("receipt must contain exactly folds 0..5")
    base = [doc["per_fold"][str(i)]["rules"]["base"]["dti"] for i in folds]
    p1_base = [p1_rows[i]["scores"]["baseline_ungated"]["dti"] for i in folds]
    devs = [abs(b - p) for b, p in zip(base, p1_base)]
    doc["summary"]["instrument_amendment_A1"] = dict(
        anchor="evidence/p1_holdout_20261007.json baseline_ungated",
        per_fold_base=base,
        per_fold_anchor=p1_base,
        per_fold_deviation=devs,
        max_abs_dev=float(max(devs)),
        tol=TOL,
        passes=bool(max(devs) <= TOL),
        note=("Amendment A1 in knowledge/preregistration-2026-10-08.md section 6: "
              "archived frozen-best fields were never committed; the P1 receipt is "
              "the same procedure in the same pipeline state."))
    RECEIPT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc["summary"]["instrument_amendment_A1"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
