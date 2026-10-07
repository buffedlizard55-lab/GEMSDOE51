#!/usr/bin/env python3
"""Does the distance to the *visible* inventory carry usable placement signal?

Two facts motivate this experiment.

1.  The reported highest-scoring family artifacts are thin dot sets whose median
    distance to the mapped catalogue is ~1.5-2.0 km (measured here from the
    published files), and the best-scoring one removed every dot within 200 m of
    the catalogue.  So the hidden truth is *not* hugging the mapped traces.
2.  In the off-catalogue A/B instrument the pure "halo" control (uniform dots in
    the 2-5 px ring around A) already beats uniform dots over the candidate area
    (fold 0: B_all 0.0959 vs 0.0655, archived run), so *some* of the hidden truth
    does sit near the visible inventory.

This script asks the operational question: if the detector's field is multiplied
by a fixed radial weight in the distance-to-inventory coordinate, does the
hard-instrument DTI improve at matched mass?  The weight family is deliberately
tiny (three Gaussian profiles plus the unweighted control) so that a four-fold
comparison is not a search.

Everything is deterministic; no model is trained; nothing is emitted as a
submission.

Usage::

    python3 scripts/run_ring_profile_ab.py --fields work/fields
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

from gems51.emission import nms_dots, rasterise     # noqa: E402
from gems51.grid import GRID                        # noqa: E402
from gems51.metric import dti_binary                # noqa: E402

P = ROOT / "data" / "prepared"
PROFILES = {"none": (None, None), "ring_3_3": (3.0, 3.0), "ring_8_8": (8.0, 8.0),
            "ring_15_15": (15.0, 15.0)}


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
    ap.add_argument("--folds", default="0,1,2,3")
    ap.add_argument("--grid", type=int, default=2)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--ratios", type=float, nargs="*", default=[2.0, 3.47, 5.0])
    ap.add_argument("--excl", type=float, default=2.0)
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "ring_profile_ab.json"))
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
    # measured distance profile of the hidden systems from the visible inventory
    prof: dict = {}
    for nm, m in (("B_all", B), ("B_far", B_far)):
        d = dA[m]
        prof[nm] = dict(p10=float(np.percentile(d, 10)), p25=float(np.percentile(d, 25)),
                        median=float(np.median(d)), p75=float(np.percentile(d, 75)),
                        p90=float(np.percentile(d, 90)), max=float(d.max()))
        print(f"  d(dA) {nm}: {prof[nm]}", flush=True)

    rows: list[dict] = []
    t0 = time.time()
    for bi in [int(x) for x in args.folds.split(",") if x != ""]:
        fpath = Path(args.fields) / f"field_ab_fold{bi}_static.npy"
        if not fpath.exists():
            continue
        field = np.load(fpath)
        blk = blocks_[bi] & footprint
        truth_all, truth_far = B & blk, B_far & blk
        n_t = int(truth_all.sum())
        dom = footprint & np.isfinite(field)
        cand = blk & dom & (dA >= args.excl)
        for pname, (mu, sigma) in PROFILES.items():
            if mu is None:
                scaled = field
            else:
                w = np.exp(-0.5 * ((dA - mu) / sigma) ** 2).astype(np.float32)
                scaled = (np.nan_to_num(field, nan=0.0) * w).astype(np.float32)
                scaled[~dom] = np.nan
            for ratio in args.ratios:
                n_dots = int(round(ratio * n_t))
                ys, xs = nms_dots(scaled, n_dots, radius=args.nms_radius,
                                  exclude=~cand, valid=dom)
                mask = rasterise(ys, xs) > 0
                rec = dict(fold=bi, profile=pname, ratio=ratio, n_dots=int(mask.sum()))
                for tn, truth in (("all", truth_all), ("far", truth_far)):
                    if int(truth.sum()) == 0:
                        continue
                    r = dti_binary(mask, truth, valid=footprint & blk, known=A)
                    rec[f"dti_{tn}"] = round(float(r["dti"]), 6)
                rows.append(rec)
        print(f"  fold {bi} done ({time.time()-t0:.0f}s)", flush=True)
        del field

    summary = {}
    for pname in PROFILES:
        for ratio in args.ratios:
            va = [r["dti_all"] for r in rows if r["profile"] == pname
                  and r["ratio"] == ratio and "dti_all" in r]
            vf = [r["dti_far"] for r in rows if r["profile"] == pname
                  and r["ratio"] == ratio and "dti_far" in r]
            if va:
                summary[f"{pname}|r{ratio:g}"] = dict(
                    mean_dti_all=float(np.mean(va)),
                    mean_dti_far=float(np.mean(vf)) if vf else None, n=len(va))
    out = dict(script="scripts/run_ring_profile_ab.py", config=vars(args),
               b_distance_profile=prof, rows=rows, summary=summary,
               runtime_s=round(time.time() - t0, 1),
               limitations=["off-catalogue A/B instrument, not a competition score",
                            "B systems are interleaved with A, so the measured distance "
                            "profile is a property of this split, not of the hidden set"])
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n=== mean DTI_all by (radial profile, mass ratio) ===")
    for k, v in sorted(summary.items(), key=lambda kv: -kv[1]["mean_dti_all"]):
        print(f"  {v['mean_dti_all']:.4f}  far={None if v['mean_dti_far'] is None else round(v['mean_dti_far'],4)}  {k}")
    print(f"wrote {args.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
