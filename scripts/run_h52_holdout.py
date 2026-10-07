#!/usr/bin/env python3
"""H52 holdout: strike-aligned line emission vs the incumbent point emission.

Preregistration: ``registry/preregistration_h52.json`` (frozen before this ran).
Receipt written: ``evidence/h52_holdout_<utc>.json``.

Protocol (unchanged from the repository's established instrument, so numbers stay
comparable with ``data/holdout_*.json``):

  * six contiguous 3x3 spatial blocks of the visible catalogue; the block is the
    fold's truth, the rest of the catalogue is "known" (masked by the scorer);
  * 12 px training buffer around the block;
  * belief field = 50/50 blend of the H-H arm (base + facecoh + hh_ extras) and
    the H-D arm (base + facecoh), trained per fold with the same detector
    hyper-parameters as ``scripts/run_experiments.py``;
  * emitted mass = 3.47 x n_truth for every variant (matched mass is what makes a
    proxy DTI comparable across variants);
  * every variant is scored twice: reading A (``gems51.metric.dti_binary``, mass
    on published faults deleted) and reading B (``gems51.live_metric``, counted
    as false positive), so the convention ambiguity is never hidden.

Stage 1 (reported separately, never blended into Stage 2)
  * fold-specific rank-space strain-budget deficit over 10 km tiles
    (``gems51.stage1``), with the held-out trace rows removed from the slip-rate
    table;
  * approved domain = tiles at/above the q-th percentile of the deficit;
  * Stage-1 is scored alone by throwing uniform random dots inside the approved
    area of the block and comparing with uniform random dots over the whole block;
  * Stage-2 confinement is enforced at emission time, and the dominance lift
    (emitted share inside approved / approved area share) is reported.

Usage
-----
    .venv/bin/python scripts/run_h52_holdout.py [--from-cache] [--folds 6]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import emission2 as em2          # noqa: E402
from gems51 import strain_budget as sb       # noqa: E402
from gems51 import stage1 as st1             # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID                 # noqa: E402
from gems51.holdout import make_folds        # noqa: E402
from gems51.live_metric import dti_binary_live, on_catalogue_mass  # noqa: E402
from gems51.metric import dti_binary         # noqa: E402

P = ROOT / "data" / "prepared"
EXTRA_NAMES = ("facecoh", "hh_")
ARM_KEYS = {"HH": EXTRA_NAMES, "HD": ("facecoh",)}


def load_extras(arm: str):
    path = P / "extras_static.dat"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run scripts/build_extras.py first")
    names = json.loads((P / "extras_static_names.json").read_text())
    keys = ARM_KEYS[arm]
    keep = [i for i, n in enumerate(names) if any(k in n for k in keys)]
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def fold_fields(fold, stack: Stack, extras, seed: int, save: bool):
    """Train both arms on the fold's training pool and return the 50/50 blend."""
    fields = {}
    for arm in ("HH", "HD"):
        cache = P / f"h52_field_{arm}_fold{fold.index}.npy"
        if cache.exists():
            fields[arm] = np.load(cache)
            continue
        names, mm, keep = extras[arm]
        # memmap views, not materialised copies: 9 layers x 49 MB would otherwise
        # be resident on a 3 GB box (OOM risk observed 2026-10-07).
        cols = [mm[i] for i in keep]
        rng = np.random.default_rng(2000 + fold.index)
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool, 250_000, rng, extra=cols)
        model = fit_detector(X, y, seed=fold.index)
        del X, y
        f = predict_grid(model, stack, stack_footprint, extra=cols)
        if save:
            np.save(cache, f)
        fields[arm] = f
    blend = 0.5 * (fields["HH"] + fields["HD"])
    del fields
    return blend


