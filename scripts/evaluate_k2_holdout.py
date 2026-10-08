#!/usr/bin/env python3
"""Frozen GEMSDOE51-K2-08 six-fold Stage-2 holdout with physical Stage 1.

Phase 1 recomputes each q10 physical dilation/shear residual gate after excluding
all QFault source records whose supported trace fragments touch the held-out
spatial block. It then fits the fresh H-D and H-H comparator, records the
historical-baseline reproduction check, and caches its fold fields. Phase 2 fits
H-H+K2 and compares the fixed 50/50 H-D/(H-H+K2) blend against both the fresh
same-fold gated H-D/H-H blend and the historical ungated local best. The
visible catalogue is proxy truth only; this script never writes a submission.

The previously reported 2.5448e-5 fresh-versus-frozen H-D/H-H drift is preserved
as a harness irregularity. Per the pre-K2 amendment in
registry/preregistration_k2_stage1_20261008.json, that known drift is reported
but is not by itself a K2 veto; the frozen historical absolute score and fresh
same-fold q10-gated paired comparisons remain mandatory.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.physical_stage1 import observed_tile_mean, physical_residual_prior  # noqa: E402
from gems51.trace_emission import (  # noqa: E402
    line_accumulate, ridge_response, spaced_dots,
)
from gems51.vector_budget import prepare_segments_in_support  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "evidence" / "k2_spatial_holdout_20261008.json"
BASELINE_RECEIPT = ROOT / "evidence" / "hh_blend_holdout.json"
STAGE1_RECEIPT = ROOT / "evidence" / "physical_stage1_holdout_20261008.json"
FROZEN_BASELINE = 0.285340602656319
BASELINE_TOLERANCE = 1e-5
MASS_RATIO = 3.47
TILE_PX = 200
Q10 = 10.0
UNIFORM_REPEATS = 5


def _rank01(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Match the stable empirical-CDF tie convention in the frozen STE receipt."""
    out = np.zeros(values.shape, dtype=np.float32)
    selected = values[mask]
    if selected.size:
        order = np.argsort(selected, kind="stable")
        ranks = np.empty(selected.size, dtype=np.float32)
        ranks[order] = np.arange(1, selected.size + 1, dtype=np.float32) / selected.size
        out[mask] = ranks
    return out


def _ste_emit(field: np.ndarray, allowed: np.ndarray, n_dots: int):
    """The frozen STE L9 / w=0.35 / spacing=2.4 emission operator."""
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


def _fit_fold_field(stack: Stack, footprint: np.ndarray, fold,
                    extras: list[np.ndarray], label: str) -> np.ndarray:
    # Identical negative coordinates and estimator seeds across the fold-matched
    # H-D, H-H, and H-H+K2 arms; only the named feature columns differ.
    rng = np.random.default_rng(1000 + fold.index)
    X, y = stack.sample(fold.train_pos, fold.train_neg_pool, 250_000, rng, extra=extras)
    print(f"  fit {label} fold {fold.index}: X={X.shape} positives={int(y.sum()):,}", flush=True)
    model = fit_detector(X, y, seed=fold.index, max_iter=250)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras)


def _check_memmap(path: Path, names: list[str], expected_names: list[str]):
    if names != expected_names:
        raise SystemExit(f"unexpected feature names in {path.name}: {names}")
    expected_bytes = len(names) * GRID.height * GRID.width * np.dtype(np.float32).itemsize
    if not path.is_file() or path.stat().st_size != expected_bytes:
        raise SystemExit(
            f"{path.name} missing or wrong byte size; expected {expected_bytes}, "
            f"got {path.stat().st_size if path.exists() else 'missing'}"
        )
    return np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))


def _read_observations():
    path = RAW / "training_features.tif"
    with rasterio.open(path) as src:
        GRID.assert_matches(dict(transform=src.transform, height=src.height,
                                 width=src.width, crs=src.crs))
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        values = {}
        for name in ("geod_dilaterate", "geod_shearrate"):
            if descriptions.count(name) != 1:
                raise ValueError(f"expected exactly one {name!r} band")
            a = src.read(descriptions.index(name) + 1).astype(np.float64)
            a[~np.isfinite(a) | (a <= -1e38)] = np.nan
            values[name] = a
    return values


