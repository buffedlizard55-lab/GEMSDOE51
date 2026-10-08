#!/usr/bin/env python3
"""Build a new H53-A diagnostic GeoTIFF after holdout; never label it upload-safe.

The output is a fresh full-map fit of the existing H-D/H-H Stage-2 detector,
constrained to a q10 mask made from the preregistered H53-A componentwise
strain-budget residual. It does not read or reuse any previous prediction
raster. H53-A did not clear the local promotion rule, so the only permitted role
of this file is research/audit. It is written under docs/downloads solely to
make the warning and verification record visible; no competition slot is used.
"""
from __future__ import annotations

import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import trace_emission as te  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.stage1_residual import (  # noqa: E402
    approved_domain,
    combined_deficit_rank,
    component_residual,
)
from gems51.strain_budget import observed_tiles  # noqa: E402
from gems51.submission import verify, write_tif  # noqa: E402
from gems51.uniqueness import run_gate  # noqa: E402
from gems51.vector_budget import budget, summaries  # noqa: E402

P = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
SEGMENTS = ROOT / "registry" / "official" / "trace_segments_utm11.csv"
STAGE1_RECEIPT = ROOT / "evidence" / "h53_stage1_holdout_20261008.json"
STAGE2_RECEIPT = ROOT / "evidence" / "h53_stage2_holdout_20261008.json"
DOT_BUDGET = 44_069
UNIT_FACTOR = 1e-8
Q10 = 10.0
SPACING = 2.4


def _load_group(group: str) -> tuple[list[str], list[np.ndarray]]:
    names_path = P / f"arm_{group}_names.json"
    data_path = P / f"arm_{group}.dat"
    if not names_path.is_file() or not data_path.is_file():
        raise SystemExit(f"missing Stage-2 feature group {group}; run scripts/build_arm_extras.py")
    names = json.loads(names_path.read_text(encoding="utf-8"))
    mm = np.memmap(data_path, dtype=np.float32, mode="r",
                   shape=(len(names), *GRID.shape))
    return names, [np.asarray(mm[i], dtype=np.float32) for i in range(len(names))]


def _load_observations() -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(RAW / "training_features.tif") as src:
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        arrays = []
        for name in ("geod_dilaterate", "geod_shearrate"):
            if name not in descriptions:
                raise SystemExit(f"missing official geodetic input band {name}")
            value = src.read(descriptions.index(name) + 1).astype(np.float32)
            value[value <= -1e38] = np.nan
            arrays.append(value)
    return arrays[0], arrays[1]


