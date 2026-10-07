#!/usr/bin/env python3
"""Emission-geometry sweep on the spatially blocked holdout, at matched mass.

What this measures
------------------
The detector field is held *fixed* (the saved per-fold belief rasters written by
``scripts/run_experiments.py --save-fields``), and only the rule that turns that
field into emitted pixels is varied.  Every rule is given the same mass budget
(``ratio * n_truth`` dots inside the held-out block), so the comparison is a
clean A/B of emission geometry: identical detector, identical mass, identical
scoring domain.

Rules compared
--------------
``iso_nms_rR``      the incumbent: isotropic greedy non-maximum suppression of
                    the raw belief field with exclusion radius R px
                    (``gems51.emission.nms_dots``)
``ste_...``         strike-coherent trace emission (``gems51.trace_emission``):
                    multi-scale Frangi ridge response -> along-strike line
                    accumulation -> optional across-strike thinning -> greedy
                    along-trace spacing.

Why this can win
----------------
``TP_w`` is a sum over the *truth* with a max over nearby predictions, so a dot
on the shoulder of a blob earns at most k(2) = 1/3 of what a dot on the crest
earns, and two dots across the width of one structure earn once but cost twice.
Isotropic NMS is blind to both facts; the strike-coherent rule is built around
them.  See the module docstring of ``gems51.trace_emission`` for the citations.

Usage
-----
    python3 scripts/run_emission_geometry.py --folds 0,2,4 --ratio 3.47
    python3 scripts/run_emission_geometry.py --folds all --rules-file <json>
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

from gems51 import trace_emission as te          # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.holdout import make_folds            # noqa: E402
from gems51.metric import dti_binary             # noqa: E402

P = ROOT / "data" / "prepared"


def build_rules(args) -> list[dict]:
    rules = [dict(kind="iso", spacing=r) for r in args.iso_radii]
    for ll in args.line_lens:
        for w in args.w_cont:
            for sp in args.spacings:
                for thin in args.thin:
                    rules.append(dict(kind="ste", line_len=ll, w_cont=w,
                                      spacing=sp, thin=bool(thin)))
    return rules


def rule_name(r: dict) -> str:
    if r["kind"] == "iso":
        return f"iso_nms_r{r['spacing']:g}"
    return (f"ste_L{r['line_len']}_w{r['w_cont']:g}_s{r['spacing']:g}"
            f"_{'thin' if r['thin'] else 'nothin'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H_D")
    ap.add_argument("--folds", default="all")
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--iso-radii", type=float, nargs="*", default=[2.4])
    ap.add_argument("--line-lens", type=int, nargs="*", default=[9])
    ap.add_argument("--w-cont", type=float, nargs="*", default=[0.0, 0.35, 0.6])
    ap.add_argument("--spacings", type=float, nargs="*", default=[2.4, 3.0])
    ap.add_argument("--thin", type=int, nargs="*", default=[1, 0])
    ap.add_argument("--sigmas", type=float, nargs="*", default=[1.0, 2.0, 3.5])
    ap.add_argument("--out", default=str(ROOT / "evidence" / "emission_geometry.json"))
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    want = (list(range(len(folds))) if args.folds == "all"
            else [int(x) for x in args.folds.split(",") if x != ""])

    rules = build_rules(args)
    print(f"[emission-geometry] {len(rules)} rules x {len(want)} folds, "
          f"ratio={args.ratio}", flush=True)

    rows: list[dict] = []
    t0 = time.time()
    for fi in want:
        fold = folds[fi]
        fpath = P / f"field_{args.arm}_fold{fold.index}.npy"
        if not fpath.exists():
            print(f"  fold {fi}: MISSING {fpath.name} -- run run_experiments.py "
                  f"--arm {args.arm} --save-fields first")
            continue
        field = np.load(fpath)
        dom = footprint & np.isfinite(field)
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= args.excl_radius
        cand0 = in_block & ~excl & dom
        n_dots = int(round(args.ratio * fold.n_truth))

        # --- expensive, rule-independent part: ridge response at every scale ---
        f0 = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        v = np.zeros(f0.shape, np.float32)
        for s in args.sigmas:
            vi, _ = te.ridge_response(f0, dom, s)
            np.copyto(v, vi, where=vi > v)
        rf = te._rank01(f0, dom)
        acc_cache: dict[int, tuple] = {}

        for r in rules:
            nm = rule_name(r)
            if r["kind"] == "iso":
                ys, xs = nms_dots(field, n_dots, radius=r["spacing"],
                                  exclude=~cand0, valid=dom)
            else:
                ll = r["line_len"]
                if ll not in acc_cache:
                    acc, ang = te.line_accumulate(v, length=ll, n_orient=12)
                    acc_cache[ll] = (te._rank01(acc, dom), ang)
                ra, ang = acc_cache[ll]
                w = r["w_cont"]
                score = (rf ** (1.0 - w)) * (ra ** w)
                score = np.where(dom, score, 0.0).astype(np.float32)
                cand = cand0
                if r["thin"]:
                    crest = te.across_strike_thin(score, ang, dom, step=1.0)
                    if int((cand0 & crest).sum()) >= n_dots:
                        cand = cand0 & crest
                ys, xs = te.spaced_dots(score, cand, n_dots, spacing=r["spacing"])
            pred = rasterise(ys, xs)
            res = dti_binary(pred > 0, fold.truth, valid=footprint & fold.block,
                             known=fold.known)
            rows.append(dict(fold=fold.index, rule=nm, n_dots=int(len(ys)),
                             dti=res["dti"], tp=res["tp"], fp=res["fp"],
                             n_truth=res["n_truth"],
                             credit_per_dot=res["tp"] / max(len(ys), 1)))
            print(f"  fold {fold.index} {nm:34s} dots={len(ys):6d} "
                  f"dti={res['dti']:.4f} credit/dot={res['tp']/max(len(ys),1):.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        del field, f0, v, rf, acc_cache

    # --- paired summary against the incumbent -------------------------------
    base = f"iso_nms_r{args.iso_radii[0]:g}"
    by_rule: dict[str, dict[int, float]] = {}
    for r in rows:
        by_rule.setdefault(r["rule"], {})[r["fold"]] = r["dti"]
    summary = []
    for nm, per in by_rule.items():
        deltas = [per[f] - by_rule[base][f] for f in per if f in by_rule.get(base, {})]
        summary.append(dict(
            rule=nm, folds=len(per), mean_dti=float(np.mean(list(per.values()))),
            mean_delta_vs_incumbent=float(np.mean(deltas)) if deltas else None,
            folds_better=int(sum(d > 0 for d in deltas)) if deltas else None,
            per_fold={str(k): round(v, 6) for k, v in sorted(per.items())}))
    summary.sort(key=lambda d: -d["mean_dti"])

    out = dict(
        instrument=("spatially blocked holdout, 3x3 grid, 12 px training buffer; "
                    "detector field held fixed, only the emission rule varies; "
                    "mass matched at ratio * n_truth inside the held-out block"),
        arm=args.arm, ratio=args.ratio, excl_radius=args.excl_radius,
        incumbent=base, config=vars(args), rows=rows, summary=summary)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== mean DTI by rule ===")
    for s in summary:
        d = s["mean_delta_vs_incumbent"]
        print(f"  {s['mean_dti']:.4f}  d={0.0 if d is None else d:+.4f}  "
              f"{s['folds_better']}/{s['folds']}  {s['rule']}")
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