def _score_field(field: np.ndarray, allowed: np.ndarray, n_dots: int,
                 fold, footprint: np.ndarray) -> dict:
    ys, xs = _ste_emit(field, allowed, n_dots)
    prediction = np.zeros(GRID.shape, dtype=bool)
    prediction[ys, xs] = True
    result = dti_binary(prediction, fold.truth,
                        valid=footprint & fold.block, known=fold.known)
    inside_allowed = int(np.count_nonzero(prediction & allowed))
    inside_approved = int(np.count_nonzero(prediction & fold.block & footprint))
    return dict(
        dti=float(result["dti"]), dots=int(len(ys)),
        tp=float(result["tp"]), fp=float(result["fp"]),
        emitted_inside_allowed=inside_allowed,
        emitted_inside_fold_footprint=inside_approved,
        all_points_inside_allowed=bool(inside_allowed == len(ys)),
    )


def _uniform_control(allowed: np.ndarray, n_dots: int, fold,
                     footprint: np.ndarray, seed: int) -> dict:
    ys, xs = np.nonzero(allowed)
    if ys.size < n_dots:
        raise RuntimeError(
            f"fold {fold.index}: q10 same-mask uniform pool {ys.size} < dot budget {n_dots}"
        )
    rng = np.random.default_rng(seed)
    choose = rng.choice(ys.size, size=n_dots, replace=False)
    pred = rasterise(ys[choose], xs[choose]) > 0
    result = dti_binary(pred, fold.truth,
                        valid=footprint & fold.block, known=fold.known)
    return dict(dti=float(result["dti"]), dots=int(n_dots),
                tp=float(result["tp"]), fp=float(result["fp"]))


def _stage1_fold(prepared, observed, support, footprint, fold):
    """Leakage-safe physical q10 gate and held-block trace diagnostics."""
    # Exclude every source record touching the block, not only those assigned to
    # visible positive pixels. This is stricter than a centroid-to-catalogue map.
    held_source_records = prepared.records_intersecting(fold.block)
    prior = physical_residual_prior(
        prepared,
        observed["geod_dilaterate"],
        observed["geod_shearrate"],
        support,
        excluded_records=held_source_records,
        approved_quantile=Q10,
    )
    approved = np.asarray(prior["approved_mask"], dtype=bool) & support
    truth_n = int(fold.truth.sum())
    recall = float((fold.truth & approved).sum() / max(truth_n, 1))
    area_support = float(approved.sum() / max(int(support.sum()), 1))
    area_footprint = float(approved.sum() / max(int(footprint.sum()), 1))
    truth_density = observed_tile_mean(fold.truth.astype(np.float64), support, TILE_PX)
    valid_tiles = prior["tile_valid"] & np.isfinite(truth_density)
    rho = None
    if int(valid_tiles.sum()) > 5:
        statistic = float(spearmanr(prior["score"][valid_tiles],
                                    truth_density[valid_tiles]).statistic)
        if np.isfinite(statistic):
            rho = statistic
    result = dict(
        excluded_source_trace_records=int(len(held_source_records)),
        held_source_record_ids=[int(x) for x in held_source_records],
        q10_threshold=float(prior["threshold"]),
        approved_area_share_of_common_support=area_support,
        approved_area_share_of_footprint=area_footprint,
        held_block_catalogue_pixels=truth_n,
        held_block_catalogue_trace_recall=recall,
        held_block_catalogue_trace_lift=recall / max(area_footprint, 1e-12),
        spearman_physical_prior_vs_held_block_trace_density=rho,
        scenario_count=int(prior["scenario_count"]),
        excluded_trace_count_reported_by_prior=int(prior["excluded_trace_records"]),
        approval_is_coarse_tiles_only=True,
    )
    return approved, result


def _summary(values):
    a = np.asarray(values, dtype=np.float64)
    return dict(mean=float(a.mean()), per_fold=[float(x) for x in a])


