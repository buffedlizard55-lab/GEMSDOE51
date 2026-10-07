#!/usr/bin/env python3
"""Auto-context (level-2 stacked) detector on the spatially blocked holdout.

Protocol, per fold
------------------
1. level-1 is fitted on the fold's training positives/negatives and predicts the
   whole grid -> ``field_L1``.  That model never saw the held-out block.
2. the training region is split into two contiguous slabs; for each slab a
   *separate* level-1 is fitted on the other slab and predicts the first.  This
   gives a cross-fitted belief over the training region that is not
   contaminated by its own labels (Breiman 1996, doi:10.1007/BF00117832).
3. context layers (``gems51.autocontext.CONTEXT_NAMES``) are computed twice —
   once from the cross-fitted belief (used to build the level-2 *training*
   rows) and once from ``field_L1`` (used to predict the held-out block).
4. level-2 is fitted on [physical features | arm extras | context] and its
   belief over the block is scored with exactly the same emission and metric
   code as ``scripts/run_experiments.py``, so the numbers are directly
   comparable to ``data/holdout_H_D.json``.

Usage
-----
    python3 scripts/run_autocontext.py --arm H_D --ratios 2,3.47,5
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

from gems51 import trace_emission as te                       # noqa: E402
from gems51.autocontext import CONTEXT_NAMES, context_features, contiguous_parts  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise                # noqa: E402
from gems51.grid import GRID                                   # noqa: E402
from gems51.holdout import make_folds                          # noqa: E402
from gems51.metric import dti_binary                           # noqa: E402

P = ROOT / "data" / "prepared"
ARMS = {"base": [], "H_D": ["facecoh"]}


def load_extras(arm: str):
    path = P / "extras_static.dat"
    if not path.exists():
        return [], None, []
    names = json.loads((P / "extras_static_names.json").read_text())
    keys = ARMS.get(arm, [])
    keep = [i for i, n in enumerate(names) if any(k in n for k in keys)]
    if not keep:
        return [], None, []
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H_D", choices=list(ARMS))
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--neg", type=int, default=250000)
    ap.add_argument("--neg-l1", type=int, default=150000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--ratios", default="2,3.47,5")
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--ste-w", type=float, default=0.35)
    ap.add_argument("--ste-spacing", type=float, default=2.4)
    ap.add_argument("--folds", default="all")
    ap.add_argument("--save-fields", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "autocontext_holdout.json"))
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    folds = make_folds(footprint, catalogue, buffer_px=args.buffer,
                       n_rows=args.grid, n_cols=args.grid, min_truth=500)
    want = (list(range(len(folds))) if args.folds == "all"
            else [int(x) for x in args.folds.split(",") if x != ""])
    ex_names, ex_mm, ex_keep = load_extras(args.arm)
    ratios = [float(v) for v in args.ratios.split(",")]
    print(f"[autocontext] arm={args.arm} folds={want} extras={ex_names}", flush=True)

    rows: list[dict] = []
    t0 = time.time()
    for fi in want:
        fold = folds[fi]
        extra_static = ([np.asarray(ex_mm[i], dtype=np.float32) for i in ex_keep]
                        if ex_mm is not None else [])
        rng = np.random.default_rng(1000 + fold.index)

        # ---- level 1 over the whole training region -------------------------
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, args.neg_l1, rng,
                            extra=extra_static)
        m1 = fit_detector(X, y, seed=fold.index, max_iter=args.max_iter)
        del X, y
        field_l1 = predict_grid(m1, stack, footprint, extra=extra_static)
        print(f"  fold {fi}: level-1 done ({time.time()-t0:.0f}s)", flush=True)

        # ---- cross-fitted level-1 belief over the training region -----------
        train_region = footprint & ~ndi.binary_dilation(
            fold.block, structure=np.ones((3, 3)), iterations=max(args.buffer, 0))
        parts = contiguous_parts(train_region, k=2, axis=0)
        field_cf = np.full(GRID.shape, np.nan, dtype=np.float32)
        for pi, part in enumerate(parts):
            other = train_region & ~part
            Xp, yp = stack.sample(fold.train_pos & other,
                                  fold.train_neg_pool & other,
                                  args.neg_l1, np.random.default_rng(2000 + 10 * fi + pi),
                                  extra=extra_static)
            mp = fit_detector(Xp, yp, seed=100 + pi, max_iter=args.max_iter)
            del Xp, yp
            fp_ = predict_grid(mp, stack, part, extra=extra_static)
            field_cf[part] = fp_[part]
            del mp, fp_
        # outside the training region (i.e. in the block) use the full level-1
        need = np.isnan(field_cf) & footprint
        field_cf[need] = field_l1[need]
        print(f"  fold {fi}: cross-fit done ({time.time()-t0:.0f}s)", flush=True)

        ctx_train = context_features(field_cf, footprint)
        ctx_test = context_features(field_l1, footprint)

        # ---- level 2 --------------------------------------------------------
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, args.neg,
                            np.random.default_rng(3000 + fi),
                            extra=extra_static + ctx_train)
        m2 = fit_detector(X, y, seed=fold.index, max_iter=args.max_iter)
        n_feat = X.shape[1]
        del X, y
        field_l2 = predict_grid(m2, stack, footprint, extra=extra_static + ctx_test)
        del ctx_train, ctx_test
        print(f"  fold {fi}: level-2 done ({time.time()-t0:.0f}s)", flush=True)
        if args.save_fields:
            np.save(P / f"field_AC_{args.arm}_fold{fold.index}.npy", field_l2)

        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= args.excl_radius
        cand0 = in_block & ~excl & footprint

        for tag, field in (("L1", field_l1), ("L2", field_l2)):
            dom = footprint & np.isfinite(field)
            m = in_block & dom
            auc = float(roc_auc_score(fold.truth[m], field[m]))
            f0 = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
            v = np.zeros(f0.shape, np.float32)
            for s in (1.0, 2.0, 3.5):
                vi, _ = te.ridge_response(f0, dom, s)
                np.copyto(v, vi, where=vi > v)
            acc, _ = te.line_accumulate(v, length=9, n_orient=12)
            rf, ra = te._rank01(f0, dom), te._rank01(acc, dom)
            w = args.ste_w
            ste = np.where(dom, (rf ** (1 - w)) * (ra ** w), 0.0).astype(np.float32)
            for ratio in ratios:
                k = int(round(ratio * fold.n_truth))
                ys, xs = nms_dots(field, k, radius=args.nms_radius,
                                  exclude=~cand0, valid=dom)
                r_iso = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                                   valid=footprint & fold.block, known=fold.known)
                ys, xs = te.spaced_dots(ste, cand0, k, spacing=args.ste_spacing)
                r_ste = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                                   valid=footprint & fold.block, known=fold.known)
                rows.append(dict(fold=fi, level=tag, ratio=ratio, auc=auc,
                                 n_truth=fold.n_truth, n_feat=n_feat,
                                 dti_iso=r_iso["dti"], dti_ste=r_ste["dti"]))
                print(f"    fold {fi} {tag} r{ratio:<5g} auc={auc:.4f} "
                      f"iso={r_iso['dti']:.4f} ste={r_ste['dti']:.4f} "
                      f"({time.time()-t0:.0f}s)", flush=True)
            del f0, v, acc, rf, ra, ste
        del field_l1, field_cf, field_l2, m1, m2

    summary = {}
    for tag in ("L1", "L2"):
        for ratio in ratios:
            sel = [r for r in rows if r["level"] == tag and r["ratio"] == ratio]
            if not sel:
                continue
            summary[f"{tag}_r{ratio:g}"] = dict(
                auc=float(np.mean([r["auc"] for r in sel])),
                dti_iso=float(np.mean([r["dti_iso"] for r in sel])),
                dti_ste=float(np.mean([r["dti_ste"] for r in sel])),
                n_folds=len(sel))
    # paired deltas L2 - L1 at each ratio
    paired = {}
    for ratio in ratios:
        for key in ("dti_iso", "dti_ste"):
            d = []
            for fi in want:
                a = next((r for r in rows if r["fold"] == fi and r["level"] == "L2"
                          and r["ratio"] == ratio), None)
                b = next((r for r in rows if r["fold"] == fi and r["level"] == "L1"
                          and r["ratio"] == ratio), None)
                if a and b:
                    d.append(a[key] - b[key])
            if d:
                paired[f"L2-L1_{key}_r{ratio:g}"] = dict(
                    mean_delta=float(np.mean(d)), folds_better=int(sum(x > 0 for x in d)),
                    n_folds=len(d), per_fold=[round(x, 6) for x in d])

    out = dict(instrument="spatially blocked holdout, level-1 vs level-2 auto-context",
               config=vars(args), rows=rows, summary=summary, paired=paired)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== summary ===")
    for k, v in summary.items():
        print(f"  {k:12s} auc={v['auc']:.4f} iso={v['dti_iso']:.4f} ste={v['dti_ste']:.4f}")
    print("=== paired L2 - L1 ===")
    for k, v in paired.items():
        print(f"  {k:26s} {v['mean_delta']:+.4f}  {v['folds_better']}/{v['n_folds']}")
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
