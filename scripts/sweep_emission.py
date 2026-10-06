#!/usr/bin/env python3
"""Sweep emission geometry (NMS spacing x mass) on already-computed fold fields.

This re-uses the fields written by ``run_experiments.py --save-fields``, so it
costs no model fitting.  Spacing and mass are the two degrees of freedom the
break-even analysis says matter, and neither is settled by the feature choice.
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

from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H_D")
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--grid", type=int, default=3)
    ap.add_argument("--buffer", type=int, default=12)
    ap.add_argument("--min-truth", type=int, default=500)
    ap.add_argument("--radii", default="1.5,2.4,3.5,5.0,7.0")
    ap.add_argument("--ratios", default="1.5,2.5,3.47,5,7,10")
    ap.add_argument("--excl-radius", type=float, default=2.0)
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    folds = make_folds(footprint, catalogue, buffer_px=a.buffer,
                       n_rows=a.grid, n_cols=a.grid, min_truth=a.min_truth)[:a.folds]
    radii = [float(v) for v in a.radii.split(",")]
    ratios = [float(v) for v in a.ratios.split(",")]

    grid = np.zeros((len(radii), len(ratios)))
    counts = np.zeros((len(radii), len(ratios)))
    per_fold = np.zeros((len(folds), len(radii), len(ratios)))
    t0 = time.time()
    for fi, fold in enumerate(folds):
        fp = P / f"field_{a.arm}_fold{fold.index}.npy"
        if not fp.exists():
            print("missing", fp)
            continue
        field = np.load(fp)
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= a.excl_radius
        for i, rad in enumerate(radii):
            for j, ratio in enumerate(ratios):
                k = int(round(ratio * fold.n_truth))
                ys, xs = nms_dots(field, k, radius=rad,
                                  exclude=excl | ~in_block, valid=footprint)
                r = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                               valid=footprint & fold.block, known=fold.known)
                per_fold[fi, i, j] = r["dti"]
        print(f"  fold {fold.index} done ({time.time()-t0:.0f}s)", flush=True)
        del field

    grid = per_fold.mean(axis=0)
    out = dict(config=vars(a), radii=radii, ratios=ratios,
               mean_dti=grid.tolist(), per_fold=per_fold.tolist())
    (ROOT / "data" / "emission_sweep.json").write_text(json.dumps(out, indent=1))

    print("\nrows = NMS spacing (px), cols = mass ratio M/|G|")
    print("        " + "".join(f"{r:>8g}" for r in ratios))
    for i, rad in enumerate(radii):
        print(f"  {rad:5g} " + "".join(f"{grid[i, j]:8.4f}" for j in range(len(ratios))))
    bi, bj = np.unravel_index(np.argmax(grid), grid.shape)
    print(f"\nbest: spacing {radii[bi]} px, ratio {ratios[bj]}, mean DTI {grid[bi, bj]:.4f}")
    # std of the paired difference vs the reference cell (2.4, 3.47)
    ri = radii.index(2.4) if 2.4 in radii else 0
    rj = ratios.index(3.47) if 3.47 in ratios else 0
    d = per_fold[:, bi, bj] - per_fold[:, ri, rj]
    print(f"paired vs (2.4, 3.47): mean {d.mean():+.4f}  folds positive "
          f"{int((d>0).sum())}/{len(d)}")
    print(f"wrote data/emission_sweep.json ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
