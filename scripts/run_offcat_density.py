#!/usr/bin/env python3
"""Turn the off-catalogue mass arms into a promotion decision.

    python3 scripts/run_offcat_holdout.py      # produces evidence/offcat_holdout.json (all arms)
    python3 scripts/run_offcat_density.py      # extracts the density arms -> offcat_density_sweep.json

WHY THIS EXISTS
---------------
The hidden label density is unknown. We therefore treat density as a sensitivity variable rather
than assert a hidden-K estimate. Under DTI = T / (0.2T + 0.2F + 0.8K), extra prediction mass
helps only when it earns enough additional weighted credit. The mass optimum should be screened on
the faithful instrument (fault systems split A/B, detector trained on A alone), not inferred from
the visible catalogue's denser known-fault distribution.

PROMOTION RULE (pre-registered, identical to the one that killed the coverage lattice, IR-51-05):
an arm may replace the shipped rule only if mean paired DTI on the B_far truth > 0 AND the paired
contrast is positive in >= 3 of 4 folds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = "thin_d0.04_s3.0"


def main() -> int:
    src = ROOT / "evidence/offcat_holdout.json"
    if not src.exists():
        print(f"missing {src}; run scripts/run_offcat_holdout.py first")
        return 2
    d = json.loads(src.read_text())
    results = d.get("results", [])
    paired = d.get("paired", {})
    folds = sorted({r["fold"] for r in results})

    arms = sorted({r["rule"] for r in results if r["rule"].startswith("thin_d")})
    rows = []
    for arm in arms:
        vals = [r["dti_B_far"] for r in results if r["rule"] == arm]
        pv = paired.get(f"{arm}|B_far", {})
        pv = pv if pv else paired.get(f"{arm}|B_all", {})
        deltas = [float(v) for v in pv.get("per_fold", [])]
        mean_delta = float(pv.get("mean_delta", float("nan")))
        n_pos = int(pv.get("folds_positive", 0))
        rows.append(dict(arm=arm, n_px=int(np.mean([r["n_px"] for r in results if r["rule"] == arm])),
                         dti_B_far=float(np.mean(vals)), delta_vs_shipped=mean_delta,
                         folds_positive=n_pos, n_folds=len(deltas),
                         promoted=bool(arm != SHIPPED and mean_delta > 0 and n_pos >= 3)))

    out = dict(instrument="off-catalogue A/B, truth = B_far, official DTI",
               shipped_arm=SHIPPED,
               promotion_rule="mean paired DTI > 0 AND >= 3/4 folds positive",
               results=rows,
               conclusion=("no arm cleared the pre-registered bar; the shipped density stands"
                           if not any(r["promoted"] for r in rows) else
                           "arm(s) cleared the bar: " + ", ".join(r["arm"] for r in rows if r["promoted"])))
    (ROOT / "evidence/offcat_density_sweep.json").write_text(json.dumps(out, indent=1) + "\n")

    print(f"{'arm':<20}{'dots':>8}{'DTI(B_far)':>12}{'paired':>10}{'folds+':>8}  verdict")
    for r in rows:
        print(f"{r['arm']:<20}{r['n_px']:>8}{r['dti_B_far']:>12.4f}{r['delta_vs_shipped']:>+10.4f}"
              f"{r['folds_positive']:>5}/{r['n_folds']:<3}  {'PROMOTED' if r['promoted'] else ''}")
    print("\n" + out["conclusion"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
