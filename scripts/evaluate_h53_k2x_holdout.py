#!/usr/bin/env python3
"""Preregistered H53-K2x six-fold spatial holdout; writes evidence only.

The instrument refits H-D, H-H, and H-H+K2x on the same six spatial folds.
It first checks fresh ungated H-D/H-H against the frozen baseline, then compares
matched-mass Stage-1-q10-confined blends using the same fixed STE emission. The
visible known-fault catalogue is proxy truth only. The preregistration and the
unit/provenance audit are in knowledge/candidate-hypotheses-2026-10-08.md and
evidence/h53_k2x_input_audit_20261008.json. This script never creates or
clears a competition submission artifact or slot.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51 import strain_budget as sb  # noqa: E402
from gems51.trace_emission import ridge_response, line_accumulate, spaced_dots  # noqa: E402

P = ROOT / "data" / "prepared"
OUT = ROOT / "evidence" / "h53_k2x_holdout_20261008.json"
BASELINE_RECEIPT = ROOT / "evidence" / "hh_blend_holdout.json"
STAGE1_RECEIPT = ROOT / "evidence" / "official_vector_budget_20261007.json"
FEATURE_RECEIPT = ROOT / "evidence" / "h53_k2x_feature_build_20261008.json"
FROZEN_BASELINE = 0.285340602656319
TOLERANCE = 1e-5


def _rank01(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Match evaluate_hh_blend.py's stable empirical-CDF tie convention."""
    out = np.zeros(values.shape, dtype=np.float32)
    selected = values[mask]
    if selected.size:
        order = np.argsort(selected, kind="stable")
        ranks = np.empty(selected.size, dtype=np.float32)
        ranks[order] = np.arange(1, selected.size + 1, dtype=np.float32) / selected.size
        out[mask] = ranks
    return out


def _ste_emit(field: np.ndarray, allowed: np.ndarray, n_dots: int):
    """Byte-for-byte-equivalent scoring logic to the frozen blend receipt."""
    dom = np.isfinite(field) & allowed
    safe = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    response = np.zeros(safe.shape, dtype=np.float32)
    for sigma in (1.0, 2.0, 3.5):
        ridge, _ = ridge_response(safe, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = _rank01(safe, dom)
    accumulated, _ = line_accumulate(response, length=9, n_orient=12)
    accumulated_rank = _rank01(accumulated, dom)
    score = (raw_rank ** 0.65) * (accumulated_rank ** 0.35)
    return spaced_dots(score.astype(np.float32), dom, n_dots, spacing=2.4)


def _selected_extra_arrays(stack: Stack, extras_mm, name_indices: list[int]) -> list[np.ndarray]:
    return [np.asarray(extras_mm[i], dtype=np.float32) for i in name_indices]


def _fit_fold_field(stack: Stack, footprint: np.ndarray, fold, extras: list[np.ndarray]):
    # The exact same negative coordinates are used for all three models in a
    # fold, as run_experiments.py does when each arm uses seed 1000 + fold.index.
    rng = np.random.default_rng(1000 + fold.index)
    X, y = stack.sample(fold.train_pos, fold.train_neg_pool, 250_000, rng, extra=extras)
    model = fit_detector(X, y, seed=fold.index, max_iter=250)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras)


def _load_stage1_inputs(footprint: np.ndarray, catalogue: np.ndarray):
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    ys, xs, trace_ids = sb.trace_assignments(catalogue, df)
    observations = {}
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as src:
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        for name in ("geod_2ndinv", "geod_shearrate", "geod_dilaterate"):
            if name not in descriptions:
                raise SystemExit(f"Stage-1 source layer {name!r} missing from training raster")
            value = src.read(descriptions.index(name) + 1).astype(np.float64)
            value[value <= -1e38] = np.nan
            observations[name] = value
    if any(value.shape != footprint.shape for value in observations.values()):
        raise SystemExit("Stage-1 source layers do not match the validated competition grid")
    return df, (ys, xs, trace_ids), observations


