#!/usr/bin/env python3
"""Paired evaluation of *fixed-support* variants of the promoted STE emission.

Motivation
----------
`evidence/hh_blend_holdout.json` scores a *procedure* (per-fold fields -> per-fold STE emission).
The shipped artifact is that same procedure applied globally, and its fold fields are no longer on
disk, so no new procedure can be re-scored without retraining.  What *can* be measured, exactly and
cheaply, is a paired comparison between two fixed supports on the same six blocked folds:

    DTI(support) = dti_binary(support & block, fold.truth, valid=footprint & block, known=fold.known)

This is the standard "score the frozen artifact" protocol and it is what this script reports.  It is
not the same as the field-emission protocol of the frozen receipt, and the difference is stated in
the receipt.

New evidence being tested
-------------------------
`evidence/layer_screen_offcatalogue.json` + `evidence/layer_screen_controls.json` +
`evidence/lidar_field_holdout.json` (all 2026-10-07): among every layer of the prepared stack, the
along-strike anisotropy of 1-m lidar relief combined with positive-Laplacian crest and
step magnitude (`lin_relief+lapneg+step`) is the strongest ranker of off-catalogue structure on the
live-aligned SGMC instrument (S=0.142 at 44k dots vs random 0.085; the frozen-dot family's own
emission scores ~0.10).  This script thins the promoted support using that field and measures the
consequence on both instruments.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/evaluate_support_variants.py [--write]
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
FRACTIONS = (0.80, 0.60, 0.45, 0.30)
FROZEN_MEAN = 0.285340602656319
FROZEN_PER_FOLD = [0.28358474213082796, 0.27178387428750844, 0.29027025890966246,
                   0.24335930706370568, 0.30504916677291494, 0.3179962667732945]


def rank01(a, mask):
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    o = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[mask] = (o / max(1, v.size - 1)).astype(np.float32)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the chosen variant as a submission TIFF")
    a = ap.parse_args()
    t0 = time.time()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r", shape=(len(names), H, W))

    def get(nm):
        return np.asarray(mm[names.index(nm)], np.float32)

    parent_path = ROOT / "docs" / "downloads" / PARENT
    with rasterio.open(parent_path) as ds:
        parent = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    print(f"[parent] {int(parent.sum()):,} dots from {PARENT}")

    dcat = ndi.distance_transform_edt(~catalogue).astype(np.float32)

    # live-aligned morphology field (the session's new evidence)
    f = ((rank01(get("lid_relief_s15_lin"), footprint)
          + rank01(get("lid_lapneg_max"), footprint)
          + rank01(get("lid_step_max"), footprint)) / 3.0).astype(np.float32)

    # Stage-1 q10 approved tiles (method-brief requirement) -- recomputed here, receipt follows
    import pandas as pd
    from gems51 import strain_budget as sb
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    cfg = sb.BudgetConfig(tile_px=100)
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        obs = s.read(descs.index("geod_2ndinv") + 1).astype(np.float64)
    obs[obs <= -1e38] = np.nan
    exx, eyy, exy, _L, _n, _a, _m, tshape, _meta = sb.kostrov_tiles(catalogue, df, cfg)
    f_ii = sb.invariant(exx, eyy, exy, "II")
    o_t = sb.observed_tiles(obs, footprint, cfg.tile_px)
    okk = np.isfinite(o_t) & (o_t > 0)
    qf = sb.quantile_map(np.where(okk, f_ii, np.nan))
    qo = sb.quantile_map(np.where(okk, o_t, np.nan))
    resid = qo - qf
    finr = np.isfinite(resid)
    thr = np.quantile(resid[finr], 0.10)
    approved = np.repeat(np.repeat(finr & (resid >= thr), cfg.tile_px, 0), cfg.tile_px, 1)[:H, :W] & footprint
    print(f"[stage1] q10 approved = {approved.sum()/footprint.sum():.4f} of footprint")

    # instruments
    off2 = footprint & (dcat > 2.0)
    sgmc = get("sgmc_fault") > 0.5
    up, lp = get("lid_upface_max"), get("lid_lappos_max")
    fin = np.isfinite(up) & np.isfinite(lp)
    thr99 = np.percentile(up[footprint & fin], 99.0)
    truth_s = sgmc & off2
    truth_l = fin & (up >= thr99) & (lp > 0) & off2

    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3, min_truth=500)

    def score(support):
        per = []
        for fold in folds:
            r = dti_binary(support & fold.block, fold.truth,
                           valid=footprint & fold.block, known=fold.known)
            per.append(float(r["dti"]))
        s_ = dti_binary(support, truth_s, valid=footprint, known=catalogue)
        l_ = dti_binary(support, truth_l, valid=footprint, known=catalogue)
        return dict(px=int(support.sum()), proxy_mean=float(np.mean(per)), proxy_per_fold=per,
                    S=float(s_["dti"]), L=float(l_["dti"]),
                    S_cov=float(s_["coverage"]), L_cov=float(l_["coverage"]))

    variants = {"parent": parent, "parent_q10": parent & approved}
    ys, xs = np.nonzero(parent)
    order = np.argsort(-f[ys, xs], kind="stable")          # best morphology first
    for frac in FRACTIONS:
        m = int(round(frac * ys.size))
        keep = np.zeros_like(parent)
        keep[ys[order[:m]], xs[order[:m]]] = True
        variants[f"morph_{int(frac*100)}"] = keep
        variants[f"morph_{int(frac*100)}_q10"] = keep & approved

    results = {}
    for k, v in variants.items():
        results[k] = score(v)
        print(f"  {k:20s} px={results[k]['px']:6d} proxy={results[k]['proxy_mean']:.6f} "
              f"S={results[k]['S']:.4f} L={results[k]['L']:.4f} S_cov={results[k]['S_cov']:.3f}",
              flush=True)

    # pre-declared choice rule
    pm = results["parent"]["proxy_mean"]
    cands = {k: r for k, r in results.items()
             if r["proxy_mean"] >= pm - 0.002 and k != "parent"}
    best = max(cands, key=lambda k: cands[k]["S"]) if cands else None
    print(f"[rule] parent proxy={pm:.6f}; candidates within 0.002: {sorted(cands)}; chosen={best}")

    out = dict(schema_version=1, instrument="paired fixed-support six-fold blocked proxy",
               parent=PARENT, parent_frozen_receipt_mean=FROZEN_MEAN,
               parent_frozen_receipt_per_fold=FROZEN_PER_FOLD,
               protocol="support & block vs fold.truth; valid=footprint & block; known=fold.known",
               morphology_field="mean rank01 of lid_relief_s15_lin, lid_lapneg_max, lid_step_max",
               stage1_q10_area_share=float(approved.sum() / footprint.sum()),
               results=results, choice_rule="max S s.t. proxy_mean >= parent_mean - 0.002",
               chosen=best, evidence=["evidence/layer_screen_offcatalogue.json",
                                      "evidence/layer_screen_controls.json",
                                      "evidence/lidar_field_holdout.json"],
               caveats=["fixed-support protocol is not the field-emission protocol of the frozen receipt",
                        "instruments S and L are local proxies, not organizer labels",
                        "no organizer score exists for any variant"])
    out_path = ROOT / "evidence" / "support_variants_20261007.json"
    out_path.write_text(json.dumps(out, indent=1))
    print(f"wrote {out_path} ({time.time()-t0:.0f}s)")

    if a.write and best:
        support = variants[best]
        from gems51.submission import write_tif
        from gems51.uniqueness import run_gate
        priors = sorted((ROOT / "data" / "refs").glob("*.tif")) + sorted((ROOT / "data" / "prior").glob("*.tif"))
        tif = ROOT / "docs" / "downloads" / f"gemsdoe51-{best}-q10-zeros.tif"
        rec = write_tif(tif, support.astype(np.float32), footprint, outside=0.0, nodata=None)
        gate = run_gate(tif, priors, support, footprint, approved)
        print("[format]", json.dumps(rec["checks"], indent=1))
        print("[gate]", gate.verdict)
        (ROOT / "evidence" / f"format_{best}_20261007.json").write_text(json.dumps(rec, indent=1))
        (ROOT / "evidence" / f"uniqueness_{best}_20261007.json").write_text(json.dumps(gate.as_dict(), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
