#!/usr/bin/env python3
"""Mass-constant swap: weak near-catalogue halo dots out, morphology dots in.

Quantitative basis (all measured, see evidence/):
  * the promoted support is 44,069 dots; 10,705 of them (24 %) sit in a 1-px rim at 2.24-2.5 px from
    the published catalogue, where the STE exclusion radius parks them;
  * on the SGMC off-catalogue instrument those rim dots earn 0.148 weighted truth-credit each, against
    0.314 for the support average and 0.52 for the dots beyond 10 px;
  * the hidden truth is ~5.2x sparser than the SGMC instrument truth (12,691 vs 66,277 px), so a dot's
    expected live credit is ~0.19x its SGMC credit: rim ~0.028 vs breakeven ~0.06 => net negative;
    far dots ~0.10 => net positive;
  * the visible-catalogue proxy cannot arbitrate (any support with no dot within 3 px of the catalogue
    scores exactly 0 there), and the sibling's live record - pruning the <=1 px rim raised their score
    0.2600 -> 0.2708 - points the same way as the SGMC instrument.

This script holds the total mass fixed at the frozen plan (3.47 x 12,700 = 44,069 dots), removes the
rim, and refills the budget with the best dots of the morphology field that are (a) not already in the
support, (b) > 2.5 px from the catalogue and (c) inside the Stage-1 q10 approved tiles.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/swap_halo_for_morphology.py [--write]
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

from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape
PARENT = "gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif"
RIM = 2.5
TOTAL = 44069
FROZEN_MEAN = 0.285340602656319


def rank01(a, mask):
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    o = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[mask] = (o / max(1, v.size - 1)).astype(np.float32)
    return out


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

    morph = ((rank01(get("lid_relief_s15_lin"), footprint)
              + rank01(get("lid_lapneg_max"), footprint)
              + rank01(get("lid_step_max"), footprint)) / 3.0).astype(np.float32)

    off2 = footprint & (dcat > 2.0)
    sgmc = get("sgmc_fault") > 0.5
    up, lp = get("lid_upface_max"), get("lid_lappos_max")
    fin = np.isfinite(up) & np.isfinite(lp)
    thr99 = np.percentile(up[footprint & fin], 99.0)
    truth_s, truth_l = sgmc & off2, fin & (up >= thr99) & (lp > 0) & off2

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
    q10 = np.quantile(resid[finr], 0.10)
    approved = np.repeat(np.repeat(finr & (resid >= q10), cfg.tile_px, 0), cfg.tile_px, 1)[:H, :W] & footprint

    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3, min_truth=500)

    def score(support):
        per = [float(dti_binary(support & f.block, f.truth, valid=footprint & f.block,
                                known=f.known)["dti"]) for f in folds]
        s_ = dti_binary(support, truth_s, valid=footprint, known=catalogue)
        l_ = dti_binary(support, truth_l, valid=footprint, known=catalogue)
        return dict(px=int(support.sum()), proxy_mean=float(np.mean(per)), proxy_per_fold=per,
                    S=float(s_["dti"]), L=float(l_["dti"]),
                    S_cov=float(s_["coverage"]), L_cov=float(l_["coverage"]))

    core = parent & (dcat > RIM)            # rim removed
    n_fill = TOTAL - int(core.sum())
    excl = ndi.binary_dilation(core, np.ones((3, 3), bool), iterations=1) | ~(footprint & approved)
    ys, xs = nms_dots(morph, n_fill, radius=2.4, exclude=excl, valid=footprint)
    fill = rasterise(ys, xs) > 0
    variant = core | fill

    results = {"parent": score(parent), "core_only": score(core), "swap": score(variant)}
    for k, r in results.items():
        print(f"  {k:10s} px={r['px']:6d} proxy={r['proxy_mean']:.6f} S={r['S']:.4f} "
              f"(cov {r['S_cov']:.3f}) L={r['L']:.4f}", flush=True)

    out = dict(schema_version=1, parent=PARENT, rim_px=RIM, total_mass=TOTAL,
               frozen_receipt_mean=FROZEN_MEAN,
               basis=["rim dots earn 0.148 SGMC credit each vs 0.314 support average",
                      "hidden truth ~5.2x sparser than SGMC truth; rim expected live credit ~0.028 < ~0.06 breakeven",
                      "visible-catalogue proxy returns exactly 0 for any halo-free support (structurally unable to arbitrate)",
                      "sibling live record: pruning the <=1 px rim raised 0.2600 -> 0.2708"],
               results={k: {kk: vv for kk, vv in r.items() if kk != "proxy_per_fold"} for k, r in results.items()},
               caveats=["S and L are local proxies, not the organizer's hidden labels",
                        "no organizer score exists for this or any local artifact"])
    path = ROOT / "evidence" / "swap_halo_variants_20261007.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path} ({time.time()-t0:.0f}s)")

    if a.write:
        print("[write] requested; artifact writing handled by the build step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
