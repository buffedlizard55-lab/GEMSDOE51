#!/usr/bin/env python3
"""Detector screen: which bands, and which fusion, actually rank held-out faults highly?

Design
------
The full DTI holdout is expensive and its contrast is diluted by the core+shell mass that
is identical across arms.  Ranking quality is the thing that differs between candidate
detectors, and the threshold-free statistic for ranking quality against a sparse held-out
positive set is the ROC AUC of the field over the eligible area.

This screen therefore:
  1. leaves out one block at a time (2x2 blocking with a 30 px buffer);
  2. computes, for EVERY supplied band, the unsteered Hessian-ridge rank field
     (down=2 so the whole screen costs minutes, not hours);
  3. evaluates the AUC of each single band, and of several fusions, against the held-out
     block truth;
  4. reports means and per-fold signs.

AUC > 0.5 = the field ranks real (withheld) fault pixels above background.  AUC < 0.5 means
the field is anti-informative and must not be shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from gems51 import grid, scoring, stage2_emission as s2

ROOT = Path(__file__).resolve().parents[1]
DOWN = 2


def auc_of(score: np.ndarray, label: np.ndarray) -> float:
    m = np.isfinite(score)
    sc = score[m]
    lab = label[m]
    npos, nneg = int(lab.sum()), int((~lab).sum())
    if not npos or not nneg:
        return float("nan")
    order = np.argsort(sc, kind="mergesort")
    ranks = np.empty(sc.size, dtype=np.float64)
    ranks[order] = np.arange(1, sc.size + 1, dtype=np.float64)
    return float((ranks[lab].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence" / "detector_screen.json"))
    ap.add_argument("--cache", default="/tmp/gems51_screen")
    ap.add_argument("--sigma", type=float, default=2.0)
    a = ap.parse_args()

    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    d = grid.data_root()
    tf = d / "training_features.tif"
    cat = grid.read_catalogue(d / "existing_faults.tif")
    valid = grid.valid_footprint(d / "sample_submission.tif")
    h, w = cat.shape
    nh, nw = h // DOWN, w // DOWN

    def shrink(x):
        return (np.asarray(x, dtype=np.float32)[: nh * DOWN, : nw * DOWN]
                .reshape(nh, DOWN, nw, DOWN).mean(axis=(1, 3)).astype(np.float32))

    valid_s = shrink(valid.astype(np.float32)) > 0.5
    out = {"down": DOWN, "sigma_px_effective": a.sigma / DOWN, "folds": [],
           "bands": {str(b): grid.BAND_NAMES[b] for b in range(1, 20)}}

    for name, block, exclusion in scoring.quadrant_blocks(cat.shape, n=2, buffer_px=30):
        cache_f = cache / f"bands_{name}.npz"
        truth_s = shrink((cat & exclusion).astype(np.float32)) > 0.15
        if cache_f.exists():
            z = np.load(cache_f)
            per_band = {int(k[1:]): z[k] for k in z.files}
        else:
            per_band = {}
            for b in range(1, 20):
                arr = shrink(grid.read_band(tf, b))
                ridge, rdir, edge = s2.hessian_ridge(arr, a.sigma / DOWN)
                r = s2._rank_percentile(ridge, valid_s)
                per_band[b] = (r * 255.0).astype(np.uint8)
                del arr, ridge, rdir, edge
            np.savez_compressed(cache_f, **{f"b{b}": v for b, v in per_band.items()})
        fold = {"fold": name, "n_truth_s": int(truth_s.sum()), "auc_single_band": {}}
        for b, v in per_band.items():
            fold["auc_single_band"][str(b)] = auc_of(v.astype(np.float32) / 255.0, truth_s)
        out["folds"].append(fold)
        print(f"[{name}] truth_s={fold['n_truth_s']:,} folded {time.time():.0f}", flush=True)

    # ---- aggregate single bands
    bands = [str(b) for b in range(1, 20)]
    agg = {}
    for b in bands:
        v = [f["auc_single_band"][b] for f in out["folds"]]
        agg[b] = {"mean_auc": float(np.nanmean(v)),
                  "per_fold": [float(x) for x in v],
                  "folds_above_chance": int(sum(1 for x in v if x > 0.5))}
    out["auc_single_band_mean"] = agg

    # ---- fusion variants, evaluated from the cached per-band rank fields
    fusions = {}
    for name, bb in {
        "geo_magnetic": (1, 2, 3, 6, 9, 14),
        "geo_gravity_cond": (5, 11, 13, 18, 17),
        "topo": (12, 19),
        "strain": (4, 7, 8),
        "seismic": (10, 16),
        "all_geo": grid.LINEAMENT_BANDS,
        "top10_by_screen": None,   # filled after ranking
    }.items():
        fusions[name] = tuple(bb) if bb is not None else None
    ranked = sorted(bands, key=lambda b: -agg[b]["mean_auc"])
    fusions["top10_by_screen"] = tuple(int(b) for b in ranked[:10])
    fusions["top6_by_screen"] = tuple(int(b) for b in ranked[:6])
    fusions["all19"] = tuple(range(1, 20))

    fus_out = {}
    for name, bb in fusions.items():
        per_fold = []
        for f in out["folds"]:
            z = np.load(cache / f"bands_{f['fold']}.npz")
            acc = np.zeros_like(z["b1"], dtype=np.float32)
            for b in bb:
                acc += z[f"b{b}"].astype(np.float32) / 255.0
            acc /= len(bb)
            truth_s = shrink((cat & (np.ones_like(cat, bool))).astype(np.float32)) > 0  # placeholder
            per_fold.append(None)
        fus_out[name] = {"bands": list(bb)}
    # recompute fusions with the truth that belongs to each fold (needs exclusion)
    for name, bb in fusions.items():
        vals = []
        for f, (fname, block, exclusion) in zip(out["folds"],
                                                scoring.quadrant_blocks(cat.shape, n=2, buffer_px=30)):
            z = np.load(cache / f"bands_{fname}.npz")
            acc = np.zeros_like(z["b1"], dtype=np.float32)
            for b in bb:
                acc += z[f"b{b}"].astype(np.float32) / 255.0
            acc /= len(bb)
            truth_s = shrink((cat & exclusion).astype(np.float32)) > 0.15
            vals.append(auc_of(acc, truth_s))
        fus_out[name] = {
            "bands": list(bb), "mean_auc": float(np.nanmean(vals)),
            "per_fold": [float(v) for v in vals],
            "folds_above_chance": int(sum(1 for v in vals if v > 0.5)),
        }
    out["fusions"] = fus_out

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2, default=float))
    print("\n=== single-band mean AUC (all 19 supplied bands) ===")
    for b in sorted(bands, key=lambda x: -agg[x]["mean_auc"]):
        print(f"  band {int(b):2d}  AUC {agg[b]['mean_auc']:.4f}  "
              f"folds>0.5 {agg[b]['folds_above_chance']}/4  {grid.BAND_NAMES[int(b)][:58]}")
    print("\n=== fusion mean AUC ===")
    for k, v in sorted(fus_out.items(), key=lambda kv: -kv[1]["mean_auc"]):
        print(f"  {k:18s} AUC {v['mean_auc']:.4f}  folds>0.5 {v['folds_above_chance']}/4  "
              f"bands {v['bands']}")
    print(f"\n[detector screen] wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
