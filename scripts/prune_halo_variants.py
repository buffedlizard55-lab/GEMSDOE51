#!/usr/bin/env python3
"""Does the promoted emission's near-catalogue halo earn its mass?

The promoted STE artifact (44,069 dots) has 38.7 % of its dots within 3 px (300 m) of the published
catalogue and 55.8 % within 5 px - a rim hug at the exclusion radius.  The sibling's live record is
the only live evidence available on this question: pruning everything within 1 px raised their score
0.2600 -> 0.2708 and the 2 px version projects 0.2747.  Here the same pruning is applied to our
support and measured on

  * the SGMC off-catalogue instrument (S, live-aligned: sibling calibration rho=+0.54 over 12
    live-scored artifacts), whose truth is *mostly far* from the catalogue (median 21.2 px), so it
    does not simply reward the halo;
  * the 1-m lidar scarp instrument (L);
  * the paired fixed-support six-fold visible-catalogue proxy (continuity only).

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/prune_halo_variants.py [--write]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape
PARENT = "gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif"
THRESHOLDS = (2.5, 3.0, 4.0, 5.0, 6.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    t0 = time.time()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    dcat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r", shape=(len(names), H, W))

    def get(nm):
        return np.asarray(mm[names.index(nm)], np.float32)

    with rasterio.open(ROOT / "docs" / "downloads" / PARENT) as ds:
        parent = np.isfinite(ds.read(1)) & (ds.read(1) > 0)

    off2 = footprint & (dcat > 2.0)
    sgmc = get("sgmc_fault") > 0.5
    up, lp = get("lid_upface_max"), get("lid_lappos_max")
    fin = np.isfinite(up) & np.isfinite(lp)
    thr99 = np.percentile(up[footprint & fin], 99.0)
    truth_s, truth_l = sgmc & off2, fin & (up >= thr99) & (lp > 0) & off2

    # q10 approved tiles (Stage-1 confinement requirement)
    import pandas as pd
    from gems51 import strain_budget as sb
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    cfg = sb.BudgetConfig(tile_px=100)
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        obs = s.read(descs.index("geod_2ndinv") + 1).astype(np.float64)
    obs[obs <= -1e38] = np.nan
    exx, eyy, exy, _L, _n, _a, _m, _ts, _meta = sb.kostrov_tiles(catalogue, df, cfg)
    f_ii = sb.invariant(exx, eyy, exy, "II")
    o_t = sb.observed_tiles(obs, footprint, cfg.tile_px)
    okk = np.isfinite(o_t) & (o_t > 0)
    resid = (sb.quantile_map(np.where(okk, o_t, np.nan)) - sb.quantile_map(np.where(okk, f_ii, np.nan)))
    finr = np.isfinite(resid)
    q10_thr = np.quantile(resid[finr], 0.10)
    approved = np.repeat(np.repeat(finr & (resid >= q10_thr), cfg.tile_px, 0), cfg.tile_px, 1)[:H, :W] & footprint

    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3, min_truth=500)

    def score(support):
        per = [float(dti_binary(support & f.block, f.truth, valid=footprint & f.block,
                                known=f.known)["dti"]) for f in folds]
        s_ = dti_binary(support, truth_s, valid=footprint, known=catalogue)
        l_ = dti_binary(support, truth_l, valid=footprint, known=catalogue)
        return dict(px=int(support.sum()), proxy_mean=float(np.mean(per)), proxy_per_fold=per,
                    S=float(s_["dti"]), L=float(l_["dti"]),
                    S_cov=float(s_["coverage"]), L_cov=float(l_["coverage"]))

    variants = {"parent": parent}
    for d in THRESHOLDS:
        keep = parent & (dcat > d)
        variants[f"prune_{d:.1f}"] = keep
        variants[f"prune_{d:.1f}_q10"] = keep & approved
    variants["far_only_gt10"] = parent & (dcat > 10.0)
    variants["parent_q10"] = parent & approved

    res = {k: score(v) for k, v in variants.items()}
    for k, r in res.items():
        print(f"  {k:18s} px={r['px']:6d} ({r['px']/int(parent.sum()):5.1%}) "
              f"proxy={r['proxy_mean']:.6f} S={r['S']:.4f} (cov {r['S_cov']:.3f}) L={r['L']:.4f}",
              flush=True)

    out = dict(schema_version=1, parent=PARENT, parent_px=int(parent.sum()),
               instrument="S=SGMC off-catalogue (>2px), L=lidar scarp; proxy=paired fixed-support 6-fold",
               results=res,
               caveats=["live implication from the sibling record only (prune<=1px: 0.2600->0.2708)",
                        "no organizer score for any variant; S/L are local proxies"])
    path = ROOT / "evidence" / "prune_halo_variants_20261007.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
