#!/usr/bin/env python3
"""H52-A holdout: does a structural-inheritance prior improve dot placement?

Preregistration: ``registry/preregistration_h52_amendment3.json`` (frozen before
this script ran).  Receipt: ``evidence/h52_tip_holdout_<utc>.json``.

Arms (all at identical emitted mass, identical flank exclusion and identical STE
geometry; only the *score* that STE eats changes):

  B0  field                         (incumbent: the 50/50 H-H/H-D blend)
  B1  field * (1 + kappa * prior)   kappa in the preregistered grid

``prior`` is the structural-inheritance field of ``gems51.tip_model`` painted from
the fold's *training-visible* catalogue only (``fold.train_pos``), so no held-out
pixel can leak into the prior.

Every arm is scored twice, on two instruments:
  * full block (comparable with the repository's historical numbers), and
  * block interior eroded by ``--erode`` px, which removes the block-boundary
    advantage the local instrument is known to give to edge-adjacent extrapolation.

Both scoring readings (A: on-catalogue mass deleted, B: counted as false positive)
are reported for every arm.

Usage
-----
    .venv/bin/python scripts/run_h52_tip_holdout.py [--folds 6] [--kappa 0.5,1,2,4]
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
from gems51 import tip_model as tm           # noqa: E402
from gems51.holdout import make_folds        # noqa: E402
from gems51.live_metric import dti_binary_live  # noqa: E402
from gems51.metric import dti_binary         # noqa: E402

P = ROOT / "data" / "prepared"


def ste_emit(field, k, forbid, allow):
    """The validated STE geometry, unchanged from scripts/evaluate_hh_blend.py."""
    return em2.ste_topn(field, k, forbid=forbid, allow=allow)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--kappa", default="0.5,1.0,2.0,4.0")
    ap.add_argument("--erode", type=int, default=30)
    ap.add_argument("--corridor", type=int, default=40)
    ap.add_argument("--stage1-q", type=float, default=10.0)
    ap.add_argument("--tile-px", type=int, default=100)
    args = ap.parse_args()
    kappas = [float(x) for x in args.kappa.split(",") if x != ""]

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)[:args.folds]
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = st1.load_observed()
    cfg = sb.BudgetConfig(tile_px=args.tile_px)
    trace_y, trace_x, trace_ids = sb.trace_assignments(catalogue, df)

    rows = []
    t0 = time.time()
    for fold in folds:
        field = 0.5 * (np.load(P / f"h52_field_HH_fold{fold.index}.npy")
                       + np.load(P / f"h52_field_HD_fold{fold.index}.npy"))
        in_block = fold.block & footprint
        f2 = em2.catalogue_flank_zone(fold.known, 2.0)
        legal = in_block & ~f2
        k = int(round(args.ratio * fold.n_truth))

        held = np.unique(trace_ids[fold.block[trace_y, trace_x]])
        s1 = st1.stage1_field(fold.known, footprint, df.loc[~df.index.isin(held)], obs, cfg)
        approved = st1.approved_mask(s1["deficit"], footprint, args.tile_px, args.stage1_q)
        prior_res = tm.tip_prior(fold.train_pos, corridor_px=args.corridor,
                                 half_width_px=2.0, tau_px=12.0, bridge_gap_px=40.0,
                                 exclude=f2)
        prior = prior_res["prior"]

        interior = ndi.binary_erosion(fold.block, np.ones((3, 3), bool),
                                      iterations=int(args.erode)) & footprint
        truth_int = fold.truth & interior

        out = {}
        # unconfined reference + the confined arms that the submission actually uses
        arms = [("B0_field", 0.0, False)]
        arms += [(f"B_conf{k:g}" if k > 0 else "B_conf0", k, True) for k in [0.0] + kappas]
        for label, kap, confine in arms:
            score = field if kap == 0 else tm.boosted_score(field, prior, kap)
            allow = legal & approved if confine else legal
            ys, xs = ste_emit(score, k, f2, allow)
            pred = em2.rasterise(ys, xs) > 0
            valid = footprint & fold.block
            a = dti_binary(pred, fold.truth, valid=valid, known=fold.known)
            b = dti_binary_live(pred, fold.truth, valid=valid, known=fold.known)
            ai = dti_binary(pred, truth_int, valid=interior, known=fold.known)
            bi = dti_binary_live(pred, truth_int, valid=interior, known=fold.known)
            in_ap = int((pred & approved).sum())
            in_c = int((pred & (prior > 0.1)).sum())
            out[label] = dict(
                kappa=kap, dti_A=float(a["dti"]), dti_B=float(b["dti"]),
                dti_A_interior=float(ai["dti"]), dti_B_interior=float(bi["dti"]),
                dots=int(pred[valid].sum()), tp=float(a["tp"]), fp=float(a["fp"]),
                dots_in_corridor=in_c, dots_in_corridor_share=in_c / max(int(pred[valid].sum()), 1),
                dots_in_approved_share=in_ap / max(int(pred[valid].sum()), 1),
            )
        # control arms: uniform placement with the same mass (null models)
        rng = np.random.default_rng(9000 + fold.index)
        for cname, cmask in (("U_block", in_block), ("U_approved", in_block & approved)):
            idx = np.flatnonzero(cmask.ravel())
            take = rng.choice(idx, size=min(k, idx.size), replace=False)
            pred = np.zeros(footprint.shape, bool)
            pred.ravel()[take] = True
            pred &= ~f2
            b = dti_binary_live(pred, fold.truth, valid=valid, known=fold.known)
            bi = dti_binary_live(pred, truth_int, valid=interior, known=fold.known)
            out[cname] = dict(kappa=0.0, dti_A=float(dti_binary(pred, fold.truth, valid=valid, known=fold.known)["dti"]),
                              dti_B=float(b["dti"]), dti_A_interior=float(dti_binary(pred, truth_int, valid=interior, known=fold.known)["dti"]),
                              dti_B_interior=float(bi["dti"]), dots=int(pred[valid].sum()),
                              tp=float(b["tp"]), fp=float(b["fp"]), dots_in_corridor=0,
                              dots_in_corridor_share=0.0)

        # how informative is the raw prior about the held-out truth?
        corr = prior > 0.1
        prior_share = float(corr[in_block].mean())
        truth_in_corr = float((corr & fold.truth).sum() / max(int(fold.truth.sum()), 1))
        rows.append(dict(fold=int(fold.index), n_truth=int(fold.n_truth),
                         n_truth_interior=int(truth_int.sum()),
                         n_tips=int(prior_res["tips"]["n_tips"]),
                         n_bridges=int(prior_res["n_bridges"]),
                         prior_share_block=prior_share,
                         truth_share_in_corridor=truth_in_corr,
                         prior_lift=truth_in_corr / max(prior_share, 1e-9),
                         approved_share_of_block=float((approved & in_block).sum()
                                                      / max(int(in_block.sum()), 1)),
                         outputs=out))
        print(f"  fold {fold.index} truth={fold.n_truth} tips={prior_res['tips']['n_tips']} "
              f"bridges={prior_res['n_bridges']}: " + "  ".join(
                  f"{lab}:A={v['dti_A']:.4f}/Ai={v['dti_A_interior']:.4f}"
                  for lab, v in out.items()) + f"  ({time.time() - t0:.0f}s)", flush=True)

    labels = list(rows[0]["outputs"])
    summary = {lab: dict(
        dti_A_mean=float(np.mean([r["outputs"][lab]["dti_A"] for r in rows])),
        dti_B_mean=float(np.mean([r["outputs"][lab]["dti_B"] for r in rows])),
        dti_A_interior_mean=float(np.mean([r["outputs"][lab]["dti_A_interior"] for r in rows])),
        dti_B_interior_mean=float(np.mean([r["outputs"][lab]["dti_B_interior"] for r in rows])),
        dti_B_per_fold=[r["outputs"][lab]["dti_B"] for r in rows],
        corridor_share=[r["outputs"][lab]["dots_in_corridor_share"] for r in rows],
    ) for lab in labels}

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = dict(
        created_utc=utc, prereg="GEMSDOE51-H52-PREREG-1-A3",
        instrument=("six contiguous 3x3 blocks of the visible catalogue, 12 px buffer, "
                    "cached H-H/H-D fold fields, STE geometry, mass 3.47 x n_truth, "
                    "catalogue flank 2 px"), kappas=kappas, erode_px=int(args.erode),
        corridor_px=int(args.corridor), rows=rows, summary=summary,
        note=("Local proxy only; the proxy truth is the visible catalogue. The prior is "
              "painted from fold.train_pos, so it can never see the held-out block."),
    )
    out_path = ROOT / "evidence" / f"h52_tip_holdout_{utc}.json"
    out_path.write_text(json.dumps(receipt, indent=1, default=str))
    print(json.dumps(summary, indent=1))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
