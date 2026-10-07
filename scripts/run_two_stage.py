#!/usr/bin/env python3
"""Two-stage evaluation: Stage 1 tile prior, Stage 2 fine-scale model, separately scored.

Stage 1 is scored on its own, with no Stage 2 involvement: dots are thrown down
**uniformly at random** inside the approved tiles and the DTI is compared with
dots thrown uniformly at random over the whole held-out block.  That isolates
the prior.  Stage 2 is then scored twice, gated and ungated, at identical mass.

Usage:
    python scripts/run_two_stage.py --fields data/prepared/field_base_fold{}.npy
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def load_observed(tile_px: int):
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        out = {}
        for nm in ["geod_2ndinv", "geod_shearrate", "geod_dilaterate"]:
            a = s.read(descs.index(nm) + 1).astype(np.float64)
            a[a <= -1e38] = np.nan
            out[nm] = a
    return out


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    nt_y, nt_x = tiles.shape
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def stage1_field(catalogue_known: np.ndarray, footprint: np.ndarray, df, obs,
                 cfg: sb.BudgetConfig):
    """Exploratory rank residual Q(observed II) - Q(fault tensor II), per tile.

    The dilatation and shear layers are returned only as separate observed-rank
    diagnostics. They are NOT subtracted from the fault II: that would compare
    different tensor quantities until their definitions and units are verified.
    """
    exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
        catalogue_known, df, cfg, area_mask=footprint)
    II_f = sb.invariant(exx, eyy, exy, "II")
    obsII = sb.observed_tiles(obs["geod_2ndinv"], footprint, cfg.tile_px)
    obsDIL = sb.observed_tiles(obs["geod_dilaterate"], footprint, cfg.tile_px)
    obsSH = sb.observed_tiles(obs["geod_shearrate"], footprint, cfg.tile_px)

    # Restrict ranks to tiles with valid footprint area. Rank-space differences
    # are a scale-free heuristic, not an absolute physical strain subtraction.
    dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, cfg.tile_px)
    ok_t = np.isfinite(dom) & (dom > 0.05)
    q_f = sb.quantile_map(np.where(ok_t, II_f, np.nan))
    q_o = sb.quantile_map(np.where(ok_t, obsII, np.nan))
    deficit = q_o - q_f
    return dict(deficit=deficit,
                dilatation_rank=sb.quantile_map(np.where(ok_t, obsDIL, np.nan)),
                shear_rank=sb.quantile_map(np.where(ok_t, obsSH, np.nan)),
                II_fault=II_f, II_obs=obsII, trace_len=lent, ok_tiles=ok_t, meta=meta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--min-truth", type=int, default=500)
    ap.add_argument("--limit-folds", type=int, default=0)
    ap.add_argument("--thresholds", default="50,60,70,80")
    ap.add_argument("--ratios", default="3.47")
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--fields", default="")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rate-convention", choices=("vertical", "fault_plane"),
                    default="vertical", help="Interpret source rate as vertical or total fault-plane slip")
    ap.add_argument("--assume-unknown-normal", action=argparse.BooleanOptionalAction,
                    default=True, help="Use explicit normal-fault fallback for unknown slip sense")
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed(a.tile_px)
    folds = make_folds(footprint, catalogue, buffer_px=a.buffer,
                       n_rows=a.grid, n_cols=a.grid, min_truth=a.min_truth)
    if a.limit_folds:
        folds = folds[:a.limit_folds]
    cfg = sb.BudgetConfig(tile_px=a.tile_px,
                          rate_convention=a.rate_convention,
                          assume_unknown_normal=a.assume_unknown_normal)
    thresholds = [float(t) for t in a.thresholds.split(",")]
    ratios = [float(r) for r in a.ratios.split(",")]
    # Trace assignments are label-only bookkeeping. Each held-out spatial block
    # drops every linked attribute row from its budget before the prior is built.
    trace_y, trace_x, trace_ids = sb.trace_assignments(catalogue, df)

    rows = []
    t0 = time.time()
    for fold in folds:
        in_held_block = fold.block[trace_y, trace_x]
        held_trace_ids = np.unique(trace_ids[in_held_block])
        df_budget = df.loc[~df.index.isin(held_trace_ids)]
        s1 = stage1_field(fold.known, footprint, df_budget, obs, cfg)
        def_big = upsample(s1["deficit"], a.tile_px)
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= a.excl_radius

        row = dict(fold=fold.index, n_truth=fold.n_truth,
                   budget_trace_rows=int(len(df_budget)),
                   held_out_trace_rows=int(len(held_trace_ids)))
        # ---- how much of the held-out truth sits in the top-q tiles? --------
        db = def_big[in_block]
        tb = fold.truth[in_block]
        finite = np.isfinite(db)
        for q in thresholds:
            thr = np.nanpercentile(db[finite], q)
            appr = finite & (db >= thr)
            row[f"recall_q{q}"] = float(tb[appr].sum() / max(tb.sum(), 1))
            row[f"area_q{q}"] = float(appr.sum() / max(finite.sum(), 1))
        # tile-level rank correlation between the deficit and held-out fault density
        tl_truth = sb.observed_tiles(fold.truth.astype(np.float64), footprint, a.tile_px)
        ok = s1["ok_tiles"] & np.isfinite(tl_truth)
        row["spearman_deficit_vs_heldout"] = float(
            spearmanr(s1["deficit"][ok], tl_truth[ok]).statistic) if ok.sum() > 5 else float("nan")

        # ---- Stage 1 ALONE: uniform random dots inside approved tiles -------
        for q in thresholds:
            thr = np.nanpercentile(db[finite], q)
            appr = finite & (db >= thr)
            for ratio in ratios:
                k = int(round(ratio * fold.n_truth))
                ys = np.zeros(k, np.int32)
                # random placement inside the approved part of the block
                cand = np.zeros(GRID.shape, bool)
                tmp = np.zeros(GRID.shape, bool)
                tmp[in_block] = appr
                cand = tmp & ~excl
                yy, xx = np.nonzero(cand)
                sel = np.random.default_rng(a.seed + fold.index).choice(
                    yy.size, size=min(k, yy.size), replace=False)
                pred = rasterise(yy[sel], xx[sel])
                r = dti_binary(pred > 0, fold.truth, valid=footprint & fold.block,
                               known=fold.known)
                row[f"s1_dti_q{q}_r{ratio}"] = r["dti"]
        # uniform over the whole block (no gate) -- the control for Stage 1
        yy, xx = np.nonzero(in_block & ~excl)
        for ratio in ratios:
            k = int(round(ratio * fold.n_truth))
            sel = np.random.default_rng(a.seed + fold.index).choice(
                yy.size, size=min(k, yy.size), replace=False)
            pred = rasterise(yy[sel], xx[sel])
            r = dti_binary(pred > 0, fold.truth, valid=footprint & fold.block,
                           known=fold.known)
            row[f"s1_dti_uniform_r{ratio}"] = r["dti"]

        # ---- Stage 2, gated vs ungated --------------------------------------
        if a.fields:
            fp = a.fields.format(fold.index)
            field = np.load(fp) if Path(fp).exists() else None
            if field is None:
                print(f"  (no field {fp})", flush=True)
            else:
                for ratio in ratios:
                    k = int(round(ratio * fold.n_truth))
                    # ungated
                    ys, xs = nms_dots(field, k, radius=a.nms_radius,
                                      exclude=excl | ~in_block, valid=footprint)
                    r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                                   valid=footprint & fold.block, known=fold.known)
                    row[f"s2_ungated_r{ratio}"] = r["dti"]
                    for q in thresholds:
                        thr = np.nanpercentile(db[finite], q)
                        tmp = np.zeros(GRID.shape, bool)
                        tmp[in_block] = finite & (db >= thr)
                        ys, xs = nms_dots(field, k, radius=a.nms_radius,
                                          exclude=excl | ~in_block | ~tmp,
                                          valid=footprint)
                        r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                                       valid=footprint & fold.block, known=fold.known)
                        row[f"s2_gated_q{q}_r{ratio}"] = r["dti"]
        print(f"  fold {fold.index:2d} "
              + "  ".join(f"q{q}:recall={row[f'recall_q{q}']:.3f}/area={row[f'area_q{q}']:.3f}"
                          for q in thresholds)
              + f"  rho={row['spearman_deficit_vs_heldout']:.3f}"
              + f"  ({time.time()-t0:.0f}s)", flush=True)
        rows.append(row)

    out = {}
    for key in rows[0]:
        v = [r[key] for r in rows if key in r]
        if v and isinstance(v[0], (int, float, np.floating)):
            out[key] = dict(mean=float(np.mean(v)), per_fold=[float(x) for x in v])
    p = ROOT / "data" / "two_stage_results.json"
    p.write_text(json.dumps(dict(config=vars(a), per_fold=rows, summary=out), indent=1))
    print(json.dumps(out, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
