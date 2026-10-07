#!/usr/bin/env python3
"""Evaluate the pre-declared conservative H-H/H-D field blend.

This is a detector-stability follow-up, not a new geological label.  It uses
saved, fold-matched H-D and H-H fields, a fixed 50/50 probability blend, and
emits the exact previously screened STE L9 geometry at M/|G|=3.47.  Both the
isotropic NMS and STE outputs are reported.  The visible catalogue remains a
proxy truth; this script never authorizes a competition slot.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import trace_emission as te  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def ste_emit(field: np.ndarray, candidate: np.ndarray, n_dots: int) -> tuple[np.ndarray, np.ndarray]:
    dom = np.isfinite(field) & candidate
    f0 = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    response = np.zeros(f0.shape, np.float32)
    for sigma in (1.0, 2.0, 3.5):
        ridge, _ = te.ridge_response(f0, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = te._rank01(f0, dom)
    acc, _ = te.line_accumulate(response, length=9, n_orient=12)
    acc_rank = te._rank01(acc, dom)
    score = (raw_rank ** 0.65) * (acc_rank ** 0.35)
    return te.spaced_dots(score.astype(np.float32), dom, n_dots, spacing=2.4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weight-hh", type=float, default=0.5,
                    help="fixed H-H contribution; default is the pre-declared 50/50 blend")
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "hh_blend_holdout.json"))
    args = ap.parse_args()
    if not 0.0 <= args.weight_hh <= 1.0:
        raise SystemExit("--weight-hh must be in [0,1]")

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    rows = []
    for fold in folds:
        h_d = np.load(P / f"field_H_D_fold{fold.index}.npy")
        h_h = np.load(P / f"field_H_H_fold{fold.index}.npy")
        field = ((1.0 - args.weight_hh) * h_d + args.weight_hh * h_h).astype(np.float32)
        in_block = fold.block & footprint
        excl = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed = in_block & ~excl & np.isfinite(field)
        k = int(round(args.ratio * fold.n_truth))
        outputs = {}
        for name in ("nms", "ste"):
            if name == "nms":
                ys, xs = nms_dots(field, k, radius=2.4,
                                  exclude=~allowed, valid=footprint)
            else:
                ys, xs = ste_emit(field, allowed, k)
            result = dti_binary(rasterise(ys, xs) > 0, fold.truth,
                                 valid=footprint & fold.block, known=fold.known)
            outputs[name] = dict(dti=float(result["dti"]), dots=int(len(ys)),
                                 tp=float(result["tp"]), fp=float(result["fp"]))
        rows.append(dict(fold=fold.index, n_truth=fold.n_truth, outputs=outputs))
        print(f"fold {fold.index}: NMS={outputs['nms']['dti']:.6f} "
              f"STE={outputs['ste']['dti']:.6f}", flush=True)

    summary = {}
    for name in ("nms", "ste"):
        values = [r["outputs"][name]["dti"] for r in rows]
        summary[name] = dict(mean=float(np.mean(values)), per_fold=values)
    out = dict(
        instrument="six-fold spatial holdout; visible known-fault proxy truth",
        comparator="H-D and H-H fields are fold-matched; only a fixed 50/50 field blend and fixed STE L9 emission are evaluated",
        config=vars(args), per_fold=rows, summary=summary,
        limitations=["not a hidden-test score", "no competition slot authorized", "blend is not a new geology claim"],
    )
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