def _stage1_q10_approved(footprint: np.ndarray, fold, df, assignments, observations):
    """Leakage-safe q10 deficit mask: remove source rows tied to fold.truth."""
    ys, xs, trace_ids = assignments
    held_rows = np.unique(trace_ids[fold.truth[ys, xs]])
    df_budget = df.loc[~df.index.isin(held_rows)]
    cfg = sb.BudgetConfig(tile_px=100, rate_convention="vertical",
                          assume_unknown_normal=True)
    exx, eyy, exy, *_ = sb.kostrov_tiles(fold.known, df_budget, cfg,
                                          area_mask=footprint)
    fault_ii = sb.invariant(exx, eyy, exy, "II")
    observed_ii = sb.observed_tiles(observations["geod_2ndinv"], footprint, 100)
    support = sb.observed_tiles(np.ones(footprint.shape, dtype=np.float32), footprint, 100)
    valid_tiles = np.isfinite(support) & (support > 0.05)
    q_fault = sb.quantile_map(np.where(valid_tiles, fault_ii, np.nan))
    q_observed = sb.quantile_map(np.where(valid_tiles, observed_ii, np.nan))
    deficit = q_observed - q_fault
    big = np.repeat(np.repeat(deficit, 100, axis=0), 100, axis=1)
    big = big[:footprint.shape[0], :footprint.shape[1]]
    finite = footprint & np.isfinite(big)
    threshold = float(np.nanpercentile(big[finite], 10.0))
    approved = finite & (big >= threshold)
    return approved, dict(
        held_trace_rows=int(len(held_rows)), budget_trace_rows=int(len(df_budget)),
        threshold=threshold,
        approved_area_share=float(approved.sum() / max(int(footprint.sum()), 1)),
    )


def _score_field(field, allowed, n_dots, fold, footprint):
    ys, xs = _ste_emit(field, allowed, n_dots)
    prediction = np.zeros(GRID.shape, dtype=bool)
    prediction[ys, xs] = True
    result = dti_binary(prediction, fold.truth,
                        valid=footprint & fold.block, known=fold.known)
    return dict(dti=float(result["dti"]), dots=int(len(ys)),
                tp=float(result["tp"]), fp=float(result["fp"]),
                emitted_inside_allowed=int(np.count_nonzero(prediction & allowed)))