def variants(blend, fold, allow_s1, cat_known, n_target, price_px):
    """All preregistered emission variants for one fold, at matched mass."""
    in_block = fold.block & stack_footprint
    f2 = em2.catalogue_flank_zone(cat_known, 2.0)
    f3 = em2.catalogue_flank_zone(cat_known, 3.0)
    out = {}
    out["V0_nms2.4_flank2"] = em2.nms_topn(blend, n_target, radius=2.4,
                                           forbid=f2, allow=in_block)
    out["V1_nms2.8_flank2"] = em2.nms_topn(blend, n_target, radius=2.8,
                                           forbid=f2, allow=in_block)
    out["V2_nms2.8_flank3"] = em2.nms_topn(blend, n_target, radius=2.8,
                                           forbid=f3, allow=in_block)
    cos_c, sin_c, sup = em2.axis_from_catalogue(cat_known, sigma_grad=2.0, sigma_int=3.0)
    cos_f, sin_f, sup_f = em2.axis_from_field(blend, sigma_grad=1.0, sigma_int=5.0)
    support = sup | sup_f
    cos_a = np.where(sup, cos_c, cos_f).astype(np.float32)
    sin_a = np.where(sup, sin_c, sin_f).astype(np.float32)
    out["V3_sale_flank3"] = em2.sale_lines(blend, n_target, cos_a, sin_a, forbid=f3,
                                           allow=in_block, line_half=5, spacing=2.4,
                                           seed_sep=6.0, axis_min_strength=support)
    approved = in_block & allow_s1
    out["V4_nms2.8_flank3_s1"] = em2.nms_topn(blend, n_target, radius=2.8,
                                              forbid=f3, allow=approved)
    out["V5_sale_flank3_s1"] = em2.sale_lines(blend, n_target, cos_a, sin_a, forbid=f3,
                                              allow=approved, line_half=5, spacing=2.4,
                                              seed_sep=6.0, axis_min_strength=support)
    return out


def score_variant(ys, xs, fold, n_target):
    pred = em2.rasterise(ys, xs) > 0
    valid = stack_footprint & fold.block
    a = dti_binary(pred, fold.truth, valid=valid, known=fold.known)
    b = dti_binary_live(pred, fold.truth, valid=valid, known=fold.known)
    leak = on_catalogue_mass(pred, fold.known | fold.truth, valid=valid)
    return dict(
        n_emitted=int(pred[valid].sum()), n_target=int(n_target),
        dti_A=float(a["dti"]), dti_B=float(b["dti"]),
        tp=float(a["tp"]), fp=float(a["fp"]), coverage=float(a["coverage"]),
        on_catalogue_px=int(leak["on_catalogue_px"]),
    )


