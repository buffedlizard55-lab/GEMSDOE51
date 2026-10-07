#!/usr/bin/env python3
"""HOLDOUT VALIDATION of H-51-L (trace-axis snap) — pre-registered decision rule.

Validates the positional-refinement hypothesis on the SAME six spatially-blocked
folds as `data/holdout_H_D.json` (grid 3x3, buffer 12, min truth 500), using the
saved H_D fold fields, at matched emitted mass (ratio 3.47, the live operating
point).  Nothing is refit: refinement is a deterministic post-processing of the
NMS dot set, so the paired comparison isolates exactly one mechanism.

Pre-registered rule (knowledge/02 §4): promote iff mean dot-to-truth distance
improves in >= 5/6 folds AND mean proxy DTI does not fall by more than 0.0005.

Primary statistic (named by the README as the whole gap to the leader):
    mean distance from an emitted dot to the nearest held-out truth pixel.

Usage:
    python scripts/run_refine_holdout.py [--window 2] [--margin 0.0]
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

from gems51.detector import Stack  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.refine import build_snap_surface, refine_positions  # noqa: E402

P = ROOT / "data" / "prepared"


def dot_truth_distance(ys, xs, truth: np.ndarray) -> np.ndarray:
    d = ndi.distance_transform_edt(~truth)
    return d[ys, xs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=2)
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--suppress-radius", type=float, default=4.0)
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--min-truth", type=int, default=500)
    a = ap.parse_args()

    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    folds = make_folds(footprint, catalogue, buffer_px=a.buffer,
                       n_rows=a.grid, n_cols=a.grid, min_truth=a.min_truth)
    print(f"[refine] {len(folds)} folds; truth/fold = {[f.n_truth for f in folds]}")

    print("[refine] building snap surface ...")
    # Suppress around the ENTIRE catalogue, block pixels included: at submission
    # time the surface cannot know the hidden truth, so the validation must not
    # let the surface see the block's own pretend-hidden scarps either.
    surf = build_snap_surface(stack, footprint, suppress=catalogue,
                              suppress_radius_px=a.suppress_radius)

    rows = []
    for fold in folds:
        fpath = P / f"field_H_D_fold{fold.index}.npy"
        if not fpath.exists():
            print(f"  fold {fold.index}: missing {fpath.name}, run run_experiments.py "
                  f"--arm H_D --save-fields first"); return 2
        field = np.load(fpath)
        in_block = fold.block & footprint
        # the exclusion ring is around fold.known (catalogue OUTSIDE the block),
        # exactly as in run_experiments.py: the block's own pixels are the
        # pretend-hidden truth, and live scoring never excludes around those.
        excl = ndi.distance_transform_edt(~fold.known) <= a.excl_radius
        k = int(round(a.ratio * fold.n_truth))
        ys, xs = nms_dots(field, k, radius=a.nms_radius,
                          exclude=excl | ~in_block, valid=footprint)
        # ---------------- baseline statistics
        d_base = dot_truth_distance(ys, xs, fold.truth)
        pred = rasterise(ys, xs)
        r_base = dti_binary(pred > 0, fold.truth, valid=footprint & fold.block,
                            known=fold.known)
        # ---------------- refined
        # priority = the detector field at each dot: the same ownership order
        # NMS used to choose the dots, so contested cells resolve the same way.
        allowed = footprint & ~excl & in_block
        ry, rx, stats = refine_positions(ys, xs, surf, allowed,
                                         window=a.window, margin=a.margin,
                                         priority=field[ys, xs])
        assert len({(int(y), int(x)) for y, x in zip(ry, rx)}) == len(ry), \
            "refinement produced duplicate dots"
        d_ref = dot_truth_distance(ry, rx, fold.truth)
        pred_r = rasterise(ry, rx)
        r_ref = dti_binary(pred_r > 0, fold.truth, valid=footprint & fold.block,
                           known=fold.known)
        row = dict(
            fold=fold.index, n_truth=fold.n_truth, n_dots=int(len(ys)),
            base=dict(mean_dist_px=float(d_base.mean()),
                      median_dist_px=float(np.median(d_base)),
                      frac_within_1px=float((d_base <= 1.0).mean()),
                      frac_within_3px=float((d_base <= 3.0).mean()),
                      dti=float(r_base["dti"]), coverage=float(r_base["coverage"])),
            refined=dict(mean_dist_px=float(d_ref.mean()),
                         median_dist_px=float(np.median(d_ref)),
                         frac_within_1px=float((d_ref <= 1.0).mean()),
                         frac_within_3px=float((d_ref <= 3.0).mean()),
                         dti=float(r_ref["dti"]), coverage=float(r_ref["coverage"])),
            move_stats=stats,
            delta=dict(mean_dist_px=float(d_ref.mean() - d_base.mean()),
                       dti=float(r_ref["dti"] - r_base["dti"])),
        )
        rows.append(row)
        print(f"  fold {fold.index}: dots={len(ys):6d} moved={stats['n_moved']:6d} "
              f"({stats['moved_fraction']:.1%}) mean_dist {row['base']['mean_dist_px']:.3f}"
              f" -> {row['refined']['mean_dist_px']:.3f} px   "
              f"DTI {row['base']['dti']:.4f} -> {row['refined']['dti']:.4f}   "
              f"({time.time()-t0:.0f}s)", flush=True)

    n = len(rows)
    better_dist = sum(1 for r in rows if r["delta"]["mean_dist_px"] < 0)
    mean_ddti = float(np.mean([r["delta"]["dti"] for r in rows]))
    summary = dict(
        n_folds=n,
        folds_mean_dist_improved=better_dist,
        mean_delta_dti=mean_ddti,
        mean_base_dti=float(np.mean([r["base"]["dti"] for r in rows])),
        mean_refined_dti=float(np.mean([r["refined"]["dti"] for r in rows])),
        mean_base_dist=float(np.mean([r["base"]["mean_dist_px"] for r in rows])),
        mean_refined_dist=float(np.mean([r["refined"]["mean_dist_px"] for r in rows])),
        total_moved=int(sum(r["move_stats"]["n_moved"] for r in rows)),
        total_dots=int(sum(r["n_dots"] for r in rows)),
    )
    rule_ok = (better_dist >= 5) and (mean_ddti >= -0.0005)
    out = dict(config=vars(a), rule="promote iff mean dist improves in >=5/6 folds "
                                    "and mean DTI does not fall by >0.0005",
               rule_passed=bool(rule_ok), per_fold=rows, summary=summary)
    for dest in (ROOT / "data" / "refine_holdout.json",
                 ROOT / "evidence" / "refine_holdout.json"):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"RULE {'PASSED — promote H-51-L' if rule_ok else 'FAILED — do not promote'}")
    return 0 if rule_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
