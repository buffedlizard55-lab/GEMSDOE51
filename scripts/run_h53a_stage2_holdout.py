#!/usr/bin/env python3
"""Run the paired, gated H53-A Stage-2 spatial holdout exactly once.

The script refuses to score H53-A unless the five-split Stage-1 report exists
and the fresh canonical H-D/H-H baseline has reproduced the frozen six-fold
STE receipt within its preregistered tolerance. This is a local visible-catalogue
proxy experiment; it never writes a submission raster.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from scripts.evaluate_hh_blend import ste_emit  # noqa: E402
from scripts.h53a_pipeline import (  # noqa: E402
    NOMINAL_RATE_SCALE,
    load_stage1_inputs,
    make_vector_stage1,
    record_ids_intersecting_block,
)

P = ROOT / "data" / "prepared"
OUT = ROOT / "evidence" / "h53a_stage2_holdout_20261008.json"
STAGE1_RECEIPT = ROOT / "evidence" / "h53a_stage1_holdout_20261008.json"
BASELINE_RECEIPT = ROOT / "evidence" / "h53a_baseline_provenance_20261008.json"
FROZEN_RECEIPT = ROOT / "evidence" / "hh_blend_holdout.json"
BASELINE_FIELD_DIR = P / "h53a_baseline_fields"
FROZEN_BASELINE = 0.285340602656319
MASS_RATIO = 3.47
NEGATIVES = 250_000


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_fold_field_hashes(receipt: dict, field_dir: Path, grid_shape) -> None:
    """Verify the six audited H-D/H-H field files that Stage 2 will consume."""
    rows = receipt.get("per_fold", [])
    if len(rows) != 6 or sorted(int(r.get("fold", -1)) for r in rows) != list(range(6)):
        raise SystemExit("baseline receipt lacks the six canonical fold field hashes")
    for row in rows:
        fold = int(row["fold"])
        for arm, key in (("HD", "hd_field_sha256"), ("HH", "hh_field_sha256")):
            path = field_dir / f"{arm}_fold{fold}.npy"
            expected = row.get(key)
            if not path.is_file() or not expected or _sha256(path) != expected:
                raise SystemExit(f"audited baseline field hash failed: {path}")
            field = np.load(path, mmap_mode="r")
            if field.shape != tuple(grid_shape) or field.dtype != np.float32:
                raise SystemExit(f"audited baseline field geometry/dtype changed: {path}")
            del field


def _verify_baseline_provenance(receipt: dict) -> Path:
    """Bind the pass gate to the exact inputs, source receipt, and cached fields.

    A successful status string alone is not sufficient: Stage 2 consumes the
    audited H-D/H-H field bytes, so any missing/mutated lineage fails closed.
    """
    summary = receipt.get("summary", {})
    config = receipt.get("config", {})
    provenance = receipt.get("data_and_feature_provenance", {})
    if receipt.get("status") != "BASELINE_REPRODUCED_STAGE2_MAY_PROCEED":
        raise SystemExit("baseline provenance status is not authorized")
    if (not summary.get("reproduced")
            or not summary.get("candidate_stage2_authorized")
            or not np.isclose(summary.get("fresh_minus_frozen_mean", np.inf), 0.0,
                              rtol=0.0, atol=1e-5)
            or not np.isclose(config.get("baseline_reproduction_tolerance", np.nan),
                              1e-5, rtol=0.0, atol=0.0)
            or not np.isclose(config.get("frozen_mean", np.nan), FROZEN_BASELINE,
                              rtol=0.0, atol=1e-14)):
        raise SystemExit("baseline receipt fields do not satisfy the pinned reproduction gate")

    if not FROZEN_RECEIPT.is_file():
        raise SystemExit(f"pinned frozen baseline receipt is missing: {FROZEN_RECEIPT}")
    expected_frozen_hash = receipt.get("frozen_receipt_sha256")
    if not expected_frozen_hash or _sha256(FROZEN_RECEIPT) != expected_frozen_hash:
        raise SystemExit("frozen baseline receipt bytes differ from the audited provenance")
    frozen = json.loads(FROZEN_RECEIPT.read_text())
    frozen_scores = frozen.get("summary", {}).get("ste", {}).get("per_fold", [])
    if (len(frozen_scores) != 6
            or not np.allclose(frozen_scores, config.get("frozen_per_fold", []),
                               rtol=0.0, atol=1e-14)):
        raise SystemExit("frozen per-fold comparator differs from the audited baseline contract")

    prepared = P / "prepared_manifest.json"
    stack_names = P / "stack_names.json"
    expected_input_hashes = {
        "prepared_manifest_sha256": prepared,
        "base_stack_names_sha256": stack_names,
        "hd_names_sha256": P / "arm_hd_names.json",
        "hd_arm_memmap_sha256": P / "arm_hd.dat",
        "hh_names_sha256": P / "arm_hh_names.json",
        "hh_arm_memmap_sha256": P / "arm_hh.dat",
    }
    for key, path in expected_input_hashes.items():
        expected = provenance.get(key)
        if not path.is_file() or not expected or _sha256(path) != expected:
            raise SystemExit(f"baseline input provenance check failed: {key} ({path})")

    pinned_manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    training = next((f for f in pinned_manifest.get("files", [])
                     if f.get("id") == "training_features"), None)
    training_path = ROOT / "data" / "raw" / "training_features.tif"
    if not training or not training_path.is_file():
        raise SystemExit("pinned training raster is missing from the baseline provenance inputs")
    actual_training_hash = _sha256(training_path)
    if (actual_training_hash != training.get("sha256")
            or provenance.get("official_training_raster_sha256") != actual_training_hash):
        raise SystemExit("official training raster differs from the audited baseline input")

    field_dir = Path(receipt.get("fresh_field_cache_directory", ""))
    if not field_dir.is_absolute():
        field_dir = ROOT / field_dir
    if not field_dir.is_dir():
        raise SystemExit(f"audited fresh baseline field directory is missing: {field_dir}")
    _verify_fold_field_hashes(receipt, field_dir, GRID.shape)
    return field_dir


def _load_arm(group: str, expected_prefixes):
    path = P / f"arm_{group}.dat"
    names_path = P / f"arm_{group}_names.json"
    names = json.loads(names_path.read_text())
    if len(names) != len(set(names)):
        raise ValueError(f"duplicate feature names in {names_path}")
    absent = [prefix for prefix in expected_prefixes
              if not any(name.startswith(prefix) for name in names)]
    if absent:
        raise ValueError(f"{group} arm missing feature groups: {absent}")
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return names, mm


def _score(field, allowed, fold, footprint, n_target):
    ys, xs = ste_emit(field, allowed, n_target)
    prediction = np.zeros(GRID.shape, dtype=bool)
    prediction[ys, xs] = True
    if len(ys) != n_target:
        raise RuntimeError(
            f"fold {fold.index}: frozen emitter supplied {len(ys)} points, expected {n_target}"
        )
    if not np.all(allowed[ys, xs]):
        raise RuntimeError(f"fold {fold.index}: STE emitted a point outside its allowed mask")
    result = dti_binary(prediction, fold.truth,
                        valid=footprint & fold.block, known=fold.known)
    return dict(
        dti=float(result["dti"]),
        n_emitted=int(len(ys)),
        tp=float(result["tp"]),
        fp=float(result["fp"]),
        prediction=prediction,
    )


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite frozen H53-A Stage-2 result: {OUT}")
    for path in (STAGE1_RECEIPT, BASELINE_RECEIPT):
        if not path.is_file():
            raise SystemExit(f"required pre-score audit is missing: {path}")
    prereg = json.loads((ROOT / "registry" / "preregistration_h53.json").read_text())
    stage1_receipt = json.loads(STAGE1_RECEIPT.read_text())
    baseline_receipt = json.loads(BASELINE_RECEIPT.read_text())
    if prereg.get("status") != "FROZEN_BEFORE_SCORING" or prereg.get("candidate", {}).get("id") != "H53-A":
        raise SystemExit("H53 preregistration identity/status changed; refusing candidate scoring")
    if (stage1_receipt.get("id") != "GEMSDOE51-H53-A-STAGE1-20261008"
            or stage1_receipt.get("status") != "COMPLETE_STAGE1_ONLY"
            or stage1_receipt.get("preregistration") != "registry/preregistration_h53.json"):
        raise SystemExit("separate frozen Stage-1 holdout receipt is missing or inconsistent")
    if baseline_receipt.get("status") != "BASELINE_REPRODUCED_STAGE2_MAY_PROCEED":
        raise SystemExit(
            "H53 Stage-2 scoring is blocked: fresh H-D/H-H baseline did not reproduce "
            "the frozen receipt within 1e-5 (or the baseline audit is incomplete)."
        )
    baseline_field_dir = _verify_baseline_provenance(baseline_receipt)

    hd_names, hd_mm = _load_arm("hd", ("lidrel_facecoh", "detelev_facecoh"))
    hh_names, hh_mm = _load_arm("hh", ("hh_endpoint", "hh_bridge"))
    h53_names_path = P / "arm_h53a_names.json"
    h53_path = P / "arm_h53a.dat"
    h53_names = json.loads(h53_names_path.read_text())
    expected_h53 = [
        "h53_zero_coedge_s20", "h53_offset_coedge_s20", "h53_signed_lag_s20",
        "h53_zero_coedge_s50", "h53_offset_coedge_s50", "h53_signed_lag_s50",
    ]
    if h53_names != expected_h53:
        raise SystemExit(f"H53 feature names do not match frozen list: {h53_names}")
    h53_mm = np.memmap(h53_path, dtype=np.float32, mode="r",
                       shape=(len(h53_names), *GRID.shape))
    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool)
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3,
                       min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected six spatial folds; found {len(folds)}")
    segment_rows, observations = load_stage1_inputs(footprint)
    stack = Stack(P)

    receipt = dict(
        schema_version=1,
        id="GEMSDOE51-H53-A-STAGE2-20261008",
        status="IN_PROGRESS",
        preregistration="registry/preregistration_h53.json",
        instrument="Six contiguous 3x3 spatial folds; visible known-fault catalogue is proxy truth, not organizer labels.",
        config=dict(
            buffer_px=12,
            negative_samples=NEGATIVES,
            negative_rng_seed="1000 + fold.index",
            model_seed="fold.index",
            max_iter=250,
            mass_ratio=MASS_RATIO,
            published_catalogue_exclusion_px=2.0,
            blend="fixed arithmetic 0.5 H-D + 0.5 H-H; candidate adds H53-A to H-H only",
            emitter="evaluate_hh_blend.ste_emit; STE L9; continuity=0.35; spacing=2.4 px",
            stage1="source-segment tensor; fold-excluded whole official records; literal 1e-8/year; q10 approved tiles",
            candidate_extra_names=h53_names,
            hd_extra_names=hd_names,
            hh_extra_names=hh_names,
        ),
        provenance=dict(
            stage1_receipt=str(STAGE1_RECEIPT.relative_to(ROOT)),
            stage1_receipt_sha256=_sha256(STAGE1_RECEIPT),
            baseline_receipt=str(BASELINE_RECEIPT.relative_to(ROOT)),
            baseline_receipt_sha256=_sha256(BASELINE_RECEIPT),
            baseline_field_dir=str(baseline_field_dir.relative_to(ROOT)),
            h53_names_sha256=_sha256(h53_names_path),
            h53_feature_memmap=str(h53_path.relative_to(ROOT)),
            h53_feature_memmap_sha256=_sha256(h53_path),
        ),
        versions=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            scipy=scipy.__version__,
            scikit_learn=sklearn.__version__,
        ),
        per_fold=[],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")
    frozen_by_fold = baseline_receipt["config"]["frozen_per_fold"]
    t0 = time.time()

    for fold in folds:
        hd_path = baseline_field_dir / f"HD_fold{fold.index}.npy"
        hh_path = baseline_field_dir / f"HH_fold{fold.index}.npy"
        if not hd_path.is_file() or not hh_path.is_file():
            raise SystemExit(f"fold {fold.index}: fresh baseline field cache is incomplete")
        hd_field = np.load(hd_path, mmap_mode="r")
        hh_field = np.load(hh_path, mmap_mode="r")
        baseline_field = (0.5 * hd_field + 0.5 * hh_field).astype(np.float32)
        del hh_field

        h53_extras = [hh_mm[i] for i in range(len(hh_names))]
        h53_extras.extend(h53_mm[i] for i in range(len(h53_names)))
        rng = np.random.default_rng(1000 + fold.index)
        X, y = stack.sample(fold.train_pos, fold.train_neg_pool,
                            NEGATIVES, rng, extra=h53_extras)
        model = fit_detector(X, y, seed=fold.index, max_iter=250)
        n_features = int(X.shape[1])
        del X, y
        hh_h53_field = predict_grid(model, stack, footprint, extra=h53_extras)
        del model, h53_extras
        candidate_field = (0.5 * hd_field + 0.5 * hh_h53_field).astype(np.float32)
        del hd_field, hh_h53_field

        excluded_records = record_ids_intersecting_block(segment_rows, fold.block)
        stage1 = make_vector_stage1(
            segment_rows,
            observations,
            footprint,
            excluded_record_ids=excluded_records,
            rate_scale=NOMINAL_RATE_SCALE,
            convention="fault_plane",
            q=10.0,
        )
        approved = stage1["approved"]
        in_block = fold.block & footprint
        exclusion = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed_ungated = in_block & ~exclusion
        allowed_gated = allowed_ungated & approved
        n_target = int(round(MASS_RATIO * fold.n_truth))
        baseline_ungated = _score(baseline_field, allowed_ungated, fold, footprint, n_target)
        candidate_ungated = _score(candidate_field, allowed_ungated, fold, footprint, n_target)
        baseline_gated = _score(baseline_field, allowed_gated, fold, footprint, n_target)
        candidate_gated = _score(candidate_field, allowed_gated, fold, footprint, n_target)

        area_share_footprint = float((approved & footprint).sum() / max(int(footprint.sum()), 1))
        area_share_block = float((approved & in_block).sum() / max(int(in_block.sum()), 1))
        predicted_inside = int((candidate_gated["prediction"] & approved).sum())
        emitted_share_inside = predicted_inside / max(n_target, 1)
        dominance_lift = emitted_share_inside / max(area_share_block, 1e-12)
        if predicted_inside != candidate_gated["n_emitted"]:
            raise RuntimeError(f"fold {fold.index}: candidate points escaped q10 approved mask")
        for item in (baseline_ungated, candidate_ungated, baseline_gated, candidate_gated):
            item.pop("prediction")

        record = dict(
            fold=int(fold.index),
            n_truth=int(fold.n_truth),
            n_target=n_target,
            n_candidate_features=n_features,
            held_out_trace_record_count=int(len(excluded_records)),
            held_out_trace_record_ids_sha256=hashlib.sha256(
                np.asarray(excluded_records, dtype="<i8").tobytes()
            ).hexdigest(),
            stage1=dict(
                rate_scale=NOMINAL_RATE_SCALE,
                convention="fault_plane",
                q10_threshold=float(stage1["threshold"]),
                approved_area_share_footprint=area_share_footprint,
                approved_area_share_block=area_share_block,
                held_out_segment_length_used_m=float(stage1["budget_meta"]["used_length_m"]),
            ),
            candidate_domain=dict(
                emitted_share_inside_approved=emitted_share_inside,
                dominance_lift=dominance_lift,
                every_point_inside_approved=(predicted_inside == candidate_gated["n_emitted"]),
            ),
            frozen_ungated_dti=float(frozen_by_fold[fold.index]),
            outputs=dict(
                fresh_hd_hh_ungated=baseline_ungated,
                fresh_hd_hh_stage1_q10=baseline_gated,
                fresh_hd_hh_h53a_ungated=candidate_ungated,
                fresh_hd_hh_h53a_stage1_q10=candidate_gated,
            ),
        )
        receipt["per_fold"].append(record)
        OUT.write_text(json.dumps(receipt, indent=1) + "\n")
        delta = candidate_gated["dti"] - baseline_gated["dti"]
        print(
            f"fold {fold.index}: base_q10={baseline_gated['dti']:.6f} "
            f"H53_q10={candidate_gated['dti']:.6f} delta={delta:+.6f} "
            f"area={area_share_footprint:.3f} lift={dominance_lift:.3f} "
            f"({time.time() - t0:.0f}s)",
            flush=True,
        )
        del baseline_field, candidate_field, stage1

    frozen = np.asarray(frozen_by_fold, dtype=np.float64)
    base_ungated = np.asarray([r["outputs"]["fresh_hd_hh_ungated"]["dti"]
                               for r in receipt["per_fold"]], dtype=np.float64)
    base_gated = np.asarray([r["outputs"]["fresh_hd_hh_stage1_q10"]["dti"]
                             for r in receipt["per_fold"]], dtype=np.float64)
    candidate_ungated = np.asarray([r["outputs"]["fresh_hd_hh_h53a_ungated"]["dti"]
                                    for r in receipt["per_fold"]], dtype=np.float64)
    candidate_gated = np.asarray([r["outputs"]["fresh_hd_hh_h53a_stage1_q10"]["dti"]
                                  for r in receipt["per_fold"]], dtype=np.float64)
    paired = candidate_gated - base_gated
    area_footprint = np.asarray([r["stage1"]["approved_area_share_footprint"]
                                 for r in receipt["per_fold"]])
    dominance_lift = np.asarray([r["candidate_domain"]["dominance_lift"]
                                 for r in receipt["per_fold"]])
    inside = all(r["candidate_domain"]["every_point_inside_approved"]
                 for r in receipt["per_fold"])
    baseline_ok = bool(baseline_receipt["summary"]["reproduced"])
    area_ok = bool(np.all(area_footprint >= 2.0 / 3.0))
    non_dominant = bool(np.all(dominance_lift <= 1.5) and inside)
    candidate_beats_frozen = bool(candidate_gated.mean() > FROZEN_BASELINE)
    candidate_beats_paired = bool(paired.mean() > 0.0)
    fold_gate = int((paired > 0).sum()) >= 4
    gates = dict(
        baseline_reproduced=baseline_ok,
        candidate_q10_mean_exceeds_frozen_mean=candidate_beats_frozen,
        candidate_q10_mean_exceeds_same_fold_q10_comparator=candidate_beats_paired,
        positive_paired_folds_at_least_4_of_6=fold_gate,
        approved_area_at_least_two_thirds_every_fold=area_ok,
        stage1_non_dominant_lift_at_most_1_5_and_all_points_inside=non_dominant,
    )
    promoted = all(gates.values())
    receipt["summary"] = dict(
        frozen_mean_dti=FROZEN_BASELINE,
        fresh_baseline_ungated_mean_dti=float(base_ungated.mean()),
        fresh_baseline_q10_mean_dti=float(base_gated.mean()),
        candidate_ungated_mean_dti=float(candidate_ungated.mean()),
        candidate_q10_mean_dti=float(candidate_gated.mean()),
        candidate_minus_frozen=float(candidate_gated.mean() - FROZEN_BASELINE),
        candidate_minus_paired_q10_mean=float(paired.mean()),
        paired_q10_per_fold_delta=[float(v) for v in paired],
        positive_paired_folds=int((paired > 0).sum()),
        approved_area_share_footprint_mean=float(area_footprint.mean()),
        approved_area_share_footprint_min=float(area_footprint.min()),
        dominance_lift_mean=float(dominance_lift.mean()),
        dominance_lift_max=float(dominance_lift.max()),
        all_candidate_points_inside_approved=inside,
        gates=gates,
    )
    receipt["status"] = "PROMOTED_LOCAL_PROXY_ONLY" if promoted else "NOT_PROMOTED_RESEARCH_ONLY"
    receipt["elapsed_seconds"] = float(time.time() - t0)
    receipt["limitations"] = [
        "This is a visible-catalogue spatial proxy, not the organizer's hidden-label score.",
        "The six spatial folds have been reused for prior hypothesis work and are not an independent lockbox.",
        "Passing local promotion permits consideration of a unique upload candidate; it does not prove portal acceptance or authorize a competition slot.",
    ]
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt["summary"], indent=1))
    print(f"status: {receipt['status']}; wrote {OUT}")
    return 0 if promoted else 2


if __name__ == "__main__":
    raise SystemExit(main())
