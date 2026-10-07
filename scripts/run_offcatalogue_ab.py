#!/usr/bin/env python3
"""Off-catalogue A/B holdout — the honest instrument for "faults the catalogue misses".

Why a second instrument
-----------------------
The spatially blocked holdout (``scripts/run_experiments.py``) hides a whole
*region* of the catalogue.  Inside that region there is then no mapped fault at
all, so it cannot measure the thing the competition actually asks for: finding a
fault that the catalogue missed *while* other faults in the same place are
already mapped and masked out of scoring.

This script builds that instrument:

  1. 8-connected components of the catalogue raster are treated as fault
     *systems*.  Systems are shuffled with a fixed seed and split into
     ``A`` (kept visible: training positives + the scorer's known-mask) and
     ``B`` (hidden: the pretend-new faults), balanced by pixel count.
  2. The detector trains on ``A`` positives only.  Every non-``A`` pixel is a
     negative, **including every ``B`` pixel** — exactly the label noise of the
     real task, where unmapped faults sit inside the negative class.
  3. Folds are contiguous spatial blocks with a training buffer, so a fold's
     belief field never saw its own block.
  4. Emission must respect the production constraint (at least ``--excl-radius``
     px away from any ``A`` pixel) and is scored against ``B`` with the official
     DTI and ``A`` supplied as the masked known set.

Two truth variants are reported:
  ``B_all``  every B pixel in the block;
  ``B_far``  only B components whose nearest A pixel is >= 5 px away, i.e.
             structures that are not simply an interleaved strand of a mapped
             fault zone.  ``B_far`` is the stricter, more honest number.

Stated bias: B is drawn from the same compilation as A, so a rule that merely
haloes the catalogue flatters itself here.  The ``halo_ring`` control rule
quantifies exactly how much.

Usage
-----
    python3 scripts/run_offcatalogue_ab.py --folds 0,1,2,3 --ratio 3.47
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
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise                # noqa: E402
from gems51.grid import GRID                                   # noqa: E402
from gems51.metric import dti_binary                           # noqa: E402

P = ROOT / "data" / "prepared"
ARM_EXTRAS = ["facecoh"]          # the adopted H_D arm


def split_systems(cat: np.ndarray, seed: int, min_px: int = 20):
    """Split catalogue connected components into A (visible) and B (hidden)."""
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
    a = cat & ~b
    return a, b, lab


def load_extras():
    path = P / "extras_static.dat"
    if not path.exists():
        return [], None, []
    names = json.loads((P / "extras_static_names.json").read_text())
    keep = [i for i, nm in enumerate(names) if any(k in nm for k in ARM_EXTRAS)]
    if not keep:
        return [], None, []
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def blocks(shape, n: int):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", default="0,1,2,3")
    ap.add_argument("--grid", type=int, default=2)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--neg", type=int, default=250000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--ste-w", type=float, default=0.35)
    ap.add_argument("--ste-spacing", type=float, default=3.0)
    ap.add_argument("--ste-linelen", type=int, default=9)
    ap.add_argument("--sigmas", type=float, nargs="*", default=[1.0, 2.0, 3.5])
    ap.add_argument("--out", default=str(ROOT / "evidence" / "offcatalogue_ab.json"))
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    A, B, lab = split_systems(catalogue, args.seed)
    dA = ndi.distance_transform_edt(~A)
    # B_far: components of B whose nearest A pixel is at least 5 px away
    labB = np.where(B, lab, 0)
    far_ids = [int(i) for i in np.unique(labB) if i != 0 and dA[labB == i].min() >= 5.0]
    B_far = np.isin(labB, far_ids) if far_ids else np.zeros(B.shape, bool)
    print(f"[A/B] A={int(A.sum())} px  B={int(B.sum())} px  "
          f"B_far={int(B_far.sum())} px ({len(far_ids)} components)", flush=True)

    stack = Stack(P)
    ex_names, ex_mm, ex_keep = load_extras()
    print(f"[A/B] + {len(ex_names)} static extras: {ex_names}", flush=True)

    blks = blocks(GRID.shape, args.grid)
    want = [int(x) for x in args.folds.split(",") if x != ""]
    rows: list[dict] = []
    t0 = time.time()

    for bi in want:
        blk = blks[bi] & footprint
        if int((B & blk).sum()) < 300:
            print(f"  fold {bi}: too few B pixels ({int((B & blk).sum())}) -- skipped")
            continue
        grow = ndi.binary_dilation(blks[bi], structure=np.ones((3, 3)),
                                   iterations=max(args.buffer, 0))
        forbidden = grow & footprint
        train_pos = A & ~forbidden
        train_neg = footprint & ~A & ~forbidden      # B pixels are negatives here

        extra_cols = ([np.asarray(ex_mm[i], dtype=np.float32) for i in ex_keep]
                      if ex_mm is not None else [])
        rng = np.random.default_rng(5000 + bi)
        X, y = stack.sample(train_pos, train_neg, args.neg, rng, extra=extra_cols)
        model = fit_detector(X, y, seed=bi, max_iter=args.max_iter)
        del X, y
        field = predict_grid(model, stack, footprint, extra=extra_cols)

        dom = footprint & np.isfinite(field)
        m = blk & dom
        auc_all = float(roc_auc_score(B[m], field[m]))
        auc_far = float(roc_auc_score(B_far[m], field[m])) if B_far[m].any() else float("nan")

        cand = blk & dom & (dA >= args.excl_radius)
        truth_all = B & blk
        truth_far = B_far & blk
        n_dots = int(round(args.ratio * int(truth_all.sum())))

        # --- rule-independent transforms -----------------------------------
        f0 = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        v = np.zeros(f0.shape, np.float32)
        for s in args.sigmas:
            vi, _ = te.ridge_response(f0, dom, s)
            np.copyto(v, vi, where=vi > v)
        acc, ang = te.line_accumulate(v, length=args.ste_linelen, n_orient=12)
        rf, ra = te._rank01(f0, dom), te._rank01(acc, dom)
        w = args.ste_w
        ste_score = np.where(dom, (rf ** (1 - w)) * (ra ** w), 0.0).astype(np.float32)

        rules: dict[str, np.ndarray] = {}
        ys, xs = nms_dots(field, n_dots, radius=2.4, exclude=~cand, valid=dom)
        rules["iso_nms_r2.4"] = rasterise(ys, xs) > 0
        ys, xs = te.spaced_dots(ste_score, cand, n_dots, spacing=args.ste_spacing)
        rules[f"ste_L{args.ste_linelen}_w{w:g}_s{args.ste_spacing:g}"] = rasterise(ys, xs) > 0
        # control: a pure halo around the visible catalogue, same mass
        ring = cand & (dA >= args.excl_radius) & (dA < 5.0)
        rng2 = np.random.default_rng(7000 + bi)
        ridx = np.flatnonzero(ring.ravel())
        pick = rng2.choice(ridx, size=min(n_dots, ridx.size), replace=False)
        halo = np.zeros(GRID.shape, bool)
        halo.ravel()[pick] = True
        rules["halo_ring_2_5px"] = halo
        # control: uniform random inside the candidate region, same mass
        cidx = np.flatnonzero(cand.ravel())
        pick = rng2.choice(cidx, size=min(n_dots, cidx.size), replace=False)
        unif = np.zeros(GRID.shape, bool)
        unif.ravel()[pick] = True
        rules["uniform_random"] = unif

        for nm, mask in rules.items():
            rec = dict(fold=bi, rule=nm, n_px=int(mask.sum()),
                       auc_B_all=auc_all, auc_B_far=auc_far)
            for tn, truth in (("B_all", truth_all), ("B_far", truth_far)):
                if int(truth.sum()) == 0:
                    continue
                r = dti_binary(mask, truth, valid=footprint & blk, known=A)
                rec[f"dti_{tn}"] = r["dti"]
                rec[f"n_truth_{tn}"] = r["n_truth"]
                rec[f"credit_per_dot_{tn}"] = r["tp"] / max(int(mask.sum()), 1)
            rows.append(rec)
            print(f"  fold {bi} {nm:24s} dots={int(mask.sum()):6d} "
                  f"B_all={rec.get('dti_B_all', float('nan')):.4f} "
                  f"B_far={rec.get('dti_B_far', float('nan')):.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        del field, f0, v, acc, rf, ra, ste_score

    summary = {}
    for tn in ("B_all", "B_far"):
        by: dict[str, list] = {}
        for r in rows:
            if f"dti_{tn}" in r:
                by.setdefault(r["rule"], []).append(r[f"dti_{tn}"])
        base = by.get("iso_nms_r2.4", [])
        for nm, vals in by.items():
            pairs = [(r["fold"], r[f"dti_{tn}"]) for r in rows if r["rule"] == nm
                     and f"dti_{tn}" in r]
            bs = {r["fold"]: r[f"dti_{tn}"] for r in rows
                  if r["rule"] == "iso_nms_r2.4" and f"dti_{tn}" in r}
            d = [v - bs[f] for f, v in pairs if f in bs]
            summary[f"{nm}|{tn}"] = dict(
                mean_dti=float(np.mean(vals)), n_folds=len(vals),
                mean_delta_vs_iso=float(np.mean(d)) if d else None,
                folds_better=int(sum(x > 0 for x in d)) if d else None)
        _ = base

    out = dict(
        instrument=("off-catalogue A/B split of catalogue fault systems; detector "
                    "trained on A only with B pixels left in the negative class; "
                    "contiguous spatial folds with a training buffer; official DTI "
                    "against B with A supplied as the masked known set"),
        seed=args.seed, config=vars(args),
        a_px=int(A.sum()), b_px=int(B.sum()), b_far_px=int(B_far.sum()),
        rows=rows, summary=summary,
        bias_note=("B comes from the same compilation as A and is interleaved with "
                   "it, so a halo-style rule flatters itself here; the halo_ring "
                   "control measures that effect directly."))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== mean DTI ===")
    for k, v in sorted(summary.items(), key=lambda kv: -kv[1]["mean_dti"]):
        d = v["mean_delta_vs_iso"]
        print(f"  {v['mean_dti']:.4f}  d={0.0 if d is None else d:+.4f}  "
              f"{v['folds_better']}/{v['n_folds']}  {k}")
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
