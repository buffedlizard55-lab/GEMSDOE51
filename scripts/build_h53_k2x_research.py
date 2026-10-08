#!/usr/bin/env python3
"""Build a fresh H53-K2x research-only GeoTIFF after its failed holdout.

This is deliberately not a submission builder. It refuses to run before a
completed, failed six-fold receipt, fits new full-catalogue models, recomputes
source-corrected Stage-1 q10 tiles, confines the fixed STE point budget to those
tiles, and labels every output NOT FOR SUBMISSION. It never reads an old TIFF
as prediction input and never authorizes or consumes a competition slot.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from gems51.detector import Stack  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.submission import verify, write_tif  # noqa: E402
from scripts.build_submission_hh_blend import (  # noqa: E402
    fit_full_field,
    load_observed,
    stage1_prior,
)
from scripts.evaluate_h53_k2x_holdout import _ste_emit  # noqa: E402
from gems51 import strain_budget as sb  # noqa: E402

P = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"
HOLDOUT = ROOT / "evidence" / "h53_k2x_holdout_20261008.json"
STAGE1_REFERENCE = ROOT / "evidence" / "official_vector_budget_20261007.json"
N_DOTS = 44_069


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def open_arm(group: str):
    names_path = P / f"arm_{group}_names.json"
    data_path = P / f"arm_{group}.dat"
    if not names_path.is_file() or not data_path.is_file():
        raise SystemExit(f"prepared {group} arm missing; run build_arm_extras.py --group {group}")
    names = json.loads(names_path.read_text())
    if len(names) == 0:
        raise SystemExit(f"prepared {group} arm has no features")
    mm = np.memmap(data_path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return names, mm, [np.asarray(mm[i], dtype=np.float32) for i in range(len(names))]


def main() -> int:
    if not HOLDOUT.is_file() or not STAGE1_REFERENCE.is_file():
        raise SystemExit("completed H53 holdout and separate official-vector Stage-1 receipt are required")
    holdout = json.loads(HOLDOUT.read_text())
    if len(holdout.get("rows", [])) != 6 or holdout.get("local_holdout_gate_passed") is not False:
        raise SystemExit("research builder requires the completed six-fold NOT-PROMOTED H53 result")
    if holdout.get("submission_slot_authorized") is not False:
        raise SystemExit("refusing build: holdout receipt does not explicitly block the competition slot")

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    if footprint.shape != GRID.shape or catalogue.shape != GRID.shape:
        raise SystemExit("prepared footprint/catalogue do not match the official submission grid")
    stack = Stack(P)

    hd_names, hd_mm, hd_extra = open_arm("hd")
    hh_names, hh_mm, hh_only = open_arm("hh")
    k2_names, k2_mm, k2_only = open_arm("h53_k2x")
    if len(hd_names) != 4 or len(hh_names) != 5 or k2_names != ["h53_k2x_min_s2s5"]:
        raise SystemExit("full-map H-D/H-H/K2x feature schema differs from frozen holdout")
    hh_extra = hd_extra + hh_only
    candidate_extra = hd_extra + hh_only + k2_only

    # Fixed new seeds are for a single reproducible research rendering only.
    # They do not replace, re-score, or tune the preregistered six-fold result.
    t0 = time.time()
    print("fitting full-catalogue H-D model", flush=True)
    field_hd = fit_full_field(stack, footprint, catalogue, hd_extra,
                              seed=20261008, neg=250_000, max_iter=250)
    print("fitting full-catalogue H-H+H53-K2x model", flush=True)
    field_h53 = fit_full_field(stack, footprint, catalogue, candidate_extra,
                               seed=20261009, neg=250_000, max_iter=250)
    field = (0.5 * np.nan_to_num(field_hd, nan=0.0, posinf=0.0, neginf=0.0)
             + 0.5 * np.nan_to_num(field_h53, nan=0.0, posinf=0.0, neginf=0.0)).astype(np.float32)
    del field_hd, field_h53

    stage1 = stage1_prior(
        catalogue, footprint, sb.load_slip_rates(ROOT / "data" / "raw"),
        load_observed(), tile_px=100, q=10.0,
    )
    approved = np.asarray(stage1["approved"], dtype=bool)
    area_share = float(np.count_nonzero(approved & footprint) / max(np.count_nonzero(footprint), 1))
    if area_share < 2.0 / 3.0 or 1.0 / max(area_share, 1e-12) > 1.5:
        raise SystemExit(f"full-map q10 Stage-1 gate violates preregistered broadness: area={area_share:.6f}")

    distance_from_known = ndi.distance_transform_edt(~catalogue)
    allowed = footprint & approved & (distance_from_known > 2.0)
    ys, xs = _ste_emit(field, allowed, N_DOTS)
    if len(ys) != N_DOTS:
        raise SystemExit(f"q10 domain could not supply fixed {N_DOTS}-point budget (got {len(ys)})")
    support = np.zeros(GRID.shape, dtype=bool)
    support[ys, xs] = True
    if np.any(support & ~approved) or np.any(support & ~footprint):
        raise SystemExit("full-map H53 emission escaped the q10-approved footprint")
    if np.any(support & (distance_from_known <= 2.0)):
        raise SystemExit("emission violates the fixed 2-pixel known-catalogue exclusion")

    # Diagnose how much the broad Stage-1 domain changed the fixed detector's
    # output. This is not used for tuning or scoring.
    ungated = footprint & (distance_from_known > 2.0)
    uy, ux = _ste_emit(field, ungated, N_DOTS)
    ungated_support = np.zeros(GRID.shape, dtype=bool)
    ungated_support[uy, ux] = True
    intersection = int(np.count_nonzero(support & ungated_support))
    union = int(np.count_nonzero(support | ungated_support))
    stage1_diag = dict(
        q=10.0,
        tile_px=100,
        approved_area_share=area_share,
        implied_lift_if_all_points_inside=1.0 / max(area_share, 1e-12),
        emitted_points=int(support.sum()),
        points_inside_approved=int(np.count_nonzero(support & approved)),
        points_outside_approved=int(np.count_nonzero(support & ~approved)),
        emitted_share_inside_approved=float(np.count_nonzero(support & approved) / support.sum()),
        approved_pixel_occupancy=float(support.sum() / max(np.count_nonzero(approved), 1)),
        ungated_support_jaccard=intersection / max(union, 1),
        fraction_gated_points_also_ungated=intersection / max(int(support.sum()), 1),
        formula="source-corrected official QFault vector budget; 10-km tile, q10 of ranked observed geodetic second-invariant minus ranked budget second invariant; broad hard domain, Stage-2 score weight zero",
        all_points_confined=bool(np.all(support <= (approved & footprint))),
        receipt="evidence/official_vector_budget_20261007.json",
    )
    if stage1_diag["points_inside_approved"] != N_DOTS:
        raise SystemExit("Stage-1 confinement count did not equal the complete dot budget")

    support_hash = sha256_bytes(support.tobytes())
    digest = support_hash[:12]
    base = f"gemsdoe51-h53-k2x-q10-{digest}-zeros"
    target = DOCS / f"{base}.tif"
    zip_path = DOCS / f"{base}.zip"
    checks_path = DOCS / f"{base}-checks.json"
    artifact_path = ROOT / "evidence" / "h53_k2x_artifact_20261008.json"
    if any(p.exists() for p in (target, zip_path, checks_path, artifact_path)):
        raise SystemExit("refusing to overwrite an existing H53 artifact or receipt")

    submission_name = f"GEMSDOE51-H53-K2X-Q10-20261008-{digest.upper()}"
    note = (
        "RESEARCH ONLY / NOT FOR SUBMISSION: H53-K2x rank-space conductive anisotropy + H-D/H-H blend; "
        "q10 official-vector tile gate; STE L9, 44,069 points. Holdout failed; do not upload."
    )
    fmt = write_tif(target, support.astype(np.float32), footprint, outside=0.0, nodata=None)
    with rasterio.open(target, "r+") as dst:
        dst.update_tags(
            COMPETITION_NAME=submission_name,
            COMMENT=note,
            EXPERIMENT="H53-K2x; research-only full-catalogue inference",
            HOLDOUT="NOT_PROMOTED; visible known-fault catalogue proxy only",
            STAGE1="source-corrected official-vector q10 hard domain",
        )
    # Re-check the tagged final bytes, not the pre-tag temporary state.
    fmt = verify(target, footprint)
    if not fmt["checks"]["all_cells_finite_in_range"] or not fmt["checks"]["format_valid"]:
        raise SystemExit("local GeoTIFF checks failed; artifact is not publishable for research download")
    if fmt["checks"]["predicted_px"] != N_DOTS:
        raise SystemExit("final-byte support differs from the preregistered point budget")
    with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(target, arcname=target.name)
    with zipfile.ZipFile(zip_path, "r") as zf:
        if zf.namelist() != [target.name]:
            raise SystemExit("research ZIP must contain exactly one TIFF")

    stage1_reference = json.loads(STAGE1_REFERENCE.read_text())["holdout"]
    record = dict(
        schema_version=1,
        id="H53_K2X_Q10_RESEARCH_20261008",
        role="RESEARCH_ONLY",
        status="NOT_FOR_SUBMISSION",
        file=target.name,
        zip=zip_path.name,
        checks_file=checks_path.name,
        submission_name=submission_name,
        note=note,
        sha256=fmt["sha256"],
        bytes=fmt["bytes"],
        support_sha256=support_hash,
        format=fmt,
        holdout=dict(
            evidence="evidence/h53_k2x_holdout_20261008.json",
            candidate_mean=holdout["candidate_result"]["stage1_q10_gated_mean_dti"],
            baseline_mean=holdout["baseline"]["stage1_q10_gated_mean_dti"],
            paired_delta=holdout["candidate_result"]["paired_mean_delta_vs_stage1_gated_hd_hh"],
            folds_higher=holdout["candidate_result"]["positive_folds_vs_stage1_gated_hd_hh"],
            folds_total=6,
            frozen_best=holdout["baseline"]["frozen_mean_dti"],
            candidate_minus_frozen_best=(holdout["candidate_result"]["stage1_q10_gated_mean_dti"]
                                         - holdout["baseline"]["frozen_mean_dti"]),
            fresh_baseline=holdout["baseline"]["fresh_ungated_mean_dti"],
            frozen_baseline=holdout["baseline"]["frozen_mean_dti"],
            baseline_drift=holdout["baseline"]["fresh_minus_frozen_mean"],
            baseline_tolerance=holdout["baseline"]["reproduction_tolerance"],
            baseline_reproduced=holdout["baseline"]["reproduced"],
            holdout_gate_passed=holdout["local_holdout_gate_passed"],
        ),
        stage1=stage1_diag,
        stage1_trace_holdout=dict(
            evidence="evidence/official_vector_budget_20261007.json",
            instrument=stage1_reference["instrument"],
            mean_approved_area=float(stage1_reference["mean_area"]),
            heldout_trace_recall=float(stage1_reference["mean_recall"]),
            heldout_trace_lift=float(stage1_reference["mean_lift"]),
            score_type="separate Stage-1 trace-recall/lift; not Stage-2 DTI",
        ),
        model=dict(
            training="all visible known-fault catalogue pixels; 250,000 sampled non-catalogue pixels",
            feature_arms=dict(H_D=hd_names, H_H=hh_names, H53_K2x=k2_names),
            negative_sample_seeds=[20261008, 20261009],
            model_seeds=[20261008, 20261009],
            hgb_max_iter=250,
            blend="0.5 H-D + 0.5 H-H+H53-K2x probabilities",
            emission="STE scales 1/2/3.5 px, L9, continuity exponent 0.35, spacing 2.4 px",
            point_budget=N_DOTS,
            point_budget_is_organizer_truth_count=False,
        ),
        source="Fresh fitted model predictions; no prior TIFF was used as input.",
        decision="Research download only. The frozen H53 holdout did not promote; no competition slot is authorized.",
        portal_acceptance="NOT TESTED. Local grid/range checks do not establish organizer portal acceptance; official outside-footprint language and local all-finite zero encoding are not treated as reconciled.",
        elapsed_seconds=float(time.time() - t0),
        limitations=[
            "Visible known-fault labels are proxy training/holdout truth, not the hidden expert labels.",
            "The fresh full-catalogue point map is not itself a holdout score; six-fold results belong to the separate receipt.",
            "The supplied cond_surf unit, depth sensitivity, inversion and layer-specific source are undocumented in the local mirror; the feature operates on empirical ranks only.",
            "Electrical conductivity is non-unique and the cited fault-conductor studies are site-specific.",
            "The full-map Stage-1 q10 gate is a coarse hard domain; its physical assumptions and ambiguities remain in the separate receipt.",
            "Local format validity is not portal acceptance; no upload, score or submission-slot use occurred.",
        ],
    )
    record["zip_sha256"] = sha256_file(zip_path)
    record["zip_bytes"] = zip_path.stat().st_size
    artifact_path.write_text(json.dumps(record, indent=2) + "\n")
    checks_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