def main() -> int:
    if not BASELINE_RECEIPT.is_file() or not STAGE1_RECEIPT.is_file() or not FEATURE_RECEIPT.is_file():
        raise SystemExit("frozen Stage-2 baseline, separate official-vector Stage-1, or feature-build receipt is missing")

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected the frozen six folds; found {len(folds)}")

    def open_arm(group: str):
        names_path = P / f"arm_{group}_names.json"
        data_path = P / f"arm_{group}.dat"
        if not names_path.is_file() or not data_path.is_file():
            raise SystemExit(f"missing prepared {group} arm; run build_arm_extras.py --group {group}")
        arm_names = json.loads(names_path.read_text())
        arm_mm = np.memmap(data_path, dtype=np.float32, mode="r",
                           shape=(len(arm_names), *GRID.shape))
        return arm_names, arm_mm

    hd_names, hd_mm = open_arm("hd")
    hh_names, hh_mm = open_arm("hh")
    k2_names, k2_mm = open_arm("h53_k2x")
    if len(hd_names) != 4 or len(hh_names) != 5 or k2_names != ["h53_k2x_min_s2s5"]:
        raise SystemExit(f"arm feature schema mismatch: H-D={hd_names}, H-H={hh_names}, K2x={k2_names}")
    hd_ix = list(range(len(hd_names)))
    hh_ix = list(range(len(hh_names)))
    k2_ix = list(range(len(k2_names)))

    expected = json.loads(BASELINE_RECEIPT.read_text())["summary"]["ste"]["per_fold"]
    if len(expected) != 6:
        raise SystemExit("frozen baseline must contain six STE fold values")

    stage1_df, stage1_assignments, stage1_observations = _load_stage1_inputs(footprint, catalogue)
    stack = Stack(P)
    rows = []
    t0 = time.time()
    for fold in folds:
        hd_extra = _selected_extra_arrays(stack, hd_mm, hd_ix)
        hh_only = _selected_extra_arrays(stack, hh_mm, hh_ix)
        k2_only = _selected_extra_arrays(stack, k2_mm, k2_ix)
        hh_extra = hd_extra + hh_only
        candidate_extra = hd_extra + hh_only + k2_only

        field_hd = _fit_fold_field(stack, footprint, fold, hd_extra)
        field_hh = _fit_fold_field(stack, footprint, fold, hh_extra)
        field_candidate = _fit_fold_field(stack, footprint, fold, candidate_extra)
        base_field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                      + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
        candidate_field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                           + 0.5 * np.nan_to_num(field_candidate, nan=0.0)).astype(np.float32)

        in_block = fold.block & footprint
        exclude = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed_ungated = in_block & ~exclude
        approved, stage1_receipt = _stage1_q10_approved(
            footprint, fold, stage1_df, stage1_assignments, stage1_observations)
        allowed_gated = allowed_ungated & approved
        n_dots = int(round(3.47 * fold.n_truth))

        base_ungated = _score_field(base_field, allowed_ungated, n_dots, fold, footprint)
        candidate_ungated = _score_field(candidate_field, allowed_ungated, n_dots, fold, footprint)
        base_gated = _score_field(base_field, allowed_gated, n_dots, fold, footprint)
        candidate_gated = _score_field(candidate_field, allowed_gated, n_dots, fold, footprint)
        if base_gated["dots"] != n_dots or candidate_gated["dots"] != n_dots:
            raise SystemExit(f"fold {fold.index}: Stage-1 q10 gate cannot supply the frozen dot budget")
        if base_gated["emitted_inside_allowed"] != base_gated["dots"]:
            raise SystemExit(f"fold {fold.index}: a baseline point escaped its approved Stage-1 tile mask")
        if candidate_gated["emitted_inside_allowed"] != candidate_gated["dots"]:
            raise SystemExit(f"fold {fold.index}: a candidate point escaped its approved Stage-1 tile mask")
        emitted_share = candidate_gated["emitted_inside_allowed"] / max(candidate_gated["dots"], 1)
        dominance_lift = emitted_share / max(stage1_receipt["approved_area_share"], 1e-12)
        fold_results = dict(
            fresh_hd_hh_blend_ungated=base_ungated,
            h53_k2x_blend_ungated=candidate_ungated,
            fresh_hd_hh_blend_stage1_q10=base_gated,
            h53_k2x_blend_stage1_q10=candidate_gated,
        )
        rows.append(dict(
            fold=int(fold.index), n_truth=int(fold.n_truth), n_dots=n_dots,
            frozen_hh_hd_ste_dti=float(expected[fold.index]),
            stage1_q10=stage1_receipt,
            candidate_stage1=dict(emitted_share_inside_approved=emitted_share,
                                  lift_over_area_share=dominance_lift),
            outputs=fold_results,
        ))
        delta = (candidate_gated["dti"] - base_gated["dti"])
        print(f"fold {fold.index}: baseline_ungated={base_ungated['dti']:.6f} "
              f"candidate_ungated={candidate_ungated['dti']:.6f} "
              f"baseline_q10={base_gated['dti']:.6f} "
              f"candidate_q10={candidate_gated['dti']:.6f} "
              f"paired_gated_delta={delta:+.6f} "
              f"approved={stage1_receipt['approved_area_share']:.3f} ({time.time()-t0:.0f}s)", flush=True)
        del field_hd, field_hh, field_candidate, base_field, candidate_field

    base_values = np.asarray([r["outputs"]["fresh_hd_hh_blend_ungated"]["dti"] for r in rows])
    frozen_values = np.asarray(expected, dtype=float)
    ungated_candidate_values = np.asarray(
        [r["outputs"]["h53_k2x_blend_ungated"]["dti"] for r in rows])
    gated_base_values = np.asarray(
        [r["outputs"]["fresh_hd_hh_blend_stage1_q10"]["dti"] for r in rows])
    candidate_values = np.asarray(
        [r["outputs"]["h53_k2x_blend_stage1_q10"]["dti"] for r in rows])
    deltas = candidate_values - gated_base_values
    base_reproduction_error = float(base_values.mean() - FROZEN_BASELINE)
    reproduction_ok = abs(base_reproduction_error) <= TOLERANCE
    improves = int((deltas > 0).sum())
    approved_by_fold = [float(r["stage1_q10"]["approved_area_share"]) for r in rows]
    stage1_lift_by_fold = [1.0 / max(area, 1e-12) for area in approved_by_fold]
    approved_share = float(np.mean(approved_by_fold))
    stage1_lift = float(np.mean(stage1_lift_by_fold))
    stage1_non_dominant = bool(
        all(area >= (2.0 / 3.0) for area in approved_by_fold)
        and all(lift <= 1.5 for lift in stage1_lift_by_fold)
        and all(r["candidate_stage1"]["emitted_share_inside_approved"] == 1.0
                for r in rows)
        and all(r["outputs"]["fresh_hd_hh_blend_stage1_q10"]["emitted_inside_allowed"]
                == r["outputs"]["fresh_hd_hh_blend_stage1_q10"]["dots"] for r in rows)
    )
    holdout_promoted = bool(reproduction_ok and stage1_non_dominant
                            and candidate_values.mean() > FROZEN_BASELINE
                            and deltas.mean() > 0.0 and improves >= 4)
    stage1_reference = json.loads(STAGE1_RECEIPT.read_text())["holdout"]
    feature_build = json.loads(FEATURE_RECEIPT.read_text())

    receipt = dict(
        schema_version=1,
        candidate="H53-K2x structure-conditioned conductive-ribbon anisotropy",
        status="LOCAL_PROXY_HOLDOUT_PASS_ARTIFACT_GATES_PENDING" if holdout_promoted
                else "NOT_PROMOTED_NO_SLOT",
        instrument="six-fold 3x3 spatial holdout; visible known-fault catalogue proxy truth",
        feature_build=feature_build,
        protocol=dict(
            buffer_px=12, negative_samples=250000, negative_seed="1000 + fold.index",
            model_seed="fold.index", max_iter=250, mass_ratio=3.47,
            blend="0.5 * fresh H-D probability field + 0.5 * (fresh H-H+H53-K2x probability field)",
            emission="STE ridge scales 1/2/3.5 px, line length 9, continuity exponent 0.35, greedy spacing 2.4 px",
            candidate_features=k2_names,
            candidate_feature_source="globally empirical-rank-transformed cond_surf, depth_to_base_surf, isostatic gravity anomaly, and TMI; one fixed q95-normalized axial anisotropy feature at sigma 2/5 px",
            feature_definition="evidence/candidate_hypotheses_prereg_20261008.json#locked_implementation_spec",
            band_semantics_audit="evidence/h53_k2x_input_audit_20261008.json",
            scale_sigmas_px=[2.0, 5.0],
            stage1_gate=dict(field="source-corrected official-vector q10 geodetic second-invariant deficit", tile_px=100,
                             fold_specific_known_catalogue="yes; held-out trace rows removed",
                             heldout_stage1_source="evidence/official_vector_budget_20261007.json",
                             all_stage2_points_confined_to_approved_tiles=True),
            spatial_truth="held-out block only; known-trace exclusion radius 2 px",
        ),
        baseline=dict(
            frozen_candidate="H-D/H-H 50/50 fixed blend + STE L9/w=0.35/spacing=2.4, ungated",
            frozen_mean_dti=FROZEN_BASELINE,
            frozen_per_fold=[float(x) for x in frozen_values],
            fresh_ungated_mean_dti=float(base_values.mean()),
            fresh_ungated_per_fold=[float(x) for x in base_values],
            fresh_minus_frozen_mean=base_reproduction_error,
            reproduction_tolerance=TOLERANCE,
            reproduced=reproduction_ok,
            stage1_q10_gated_mean_dti=float(gated_base_values.mean()),
            stage1_q10_gated_per_fold=[float(x) for x in gated_base_values],
        ),
        stage1_holdout=dict(
            separately_evaluated=True,
            trace_split_evidence="evidence/official_vector_budget_20261007.json",
            trace_split_instrument=stage1_reference["instrument"],
            trace_splits=stage1_reference["splits"],
            trace_split_mean_area=float(stage1_reference["mean_area"]),
            heldout_trace_recall=float(stage1_reference["mean_recall"]),
            heldout_trace_lift=float(stage1_reference["mean_lift"]),
            spatial_fold_q10_domain=dict(
                mean_approved_area_share=approved_share,
                mean_implied_lift_if_all_stage2_points_are_confined=stage1_lift,
                approved_area_share_by_fold=approved_by_fold,
                implied_lift_by_fold=stage1_lift_by_fold,
                per_fold=[r["stage1_q10"] for r in rows],
            ),
            score_weight_in_stage2=0.0,
            stage1_metric_is_not_stage2_dti=True,
            limitations=json.loads(STAGE1_RECEIPT.read_text())["limitations"],
        ),
        candidate_result=dict(
            ungated_mean_dti=float(ungated_candidate_values.mean()),
            ungated_per_fold=[float(x) for x in ungated_candidate_values],
            stage1_q10_gated_mean_dti=float(candidate_values.mean()),
            stage1_q10_gated_per_fold=[float(x) for x in candidate_values],
            paired_deltas_vs_stage1_gated_hd_hh=[float(x) for x in deltas],
            paired_mean_delta_vs_stage1_gated_hd_hh=float(deltas.mean()),
            positive_folds_vs_stage1_gated_hd_hh=int(improves),
        ),
        stage1_non_dominance=dict(
            gate="each fold-specific q10 broad-tile deficit mask; score weight 0.0",
            approved_area_share_by_fold=approved_by_fold,
            mean_approved_area_share=approved_share,
            minimum_allowed_area_share_each_fold=2.0 / 3.0,
            expected_emitted_share_inside_approved=1.0,
            implied_lift_by_fold=stage1_lift_by_fold,
            mean_implied_lift=stage1_lift,
            maximum_allowed_lift_each_fold=1.5,
            passed=stage1_non_dominant,
        ),
        promotion_rule=("fresh ungated H-D/H-H baseline reproduces frozen mean within 1e-5; final q10-gated "
                        "candidate mean > frozen ungated best 0.285340602656319; candidate also beats "
                        "same-fold q10-gated H-D/H-H mean with paired delta > 0 and >=4/6 folds; "
                        "all baseline and candidate points inside approved tiles; each fold-specific "
                        "q10 area >=2/3 and Stage-1 implied lift <=1.5. "
                        "This is only the local holdout gate; local artifact/uniqueness/provenance checks "
                        "are separate and no slot is authorized by this receipt."),
        local_holdout_gate_passed=holdout_promoted,
        submission_slot_authorized=False,
        rows=rows,
        limitations=[
            "The known-fault catalogue is not the hidden expert truth; this is only a local ranking proxy and spatial folds have been reused across prior hypotheses.",
            "The holdout does not establish organizer score, artifact acceptance, or geothermal-vent prediction.",
            "The supplied cond_surf layer has no verified units, depth, calibration, or layer-specific source in the login-walled data release; this rank-space statistic makes no physical-unit or unique-cause claim.",
            "Conductivity is non-unique; the site-specific fault-conductor literature is not a universal rule, and some active fault zones lack an observed conductor.",
            "The local competition training raster is an owner-pinned mirror, not authenticated against the organizer download.",
            "The Stage-1 q10 mask uses a documented rate/dip/component scenario with limitations in the separate receipt; it is only a broad hard domain gate and has zero Stage-2 score weight.",
            "No competition slot is authorized here, even if the local holdout gate passes; current-inventory uniqueness, provenance, format, and portal acceptance remain separate.",
        ],
    )
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(
        fresh_ungated_baseline_mean=receipt["baseline"]["fresh_ungated_mean_dti"],
        frozen_ungated_baseline_mean=FROZEN_BASELINE,
        baseline_reproduced=reproduction_ok,
        candidate_ungated_mean=receipt["candidate_result"]["ungated_mean_dti"],
        candidate_stage1_q10_gated_mean=receipt["candidate_result"]["stage1_q10_gated_mean_dti"],
        stage1_gated_hd_hh_mean=receipt["baseline"]["stage1_q10_gated_mean_dti"],
        paired_gated_mean_delta=receipt["candidate_result"]["paired_mean_delta_vs_stage1_gated_hd_hh"],
        positive_gated_folds=improves,
        approved_area_share=approved_share,
        stage1_lift=stage1_lift,
        stage1_non_dominant=stage1_non_dominant,
        local_holdout_gate_passed=holdout_promoted,
        submission_slot_authorized=False,
        output=str(OUT.relative_to(ROOT)),
    ), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
