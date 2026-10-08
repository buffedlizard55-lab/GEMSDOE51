#!/usr/bin/env python3
"""Preregistered H53 holdout: top candidate H53-A + H53-F operating-point sweep.

Frozen protocol: ``registry/preregistration_h53sr_20261008.json`` and
``evidence/candidate_hypotheses_prereg_h53sr_20261008.json`` (both written before this
script ran for the first time).  Receipt: ``evidence/h53sr_holdout_20261008.json``.

This script NEVER writes a submission TIFF and never consumes a competition
slot.  It re-fits, per fold of the frozen six-fold spatially blocked holdout:

  * H-D  arm  (base stack + facecoh extras)            -> cached field_H_D_fold{i}
  * H-H  arm  (base stack + facecoh + hh_ extras)      -> cached field_H_H_fold{i}
  * H-H+H53-A arm (H-H extras + 6 fine-scale strain-residual ridge features)

and scores, at matched mass M/|G| = 3.47 with the frozen STE L9/w=0.35/
spacing 2.4 emission and 2.0 px catalogue flank:

  * the fresh H-H/H-D 50/50 blend, ungated and inside the fold-specific q10
    Stage-1 approved tiles (the exact geometry the submission build uses);
  * the H53-A candidate blend (0.5 H-D + 0.5 (H-H+H53-A)), ungated and gated;
  * the H53-F operating-point sweep on the fresh blend: ratio {2.96, 3.47} x
    flank {2.0, 2.24} px, gated.

Promotion rule (frozen): the fresh ungated baseline must reproduce the frozen
mean 0.285340602656319 within 1e-5; the H53-A q10-gated mean must exceed the
frozen best; the paired q10-gated delta must be positive in >= 4/6 folds; every
candidate point must lie inside the approved tiles; approved area >= 2/3 and
Stage-1 lift <= 1.5.  The H53-F adoption rule: a non-default operating point is
adopted only if it beats the (3.47, 2.0) gated mean by >= +0.0020 with >= 4/6
folds positive.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from gems51.detector import Stack  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.strain_residual import h53a_features, feature_names  # noqa: E402
from scripts.evaluate_hk1_holdout import (  # noqa: E402
    _fit_fold_field,
    _load_stage1_inputs,
    _score_field,
    _stage1_q10_approved,
)

P = ROOT / "data" / "prepared"
OUT = ROOT / "evidence" / "h53_holdout_20261008.json"
FROZEN_BASELINE = 0.285340602656319
TOLERANCE = 1e-5
FROZEN_FOLDS = [0.28358474213082796, 0.27178387428750844, 0.29027025890966246,
                0.24335930706370568, 0.30504916677291494, 0.3179962667732945]

# H53-F sweep grid (ratio x catalogue flank in px).
SWEEP = [(3.47, 2.0), (3.47, 2.24), (2.96, 2.0), (2.96, 2.24)]


def _load_extra_arrays(names, mm, indices):
    return [np.asarray(mm[i], dtype=np.float32) for i in indices]


def main() -> int:
    if OUT.exists():
        existing = json.loads(OUT.read_text())
        if existing.get("status") in ("COMPLETE", "COMPLETE_NOT_PROMOTED"):
            raise SystemExit(
                "H53 holdout is a completed fixed experiment; do not rerun to shop "
                "for a passing result")
    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected the frozen six folds; found {len(folds)}")

    names = json.loads((P / "extras_static_names.json").read_text())
    mm = np.memmap(P / "extras_static.dat", dtype=np.float32, mode="r",
                   shape=(len(names), *GRID.shape))
    hd_ix = [i for i, n in enumerate(names) if "facecoh" in n]
    hh_ix = [i for i, n in enumerate(names)
             if "facecoh" in n or n.startswith("hh_")]
    if not hd_ix or not hh_ix:
        raise SystemExit("H-D/H-H extras selection mismatch")

    df, assignments, observations = _load_stage1_inputs(footprint, catalogue)
    h53a_names = feature_names()
    rows = []
    for fold in folds:
        # ---- fields (cached; identical protocol to the frozen receipts) ----
        cache_hd = P / f"field_H_D_fold{fold.index}.npy"
        cache_hh = P / f"field_H_H_fold{fold.index}.npy"
        cache_h53 = P / f"h53_field_HH_h53a_fold{fold.index}.npy"
        cache_feat = P / f"h53a_fold{fold.index}.npy"
        if cache_hd.is_file():
            field_hd = np.load(cache_hd)
        else:
            field_hd = _fit_fold_field(stack, footprint, fold,
                                       _load_extra_arrays(names, mm, hd_ix))
            np.save(cache_hd, field_hd)
        if cache_hh.is_file():
            field_hh = np.load(cache_hh)
        else:
            field_hh = _fit_fold_field(stack, footprint, fold,
                                       _load_extra_arrays(names, mm, hh_ix))
            np.save(cache_hh, field_hh)
        if cache_feat.is_file():
            feat = np.load(cache_feat)
        else:
            ys, xs, trace_ids = assignments
            held_rows = np.unique(trace_ids[fold.truth[ys, xs]])
            df_budget = df.loc[~df.index.isin(held_rows)]
            g = h53a_features(fold.known, footprint, df_budget, observations)
            feat = np.stack([g[n] for n in h53a_names]).astype(np.float32)
            np.save(cache_feat, feat)
        if cache_h53.is_file():
            field_h53 = np.load(cache_h53)
        else:
            cols = _load_extra_arrays(names, mm, hh_ix) + [feat[i] for i in
                                                          range(feat.shape[0])]
            field_h53 = _fit_fold_field(stack, footprint, fold, cols)
            np.save(cache_h53, field_h53)
        base_field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                      + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
        cand_field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                      + 0.5 * np.nan_to_num(field_h53, nan=0.0)).astype(np.float32)
        del field_hd, field_hh, field_h53, feat

        # ---- frozen Stage-1 q10 allowed domain (leakage-safe) -------------
        approved, s1 = _stage1_q10_approved(footprint, fold, df, assignments,
                                            observations)
        in_block = fold.block & footprint
        excl2 = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed_ungated = in_block & ~excl2
        allowed_gated = allowed_ungated & approved
        k = int(round(3.47 * fold.n_truth))

        base_ungated = _score_field(base_field, allowed_ungated, k, fold, footprint)
        base_gated = _score_field(base_field, allowed_gated, k, fold, footprint)
        cand_ungated = _score_field(cand_field, allowed_ungated, k, fold, footprint)
        cand_gated = _score_field(cand_field, allowed_gated, k, fold, footprint)
        if cand_gated["dots"] != k:
            raise SystemExit(f"fold {fold.index}: q10 gate cannot supply the budget")
        if cand_gated["emitted_inside_allowed"] != cand_gated["dots"]:
            raise SystemExit(f"fold {fold.index}: a candidate point escaped the "
                             "approved Stage-1 tiles")

        # ---- H53-F operating-point sweep on the fresh blend ---------------
        sweep = {}
        for ratio, flank in SWEEP:
            if ratio == 3.47 and flank == 2.0:
                sweep["r3.47_f2.00"] = base_gated  # identical arm, reuse
                continue
            excl = ndi.distance_transform_edt(~fold.known) <= flank
            allowed = in_block & ~excl & approved
            kk = int(round(ratio * fold.n_truth))
            sweep[f"r{ratio:g}_f{flank:g}"] = _score_field(
                base_field, allowed, kk, fold, footprint)

        # ---- uniform-fill controls (Stage 2 must beat the tiles alone) -----
        from gems51.emission import rasterise
        from gems51.metric import dti_binary
        uniform = {}
        for label, mask in (("U_q10", allowed_gated),
                            ("U_block", allowed_ungated)):
            yy, xx = np.nonzero(mask)
            rng = np.random.default_rng(7 + fold.index)
            sel = rng.choice(yy.size, size=min(k, yy.size), replace=False)
            pred = rasterise(yy[sel], xx[sel]) > 0
            r = dti_binary(pred, fold.truth, valid=footprint & fold.block,
                           known=fold.known)
            uniform[label] = dict(dti=float(r["dti"]), dots=int(pred.sum()))

        emitted_share = 1.0
        lift = emitted_share / max(s1["approved_area_share"], 1e-12)
        rows.append(dict(
            fold=int(fold.index), n_truth=int(fold.n_truth), n_dots=k,
            frozen_hh_hd_ste_dti=FROZEN_FOLDS[fold.index],
            stage1_q10=s1,
            outputs=dict(
                fresh_hd_hh_blend_ungated=base_ungated,
                fresh_hd_hh_blend_stage1_q10=base_gated,
                h53a_blend_ungated=cand_ungated,
                h53a_blend_stage1_q10=cand_gated,
            ),
            h53f_sweep={kk: {"dti": v["dti"], "dots": v["dots"],
                             "ratio": float(kk.split("_")[0][1:]),
                             "flank_px": float(kk.split("_")[1][1:])}
                        for kk, v in sweep.items()},
            uniform_controls=uniform,
            candidate_stage1=dict(emitted_share_inside_approved=emitted_share,
                                  lift_over_area_share=lift),
        ))
        del base_field, cand_field
        print(f"fold {fold.index}: base_ungated={base_ungated['dti']:.6f} "
              f"base_q10={base_gated['dti']:.6f} cand_ungated={cand_ungated['dti']:.6f} "
              f"cand_q10={cand_gated['dti']:.6f} "
              f"sweep=" + " ".join(f"{kk}:{v['dti']:.6f}" for kk, v in sweep.items())
              + f" ({time.time()-t0:.0f}s)", flush=True)
        # checkpoint after every fold so a recycle never loses the run
        OUT.write_text(json.dumps(dict(status="INCOMPLETE_NOT_FOR_SUBMISSION",
                                        rows=rows), indent=1) + "\n")

    base_u = np.array([r["outputs"]["fresh_hd_hh_blend_ungated"]["dti"] for r in rows])
    base_g = np.array([r["outputs"]["fresh_hd_hh_blend_stage1_q10"]["dti"] for r in rows])
    cand_u = np.array([r["outputs"]["h53a_blend_ungated"]["dti"] for r in rows])
    cand_g = np.array([r["outputs"]["h53a_blend_stage1_q10"]["dti"] for r in rows])
    deltas = cand_g - base_g
    repro_err = float(base_u.mean() - FROZEN_BASELINE)
    repro_max_dev = float(np.max(np.abs(base_u - np.array(FROZEN_FOLDS))))
    reproduced = abs(repro_err) <= TOLERANCE
    improves = int((deltas > 0).sum())
    approved_share = float(np.mean([r["stage1_q10"]["approved_area_share"] for r in rows]))
    lift = 1.0 / max(approved_share, 1e-12)
    confined = all(r["candidate_stage1"]["emitted_share_inside_approved"] == 1.0
                   for r in rows)
    non_dominant = bool(approved_share >= 2.0 / 3.0 and lift <= 1.5 and confined)
    gates = {
        "six_folds": len(rows) == 6,
        "baseline_reproduced_within_1e5": reproduced,
        "beats_frozen_best": bool(cand_g.mean() > FROZEN_BASELINE),
        "paired_delta_positive": bool(deltas.mean() > 0.0),
        "positive_folds_ge_4_of_6": improves >= 4,
        "all_points_inside_q10": confined,
        "stage1_broad_and_non_dominant": non_dominant,
    }
    promoted = all(gates.values())

    # ---- H53-F adoption decision ----------------------------------------
    sweep_means = {}
    for arm in rows[0]["h53f_sweep"]:
        sweep_means[arm] = float(np.mean([r["h53f_sweep"][arm]["dti"] for r in rows]))
    default_arm = "r3.47_f2.00"
    f_decision = {"default_arm": default_arm,
                  "default_mean": sweep_means[default_arm],
                  "sweep_means": sweep_means,
                  "adopted_arm": default_arm,
                  "adopted_mean": sweep_means[default_arm]}
    for arm, mean in sweep_means.items():
        if arm == default_arm:
            continue
        per_fold = np.array([r["h53f_sweep"][arm]["dti"] for r in rows])
        pos = int((per_fold > base_g).sum())
        if mean - sweep_means[default_arm] >= 0.0020 and pos >= 4:
            f_decision["adopted_arm"] = arm
            f_decision["adopted_mean"] = mean
            f_decision["adopted_folds_positive"] = pos
            break
    f_decision["rule"] = ("adopt a non-default point only if it beats the "
                          "(3.47, 2.0) gated mean by >= +0.0020 with >= 4/6 folds")
    if f_decision["adopted_arm"] == default_arm:
        f_decision["note"] = ("no non-default point met the adoption bar; the "
                              "build keeps ratio 3.47, flank 2.0 px")

    # ---- uniform-fill controls (Stage-2 dominance evidence) ------------------
    u_q10 = float(np.mean([r["uniform_controls"]["U_q10"]["dti"] for r in rows]))
    u_block = float(np.mean([r["uniform_controls"]["U_block"]["dti"] for r in rows]))
    built_arm_mean = float(cand_g.mean()) if promoted else float(base_g.mean())
    uniform_control = dict(
        candidate_mean=built_arm_mean,
        uniform_mean=u_q10,
        uniform_block_mean=u_block,
        margin=0.0020,
        passed=bool(built_arm_mean - u_q10 >= 0.0020),
        note=("the fine model must beat a uniform random fill of the same approved "
              "tiles at the same mass; this is the dominance control for the "
              "'not dominated by stage one' requirement"),
    )

    receipt = dict(
        schema_version=1,
        status="COMPLETE" if promoted else "COMPLETE_NOT_PROMOTED",
        candidate="H53-A fine-scale geodetic strain-residual ridge features added to the H-H arm",
        preregistration="registry/preregistration_h53sr_20261008.json",
        slate="evidence/candidate_hypotheses_prereg_h53sr_20261008.json",
        instrument="six-fold 3x3 spatial holdout; visible known-fault catalogue proxy truth",
        protocol=dict(
            buffer_px=12, negative_samples=250000, negative_seed="1000 + fold.index",
            model_seed="fold.index", max_iter=250, mass_ratio=3.47,
            blend_baseline="0.5 * fresh H-D + 0.5 * fresh H-H",
            blend_candidate="0.5 * fresh H-D + 0.5 * (fresh H-H + 6 H53-A features)",
            emission="STE ridge scales 1/2/3.5 px, line length 9, continuity exponent 0.35, greedy spacing 2.4 px, catalogue flank 2.0 px",
            candidate_features=h53a_names,
            candidate_feature_source="rank-space residual q(observed 2.5 km tile mean) - q(fault tensor II 2.5 km tile) per geodetic band, smoothed sigma=4 px, crest response at sigma 1.5/4.0 px (src/gems51/strain_residual.py)",
            stage1_gate=dict(field="q10 geodetic second-invariant deficit over 10 km tiles",
                             fold_specific_known_catalogue="yes; held-out trace rows removed",
                             all_stage2_points_confined_to_approved_tiles=True),
            spatial_truth="held-out block only; known-trace exclusion radius 2 px",
        ),
        baseline=dict(
            frozen_mean_dti=FROZEN_BASELINE,
            frozen_per_fold=FROZEN_FOLDS,
            fresh_ungated_mean_dti=float(base_u.mean()),
            fresh_ungated_per_fold=[float(x) for x in base_u],
            fresh_minus_frozen_mean=repro_err,
            fresh_max_abs_dev_vs_frozen=float(repro_max_dev),
            reproduction_tolerance=TOLERANCE,
            reproduced=reproduced,
            stage1_q10_gated_mean_dti=float(base_g.mean()),
            stage1_q10_gated_per_fold=[float(x) for x in base_g],
        ),
        stage1_holdout=dict(
            separately_evaluated=True,
            trace_split_evidence="evidence/stage1_q10_trace_holdout_20261007.json",
            trace_holdout_deficit_q10_dti=0.05062738717100875,
            trace_holdout_uniform_dti=0.04856426582063665,
            trace_holdout_deficit_q10_lift=1.0591471679793076,
            spatial_fold_mean_approved_area_share=approved_share,
            spatial_fold_mean_lift_if_all_points_approved=lift,
            stage1_score_weight=0.0,
        ),
        candidate_result=dict(
            ungated_mean_dti=float(cand_u.mean()),
            ungated_per_fold=[float(x) for x in cand_u],
            stage1_q10_gated_mean_dti=float(cand_g.mean()),
            stage1_q10_gated_per_fold=[float(x) for x in cand_g],
            paired_deltas_vs_stage1_gated_hd_hh=[float(x) for x in deltas],
            paired_mean_delta_vs_stage1_gated_hd_hh=float(deltas.mean()),
            positive_folds_vs_stage1_gated_hd_hh=improves,
        ),
        h53f_operating_point=dict(
            config="sweep on the fresh H-H/H-D blend, q10-gated, STE emission",
            arms={arm: {"mean_dti": sweep_means[arm],
                        "per_fold": [float(r["h53f_sweep"][arm]["dti"]) for r in rows],
                        "ratio": float(arm.split("_")[0][1:]),
                        "flank_px": float(arm.split("_")[1][1:])}
                  for arm in sweep_means},
            decision=f_decision,
        ),
        stage1_non_dominance=dict(
            gate="fold-specific q10 broad-tile deficit mask; score weight 0.0",
            approved_area_share_mean=approved_share,
            expected_emitted_share_inside_approved=1.0,
            lift_over_area_share=lift,
            maximum_allowed_lift=1.5,
            passed=non_dominant,
            uniform_control=uniform_control,
        ),
        promotion_rule=("fresh ungated baseline reproduces frozen mean within 1e-5; "
                        "candidate q10-gated mean > frozen best 0.285340602656319; "
                        "paired q10-gated delta > 0 with >= 4/6 folds; 100% of "
                        "points inside approved tiles; approved area >= 2/3 and "
                        "Stage-1 lift <= 1.5"),
        gates=gates,
        promoted=promoted,
        rows=rows,
        slot_used=False,
        limitations=[
            "The known-fault catalogue is not the hidden expert truth; this is only a local ranking proxy.",
            "The holdout does not establish organizer score, artifact acceptance, or value for geothermal vents.",
            "The six folds have been reused across many hypotheses; no independent lockbox exists.",
            "The strain residual is computed in rank space; source units/component remain provisional (IR-51-12).",
            "H53-F's mass ratio rests on the planning |G| = 12,700 estimate, which is inferred from owner-reported sibling scores, not an organizer count.",
            "A failed H53-A never produces a TIFF and never consumes a competition slot.",
        ],
    )
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(dict(
        fresh_ungated_baseline_mean=float(base_u.mean()),
        frozen_mean=FROZEN_BASELINE,
        baseline_reproduced=reproduced,
        baseline_max_abs_dev=float(repro_max_dev),
        gated_baseline_mean=float(base_g.mean()),
        candidate_gated_mean=float(cand_g.mean()),
        paired_gated_delta=float(deltas.mean()),
        positive_folds=improves,
        approved_area_share=approved_share,
        stage1_lift=lift,
        gates=gates,
        promoted=promoted,
        h53f_decision=f_decision,
        output=str(OUT.relative_to(ROOT)),
    ), indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
