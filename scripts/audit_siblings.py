#!/usr/bin/env python3
"""Quantitative audit of the sibling submissions kept in ``.cache/siblings``.

Answers three questions with numbers, not adjectives:

  1. **What is in them?** dot count, minimum dot spacing, value set, byte sha256.
  2. **How do they relate to the published catalogue?** share of dots within
     1/2/3/5/10 px of a mapped (USGS+INGENIOUS) fault pixel — the design choice the
     owner-reported live experiment in ``gems51.live_metric`` is about.
  3. **How much do they overlap each other and this repository's own artifacts?**
     Jaccard and containment of the dot supports, so "unique" is a measurement.

Note on scope: these files are other people's submissions.  They are used here only
as *uniqueness references* and to read off the emission geometry they chose (dot
count, spacing, catalogue clearance).  No file is copied, re-encoded or relabelled,
and no leaderboard value is mirrored (DrivenData Terms of Use).

Usage
-----
    .venv/bin/python scripts/audit_siblings.py [--out evidence/sibling_design_audit.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402

P = ROOT / "data" / "prepared"


def load_dots(path: Path) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
        prof = dict(shape=(ds.height, ds.width), crs=str(ds.crs),
                    transform=tuple(ds.transform)[:6], count=ds.count, dtype=str(ds.dtypes[0]))
    m = a > 0
    ys, xs = np.nonzero(m)
    vals = a[m]
    out = dict(n_dots=int(m.sum()), value_min=float(vals.min()), value_max=float(vals.max()),
               n_unique_values=int(np.unique(vals).size), profile=prof,
               sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               nonfinite=int((~np.isfinite(a)).sum()))
    if m.sum() >= 2:
        pts = np.c_[ys, xs]
        d, _ = cKDTree(pts).query(pts, k=2)
        out["nn_spacing_min"] = float(d[:, 1].min())
        out["nn_spacing_median"] = float(np.median(d[:, 1]))
    out["mask"] = m
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cat = np.load(P / "catalogue.npy")
    d_cat = ndi.distance_transform_edt(~cat)
    footprint = np.load(P / "footprint.npy")

    files = sorted((ROOT / ".cache" / "siblings").glob("*.tif"))
    files += sorted((ROOT / "data" / "prior").glob("*.tif"))
    rows, masks = {}, {}
    for f in files:
        rec = load_dots(f)
        m = rec.pop("mask")
        if m.shape != d_cat.shape:
            rec["shape_mismatch"] = list(m.shape)
            rows[f.name] = rec
            continue
        dd = d_cat[m]
        rec["catalogue_clearance"] = {
            f"share_within_{t}px": float((dd <= t).mean()) for t in (1, 2, 3, 5, 10, 20)
        }
        rec["share_outside_footprint"] = float((~footprint[m]).mean())
        rows[f.name] = rec
        masks[f.name] = m
        print(f"{f.name}: {rec['n_dots']:,} dots, clearance {rec['catalogue_clearance']}",
              flush=True)

    names = sorted(masks)
    overlap = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ia, ib = int(masks[a].sum()), int(masks[b].sum())
            inter = int((masks[a] & masks[b]).sum())
            if inter == 0:
                continue
            union = ia + ib - inter
            overlap[f"{a} | {b}"] = dict(
                n_a=ia, n_b=ib, intersection=inter,
                jaccard=inter / union, containment_a_in_b=inter / ia,
                containment_b_in_a=inter / ib)
    pairwise = []
    for k, v in overlap.items():
        if v["jaccard"] >= 0.05:
            pairwise.append(dict(pair=k, **{kk: round(vv, 4) for kk, vv in v.items()}))
    pairwise.sort(key=lambda r: -r["jaccard"])

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = dict(
        created_utc=utc,
        scope=("uniqueness and design audit of sibling submissions fetched from "
               "buffedlizard55-lab GitHub Pages sites + this repository's own prior artifacts"),
        files=rows, overlap_pairs=pairwise,
        note=("Owner-reported scores are NOT recorded here on purpose (DrivenData Terms of "
              "Use); only file-level geometry measured locally."),
        grid=dict(shape=list(GRID.shape), epsg=GRID.epsg, transform=list(GRID.transform)),
        catalogue_px=int(cat.sum()), footprint_px=int(footprint.sum()),
    )
    path = Path(args.out) if args.out else ROOT / "evidence" / f"sibling_design_audit_{utc}.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {path}")
    for r in pairwise[:12]:
        print(f"  {r['pair']}: J={r['jaccard']:.3f} cont={r['containment_a_in_b']:.3f}/"
              f"{r['containment_b_in_a']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
