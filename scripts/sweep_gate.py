#!/usr/bin/env python3
"""Hard gate versus soft prior: sweep the Stage-1 weight on the Stage-2 field.

The hard gate (emit only inside approved tiles) is the design the brief asks for.
It is measured here alongside a soft multiplicative prior

    score = field * (1 + w * z),   z = (deficit_q - mean) / std

so that the weight can be chosen on the holdout rather than asserted.  w = 0
recovers the ungated Stage-2 model, which is the number the gate has to beat.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def load_observed():
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        a = s.read(descs.index("geod_2ndinv") + 1).astype(np.float64)
        a[a <= -1e38] = np.nan
        return a


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H_D")
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--ratios", default="3.47")
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--weights", default="0,0.05,0.1,0.2,0.4,0.8")
    ap.add_argument("--hard-q", default="70,90")
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()
    cfg = sb.BudgetConfig(tile_px=a.tile_px)
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)[:a.folds]
    trace_y, trace_x, trace_ids = sb.trace_assignments(catalogue, df)
    weights = [float(v) for v in a.weights.split(",")]
    hard_q = [float(v) for v in a.hard_q.split(",")]
    ratios = [float(v) for v in a.ratios.split(",")]

    res = {w: [] for w in weights}
    res_hard = {q: [] for q in hard_q}
    stage1_trace_rows = []
    t0 = time.time()
    for fold in folds:
        fp = P / f"field_{a.arm}_fold{fold.index}.npy"
        if not fp.exists():
            continue
        field = np.load(fp)
        held = np.unique(trace_ids[fold.block[trace_y, trace_x]])
        df_budget = df.loc[~df.index.isin(held)]
        stage1_trace_rows.append(dict(fold=int(fold.index), held_out=int(len(held)),
                                      budget_rows=int(len(df_budget))))
        exx, eyy, exy, lent, npix, asg, mom, tsh, meta = sb.kostrov_tiles(
            fold.known, df_budget, cfg, area_mask=footprint)
        II_f = sb.invariant(exx, eyy, exy, "II")
        obsII = sb.observed_tiles(obs, footprint, a.tile_px)
        dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, a.tile_px)
        ok_t = np.isfinite(dom) & (dom > 0.05)
        deficit = (sb.quantile_map(np.where(ok_t, obsII, np.nan))
                   - sb.quantile_map(np.where(ok_t, II_f, np.nan)))
        big = upsample(deficit, a.tile_px)
        v = big[footprint & np.isfinite(big)]
        z = (big - v.mean()) / max(v.std(), 1e-9)
        z = np.clip(z, -4.0, 4.0)

        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= a.excl_radius
        for ratio in ratios:
            k = int(round(ratio * fold.n_truth))
            for w in weights:
                sc = field * (1.0 + w * z) if w else field
                ys, xs = nms_dots(sc, k, radius=a.nms_radius,
                                  exclude=excl | ~in_block, valid=footprint)
                r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                               valid=footprint & fold.block, known=fold.known)
                res[w].append(r["dti"])
            for q in hard_q:
                thr = np.nanpercentile(v, q)
                appr = np.zeros(GRID.shape, bool)
                appr[footprint] = np.isfinite(big[footprint]) & (big[footprint] >= thr)
                ys, xs = nms_dots(field, k, radius=a.nms_radius,
                                  exclude=excl | ~in_block | ~appr, valid=footprint)
                r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                               valid=footprint & fold.block, known=fold.known)
                res_hard[q].append(r["dti"])
        print(f"  fold {fold.index} ({time.time()-t0:.0f}s)", flush=True)
        del field

    out = {"config": vars(a), "stage1_trace_rows": stage1_trace_rows,
           "soft": {str(w): dict(mean=float(np.mean(v)), per_fold=[float(x) for x in v])
                    for w, v in res.items()},
           "hard": {str(q): dict(mean=float(np.mean(v)), per_fold=[float(x) for x in v])
                    for q, v in res_hard.items()}}
    (ROOT / "data" / "gate_sweep.json").write_text(json.dumps(out, indent=1))
    base = res[0.0]
    print("\nsoft prior weight w -> mean DTI (paired vs w=0)")
    for w in weights:
        d = np.array(res[w]) - np.array(base)
        print(f"  w={w:<5g} {np.mean(res[w]):.4f}   paired {d.mean():+.4f}  "
              f"folds positive {int((d > 0).sum())}/{len(d)}")
    print("\nhard gate: approve top (100-q)% of tiles")
    for q in hard_q:
        d = np.array(res_hard[q]) - np.array(base)
        print(f"  q={q:<5g} {np.mean(res_hard[q]):.4f}   paired {d.mean():+.4f}  "
              f"folds positive {int((d > 0).sum())}/{len(d)}")
    print(f"wrote data/gate_sweep.json ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
