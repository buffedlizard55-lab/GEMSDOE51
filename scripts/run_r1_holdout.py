#!/usr/bin/env python3
"""R1 preregistered paired holdout: promoted blend with upload-legal geometry.

Question
--------
The promoted H-H/H-D 50/50 blend + STE L9 emission (six-fold proxy DTI
0.285340602656319, evidence/hh_blend_holdout.json) is not upload-legal as
archived: 13.29 % of its dots sit outside Stage-1 q10 approved tiles, and its
NaN-outside encoding has not been portal-validated.  R1 fixes geometry only
(no new geology) and this script measures the cost/benefit on the same six
spatially blocked folds, paired on identical fitted fields and mass budget.

Variants (frozen in knowledge/preregistration-2026-10-08.md BEFORE any run)
----------------------------------------------------------------------------
  base     : archived recipe reproduced exactly (instrument check; must match
             evidence/hh_blend_holdout.json STE per-fold within 1e-5).
  restrict : STE candidate mask intersected with approved q10 tiles before
             greedy spacing.
  relocate : emit unrestricted first; every dot outside approved tiles is
             moved to the nearest approved, non-excluded, unoccupied cell
             (cKDTree, lazy blocking, spacing 2.4 preserved, deterministic
             score-descending processing order).

Promotion (ALL required; identical in form to the H51-N2 precedent)
--------------------------------------------------------------------
  1. base reproduces the archived frozen-best per fold within 1e-5;
  2. mean(best confined variant) - mean(base) >= 0;
  3. best confined variant wins >= 4/6 folds vs base;
  4. 100 % of the variant's dots inside approved tiles.

Failure keeps the artifact RESEARCH ONLY. No rule edits after results.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems51 import strain_budget as sb                          # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid   # noqa: E402
from gems51.emission import rasterise                          # noqa: E402
from gems51.grid import GRID                                    # noqa: E402
from gems51.holdout import make_folds                          # noqa: E402
from gems51.metric import dti_binary                           # noqa: E402
from scripts.build_submission_hh_blend import (                 # noqa: E402
    load_observed, selected_extras, stage1_prior)
from scripts.evaluate_hh_blend import ste_emit                  # noqa: E402

P = ROOT / "data" / "prepared"
FROZEN_PER_FOLD = [0.28358474213082796, 0.27178387428750844, 0.29027025890966246,
                   0.24335930706370568, 0.30504916677291494, 0.3179962667732945]
FROZEN_MEAN = 0.285340602656319
REPRO_TOL = 1e-5
SPACING = 2.4


def relocate_dots(ys: np.ndarray, xs: np.ndarray, allowed: np.ndarray,
                  spacing: float = SPACING) -> tuple[np.ndarray, np.ndarray, dict]:
    """Move every dot outside ``allowed`` to its nearest free allowed cell.

    Dots already inside ``allowed`` keep their exact positions.  Moved dots are
    processed in input (emission score descending) order and respect the same
    circular spacing exclusion as ``te.spaced_dots`` against every kept and
    previously moved dot.  Deterministic; returns (ys, xs, stats).
    """
    H, W = allowed.shape
    ys = np.asarray(ys, dtype=np.int64)
    xs = np.asarray(xs, dtype=np.int64)
    inside = allowed[ys, xs]
    moved = 0
    failed = 0
    max_move_dist = 0.0
    move_dists: list[float] = []

    r = int(np.ceil(spacing))
    PW = W + 2 * r
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    nb = (dy * dy + dx * dx) <= spacing * spacing
    flat_offs = dy[nb].astype(np.int64) * PW + dx[nb].astype(np.int64)
    blocked = np.zeros((H + 2 * r) * PW, dtype=bool)

    def padp(y: int, x: int) -> int:
        return (y + r) * PW + (x + r)

    for y, x, keep in zip(ys, xs, inside):
        if keep:
            blocked[padp(y, x) + flat_offs] = True

    avail = np.argwhere(allowed)
    n_avail = avail.shape[0]
    tree = cKDTree(avail) if n_avail else None

    out_y = ys.copy()
    out_x = xs.copy()
    for i in range(ys.size):
        if inside[i]:
            continue
        if tree is None:
            failed += 1
            continue
        target = None
        for kq in (64, 256, 1024, 8192, min(65536, n_avail)):
            _, idxs = tree.query((ys[i], xs[i]), k=min(kq, n_avail))
            idxs = np.atleast_1d(idxs)
            for j in idxs:
                yj, xj = int(avail[j, 0]), int(avail[j, 1])
                if not blocked[padp(yj, xj)]:
                    target = (yj, xj)
                    break
            if target is not None:
                break
        if target is None:
            failed += 1
            continue
        yj, xj = target
        d = float(np.hypot(yj - ys[i], xj - xs[i]))
        move_dists.append(d)
        max_move_dist = max(max_move_dist, d)
        out_y[i] = yj
        out_x[i] = xj
        blocked[padp(yj, xj) + flat_offs] = True
        moved += 1
    stats = dict(moved=moved, failed=failed, n=int(ys.size),
                 mean_move_px=(float(np.mean(move_dists)) if move_dists else 0.0),
                 p95_move_px=(float(np.percentile(move_dists, 95)) if move_dists else 0.0),
                 max_move_px=max_move_dist)
    return out_y, out_x, stats


def fit_fold_fields(stack: Stack, fold, extras_hd, extras_hh, args):
    """Fit the H-D and H-H fold fields exactly as run_experiments.py did."""
    out = {}
    for arm, extras in (("H_D", extras_hd), ("H_H", extras_hh)):
        cache = P / f"field_{arm}_fold{fold.index}.npy"
        if cache.exists() and not args.force:
            out[arm] = np.load(cache)
            continue
        rng = np.random.default_rng(1000 + fold.index)
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, args.neg, rng,
                            extra=extras)
        model = fit_detector(X, y, seed=fold.index, max_iter=args.max_iter)
        del X, y
        field = predict_grid(model, stack, footprint=footprint_global, extra=extras)
        np.save(cache, field)
        out[arm] = field
        print(f"  [fit] fold {fold.index} {arm} cached", flush=True)
    return out


footprint_global: np.ndarray | None = None


def main() -> int:
    global footprint_global
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", default="0,1,2,3,4,5")
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--excl", type=float, default=2.0)
    ap.add_argument("--stage1-q", type=float, default=10.0)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--neg", type=int, default=250_000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--weight-hh", type=float, default=0.5)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "r1_holdout_20261008.json"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    out_path = Path(a.out)
    if out_path.exists() and not a.force:
        doc = json.loads(out_path.read_text())
    else:
        doc = dict(
            instrument="six-fold contiguous spatial holdout (3x3, 12 px buffer); "
                       "visible known-fault proxy truth; emission and scoring restricted "
                       "to the held-out block at matched mass M/|G|=%.2f" % a.ratio,
            preregistration="knowledge/preregistration-2026-10-08.md",
            rule="PROMOTE iff base reproduces archived frozen-best within 1e-5 AND "
                 "mean(best confined)-mean(base)>=0 AND best confined wins >=4/6 folds "
                 "AND 100% dots inside approved q10 tiles",
            frozen_mean=FROZEN_MEAN,
            frozen_per_fold=FROZEN_PER_FOLD,
            config=vars(a),
            per_fold={},
        )

    footprint = np.load(P / "footprint.npy")
    footprint_global = footprint
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    extras_hd, names_hd = selected_extras(stack, [], footprint, "H_D")
    extras_hh, names_hh = selected_extras(stack, [], footprint, "H_H")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    want = {int(v) for v in a.folds.split(",") if v.strip() != ""}
    print(f"[r1] extras H_D={names_hd} H_H={names_hh}", flush=True)
    t0 = time.time()

    for fold in folds:
        if fold.index not in want:
            continue
        if str(fold.index) in doc["per_fold"] and not a.force:
            print(f"[skip] fold {fold.index} already recorded", flush=True)
            continue
        fields = fit_fold_fields(stack, fold, extras_hd, extras_hh, a)
        field = ((1.0 - a.weight_hh) * fields["H_D"]
                 + a.weight_hh * fields["H_H"]).astype(np.float32)
        k = int(round(a.ratio * fold.n_truth))
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= a.excl
        base_allowed = in_block & ~excl & np.isfinite(field)
        s1 = stage1_prior(fold.known, footprint, df, obs,
                          tile_px=a.tile_px, q=a.stage1_q)
        approved = s1["approved"]
        conf_allowed = base_allowed & approved

        rules = {}
        # ---- base (frozen reproduction) ------------------------------------
        ys, xs = ste_emit(field, base_allowed, k)
        r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                       valid=footprint & fold.block, known=fold.known)
        rules["base"] = dict(dti=float(r["dti"]), dots=int(len(ys)),
                             tp=float(r["tp"]), fp=float(r["fp"]),
                             dots_inside_approved=int(approved[ys, xs].sum()))
        # ---- restrict --------------------------------------------------------
        ys_r, xs_r = ste_emit(field, conf_allowed, k)
        r = dti_binary(rasterise(ys_r, xs_r) > 0, fold.truth,
                       valid=footprint & fold.block, known=fold.known)
        rules["restrict"] = dict(dti=float(r["dti"]), dots=int(len(ys_r)),
                                 tp=float(r["tp"]), fp=float(r["fp"]),
                                 dots_inside_approved=int(approved[ys_r, xs_r].sum()))
        # ---- relocate ---------------------------------------------------------
        ys_l, xs_l, move_stats = relocate_dots(ys, xs, conf_allowed, SPACING)
        r = dti_binary(rasterise(ys_l, xs_l) > 0, fold.truth,
                       valid=footprint & fold.block, known=fold.known)
        rules["relocate"] = dict(dti=float(r["dti"]), dots=int(len(ys_l)),
                                 tp=float(r["tp"]), fp=float(r["fp"]),
                                 dots_inside_approved=int(approved[ys_l, xs_l].sum()),
                                 move_stats=move_stats)
        # ---- uniform-tiles dominance control (frozen seed 4242+fold) ---------
        # Same mass, uniformly random pixels inside the same approved domain.
        # If the confined candidate cannot beat this by >= 0.0020 on average,
        # the tiles, not the fine model, are doing the work (Stage-1 dominance).
        cand_idx = np.flatnonzero(conf_allowed.ravel())
        rng_u = np.random.default_rng(4242 + fold.index)
        sel_u = rng_u.choice(cand_idx.size, size=min(k, cand_idx.size), replace=False)
        flat_u = cand_idx[sel_u]
        pred_u = np.zeros(GRID.shape, bool)
        pred_u.ravel()[flat_u] = True
        r = dti_binary(pred_u, fold.truth,
                       valid=footprint & fold.block, known=fold.known)
        rules["uniform_tiles"] = dict(dti=float(r["dti"]), dots=int(sel_u.size),
                                      tp=float(r["tp"]), fp=float(r["fp"]))
        rec = dict(fold=fold.index, n_truth=int(fold.n_truth),
                   approved_area_share=float((approved & footprint).sum()
                                             / max(int(footprint.sum()), 1)),
                   rules=rules)
        doc["per_fold"][str(fold.index)] = rec
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, indent=1) + "\n")
        print(f"[fold {fold.index}] truth={fold.n_truth} "
              f"base={rules['base']['dti']:.6f} restrict={rules['restrict']['dti']:.6f} "
              f"relocate={rules['relocate']['dti']:.6f} "
              f"moved={move_stats['moved']} meanmove={move_stats['mean_move_px']:.2f}px "
              f"({time.time() - t0:.0f}s)", flush=True)
        del field, fields

    # ---------------------------------------------------------------- summary
    folds_done = sorted(int(key) for key in doc["per_fold"])
    summary: dict = dict(folds=folds_done, folds_evaluated=len(folds_done))
    for name in ("base", "restrict", "relocate", "uniform_tiles"):
        vals = [doc["per_fold"][str(i)]["rules"][name]["dti"] for i in folds_done]
        summary[name] = dict(per_fold=vals, mean=float(np.mean(vals)))
    if len(folds_done) >= 6:
        base_vals = summary["base"]["per_fold"]
        max_dev = max(abs(b - f) for b, f in zip(base_vals, FROZEN_PER_FOLD))
        summary["instrument"] = dict(
            base_reproduces_frozen=bool(max_dev <= REPRO_TOL),
            max_abs_dev=float(max_dev), tol=REPRO_TOL)
        candidates = {}
        for name in ("restrict", "relocate"):
            vals = summary[name]["per_fold"]
            delta = float(summary[name]["mean"] - summary["base"]["mean"])
            wins = int(sum(v > b for v, b in zip(vals, base_vals)))
            inside_shares = [doc["per_fold"][str(i)]["rules"][name]["dots_inside_approved"]
                             / max(doc["per_fold"][str(i)]["rules"][name]["dots"], 1)
                             for i in folds_done]
            candidates[name] = dict(mean_delta=delta, folds_won=wins,
                                    min_inside_share=float(min(inside_shares)))
        best = max(candidates, key=lambda nm: summary[nm]["mean"])
        c = candidates[best]
        ok = (summary["instrument"]["base_reproduces_frozen"]
              and c["mean_delta"] >= 0.0 and c["folds_won"] >= 4
              and c["min_inside_share"] >= 1.0)
        summary["candidates"] = candidates
        summary["selected_variant"] = best
        summary["dominance_control"] = dict(
            confined_mean=summary[best]["mean"],
            uniform_tiles_mean=summary["uniform_tiles"]["mean"],
            excess=summary[best]["mean"] - summary["uniform_tiles"]["mean"],
            margin=0.0020,
            passed=bool(summary[best]["mean"] - summary["uniform_tiles"]["mean"] >= 0.0020))
        summary["verdict"] = "PROMOTED_" + best if ok else "NOT_PROMOTED"
        summary["promotion_note"] = (
            "PROMOTED (%s): confined geometry is not worse than the archived promoted "
            "blend on the paired six-fold proxy and is fully inside q10 approved tiles. "
            "Local proxy only; no organizer score is claimed." % best
            if ok else
            "NOT_PROMOTED: the preregistered rule was not met in full. Any artifact from "
            "this session is RESEARCH ONLY / DO NOT SUBMIT.")
    doc["summary"] = summary
    out_path.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
