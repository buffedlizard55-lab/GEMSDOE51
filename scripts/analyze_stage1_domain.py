#!/usr/bin/env python3
"""Scan the Stage-1 approved-domain quantile and measure what each setting buys/costs.

Why this exists: ``stage1.approved_mask`` approves tiles whose rank-space strain-budget
deficit is at or above the ``q``-th percentile, so **q10 approves ~90 % of the footprint**
(the lowest-deficit tenth is excluded), not 10 %.  The standing brief wants a *coarse*
prior that is not dominated by its own footprint, and the repository's uniqueness gate
compares supports, so the domain width is a real design decision that has to be measured
rather than assumed.

The script reports, for each candidate quantile:

  * approved area share of the footprint,
  * how much of an existing artifact's dot set falls inside it (containment of the old
    file in the new domain -- a direct, if crude, upper bound on how much of a new
    confined file can look like the old one),
  * how much of the published catalogue falls inside it (a sanity check on the hypothesis
    that the deficit is elevated where the catalogue may be incomplete),
  * the deficit value of each emitted dot's tile (distribution).

Usage
-----
    .venv/bin/python scripts/analyze_stage1_domain.py [--artifact docs/downloads/<name>.tif]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import stage1 as st1          # noqa: E402
from gems51 import strain_budget as sb    # noqa: E402

P = ROOT / "data" / "prepared"
QUANTILES = (10, 30, 50, 60, 70, 80, 90)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="")
    ap.add_argument("--tile-px", type=int, default=100)
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = st1.load_observed()
    cfg = sb.BudgetConfig(tile_px=args.tile_px)

    print("[1/3] full-catalogue strain-budget deficit (rank space)")
    s1 = st1.stage1_field(catalogue, footprint, df, obs, cfg)
    deficit = s1["deficit"]
    finite_tiles = int(np.isfinite(deficit).sum())
    print(f"    finite tiles: {finite_tiles} of {deficit.size}")

    dots = None
    art = args.artifact
    if not art:
        cands = sorted((ROOT / "docs" / "downloads").glob("*.tif"))
        art = str(cands[-1]) if cands else ""
    if art and Path(art).is_file():
        with rasterio.open(art) as ds:
            dots = np.nan_to_num(ds.read(1), nan=0.0, posinf=0.0, neginf=0.0) > 0
        if dots.shape != footprint.shape:
            raise SystemExit(f"{art} has shape {dots.shape}, expected {footprint.shape}")
        print(f"[2/3] artifact dot set: {Path(art).name} ({int(dots.sum()):,} dots)")
    else:
        print("[2/3] no artifact given/found: containment column will be null")

    rows = []
    for q in QUANTILES:
        m = st1.approved_mask(deficit, footprint, args.tile_px, float(q))
        area = float((m & footprint).sum() / max(int(footprint.sum()), 1))
        row = dict(q=q, approved_area_share=area,
                   catalogue_share_inside=float((m & catalogue).sum()
                                                / max(int(catalogue.sum()), 1)))
        if dots is not None:
            row["artifact_dots_inside"] = int((m & dots).sum())
            row["artifact_dot_containment"] = float((m & dots).sum() / max(int(dots.sum()), 1))
        rows.append(row)
        extra = (f" old-file dots inside {row['artifact_dot_containment']*100:6.2f}%"
                 if "artifact_dot_containment" in row else "")
        print(f"    q{q:>3}: approved {area*100:6.2f}% of footprint; "
              f"catalogue inside {row['catalogue_share_inside']*100:5.2f}%{extra}")

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = dict(
        created_utc=utc, tile_px=int(args.tile_px), artifact=(Path(art).name if art else None),
        rows=rows,
        note=("approved = deficit rank >= q-th percentile, so q10 is the WIDEST domain "
              "(~90 % of the footprint) and q90 the narrowest. Containment of the old artifact "
              "inside the domain bounds how much of a newly confined file can coincide with it."),
        stage1_meta=s1.get("meta"),
    )
    path = ROOT / "evidence" / f"stage1_domain_scan_{utc}.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"[3/3] wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
