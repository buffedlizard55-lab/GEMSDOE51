#!/usr/bin/env python3
"""Spatially blocked holdout for competing fault-detector hypotheses.

Scoring design
--------------
Emission and scoring are both **restricted to the held-out block**, and the
number of emitted dots is set as a fixed multiple of the block's own truth size.
That is the only way the proxy number is comparable to a live DTI: the official
metric is DTI = TP / (0.2*M + 0.8*|G|), i.e. it depends on submitted mass and
truth size only through their ratio, so matching M/|G| is what makes a proxy
number mean the same thing as a live number.

Known biases, stated up front:
  * truth density inside a block is several times the regional average, so the
    absolute proxy DTI is optimistic;
  * the block is "unmapped territory", whereas in reality known faults are
    interleaved with the hidden ones and their neighbourhoods are excluded;
  * the proxy truth is the visible catalogue, so it can only reward rediscovery
    of the *kind* of fault already mapped.
It is an instrument for ranking hypotheses at matched mass.  It is not a score.

Usage
-----
  python scripts/run_experiments.py --arm base --arm H_E --folds 9
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"

# hypothesis -> which static extra groups (substring match on extras_static names)
ARMS = {
    "base": [],                                   # 58 physical stack features
    "H_E": ["base_s", "cond_s", "grav2_s", "base_step_coh"],   # basin-edge geophysics
    "H_D": ["facecoh"],                           # scarp-facing coherence
    "H_C": [],                                    # catalogue tips (fold-dependent)
    "H_ALL": ["base_s", "cond_s", "grav2_s", "base_step_coh", "facecoh"],
}


def load_extras(arm: str):
    """(names, memmap, row indices) of the static extras selected by the arm."""
    path = P / "extras_static.dat"
    empty = ([], None, [])
    if not path.exists():
        return empty
    names = json.loads((P / "extras_static_names.json").read_text())
    keys = ARMS.get(arm, [])
    keep = [i for i, n in enumerate(names) if any(k in n for k in keys)]
    if not keep:
        return empty
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def run(args):
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    folds = make_folds(footprint, catalogue, buffer_px=args.buffer,
                       n_rows=args.grid, n_cols=args.grid, min_truth=args.min_truth)
    if args.limit_folds:
        folds = folds[:args.limit_folds]
    print(f"[holdout] {len(folds)} folds; truth/fold = {[f.n_truth for f in folds]}")

    ex_names, ex_mm, ex_keep = load_extras(args.arm)
    print(f"[arm {args.arm}] + {len(ex_names)} static extras: {ex_names}")

    ratios = [float(v) for v in args.ratios.split(",")]
    t0 = time.time()
    rows = []
    for fold in folds:
        # ---- feature matrix -------------------------------------------------
        rng = np.random.default_rng(1000 + fold.index)
        extra_cols = []
        if ex_mm is not None:
            extra_cols += [np.asarray(ex_mm[i], dtype=np.float32) for i in ex_keep]
        if args.arm in ("H_C", "H_ALL"):
            from gems51.extras import build_catalogue_dependent
            cd = build_catalogue_dependent(stack, footprint, fold.known)
            extra_cols += [cd["d_tip"]]
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, args.neg, rng,
                            extra=extra_cols)
        model = fit_detector(X, y, seed=fold.index, max_iter=args.max_iter)
        n_feat = X.shape[1]
        del X, y
        field = predict_grid(model, stack, footprint, extra=extra_cols)
        if args.save_fields:
            np.save(P / f"field_{args.arm}_fold{fold.index}.npy", field)

        # ---- block-restricted emission and scoring --------------------------
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= args.excl_radius
        row = dict(fold=fold.index, n_truth=fold.n_truth, n_feat=n_feat,
                   train_pos=int(fold.train_pos.sum()),
                   block_px=int(in_block.sum()))
        m = in_block & np.isfinite(field)
        row["auc_inblock"] = float(roc_auc_score(fold.truth[m], field[m]))
        for ratio in ratios:
            k = int(round(ratio * fold.n_truth))
            ys, xs = nms_dots(field, k, radius=args.nms_radius,
                              exclude=excl | ~in_block, valid=footprint)
            pred = rasterise(ys, xs)
            r = dti_binary(pred > 0, fold.truth, valid=footprint & fold.block,
                           known=fold.known)
            row[f"dti_r{ratio}"] = r["dti"]
            row[f"px_r{ratio}"] = int(r["mass"])
        print(f"  fold {fold.index:2d} truth={fold.n_truth:6d} "
              f"auc={row['auc_inblock']:.4f}  "
              + "  ".join(f"r{r}:{row[f'dti_r{r}']:.4f}" for r in ratios)
              + f"  ({time.time()-t0:.0f}s)", flush=True)
        rows.append(row)
        del field

    summary = {"arm": args.arm, "ratios": ratios,
               "auc_mean": float(np.mean([r["auc_inblock"] for r in rows])),
               "auc_per_fold": [r["auc_inblock"] for r in rows]}
    for r in ratios:
        v = [x[f"dti_r{r}"] for x in rows]
        summary[f"dti_r{r}"] = dict(mean=float(np.mean(v)), std=float(np.std(v)),
                                    per_fold=[float(z) for z in v])
    out = ROOT / "data" / f"holdout_{args.arm}.json"
    out.write_text(json.dumps(dict(config=vars(args), per_fold=rows, summary=summary), indent=1))
    print(json.dumps(summary, indent=1))
    print(f"wrote {out} ({time.time()-t0:.0f}s)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="base", choices=list(ARMS))
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--min-truth", type=int, default=500)
    ap.add_argument("--limit-folds", type=int, default=0)
    ap.add_argument("--neg", type=int, default=250000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--ratios", default="1,2,3.47,5,8")
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--save-fields", action="store_true")
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