def stage1_alone(fold, deficit_tiles, footprint, n_target, seed):
    """Stage-1 scored alone: uniform random dots inside approved tiles vs whole block."""
    in_block = fold.block & footprint
    excl = ndi.distance_transform_edt(~fold.known) <= 2.0
    big = st1.upsample(deficit_tiles, TILE_PX)
    db = big[in_block]
    finite = np.isfinite(db)
    thr = float(np.nanpercentile(db[finite], STAGE1_Q))
    appr = np.zeros(GRID.shape, bool)
    appr[in_block] = finite & (db >= thr)
    out = {}
    for label, mask in (("uniform_in_approved", appr & ~excl),
                        ("uniform_in_block", in_block & ~excl)):
        yy, xx = np.nonzero(mask)
        rng = np.random.default_rng(seed)
        k = min(int(n_target), yy.size)
        sel = rng.choice(yy.size, size=k, replace=False)
        pred = em2.rasterise(yy[sel], xx[sel]) > 0
        out[label] = dti_binary(pred, fold.truth, valid=footprint & fold.block,
                                known=fold.known)["dti"]
    out["approved_area_share_of_block"] = float(
        appr[in_block].sum() / max(int(in_block.sum()), 1))
    out["approved_area_share_of_footprint"] = float(
        (big >= thr)[footprint & np.isfinite(big)].mean())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--stage1-q", type=float, default=10.0)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--folds", type=int, default=0, help="0 = all")
    ap.add_argument("--from-cache", action="store_true",
                    help="reuse cached per-fold fields (emission comparison only)")
    args = ap.parse_args()

    global stack_footprint, TILE_PX, STAGE1_Q
    TILE_PX, STAGE1_Q = args.tile_px, args.stage1_q
    stack_footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    folds = make_folds(stack_footprint, catalogue, buffer_px=args.buffer,
                       n_rows=args.grid, n_cols=args.grid, min_truth=500)
    if args.folds:
        folds = folds[:args.folds]
    extras = {a: load_extras(a) for a in ("HH", "HD")}
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = st1.load_observed()
    cfg = sb.BudgetConfig(tile_px=args.tile_px)
    trace_y, trace_x, trace_ids = sb.trace_assignments(catalogue, df)

    t0 = time.time()
    rows = []
    for fold in folds:
        n_target = int(round(args.ratio * fold.n_truth))
        in_block = fold.block & stack_footprint
        held = np.unique(trace_ids[fold.block[trace_y, trace_x]])
        s1 = st1.stage1_field(fold.known, stack_footprint,
                              df.loc[~df.index.isin(held)], obs, cfg)
        allow_s1 = st1.approved_mask(s1["deficit"], stack_footprint, args.tile_px, args.stage1_q)
        s1_alone = stage1_alone(fold, s1["deficit"], stack_footprint, n_target,
                                seed=7 + fold.index)

        if args.from_cache:
            blend = 0.5 * (np.load(P / f"h52_field_HH_fold{fold.index}.npy")
                           + np.load(P / f"h52_field_HD_fold{fold.index}.npy"))
        else:
            blend = fold_fields(fold, stack, extras, seed=fold.index, save=True)

        row = dict(fold=int(fold.index), n_truth=int(fold.n_truth), n_target=n_target,
                   held_out_trace_rows=int(held.size), stage1=s1_alone)
        for name, (ys, xs) in variants(blend, fold, allow_s1, fold.known,
                                       n_target, None).items():
            sc = score_variant(ys, xs, fold, n_target)
            if "flank3_s1" in name:
                pred = em2.rasterise(ys, xs) > 0
                inside = int((pred & allow_s1).sum())
                area = float((allow_s1 & in_block).sum() / max(int(in_block.sum()), 1))
                sc["stage1_area_share"] = area
                sc["stage1_emitted_share"] = inside / max(sc["n_emitted"], 1)
                sc["stage1_lift"] = (inside / max(sc["n_emitted"], 1)) / max(area, 1e-9)
            row[name] = sc
        rows.append(row)
        print(f"  fold {row['fold']} truth={row['n_truth']:6d} "
              + "  ".join(f"{k.split('_')[0]}:A={v['dti_A']:.4f}/B={v['dti_B']:.4f}"
                          for k, v in row.items() if isinstance(v, dict) and "dti_A" in v)
              + f"  ({time.time()-t0:.0f}s)", flush=True)

    names = [k for k in rows[0] if isinstance(rows[0][k], dict) and "dti_A" in rows[0][k]]
    summary = {}
    for n in names:
        summary[n] = dict(
            dti_A_mean=float(np.mean([r[n]["dti_A"] for r in rows])),
            dti_A_per_fold=[float(r[n]["dti_A"]) for r in rows],
            dti_B_mean=float(np.mean([r[n]["dti_B"] for r in rows])),
            dti_B_per_fold=[float(r[n]["dti_B"]) for r in rows],
            on_catalogue_px_total=int(sum(r[n]["on_catalogue_px"] for r in rows)),
        )
        if "stage1_lift" in rows[0][n]:
            summary[n]["stage1_lift"] = [float(r[n]["stage1_lift"]) for r in rows]
            summary[n]["stage1_emitted_share"] = [float(r[n]["stage1_emitted_share"]) for r in rows]
    summary["stage1_alone"] = {
        k: float(np.mean([r["stage1"][k] for r in rows]))
        for k in rows[0]["stage1"]}

    # ---- preregistered promotion decision ------------------------------------
    base = np.array(summary["V0_nms2.4_flank2"]["dti_B_per_fold"])
    decision = {"prereg": "registry/preregistration_h52.json"}
    for cand in ("V4_nms2.8_flank3_s1", "V5_sale_flank3_s1"):
        cur = np.array(summary[cand]["dti_B_per_fold"])
        delta = cur - base
        ungated = {"V4_nms2.8_flank3_s1": "V2_nms2.8_flank3",
                   "V5_sale_flank3_s1": "V3_sale_flank3"}[cand]
        cost = np.array(summary[ungated]["dti_B_per_fold"]) - cur
        lift = float(np.mean(summary[cand].get("stage1_lift", [np.nan])))
        decision[cand] = dict(
            mean_delta_vs_V0=float(delta.mean()), folds_positive=int((delta > 0).sum()),
            confined_cost_mean=float(cost.mean()),
            stage1_lift_mean=lift,
            passes_primary=bool(delta.mean() >= 0.0020 and (delta > 0).sum() >= 4),
            passes_secondary=bool(np.isfinite(lift) and lift <= 1.5),
            passes_tertiary=bool(cost.mean() <= 0.0050),
        )
        decision[cand]["PROMOTE"] = bool(decision[cand]["passes_primary"]
                                         and decision[cand]["passes_secondary"]
                                         and decision[cand]["passes_tertiary"])

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = dict(created_utc=utc, config=vars(args), folds=rows,
                   summary=summary, promotion_decision=decision,
                   instrument_note=("Proxy truth is the visible catalogue; the block boundary "
                                    "is unmasked, so the flank rules cannot be validated here. "
                                    "A pass licenses packaging, never a score claim."))
    out = ROOT / "evidence" / f"h52_holdout_{utc}.json"
    out.write_text(json.dumps(receipt, indent=1, default=str))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.endswith("per_fold")}
                      for k, v in summary.items()}, indent=1))
    print(json.dumps(decision, indent=1))
    print(f"wrote {out} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