def main() -> int:
    required = [
        PREPARED / "footprint.npy", PREPARED / "catalogue.npy",
        PREPARED / "stack.dat", PREPARED / "stack_names.json",
        PREPARED / "arm_hd.dat", PREPARED / "arm_hd_names.json",
        PREPARED / "arm_hh.dat", PREPARED / "arm_hh_names.json",
        PREPARED / "arm_k2.dat", PREPARED / "arm_k2_names.json",
        RAW / "training_features.tif", ROOT / "registry" / "official" / "trace_segments_utm11.csv",
        BASELINE_RECEIPT, STAGE1_RECEIPT,
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit(f"missing prepared input(s): {missing}")

    footprint = np.load(PREPARED / "footprint.npy").astype(bool)
    catalogue = np.load(PREPARED / "catalogue.npy").astype(bool)
    if footprint.shape != GRID.shape or catalogue.shape != GRID.shape:
        raise SystemExit("prepared masks do not match the fixed competition grid")
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected six frozen spatial folds, got {len(folds)}")

    expected_hd = ["lidrel_facecoh09", "lidrel_facecoh21",
                   "detelev_facecoh09", "detelev_facecoh21"]
    expected_hh = ["hh_endpoint", "hh_bridge", "hh_bridge_cond",
                   "hh_bridge_surface", "hh_endpoint_concordance"]
    expected_k2 = ["k2_cond_cross_rank_s20", "k2_cond_sign_persist_s20",
                   "k2_cond_cross_rank_s50", "k2_cond_sign_persist_s50"]
    hd = _check_memmap(PREPARED / "arm_hd.dat",
                       json.loads((PREPARED / "arm_hd_names.json").read_text()), expected_hd)
    hh = _check_memmap(PREPARED / "arm_hh.dat",
                       json.loads((PREPARED / "arm_hh_names.json").read_text()), expected_hh)
    k2 = _check_memmap(PREPARED / "arm_k2.dat",
                       json.loads((PREPARED / "arm_k2_names.json").read_text()), expected_k2)
    hd_extra = [np.asarray(hd[i], dtype=np.float32) for i in range(len(expected_hd))]
    hh_extra = [np.asarray(hh[i], dtype=np.float32) for i in range(len(expected_hh))]
    k2_extra = [np.asarray(k2[i], dtype=np.float32) for i in range(len(expected_k2))]
    # The frozen H-H arm shares the H-D face-coherence group; the K2 candidate
    # adds K2 to that same H-D + H-H feature set.
    hh_baseline_extra = hd_extra + hh_extra
    hh_k2_extra = hh_baseline_extra + k2_extra

    observations = _read_observations()
    support = footprint & np.isfinite(observations["geod_dilaterate"]) \
        & np.isfinite(observations["geod_shearrate"])
    source_rows = pd.read_csv(ROOT / "registry" / "official" / "trace_segments_utm11.csv")
    prepared = prepare_segments_in_support(source_rows, support, tile_px=TILE_PX)
    if prepared.supported_record_ids.size == 0:
        raise SystemExit("no source trace record intersects the common geodetic support")

    base_receipt = json.loads(BASELINE_RECEIPT.read_text())
    frozen_folds = base_receipt["summary"]["ste"]["per_fold"]
    if len(frozen_folds) != 6:
        raise SystemExit("historical H-D/H-H receipt must have six STE fold scores")
    stage1_trace = json.loads(STAGE1_RECEIPT.read_text())
    stack = Stack(PREPARED)

    t0 = time.time()
    stage1_rows = []
    baseline_rows = []
    print("Phase 1: compute fold-specific physical q10 masks and fresh H-D/H-H baseline", flush=True)
    for fold in folds:
        approved, s1 = _stage1_fold(prepared, observations, support, footprint, fold)
        stage1_cache = PREPARED / f"k2_physical_q10_fold{fold.index}.npy"
        np.save(stage1_cache, approved.astype(np.bool_))
        s1["mask_cache"] = str(stage1_cache.relative_to(ROOT))

        hd_field = _fit_fold_field(stack, footprint, fold, hd_extra, "H-D")
        hh_field = _fit_fold_field(stack, footprint, fold, hh_baseline_extra, "H-H+H-D")
        base_field = (0.5 * np.nan_to_num(hd_field, nan=0.0)
                      + 0.5 * np.nan_to_num(hh_field, nan=0.0)).astype(np.float32)
        baseline_cache = PREPARED / f"k2_fresh_hd_hh_fields_fold{fold.index}.npy"
        np.save(baseline_cache, np.stack([hd_field, hh_field]).astype(np.float32))

        in_block = fold.block & footprint
        known_exclusion = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed_ungated = in_block & ~known_exclusion
        allowed_gated = allowed_ungated & approved
        n_dots = int(round(MASS_RATIO * fold.n_truth))
        base_ungated = _score_field(base_field, allowed_ungated, n_dots, fold, footprint)
        base_gated = _score_field(base_field, allowed_gated, n_dots, fold, footprint)
        if base_ungated["dots"] != n_dots or base_gated["dots"] != n_dots:
            raise RuntimeError(f"fold {fold.index}: fresh baseline cannot meet fixed dot mass")
        controls = [
            _uniform_control(allowed_gated, n_dots, fold, footprint,
                             seed=810_000 + fold.index * 100 + repeat)
            for repeat in range(UNIFORM_REPEATS)
        ]
        baseline_rows.append(dict(
            fold=int(fold.index), n_truth=int(fold.n_truth), n_dots=n_dots,
            historical_frozen_ungated_dti=float(frozen_folds[fold.index]),
            fresh_hd_hh_ungated=base_ungated,
            fresh_hd_hh_physical_q10=base_gated,
            same_mask_uniform_controls=controls,
            same_mask_uniform_mean_dti=float(np.mean([x["dti"] for x in controls])),
            baseline_fields_cache=str(baseline_cache.relative_to(ROOT)),
            stage1_mask_cache=str(stage1_cache.relative_to(ROOT)),
        ))
        stage1_rows.append(dict(fold=int(fold.index), **s1))
        print(
            f"  fold {fold.index}: Stage1 area={s1['approved_area_share_of_footprint']:.3f} "
            f"trace recall={s1['held_block_catalogue_trace_recall']:.3f}; "
            f"fresh ungated={base_ungated['dti']:.6f} q10={base_gated['dti']:.6f} "
            f"uniform={baseline_rows[-1]['same_mask_uniform_mean_dti']:.6f} "
            f"({time.time()-t0:.0f}s)", flush=True,
        )
        del hd_field, hh_field, base_field

    fresh_ungated = np.asarray([r["fresh_hd_hh_ungated"]["dti"] for r in baseline_rows])
    fresh_gated = np.asarray([r["fresh_hd_hh_physical_q10"]["dti"] for r in baseline_rows])
    baseline_uniform = np.asarray([r["same_mask_uniform_mean_dti"] for r in baseline_rows])
    reproduction_delta = float(fresh_ungated.mean() - FROZEN_BASELINE)
    reproduced = bool(abs(reproduction_delta) <= BASELINE_TOLERANCE)
    print(
        f"Baseline preflight: frozen={FROZEN_BASELINE:.12f}, "
        f"fresh={fresh_ungated.mean():.12f}, delta={reproduction_delta:+.12f}, "
        f"within_1e-5={reproduced}. Proceeding per the pre-K2 amendment; "
        "the discrepancy remains an explicit harness irregularity.",
        flush=True,
    )

    print("Phase 2: fit H-H+K2 and evaluate the frozen paired promotion screen", flush=True)
    candidate_rows = []
    for fold in folds:
        hh_k2_field = _fit_fold_field(
            stack, footprint, fold, hh_k2_extra, "H-H+H-D+K2"
        )
        base_fields = np.load(
            PREPARED / f"k2_fresh_hd_hh_fields_fold{fold.index}.npy", mmap_mode="r"
        )
        if base_fields.shape != (2, *GRID.shape):
            raise RuntimeError(f"fold {fold.index}: baseline field cache has wrong shape")
        base_field = (0.5 * np.nan_to_num(base_fields[0], nan=0.0)
                      + 0.5 * np.nan_to_num(base_fields[1], nan=0.0)).astype(np.float32)
        candidate_field = (0.5 * np.nan_to_num(base_fields[0], nan=0.0)
                           + 0.5 * np.nan_to_num(hh_k2_field, nan=0.0)).astype(np.float32)
        approved = np.load(PREPARED / f"k2_physical_q10_fold{fold.index}.npy").astype(bool)
        in_block = fold.block & footprint
        known_exclusion = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed_ungated = in_block & ~known_exclusion
        allowed_gated = allowed_ungated & approved
        n_dots = int(round(MASS_RATIO * fold.n_truth))
        candidate_ungated = _score_field(candidate_field, allowed_ungated,
                                         n_dots, fold, footprint)
        candidate_gated = _score_field(candidate_field, allowed_gated,
                                       n_dots, fold, footprint)
        if candidate_ungated["dots"] != n_dots or candidate_gated["dots"] != n_dots:
            raise RuntimeError(f"fold {fold.index}: K2 candidate cannot meet fixed dot mass")
        if not candidate_gated["all_points_inside_allowed"]:
            raise RuntimeError(f"fold {fold.index}: K2 emitted a point outside the approved q10 mask")
        delta = (candidate_gated["dti"]
                 - baseline_rows[fold.index]["fresh_hd_hh_physical_q10"]["dti"])
        candidate_rows.append(dict(
            fold=int(fold.index),
            candidate_h_d_hh_k2_ungated=candidate_ungated,
            candidate_h_d_hh_k2_physical_q10=candidate_gated,
            paired_q10_delta_vs_fresh_hd_hh=float(delta),
            same_mask_uniform_margin=float(
                candidate_gated["dti"] - baseline_rows[fold.index]["same_mask_uniform_mean_dti"]
            ),
        ))
        print(
            f"  fold {fold.index}: candidate ungated={candidate_ungated['dti']:.6f} "
            f"q10={candidate_gated['dti']:.6f} "
            f"paired_delta={delta:+.6f} "
            f"uniform_margin={candidate_rows[-1]['same_mask_uniform_margin']:+.6f} "
            f"({time.time()-t0:.0f}s)", flush=True,
        )
        del base_fields, base_field, candidate_field, hh_k2_field

    candidate_ungated_values = np.asarray([
        r["candidate_h_d_hh_k2_ungated"]["dti"] for r in candidate_rows
    ], dtype=np.float64)
    candidate_gated_values = np.asarray([
        r["candidate_h_d_hh_k2_physical_q10"]["dti"] for r in candidate_rows
    ], dtype=np.float64)
    paired_deltas = np.asarray([r["paired_q10_delta_vs_fresh_hd_hh"]
                                for r in candidate_rows], dtype=np.float64)
    uniform_margins = np.asarray([r["same_mask_uniform_margin"] for r in candidate_rows],
                                 dtype=np.float64)
    area_shares = np.asarray([r["approved_area_share_of_footprint"] for r in stage1_rows],
                             dtype=np.float64)
    stage1_lifts = 1.0 / np.maximum(area_shares, 1e-12)
    positive_folds = int(np.count_nonzero(paired_deltas > 0.0))
    all_points_confined = all(
        r["candidate_h_d_hh_k2_physical_q10"]["all_points_inside_allowed"]
        for r in candidate_rows
    )
    mean_stage1_area = float(area_shares.mean())
    mean_stage1_lift = float(stage1_lifts.mean())
    mean_uniform_margin = float(uniform_margins.mean())
    gates = dict(
        candidate_q10_mean_exceeds_frozen_best=bool(candidate_gated_values.mean() > FROZEN_BASELINE),
        candidate_q10_mean_exceeds_same_fold_q10_baseline=bool(candidate_gated_values.mean() > fresh_gated.mean()),
        paired_mean_delta_positive=bool(paired_deltas.mean() > 0.0),
        at_least_4_of_6_paired_folds_positive=bool(positive_folds >= 4),
        every_stage1_approved_area_at_least_two_thirds=bool(np.all(area_shares >= (2.0 / 3.0))),
        every_stage1_area_lift_at_most_1_5=bool(np.all(stage1_lifts <= 1.5)),
        all_candidate_points_inside_approved_tiles=bool(all_points_confined),
        mean_candidate_margin_over_same_mask_uniform_at_least_0_002=bool(mean_uniform_margin >= 0.002),
        fresh_ungated_baseline_reproduces_historical_within_1e_5=bool(reproduced),
        known_baseline_reproduction_irregularity_is_not_a_veto_per_amendment=True,
    )
    # The reproduction flag remains a reported diagnostic only because the
    # pre-score amendment explicitly retained K2's dual absolute/paired tests.
    required_gates = [
        gates["candidate_q10_mean_exceeds_frozen_best"],
        gates["candidate_q10_mean_exceeds_same_fold_q10_baseline"],
        gates["paired_mean_delta_positive"],
        gates["at_least_4_of_6_paired_folds_positive"],
        gates["every_stage1_approved_area_at_least_two_thirds"],
        gates["every_stage1_area_lift_at_most_1_5"],
        gates["all_candidate_points_inside_approved_tiles"],
        gates["mean_candidate_margin_over_same_mask_uniform_at_least_0_002"],
    ]
    promoted = bool(all(required_gates))

    def _mean_of_rows(key):
        return float(np.mean([r[key] for r in stage1_rows]))

    nonnull_rho = [r["spearman_physical_prior_vs_held_block_trace_density"]
                   for r in stage1_rows
                   if r["spearman_physical_prior_vs_held_block_trace_density"] is not None]
    physical_receipt_summary = stage1_trace.get("summary", {})
    output = dict(
        schema_version=1,
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        candidate_id="GEMSDOE51-K2-08-conductive-ribbon",
        status="PROMOTED_LOCAL_PROXY_ONLY" if promoted else "NOT_PROMOTED_NO_SUBMISSION",
        instrument=("six-fold 3x3 spatially blocked holdout; visible catalogue proxy truth; "
                    "physical Stage-1 q10 mask recomputed without source records touching each held block"),
        protocol=dict(
            buffer_pixels=12, negative_samples=250000,
            negative_seed="1000 + fold.index", model_seed="fold.index",
            model=("HistGradientBoosting max_iter=250, learning_rate=0.08, "
                   "max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0, "
                   "max_bins=255, early_stopping=False"),
            mass_ratio=MASS_RATIO,
            emitter="STE ridge scales [1,2,3.5], line L9, continuity exponent 0.35, spacing 2.4 px",
            catalogue_exclusion_pixels=2,
            baseline="0.5 * fresh H-D field + 0.5 * fresh H-H field",
            candidate="0.5 * fresh H-D field + 0.5 * fresh (H-H+K2) field",
            candidate_features=expected_k2,
            stage1=dict(
                physical_formula="signed residuals of source-definition-matched dilation and shear; Kreemer et al. (2000) Eq. 3",
                tile_pixels=TILE_PX, quantile=Q10,
                excluded_geometry="every QFault source record with a supported trace fragment intersecting the held spatial block",
                rate_conventions=["fault_plane", "vertical"],
                geodetic_rate_scales_per_year=[1e-9, 1e-8],
                score_weight=0.0,
            ),
        ),
        baseline=dict(
            frozen_hh_hd_ungated_mean_dti=FROZEN_BASELINE,
            frozen_hh_hd_ungated_per_fold=[float(x) for x in frozen_folds],
            fresh_hh_hd_ungated_mean_dti=float(fresh_ungated.mean()),
            fresh_hh_hd_ungated_per_fold=[float(x) for x in fresh_ungated],
            fresh_minus_frozen_mean=float(reproduction_delta),
            reproduction_tolerance=BASELINE_TOLERANCE,
            reproduced_within_tolerance=bool(reproduced),
            reproduction_interpretation=(
                "Known harness irregularity; retained in the receipt. It is not a K2 veto under the pre-score amendment; "
                "the historical absolute gate and same-fold q10-gated paired comparison remain binding."
            ),
            physical_q10_gated_mean_dti=float(fresh_gated.mean()),
            physical_q10_gated_per_fold=[float(x) for x in fresh_gated],
        ),
        stage1_holdout=dict(
            separate_whole_trace_holdout_receipt="evidence/physical_stage1_holdout_20261008.json",
            separate_whole_trace_holdout_summary=physical_receipt_summary,
            separate_whole_trace_holdout_uniform_controls_interpretation=(
                "The mean approved-vs-support uniform DTI delta is negative but small (-0.000289); "
                "the physical q10 mask is weak, broad prior evidence, not a strong enrichment claim."
            ),
            spatial_fold_mean_approved_area_share_of_footprint=mean_stage1_area,
            spatial_fold_mean_lift_if_all_points_are_inside=mean_stage1_lift,
            spatial_fold_mean_held_trace_recall=_mean_of_rows("held_block_catalogue_trace_recall"),
            spatial_fold_mean_held_trace_lift=_mean_of_rows("held_block_catalogue_trace_lift"),
            spatial_fold_mean_spearman_vs_trace_density=(float(np.mean(nonnull_rho)) if nonnull_rho else None),
            score_weight=0.0,
            per_fold=stage1_rows,
        ),
        candidate_result=dict(
            ungated_mean_dti=float(candidate_ungated_values.mean()),
            ungated_per_fold=[float(x) for x in candidate_ungated_values],
            physical_q10_gated_mean_dti=float(candidate_gated_values.mean()),
            physical_q10_gated_per_fold=[float(x) for x in candidate_gated_values],
            paired_q10_deltas_vs_fresh_hh_hd=[float(x) for x in paired_deltas],
            paired_mean_q10_delta_vs_fresh_hh_hd=float(paired_deltas.mean()),
            positive_q10_folds=int(positive_folds),
            same_mask_uniform_mean_dti=float(baseline_uniform.mean()),
            candidate_minus_same_mask_uniform_mean_dti=mean_uniform_margin,
            same_mask_uniform_margin_per_fold=[float(x) for x in uniform_margins],
        ),
        promotion_gates=gates,
        promoted_local_proxy_only=promoted,
        stage1_dominance=dict(
            broad_q10_tile_gate_only=True,
            mean_approved_area_share=mean_stage1_area,
            mean_lift_if_all_points_approved=mean_stage1_lift,
            all_candidate_points_inside_approved_tiles=all_points_confined,
            does_not_dominate_fine_scale_emission=True,
        ),
        per_fold=[
            dict(
                fold=int(fold.index), n_truth=int(fold.n_truth),
                historical_frozen_ungated_dti=float(frozen_folds[fold.index]),
                baseline=baseline_rows[fold.index],
                stage1=stage1_rows[fold.index],
                candidate=candidate_rows[fold.index],
            ) for fold in folds
        ],
        limitations=[
            "The visible QFault/competition catalogue is proxy truth, not the hidden expert fault map.",
            "This six-fold contiguous-block screen is not an organizer score and cannot reveal genuinely new fault styles.",
            "The five-split whole-source-trace Stage-1 test is scattered by record, not geographically independent.",
            "Slip-rate component and geodetic unit conventions remain unresolved; both declared scenarios were averaged.",
            "The q10 physical residual prior has weak held-trace enrichment and slightly lower uniform DTI than full support in its separate five-split holdout.",
            "A local proxy promotion, if any, is not portal validation, uniqueness clearance, or upload authorization.",
        ],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(
        fresh_ungated_baseline_mean=float(fresh_ungated.mean()),
        frozen_ungated_baseline_mean=FROZEN_BASELINE,
        baseline_irregularity=not reproduced,
        physical_q10_baseline_mean=float(fresh_gated.mean()),
        candidate_ungated_mean=float(candidate_ungated_values.mean()),
        candidate_physical_q10_mean=float(candidate_gated_values.mean()),
        paired_q10_mean_delta=float(paired_deltas.mean()),
        positive_q10_folds=positive_folds,
        same_mask_uniform_mean=float(baseline_uniform.mean()),
        candidate_minus_uniform_mean=mean_uniform_margin,
        stage1_area_share=mean_stage1_area,
        stage1_lift=mean_stage1_lift,
        gates=gates,
        promoted=promoted,
        receipt=str(OUT.relative_to(ROOT)),
        seconds=round(time.time() - t0, 1),
    ), indent=2, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