def _ste_score(field: np.ndarray, domain: np.ndarray) -> np.ndarray:
    dom = np.asarray(domain, dtype=bool) & np.isfinite(field)
    safe = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    response = np.zeros(GRID.shape, dtype=np.float32)
    for sigma in (1.0, 2.0, 3.5):
        ridge, _ = te.ridge_response(safe, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = te._rank01(safe, dom)
    accumulated, _ = te.line_accumulate(response, length=9, n_orient=12)
    accumulated_rank = te._rank01(accumulated, dom)
    return (raw_rank ** 0.65 * accumulated_rank ** 0.35).astype(np.float32)


def _fit_full_arm(stack: Stack, positives: np.ndarray, negatives: np.ndarray,
                  extra: list[np.ndarray], seed: int) -> np.ndarray:
    rng = np.random.default_rng(1053)
    X, y = stack.sample(positives, negatives, 250_000, rng, extra=extra)
    model = fit_detector(X, y, seed=seed, max_iter=250)
    del X, y
    result = predict_grid(model, stack, positives | negatives, extra=extra)
    del model
    return result


def _prior_paths(candidate_path: Path) -> dict[str, Path]:
    paths = {}
    for root in (ROOT / "data" / "prior", ROOT / "data" / "refs",
                 ROOT / "docs" / "downloads", ROOT / "submissions",
                 ROOT / "archive" / "submissions"):
        if not root.exists():
            continue
        for path in root.rglob("*.tif"):
            if path.resolve() != candidate_path.resolve():
                paths[path.relative_to(ROOT).as_posix()] = path
    return paths


def main() -> int:
    for path in (STAGE1_RECEIPT, STAGE2_RECEIPT):
        if not path.is_file():
            raise SystemExit(f"required holdout receipt missing: {path.relative_to(ROOT)}")
    stage1_holdout = json.loads(STAGE1_RECEIPT.read_text(encoding="utf-8"))
    stage2_holdout = json.loads(STAGE2_RECEIPT.read_text(encoding="utf-8"))
    if stage1_holdout.get("status") != "STAGE1_SPATIAL_HOLDOUT_COMPLETED; STAGE2_PENDING":
        raise SystemExit("unexpected Stage-1 receipt status; inspect before building")
    # The diagnostic build is explicitly permitted after a no-go only as a
    # visibly marked research artifact. It cannot be promoted by this script.
    if stage2_holdout.get("promoted") is not False:
        raise SystemExit("this no-go research builder is only for the recorded non-promoted H53-A result")

    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool) & footprint
    if footprint.shape != GRID.shape or catalogue.shape != GRID.shape:
        raise SystemExit("prepared masks differ from the registered competition grid")
    if not footprint.any() or not catalogue.any():
        raise SystemExit("prepared footprint/catalogue is empty")

    hd_names, hd_extra = _load_group("hd")
    hh_names, hh_extra = _load_group("hh")
    segment_frame = pd.read_csv(SEGMENTS)
    tensor, budget_meta = budget(segment_frame, convention="fault_plane")
    modeled = summaries(*tensor)
    observed_dil_pix, observed_shear_pix = _load_observations()
    observed_dil = observed_tiles(observed_dil_pix, footprint, 100)
    observed_shear = observed_tiles(observed_shear_pix, footprint, 100)
    support = observed_tiles(np.ones(GRID.shape, dtype=np.float32), footprint, 100)
    valid_tiles = (np.isfinite(observed_dil) & np.isfinite(observed_shear)
                   & np.isfinite(support) & (support > 0.05))
    residual_dil = component_residual(observed_dil, modeled["dilatation"], UNIT_FACTOR)
    residual_shear = component_residual(observed_shear, modeled["shear"], UNIT_FACTOR)
    score_tiles = combined_deficit_rank(residual_dil, residual_shear, valid_tiles)
    score_pixels = np.repeat(np.repeat(score_tiles, 100, axis=0), 100, axis=1)
    score_pixels = score_pixels[:GRID.shape[0], :GRID.shape[1]]
    approved, q10_threshold = approved_domain(score_pixels, footprint, Q10)
    area_share = float((approved & footprint).sum() / max(int(footprint.sum()), 1))

    stack = Stack(P)
    positives = catalogue
    negatives = footprint & ~catalogue
    field_hd = _fit_full_arm(stack, positives, negatives, hd_extra, seed=53)
    field_hh = _fit_full_arm(stack, positives, negatives, hh_extra, seed=53)
    field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
             + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
    del field_hd, field_hh
    known_exclusion = ndi.distance_transform_edt(~catalogue) <= 2.0
    stage2_domain = footprint & ~known_exclusion & np.isfinite(field)
    allowed = stage2_domain & approved
    score = _ste_score(field, stage2_domain)
    ys, xs = te.spaced_dots(score, allowed, DOT_BUDGET, spacing=SPACING)
    if len(ys) != DOT_BUDGET:
        raise SystemExit(f"full-map allowed domain starved the fixed mass budget: {len(ys)}/{DOT_BUDGET}")
    if not np.all(approved[ys, xs]):
        raise SystemExit("a generated point escaped the full-map Stage-1 q10 mask")
    if not np.all(stage2_domain[ys, xs]):
        raise SystemExit("a generated point escaped the known-catalogue exclusion/domain")

    prediction = np.zeros(GRID.shape, dtype=np.float32)
    prediction[ys, xs] = 1.0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"gemsdoe51-h53a-budget-q10-hd-hh-r44069-{stamp}-RESEARCH-ONLY-DO-NOT-SUBMIT"
    target = ROOT / "docs" / "downloads" / f"{stem}.tif"
    zip_path = target.with_suffix(".zip")
    format_report = write_tif(target, prediction, footprint, outside=0.0, nodata=None)
    rechecked = verify(target, footprint)
    with rasterio.open(target) as src:
        saved = src.read(1)
    outside_zeros = bool(np.all(saved[~footprint] == 0.0))
    binary_inside = bool(np.isin(saved[footprint], (0.0, 1.0)).all())
    all_finite = bool(np.isfinite(saved).all())
    all_in_range = bool(((saved >= 0.0) & (saved <= 1.0)).all())
    if not (rechecked["checks"]["format_valid"] and outside_zeros
            and binary_inside and all_finite and all_in_range
            and int((saved > 0).sum()) == DOT_BUDGET):
        target.unlink(missing_ok=True)
        raise SystemExit("normalized GeoTIFF failed the post-write format/range/mass checks")

    stage2_summary = stage2_holdout["summary"]
    uniform_control = dict(
        candidate_mean=stage2_summary["q10_constrained_mean"],
        uniform_mean=stage2_summary["uniform_spaced_mean"],
        source="six-fold Stage-2 q10 holdout; not a score on the full-map TIFF",
    )
    local_gate = run_gate(
        target,
        _prior_paths(target),
        saved > 0,
        footprint,
        stage1_approved=approved,
        hard_confined=True,
        uniform_control=uniform_control,
        uniform_margin=0.002,
    ).as_dict()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(target, arcname=target.name)
    with zipfile.ZipFile(zip_path) as archive:
        zip_names = archive.namelist()
        zip_test = archive.testzip()
        zipped_bytes = archive.read(target.name)
    if zip_names != [target.name] or zip_test is not None or zipped_bytes != target.read_bytes():
        zip_path.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise SystemExit("single-TIFF ZIP integrity check failed")

    receipt = dict(
        schema_version=1,
        generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        artifact_id=f"GEMSDOE51-H53A-BUDGET-Q10-R44069-{stamp}",
        role="RESEARCH_ONLY",
        status="NOT_FOR_SUBMISSION",
        safe_to_submit=False,
        banner="RESEARCH ONLY — NOT PROMOTED ON THE SIX-FOLD HOLDOUT — DO NOT SUBMIT",
        file=str(target.relative_to(ROOT)),
        zip=str(zip_path.relative_to(ROOT)),
        sha256=format_report["sha256"],
        bytes=format_report["bytes"],
        source="Fresh full-map Stage-2 model fit from competition layers + H-D/H-H features; no previous prediction TIFF was used as model input.",
        build=dict(
            stage2="0.5 fresh H-D + 0.5 fresh H-H fitted on all visible known-fault catalogue pixels and 250000 seeded background pixels per arm; 250 HGB iterations.",
            stage2_seed=53,
            negative_sampling_seed=1053,
            feature_groups=dict(hd=hd_names, hh=hh_names),
            emission="STE ridge scales 1/2/3.5 px; line accumulator length 9, exponent 0.35; greedy spacing 2.4 px.",
            stage1="H53-A componentwise dimensional geodetic-minus-fault residual, 10 km tiles, fault_plane rate assumption, 1e-8 unit factor, fixed q10 allowed domain.",
            stage1_q10_threshold=float(q10_threshold),
            stage1_approved_area_share=area_share,
            stage1_emitted_point_share_inside_approved=float(np.mean(approved[ys, xs])),
            stage1_lift_over_approved_area=float(1.0 / max(area_share, 1e-12)),
            source_segments=len(segment_frame),
            fault_budget=budget_meta,
            dot_budget=DOT_BUDGET,
            dot_budget_note="Fixed to match existing local-best artifact mass; not an estimate of hidden truth size.",
            emitted_points=int(len(ys)),
            outside_footprint="finite zeros",
            dtype="float32",
            values="binary 0/1 probabilities",
        ),
        holdout=dict(
            stage1_receipt=str(STAGE1_RECEIPT.relative_to(ROOT)),
            stage1_primary_summary=stage1_holdout["summary"]["fault_plane_1e-08"]["combined_residual_prior"],
            stage2_receipt=str(STAGE2_RECEIPT.relative_to(ROOT)),
            stage2_promoted=bool(stage2_holdout["promoted"]),
            stage2_mean_q10=float(stage2_summary["q10_constrained_mean"]),
            stage2_frozen_ungated_best=float(stage2_summary["frozen_ungated_best_mean"]),
            stage2_q10_minus_frozen=float(stage2_summary["q10_minus_frozen_mean"]),
            stage2_gate_failures=[name for name, passed in stage2_holdout["promotion_rules"].items() if not passed],
            visible_known_fault_proxy_only=True,
            hidden_organizer_score=None,
            portal_acceptance=None,
        ),
        format=dict(
            checks=rechecked["checks"],
            outside_footprint_finite_zero=outside_zeros,
            binary_inside_footprint=binary_inside,
            all_cells_finite=all_finite,
            all_values_in_0_1=all_in_range,
            zip_entries=zip_names,
            zip_test_error=zip_test,
            zip_bytes_match_tiff=zipped_bytes == target.read_bytes(),
        ),
        local_available_artifact_gate=local_gate,
        broad_family_uniqueness="PENDING; run scripts/run_public_uniqueness_audit.py against the pinned 54-repository corpus.",
        limitations=[
            "The six-fold H53-A holdout did not promote: fresh ungated baseline reproduction exceeded its frozen tolerance, q10 mean did not beat the frozen/local ungated best, and paired q10 gating was non-positive.",
            "Stage-1 q10 residual prior had approximately 1.0 recall-over-area lift and weak tile association on visible-catalogue proxy truth.",
            "The full-map TIFF is a research diagnostic only; do not use a weekly/competition submission slot.",
            "Local format validity is not organizer portal acceptance; no hidden-test score is known.",
            "Uniqueness must be cleared separately against the full pinned public artifact inventory; local checks alone are not global proof.",
            "The scalar residual may represent off-fault deformation, aseismic motion, or slip-rate/dip/rake/unit/geometry/geodetic/model error."
        ],
    )
    out = ROOT / "evidence" / f"h53_artifact_{stamp}.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    checks_copy = target.with_name(target.stem + "-checks.json")
    checks_copy.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(
        artifact=receipt["artifact_id"],
        file=receipt["file"],
        zip=receipt["zip"],
        safe_to_submit=False,
        points=receipt["build"]["emitted_points"],
        stage1_area_share=area_share,
        local_uniqueness_verdict=local_gate["verdict"],
        format_valid=rechecked["checks"]["format_valid"],
        receipt=str(out.relative_to(ROOT)),
    ), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
