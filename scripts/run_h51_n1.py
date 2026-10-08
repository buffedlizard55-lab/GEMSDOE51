#!/usr/bin/env python3
"""H51-N1: inventory-context arm vs the static-features comparator, on both instruments.

Pre-registered question (stated before the run, recorded in the output JSON):

    Does adding the inventory-context feature group of ``gems51.inventory_context``
    — all of it computed from a ``known`` mask that never contains a scored truth
    pixel — improve the fine-scale detector on the *off-catalogue* instrument,
    and does it do so without degrading the stricter "far" subset?

Promotion rule (fixed here, before any result is seen):

    ADOPT  iff  mean dti_B_all of the n1 arm  >  mean dti_B_all of the static arm
                AND n1 beats static on B_all in at least 3 of 4 folds
                AND mean dti_B_far of n1  >=  mean dti_B_far of static - 0.002

    Other outcomes are reported as "not promoted" and no submission built from
    the arm.

Instruments
-----------
``--instrument ab``    (primary) off-catalogue A/B split of catalogue systems,
                       seed 51: A stays visible, B is hidden, every non-A pixel
                       (including B) is a training negative.  Emission must sit
                       at least ``--excl-radius`` px from A, and DTI is scored
                       against B with A as the masked known set.
``--instrument proxy`` (secondary) the repository's 3x3 spatially blocked
                       holdout with a 12 px training buffer, truth = the held-out
                       block's catalogue pixels, known = the rest of the catalogue.

Emission rules compared inside each fold at matched mass
--------------------------------------------------------
* ``iso_nms``     — the incumbent: isotropic non-maximum suppression on the field.
* ``ste_L9``      — strike-coherent emission (ridge + along-strike accumulation).
* ``credit_match``— greedy expected-credit selection (``gems51.credit_emission``)
                    at the same dot count.
* ``credit_floor``— the marginal rule alone: emit while expected credit
                    ``> alpha * DTI0`` (``--dti0``), no mass calibration.
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

from gems51 import credit_emission as ce            # noqa: E402
from gems51 import inventory_context as ic          # noqa: E402
from gems51 import trace_emission as te             # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise     # noqa: E402
from gems51.grid import GRID                        # noqa: E402
from gems51.holdout import make_folds               # noqa: E402
from gems51.metric import dti_binary                # noqa: E402

P = ROOT / "data" / "prepared"
STATIC_KEYS = ["facecoh"]          # the adopted H-D arm's static extras


def load_static_extras(names_wanted: list[str]):
    """Load the H-D static group from `arm_hd.dat` (or `extras_static.dat` if present).

    `extras_static.dat` is the full static build; it is OOM-killed in this
    sandbox, so `scripts/build_arm_extras.py --group hd` writes exactly the H-D
    layers through the same `gems51.extras.facecoh_group` code path.
    """
    for path, names_path in ((P / "extras_static.dat", P / "extras_static_names.json"),
                             (P / "arm_hd.dat", P / "arm_hd_names.json")):
        if path.exists():
            names = json.loads(names_path.read_text())
            keep = [i for i, nm in enumerate(names) if any(k in nm for k in names_wanted)]
            mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
            return [names[i] for i in keep], mm, keep
    raise SystemExit("no static extras found; run scripts/build_arm_extras.py --group hd")


def split_systems(cat: np.ndarray, seed: int, min_px: int = 20):
    lab, n = ndi.label(cat, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    comps = [i for i in range(1, n + 1) if sizes[i] >= min_px]
    rng = np.random.default_rng(seed)
    rng.shuffle(comps)
    total = sum(int(sizes[i]) for i in comps)
    b_ids, acc = [], 0
    for i in comps:
        if acc < total / 2:
            b_ids.append(i)
            acc += int(sizes[i])
    b = np.isin(lab, b_ids)
    return cat & ~b, b, lab


def grid_blocks(shape, n: int):
    H, W = shape
    ys = np.linspace(0, H, n + 1).astype(int)
    xs = np.linspace(0, W, n + 1).astype(int)
    out = []
    for i in range(n):
        for j in range(n):
            m = np.zeros(shape, bool)
            m[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = True
            out.append(m)
    return out


def emission_rules(field: np.ndarray, domain: np.ndarray, cand: np.ndarray,
                   n_dots: int, credit: np.ndarray, dti0: float, sigmas,
                   ste_w: float, ste_spacing: float, ste_linelen: int):
    rules: dict[str, np.ndarray] = {}
    ys, xs = nms_dots(field, n_dots, radius=2.4, exclude=~cand, valid=domain)
    rules["iso_nms"] = rasterise(ys, xs) > 0

    f0 = np.nan_to_num(field, nan=0.0).astype(np.float32)
    v = np.zeros(f0.shape, np.float32)
    for s in sigmas:
        vi, _ = te.ridge_response(f0, domain, s)
        np.copyto(v, vi, where=vi > v)
    acc, _ang = te.line_accumulate(v, length=ste_linelen, n_orient=12)
    rf, ra = te._rank01(f0, domain), te._rank01(acc, domain)
    w = ste_w
    ste_score = np.where(domain, (rf ** (1 - w)) * (ra ** w), 0.0).astype(np.float32)
    ys, xs = te.spaced_dots(ste_score, cand, n_dots, spacing=ste_spacing)
    rules[f"ste_L{ste_linelen}_w{w:g}_s{ste_spacing:g}"] = rasterise(ys, xs) > 0

    ys, xs, _cr = ce.select_dots(credit, cand, credit_floor=float(-np.inf),
                                 spacing_px=2.8, max_dots=n_dots,
                                 pool_size=max(n_dots * 12, 50_000))
    rules["credit_match"] = rasterise(ys, xs) > 0

    ys, xs, _cr = ce.select_dots(credit, cand, credit_floor=0.2 * dti0,
                                 spacing_px=2.8, max_dots=400_000)
    rules["credit_floor"] = rasterise(ys, xs) > 0
    return rules


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="ab", choices=["ab", "proxy"])
    ap.add_argument("--folds", default="0,1,2,3")
    ap.add_argument("--grid", type=int, default=2)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--neg", type=int, default=250_000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--dti0", type=float, default=0.28)
    ap.add_argument("--ste-w", type=float, default=0.35)
    ap.add_argument("--ste-spacing", type=float, default=3.0)
    ap.add_argument("--ste-linelen", type=int, default=9)
    ap.add_argument("--sigmas", type=float, nargs="*", default=[1.0, 2.0, 3.5])
    ap.add_argument("--arms", default="static,n1")
    ap.add_argument("--save-fields", default=None)
    ap.add_argument("--skip-emission", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = Path(args.out or (ROOT / "evidence" / f"h51_n1_{args.instrument}.json"))

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    ex_names, ex_mm, ex_keep = load_static_extras(STATIC_KEYS)
    static_cols = [np.asarray(ex_mm[i], dtype=np.float32) for i in ex_keep]
    print(f"[N1] static extras: {ex_names}", flush=True)
    relief = np.asarray(stack.data[stack.names.index("lid_relief")], dtype=np.float32)

    if args.instrument == "ab":
        A, B, lab = split_systems(catalogue, args.seed)
        dA = ndi.distance_transform_edt(~A).astype(np.float32)
        labB = np.where(B, lab, 0)
        far_ids = [int(i) for i in np.unique(labB)
                   if i != 0 and dA[labB == i].min() >= 5.0]
        B_far = np.isin(labB, far_ids) if far_ids else np.zeros(B.shape, bool)
        blocks_ = grid_blocks(GRID.shape, args.grid)
        print(f"[A/B] A={int(A.sum())} B={int(B.sum())} B_far={int(B_far.sum())}", flush=True)
    else:
        specs = make_folds(footprint, catalogue, buffer_px=args.buffer,
                           n_rows=3, n_cols=3)
        blocks_ = [s.block & footprint for s in specs]

    want = [int(x) for x in args.folds.split(",") if x != ""]
    arms = [a for a in args.arms.split(",") if a]
    rows: list[dict] = []
    t0 = time.time()

    for bi in want:
        blk_raw = blocks_[bi]
        if args.instrument == "ab":
            blk = blk_raw & footprint
            known = A
            train_pos = A & ~ndi.binary_dilation(blk_raw, np.ones((3, 3), bool),
                                                 iterations=max(args.buffer, 0)) & footprint
            train_neg = footprint & ~A & ~ndi.binary_dilation(blk_raw, np.ones((3, 3), bool),
                                                             iterations=max(args.buffer, 0))
            truth_all = B & blk
            truth_far = B_far & blk
            excl = A
        else:
            spec = specs[bi]
            blk = spec.block & footprint
            known = spec.known
            train_pos = spec.train_pos
            train_neg = spec.train_neg_pool
            truth_all = spec.truth & blk
            truth_far = np.zeros_like(truth_all)
            excl = spec.known
        if int(truth_all.sum()) < 300:
            print(f"  fold {bi}: too few truth pixels -- skipped", flush=True)
            continue

        inv = ic.inventory_features(known, footprint, relief=relief)
        inv_cols = [inv[k] for k in ic.FEATURE_NAMES]

        for arm in arms:
            extra = static_cols + (inv_cols if arm == "n1" else [])
            rng = np.random.default_rng(5000 + bi)
            X, y = stack.sample(train_pos, train_neg, args.neg, rng, extra=extra)
            model = fit_detector(X, y, seed=bi, max_iter=args.max_iter)
            del X, y
            field = predict_grid(model, stack, footprint, extra=extra, chunk=128)
            if args.save_fields:
                d = Path(args.save_fields)
                d.mkdir(parents=True, exist_ok=True)
                np.save(d / f"field_{args.instrument}_fold{bi}_{arm}.npy", field.astype(np.float32))
            print(f"  fold {bi} arm={arm} trained+predicted ({time.time()-t0:.0f}s)", flush=True)

            dom = footprint & np.isfinite(field)
            m = blk & dom
            auc_all = float(roc_auc_score(truth_all[m], field[m]))
            auc_far = (float(roc_auc_score(truth_far[m], field[m]))
                       if truth_far[m].any() else float("nan"))
            cand = blk & dom & (ndi.distance_transform_edt(~excl) >= args.excl_radius) \
                if args.instrument == "ab" else blk & dom
            n_dots = int(round(args.ratio * int(truth_all.sum())))
            if args.skip_emission:
                rows.append(dict(fold=bi, arm=arm, rule="field_only",
                                 n_dots=0, auc_truth_all=auc_all, auc_truth_far=auc_far))
                print(f"    fold {bi} {arm:6s} field_only AUC_all={auc_all:.4f} "
                      f"AUC_far={auc_far:.4f}", flush=True)
                del field
                continue
            credit = ce.expected_credit(np.clip(field, 0.0, 1.0), dom)

            rules = emission_rules(field, dom, cand, n_dots, credit, args.dti0,
                                   args.sigmas, args.ste_w, args.ste_spacing,
                                   args.ste_linelen)
            for nm, mask in rules.items():
                rec = dict(fold=bi, arm=arm, rule=nm, n_dots=int(mask.sum()),
                           auc_truth_all=auc_all, auc_truth_far=auc_far)
                for tn, truth in (("all", truth_all), ("far", truth_far)):
                    if int(truth.sum()) == 0:
                        continue
                    r = dti_binary(mask, truth, valid=footprint & blk, known=excl)
                    rec[f"dti_{tn}"] = r["dti"]
                    rec[f"n_truth_{tn}"] = r["n_truth"]
                    rec[f"credit_per_dot_{tn}"] = r["tp"] / max(int(mask.sum()), 1)
                rows.append(rec)
                print(f"    fold {bi} {arm:6s} {nm:20s} dots={int(mask.sum()):6d} "
                      f"DTI_all={rec.get('dti_all', float('nan')):.4f} "
                      f"DTI_far={rec.get('dti_far', float('nan')):.4f}", flush=True)
            del field, credit, rules

    summary: dict = {}
    keys = set((r["arm"], r["rule"]) for r in rows)
    for arm, rule in sorted(keys):
        for tn in ("all", "far"):
            vals = [r[f"dti_{tn}"] for r in rows
                    if r["arm"] == arm and r["rule"] == rule and f"dti_{tn}" in r]
            if vals:
                summary[f"{arm}|{rule}|{tn}"] = dict(
                    mean_dti=float(np.mean(vals)), n_folds=len(vals),
                    per_fold=[round(float(v), 6) for v in vals])
    # paired deltas n1 - static, per emission rule
    paired: dict = {}
    for rule in sorted(set(r["rule"] for r in rows)):
        for tn in ("all", "far"):
            s = {r["fold"]: r.get(f"dti_{tn}") for r in rows
                 if r["arm"] == "static" and r["rule"] == rule}
            n = {r["fold"]: r.get(f"dti_{tn}") for r in rows
                 if r["arm"] == "n1" and r["rule"] == rule}
            d = [n[f] - s[f] for f in sorted(set(s) & set(n))
                 if s[f] is not None and n[f] is not None]
            if d:
                paired[f"{rule}|{tn}"] = dict(mean_delta=float(np.mean(d)),
                                              folds_better=int(sum(x > 0 for x in d)),
                                              n=len(d),
                                              per_fold=[round(float(x), 6) for x in d])
    out = dict(
        script="scripts/run_h51_n1.py",
        instrument=args.instrument,
        preregistered_rule=("ADOPT iff mean dti_B_all(n1) > mean dti_B_all(static) AND "
                            "n1 beats static on B_all in >=3/4 folds AND mean dti_B_far(n1) "
                            ">= mean dti_B_far(static) - 0.002"),
        config=vars(args),
        n_rows=len(rows), rows=rows, summary=summary, paired_n1_minus_static=paired,
        runtime_s=round(time.time() - t0, 1),
        limitations=[
            "proxy/off-catalogue DTI values are not competition scores",
            "the A/B split shares one compilation between A and B",
            "no competition slot is authorized by this file",
        ])
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== summary (mean DTI) ===")
    for k, v in sorted(summary.items(), key=lambda kv: -kv[1]["mean_dti"]):
        print(f"  {v['mean_dti']:.4f}  n={v['n_folds']}  {k}")
    print("\n=== paired n1 - static ===")
    for k, v in sorted(paired.items()):
        print(f"  {v['mean_delta']:+.4f}  {v['folds_better']}/{v['n']}  {k}")
    print(f"wrote {out_path} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
