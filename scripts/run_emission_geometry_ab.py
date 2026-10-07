#!/usr/bin/env python3
"""Emission-geometry sweep on the hard (off-catalogue) instrument.

Question this answers
---------------------
The reported top family artifacts are all *thin dot sets* built from a broader
prior field, and their progression (solid prior -> dots at ~2.8 px minimum
separation -> removal of the catalogue-adjacent dots) is entirely a change of
emitted mass and geometry.  ``scripts/run_emission_geometry.py`` measured that
sweep on the *proxy* instrument (truth = held-out catalogue); this script does it
on the off-catalogue A/B instrument, where the truth is a set of systems the
model never saw as positives — the closest local analogue of "faults the
catalogue missed".

Swept dimensions (all evaluated with the official DTI on every fold):

* rule   — ``iso_nms`` (raw field, isotropic non-max suppression),
           ``ste`` (strike-coherent emission), ``raw_poisson`` (raw field,
           greedy credit-ordered Poisson-disk thinning at ``--spacing``),
           ``credit_poisson`` (same, ordered by kernel-convolved expected credit).
* mass   — ``ratio * |truth in block|`` dots, the repository's matched-mass rule.
* excl   — emission must sit at least this far (px) from the visible inventory.

No model is trained here: the fields are the fold fields written by
``scripts/run_h51_n1.py --save-fields``.  Nothing is emitted as a submission.

Usage::

    python3 scripts/run_emission_geometry_ab.py --fields work/fields
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import credit_emission as ce            # noqa: E402
from gems51 import trace_emission as te             # noqa: E402
from gems51.emission import nms_dots, rasterise     # noqa: E402
from gems51.grid import GRID                        # noqa: E402
from gems51.metric import dti_binary                # noqa: E402

P = ROOT / "data" / "prepared"


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields", default=str(ROOT / "work" / "fields"))
    ap.add_argument("--instrument", default="ab")
    ap.add_argument("--folds", default="0,1,2,3")
    ap.add_argument("--grid", type=int, default=2)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--ratios", type=float, nargs="*",
                    default=[1.0, 2.0, 3.47, 5.0, 7.0])
    ap.add_argument("--excl", type=float, nargs="*", default=[2.0, 5.0])
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--rules", nargs="*",
                    default=["iso_nms", "ste", "raw_poisson", "credit_poisson"])
    ap.add_argument("--out", default=str(ROOT / "evidence" / "emission_geometry_ab.json"))
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    A, B, lab = split_systems(catalogue, args.seed)
    dA = ndi.distance_transform_edt(~A).astype(np.float32)
    labB = np.where(B, lab, 0)
    far_ids = [int(i) for i in np.unique(labB) if i != 0 and dA[labB == i].min() >= 5.0]
    B_far = np.isin(labB, far_ids)
    blocks_ = grid_blocks(GRID.shape, args.grid)
    print(f"[A/B] A={int(A.sum())} B={int(B.sum())} B_far={int(B_far.sum())}", flush=True)

    rows: list[dict] = []
    t0 = time.time()
    for bi in [int(x) for x in args.folds.split(",") if x != ""]:
        fpath = Path(args.fields) / f"field_{args.instrument}_fold{bi}_static.npy"
        if not fpath.exists():
            print(f"  fold {bi}: {fpath.name} missing -- skipped", flush=True)
            continue
        field = np.load(fpath)
        blk = blocks_[bi] & footprint
        truth_all = B & blk
        truth_far = B_far & blk
        n_t = int(truth_all.sum())
        dom = footprint & np.isfinite(field)
        f0 = np.nan_to_num(field, nan=0.0).astype(np.float32)
        credit = ce.expected_credit(np.clip(f0, 0.0, 1.0), dom)
        v = np.zeros(f0.shape, np.float32)
        for s in (1.0, 2.0, 3.5):
            vi, _ = te.ridge_response(f0, dom, s)
            np.copyto(v, vi, where=vi > v)
        acc, _ang = te.line_accumulate(v, length=9, n_orient=12)
        rf, ra = te._rank01(f0, dom), te._rank01(acc, dom)
        ste_score = np.where(dom, (rf ** 0.65) * (ra ** 0.35), 0.0).astype(np.float32)
        del v, acc, rf, ra

        for excl in args.excl:
            cand = blk & dom & (dA >= excl)
            for ratio in args.ratios:
                n_dots = int(round(ratio * n_t))
                supports: dict[str, np.ndarray] = {}
                if "iso_nms" in args.rules:
                    ys, xs = nms_dots(field, n_dots, radius=2.4, exclude=~cand, valid=dom)
                    supports["iso_nms"] = rasterise(ys, xs) > 0
                if "ste" in args.rules:
                    ys, xs = te.spaced_dots(ste_score, cand, n_dots, spacing=3.0)
                    supports["ste"] = rasterise(ys, xs) > 0
                if "raw_poisson" in args.rules:
                    ys, xs, _ = ce.select_dots(f0, cand, -np.inf, spacing_px=args.spacing,
                                               max_dots=n_dots,
                                               pool_size=max(n_dots * 12, 50_000))
                    supports["raw_poisson"] = rasterise(ys, xs) > 0
                if "credit_poisson" in args.rules:
                    ys, xs, _ = ce.select_dots(credit, cand, -np.inf, spacing_px=args.spacing,
                                               max_dots=n_dots,
                                               pool_size=max(n_dots * 12, 50_000))
                    supports["credit_poisson"] = rasterise(ys, xs) > 0
                for nm, mask in supports.items():
                    rec = dict(fold=bi, rule=nm, ratio=ratio, excl=float(excl),
                               n_dots=int(mask.sum()))
                    for tn, truth in (("all", truth_all), ("far", truth_far)):
                        if int(truth.sum()) == 0:
                            continue
                        r = dti_binary(mask, truth, valid=footprint & blk, known=A)
                        rec[f"dti_{tn}"] = round(float(r["dti"]), 6)
                        rec[f"cpd_{tn}"] = round(float(r["tp"]) / max(int(mask.sum()), 1), 6)
                    rows.append(rec)
                print(f"  fold {bi} excl={excl} ratio={ratio}: "
                      + "  ".join(f"{nm}={supports[nm].sum()}" for nm in supports)
                      + f"  ({time.time()-t0:.0f}s)", flush=True)
        del field, credit, ste_score, f0

    summary = {}
    for nm in args.rules:
        for excl in args.excl:
            for ratio in args.ratios:
                vals_all = [r["dti_all"] for r in rows if r["rule"] == nm
                            and r["excl"] == float(excl) and r["ratio"] == ratio
                            and "dti_all" in r]
                vals_far = [r["dti_far"] for r in rows if r["rule"] == nm
                            and r["excl"] == float(excl) and r["ratio"] == ratio
                            and "dti_far" in r]
                if vals_all:
                    summary[f"{nm}|excl{excl:g}|r{ratio:g}"] = dict(
                        mean_dti_all=float(np.mean(vals_all)),
                        mean_dti_far=float(np.mean(vals_far)) if vals_far else None,
                        n=len(vals_all))
    out = dict(script="scripts/run_emission_geometry_ab.py", config=vars(args),
               rows=rows, summary=summary, runtime_s=round(time.time() - t0, 1),
               limitations=["off-catalogue A/B instrument, not a competition score",
                            "A and B come from one compilation; the halo control is bounded by that"])
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== mean DTI_all by (rule, exclusion, mass ratio) ===")
    for k, v in sorted(summary.items(), key=lambda kv: -kv[1]["mean_dti_all"]):
        far = v["mean_dti_far"]
        print(f"  {v['mean_dti_all']:.4f}  far={far if far is None else round(far,4)}  {k}")
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
