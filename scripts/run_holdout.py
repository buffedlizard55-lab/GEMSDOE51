#!/usr/bin/env python3
"""Run the spatially blocked holdout over one or more emission hypotheses.

Usage
-----
    python scripts/run_holdout.py --folds 9 --neg 400000 --sweep 20000,30000,44000,60000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def load_base():
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    return footprint, catalogue


def exclude_near(mask: np.ndarray, radius: float) -> np.ndarray:
    from scipy import ndimage as ndi
    return ndi.distance_transform_edt(~mask) <= radius


def run(args):
    footprint, catalogue = load_base()
    stack = Stack(P)
    folds = make_folds(footprint, catalogue, buffer_px=args.buffer,
                       n_rows=args.grid, n_cols=args.grid,
                       min_truth=args.min_truth)
    print(f"[holdout] {len(folds)} folds, "
          f"truth/fold = {[f.n_truth for f in folds]}")
    if args.limit_folds:
        folds = folds[:args.limit_folds]

    sweep = [int(v) for v in args.sweep.split(",")]
    results = []
    t0 = time.time()
    for fold in folds:
        rng = np.random.default_rng(1000 + fold.index)
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, args.neg, rng)
        print(f"  fold {fold.index}: train X={X.shape} pos={int(y.sum())} "
              f"({time.time()-t0:.0f}s)", flush=True)
        model = fit_detector(X, y, seed=fold.index)
        del X, y
        field = predict_grid(model, stack, footprint)
        np.save(P / f"field_fold{fold.index}.npy", field)

        excl = exclude_near(fold.known, args.excl_radius)
        row = dict(fold=fold.index, n_truth=fold.n_truth,
                   train_pos=int(fold.train_pos.sum()))
        for k in sweep:
            ys, xs = nms_dots(field, k, radius=args.nms_radius, exclude=excl,
                              valid=footprint)
            pred = rasterise(ys, xs)
            r = dti_binary(pred > 0, fold.truth, valid=footprint, known=fold.known)
            row[f"dti_{k}"] = r["dti"]
            row[f"px_{k}"] = int(r["mass"])
        # in-fold AUC: measured INSIDE the held-out block only.  A whole-footprint
        # AUC is not a valid diagnostic here, because pixels that are real faults
        # but lie outside the block are labelled negative and punish a correct
        # high score (measured: it drops a 0.63 in-block signal to 0.495).
        from sklearn.metrics import roc_auc_score
        m = np.isfinite(field) & footprint & fold.block
        row["auc"] = float(roc_auc_score(fold.truth[m], field[m]))
        print("     " + "  ".join(f"{k}:{row[f'dti_{k}']:.4f}" for k in sweep)
              + f"   auc={row['auc']:.4f}  ({time.time()-t0:.0f}s)", flush=True)
        results.append(row)
        del field, excl

    summary = {}
    for k in sweep:
        v = [r[f"dti_{k}"] for r in results]
        summary[f"dti_{k}"] = dict(mean=float(np.mean(v)), std=float(np.std(v)),
                                   per_fold=[float(x) for x in v])
    summary["auc_mean"] = float(np.mean([r["auc"] for r in results]))
    out = dict(config=vars(args), per_fold=results, summary=summary)
    p = ROOT / "data" / f"holdout_{args.tag}.json"
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"wrote {p}  ({time.time()-t0:.0f}s)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="base")
    ap.add_argument("--folds", type=int, default=9)
    ap.add_argument("--limit-folds", type=int, default=0)
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--min-truth", type=int, default=500)
    ap.add_argument("--neg", type=int, default=400000)
    ap.add_argument("--sweep", default="20000,30000,44000,60000,80000")
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
