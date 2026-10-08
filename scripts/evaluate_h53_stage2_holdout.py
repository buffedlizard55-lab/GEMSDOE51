#!/usr/bin/env python3
"""Paired Stage-2 validation for preregistered H53-A; never writes a TIFF.

The fold-fitted H-D/H-H models are the existing fixed Stage-2 baseline. The
Stage-1 q10 mask is applied only when selecting legal emission pixels; STE
ranking is computed on the ungated fold-valid domain so the coarse physical
prior does not become a fine-scale Stage-2 feature. Holdout truth is the visible
catalogue and is not organizer/hidden-label validation.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import trace_emission as te  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"
HD_DATA = P / "arm_hd.dat"
HD_NAMES = P / "arm_hd_names.json"
HH_DATA = P / "arm_hh.dat"
HH_NAMES = P / "arm_hh_names.json"
STAGE1_RECEIPT = ROOT / "evidence" / "h53_stage1_holdout_20261008.json"
STAGE1_MASKS = P / "h53_stage1_fold_masks_20261008.npz"
FROZEN_BLEND = ROOT / "evidence" / "hh_blend_holdout.json"
OUT = ROOT / "evidence" / "h53_stage2_holdout_20261008.json"
FROZEN_BEST = 0.285340602656319
REPRO_TOLERANCE = 1e-5
NEGATIVES = 250_000
MASS_RATIO = 3.47
KNOWN_EXCLUSION_PX = 2.0
SPACING_PX = 2.4


def _load_arm_arrays(path: Path, names_path: Path, expected_names: list[str]) -> list[np.ndarray]:
    if not path.is_file() or not names_path.is_file():
        raise SystemExit(f"missing prepared feature group {path.name}; run scripts/build_arm_extras.py")
    names = json.loads(names_path.read_text())
    if names != expected_names:
        raise SystemExit(f"unexpected {names_path.name}: {names}")
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [np.asarray(mm[i], dtype=np.float32) for i in range(len(names))]


def _fit_field(stack: Stack, footprint: np.ndarray, fold,
               extras: list[np.ndarray]) -> np.ndarray:
    rng = np.random.default_rng(1000 + fold.index)
    X, y = stack.sample(fold.train_pos, fold.train_neg_pool, NEGATIVES,
                        rng, extra=extras)
    model = fit_detector(X, y, seed=fold.index, max_iter=250)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras)


def _ste_score(field: np.ndarray, ungated_domain: np.ndarray) -> np.ndarray:
    """Exactly match the frozen blend STE ranking over its full legal domain."""
    dom = np.asarray(ungated_domain, dtype=bool) & np.isfinite(field)
    safe = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    response = np.zeros(safe.shape, dtype=np.float32)
    for sigma in (1.0, 2.0, 3.5):
        ridge, _ = te.ridge_response(safe, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = te._rank01(safe, dom)
    accumulated, _ = te.line_accumulate(response, length=9, n_orient=12)
    accumulated_rank = te._rank01(accumulated, dom)
    return (raw_rank ** 0.65 * accumulated_rank ** 0.35).astype(np.float32)


def _score_points(ys: np.ndarray, xs: np.ndarray, fold, footprint: np.ndarray) -> dict:
    pred = np.zeros(GRID.shape, dtype=bool)
    pred[ys, xs] = True
    result = dti_binary(pred, fold.truth,
                        valid=footprint & fold.block,
                        known=fold.known)
    return dict(
        dti=float(result["dti"]),
        dots=int(len(ys)),
        tp=float(result["tp"]),
        fp=float(result["fp"]),
        fn=float(result["fn"]),
    )


def main() -> int:
    hd_names = json.loads(HD_NAMES.read_text()) if HD_NAMES.is_file() else []
    hh_names = json.loads(HH_NAMES.read_text()) if HH_NAMES.is_file() else []
    if not hd_names or not hh_names:
        raise SystemExit("H-D/H-H arm features missing; build them with scripts/build_arm_extras.py")
    hd_extra = _load_arm_arrays(HD_DATA, HD_NAMES, hd_names)
    hh_extra = _load_arm_arrays(HH_DATA, HH_NAMES, hh_names)
    if not STAGE1_RECEIPT.is_file() or not STAGE1_MASKS.is_file():
        raise SystemExit("Stage-1 receipt/masks missing; run evaluate_h53_stage1_holdout.py first")
    stage1_receipt = json.loads(STAGE1_RECEIPT.read_text())
    frozen = json.loads(FROZEN_BLEND.read_text())
    frozen_per_fold = frozen["summary"]["ste"]["per_fold"]
    if len(frozen_per_fold) != 6:
        raise SystemExit("frozen local-best baseline must have exactly six folds")

    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool)
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3,
                       n_cols=3, min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected six frozen spatial folds, found {len(folds)}")
    masks_archive = np.load(STAGE1_MASKS)
    masks = []
    for fold in folds:
        name = f"approved_fold{fold.index}"
        if name not in masks_archive:
            raise SystemExit(f"Stage-1 mask missing {name}")
        approved = masks_archive[name].astype(bool)
        if approved.shape != GRID.shape or np.any(approved & ~footprint):
            raise SystemExit(f"Stage-1 mask {name} is not grid/footprint compatible")
        masks.append(approved)

    stack = Stack(P)
    rows = []
    started = time.time()
    for fold, approved in zip(folds, masks):
        field_hd = _fit_field(stack, footprint, fold, hd_extra)
        field_hh = _fit_field(stack, footprint, fold, hh_extra)
        field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                 + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
        in_block = fold.block & footprint
        known_exclusion = ndi.distance_transform_edt(~fold.known) <= KNOWN_EXCLUSION_PX
        ungated_domain = in_block & ~known_exclusion & np.isfinite(field)
        gated_domain = ungated_domain & approved
        if not gated_domain.any():
            raise SystemExit(f"fold {fold.index}: q10 mask leaves no legal emission pixels")
        k = int(round(MASS_RATIO * fold.n_truth))
        score = _ste_score(field, ungated_domain)

        ys_ungated, xs_ungated = te.spaced_dots(score, ungated_domain, k,
                                                spacing=SPACING_PX)
        ys_gated, xs_gated = te.spaced_dots(score, gated_domain, k,
                                            spacing=SPACING_PX)
        if len(ys_ungated) != k or len(ys_gated) != k:
            raise SystemExit(f"fold {fold.index}: fixed mass budget was starved "
                             f"(ungated={len(ys_ungated)}/{k}; gated={len(ys_gated)}/{k})")
        if not np.all(approved[ys_gated, xs_gated]):
            raise SystemExit(f"fold {fold.index}: a Stage-2 prediction escaped the Stage-1 mask")

        rng = np.random.default_rng(5300 + fold.index)
        random_score = np.full(GRID.shape, np.nan, dtype=np.float32)
        random_score[gated_domain] = rng.random(int(gated_domain.sum()), dtype=np.float32)
        ys_uniform, xs_uniform = te.spaced_dots(random_score, gated_domain, k,
                                                spacing=SPACING_PX)
        if len(ys_uniform) != k:
            raise SystemExit(f"fold {fold.index}: uniform control was starved "
                             f"({len(ys_uniform)}/{k})")

        baseline = _score_points(ys_ungated, xs_ungated, fold, footprint)
        candidate = _score_points(ys_gated, xs_gated, fold, footprint)
        uniform = _score_points(ys_uniform, xs_uniform, fold, footprint)
        auc_domain = in_block & np.isfinite(field)
        auc = float(roc_auc_score(fold.truth[auc_domain], field[auc_domain]))
        block_area = int(in_block.sum())
        approved_block_area = int((approved & in_block).sum())
        area_share = approved_block_area / max(block_area, 1)
        fold_row = dict(
            fold=int(fold.index),
            heldout_truth_pixels=int(fold.n_truth),
            fixed_dots=k,
            frozen_best_dti=float(frozen_per_fold[fold.index]),
            stage2_inblock_auc=auc,
            stage1=dict(
                approved_area_share_in_block=float(area_share),
                approved_area_share_full_footprint=float((approved & footprint).sum() / max(int(footprint.sum()), 1)),
                candidate_dots_inside_approved_share=float(np.mean(approved[ys_gated, xs_gated])),
                confinement_lift=float(1.0 / max(area_share, 1e-12)),
            ),
            outputs=dict(
                fresh_ungated_hh_hd=baseline,
                stage1_q10_hh_hd_candidate=candidate,
                same_domain_uniform_spaced=uniform,
            ),
            paired_delta_candidate_minus_ungated=float(candidate["dti"] - baseline["dti"]),
            paired_delta_candidate_minus_uniform=float(candidate["dti"] - uniform["dti"]),
        )
        rows.append(fold_row)
        print(f"fold {fold.index}: frozen={frozen_per_fold[fold.index]:.6f} "
              f"fresh={baseline['dti']:.6f} gated={candidate['dti']:.6f} "
              f"uniform={uniform['dti']:.6f} delta={candidate['dti'] - baseline['dti']:+.6f} "
              f"area={area_share:.3f} auc={auc:.4f} ({time.time() - started:.0f}s)", flush=True)
        del field_hd, field_hh, field, score, random_score

    fresh = np.asarray([row["outputs"]["fresh_ungated_hh_hd"]["dti"] for row in rows])
    gated = np.asarray([row["outputs"]["stage1_q10_hh_hd_candidate"]["dti"] for row in rows])
    uniform = np.asarray([row["outputs"]["same_domain_uniform_spaced"]["dti"] for row in rows])
    delta = gated - fresh
    delta_uniform = gated - uniform
    approved_share = float(np.mean([row["stage1"]["approved_area_share_in_block"] for row in rows]))
    mean_lift = float(1.0 / max(approved_share, 1e-12))
    reproduces = abs(float(fresh.mean()) - FROZEN_BEST) <= REPRO_TOLERANCE
    non_dominant = bool(approved_share >= (2.0 / 3.0) and mean_lift <= 1.5
                        and all(row["stage1"]["candidate_dots_inside_approved_share"] == 1.0
                                for row in rows))
    pass_rules = dict(
        fresh_ungated_reproduces_frozen=bool(reproduces),
        q10_mean_beats_frozen_ungated_best=bool(gated.mean() > FROZEN_BEST),
        q10_mean_beats_fresh_ungated=bool(gated.mean() > fresh.mean()),
        paired_delta_positive_at_least_4_of_6=bool(delta.mean() > 0.0 and int((delta > 0).sum()) >= 4),
        all_candidate_points_inside_stage1_mask=bool(all(
            row["stage1"]["candidate_dots_inside_approved_share"] == 1.0 for row in rows)),
        stage1_not_dominant=non_dominant,
        beats_same_domain_uniform_by_002=bool(delta_uniform.mean() >= 0.002),
    )
    promoted = bool(all(pass_rules.values()))
    summary = dict(
        frozen_ungated_best_mean=FROZEN_BEST,
        fresh_ungated_mean=float(fresh.mean()),
        fresh_minus_frozen_mean=float(fresh.mean() - FROZEN_BEST),
        q10_constrained_mean=float(gated.mean()),
        q10_minus_frozen_mean=float(gated.mean() - FROZEN_BEST),
        q10_minus_fresh_ungated_mean=float(delta.mean()),
        q10_minus_uniform_mean=float(delta_uniform.mean()),
        uniform_spaced_mean=float(uniform.mean()),
        auc_mean=float(np.mean([row["stage2_inblock_auc"] for row in rows])),
        q10_approved_area_share_in_block_mean=approved_share,
        q10_implied_confinement_lift=mean_lift,
        positive_paired_folds=int((delta > 0).sum()),
        q10_per_fold=[float(x) for x in gated],
        ungated_per_fold=[float(x) for x in fresh],
        uniform_per_fold=[float(x) for x in uniform],
        paired_deltas=[float(x) for x in delta],
        paired_uniform_deltas=[float(x) for x in delta_uniform],
    )
    receipt = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        candidate="H53-A Stage-1 q10 physical residual gate + unchanged H-D/H-H Stage 2",
        status="PROMOTED_LOCAL_PROXY_ONLY" if promoted else "NOT_PROMOTED_NO_SUBMISSION_SLOT",
        instrument="six contiguous 3x3 spatial blocks; visible known-fault catalogue proxy truth; not hidden organizer labels",
        stage1_evidence=str(STAGE1_RECEIPT.relative_to(ROOT)),
        stage2_protocol=dict(
            fold_count=len(folds), buffer_px=12, negatives=NEGATIVES,
            negative_seed="1000 + fold.index", HGB_iterations=250,
            blend="0.5 fresh H-D + 0.5 fresh H-H probabilities",
            features=dict(hd=json.loads(HD_NAMES.read_text()),
                          hh=json.loads(HH_NAMES.read_text())),
            score_domain="ungated fold block minus 2px known-catalogue exclusion",
            stage1_role="emission-domain constraint only; no Stage-1 score in model fit or STE rank field",
            STE="max ridge scales 1/2/3.5px; line accumulator L9, 12 orientations; rank(field)^0.65 * rank(accumulator)^0.35; greedy spacing 2.4px",
            fixed_mass_ratio=MASS_RATIO,
            dot_budget="round(3.47 * heldout visible-catalogue pixels)",
            known_exclusion_px=KNOWN_EXCLUSION_PX,
            uniform_control="seeded uniform random rank on the same q10-allowed pixels with identical spacing and dot budget",
        ),
        baseline=dict(frozen_best_mean=FROZEN_BEST,
                     frozen_best_per_fold=[float(x) for x in frozen_per_fold],
                     reproduction_tolerance=REPRO_TOLERANCE),
        summary=summary,
        promotion_rules=pass_rules,
        promoted=promoted,
        per_fold=rows,
        source_references=dict(
            competition_metric="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            kreemer_equation="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf",
            preregistration="evidence/candidate_hypotheses_budget_q10_prereg_20261008.json",
        ),
        limitations=[
            "The six-fold visible-catalogue proxy cannot establish hidden-label performance or organizer score.",
            "The Stage-1 physical residual has weak/zero observed spatial enrichment in this catalogue proxy; Stage-2 is independently reported.",
            "A pass on this holdout is a local research gate only, not portal acceptance or permission implied by any leaderboard score.",
            "No TIFF is generated by this validation script. A later research artifact must pass fresh normalization, byte/grid checks, and the configured uniqueness gate.",
        ],
    )
    OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=receipt["status"], summary=summary,
                          promotion_rules=pass_rules,
                          evidence=str(OUT.relative_to(ROOT))), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
