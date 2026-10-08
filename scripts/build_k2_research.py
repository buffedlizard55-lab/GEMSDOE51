#!/usr/bin/env python3
"""Build one genuinely new K2 full-map diagnostic GeoTIFF, research-only.

This writer is intentionally not an upload builder. It requires the completed
K2 holdout receipt and, if the candidate is not promoted, writes only an
artifact whose filename, TIFF tags, and receipt say RESEARCH ONLY — DO NOT
SUBMIT. A local format pass is not organizer portal validation.
"""
from __future__ import annotations

import hashlib
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
from gems51.submission import verify, write_tif  # noqa: E402
from gems51.trace_emission import line_accumulate, ridge_response, spaced_dots  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"
HOLDOUT = ROOT / "evidence" / "k2_spatial_holdout_20261008.json"
STAGE1 = ROOT / "evidence" / "physical_stage1_holdout_20261008.json"
FEATURE_META = PREPARED / "arm_k2_metadata.json"
FEATURE_NAMES = [
    "k2_cond_cross_rank_s20", "k2_cond_sign_persist_s20",
    "k2_cond_cross_rank_s50", "k2_cond_sign_persist_s50",
]
OUTPUT = DOCS / "gemsdoe51-k2-08-research-only-20261008.tif"
G_HIDDEN_PLANNING_ESTIMATE = 12_700  # not organizer-published hidden truth mass
MASS_RATIO = 3.47


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_extra(path: Path, names_path: Path, expected_names: list[str]):
    names = json.loads(names_path.read_text())
    if names != expected_names:
        raise SystemExit(f"unexpected feature names in {names_path.name}: {names}")
    expected_bytes = len(names) * GRID.height * GRID.width * 4
    if not path.is_file() or path.stat().st_size != expected_bytes:
        raise SystemExit(f"{path.name} is missing or does not match the fixed grid")
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [np.asarray(mm[i], dtype=np.float32) for i in range(len(names))]


def _fit_full_field(stack: Stack, footprint: np.ndarray, catalogue: np.ndarray,
                    extras: list[np.ndarray], seed: int, label: str) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pool = footprint & ~catalogue
    X, y = stack.sample(catalogue & footprint, pool, 250_000, rng, extra=extras)
    print(f"fit full {label}: X={X.shape} positives={int(y.sum()):,}", flush=True)
    model = fit_detector(X, y, seed=seed, max_iter=250)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras, chunk=128)


def _rank01(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(values.shape, dtype=np.float32)
    selected = values[mask]
    if selected.size:
        order = np.argsort(selected, kind="stable")
        ranks = np.empty(selected.size, dtype=np.float32)
        ranks[order] = np.arange(1, selected.size + 1, dtype=np.float32) / selected.size
        out[mask] = ranks
    return out


def _emit_like_holdout(field: np.ndarray, allowed: np.ndarray, n_dots: int):
    """Match the holdout STE emitter exactly, including q10 scoring domain."""
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


def _load_physical_q10(footprint: np.ndarray):
    path = PREPARED / "physical_stage1_full_q10_t200.npz"
    if not path.is_file():
        raise SystemExit("missing full-map physical Stage-1 q10 cache; run the Stage-1 holdout runner")
    with np.load(path) as data:
        approved = np.asarray(data["approved_mask"], dtype=bool)
        support = np.asarray(data["support"], dtype=bool)
    if approved.shape != GRID.shape or support.shape != GRID.shape:
        raise SystemExit("physical Stage-1 cache does not match the fixed competition grid")
    if np.any(approved & ~support) or np.any(support & ~footprint):
        raise SystemExit("physical Stage-1 q10 mask escaped its common valid footprint")
    receipt = json.loads(STAGE1.read_text())
    expected_area = float(receipt["full_map_prior"]["approved_area_fraction"])
    actual_area = float(approved.sum() / max(int(support.sum()), 1))
    if not np.isclose(expected_area, actual_area, rtol=0.0, atol=1e-12):
        raise SystemExit("physical Stage-1 full-map mask does not match its measured receipt")
    return approved, support, receipt


def main() -> int:
    if not HOLDOUT.is_file() or not STAGE1.is_file() or not FEATURE_META.is_file():
        raise SystemExit("K2 holdout, physical Stage-1, and feature metadata receipts are required")
    holdout = json.loads(HOLDOUT.read_text())
    if holdout.get("candidate_id") != "GEMSDOE51-K2-08-conductive-ribbon":
        raise SystemExit("holdout receipt is not the frozen K2-08 experiment")
    if holdout.get("promoted_local_proxy_only") is True:
        raise SystemExit(
            "this writer is research-only; a locally promoted candidate requires a separate "
            "reviewed upload builder and portal validation"
        )
    existing_output = OUTPUT.exists()

    t0 = time.time()
    footprint = np.load(PREPARED / "footprint.npy").astype(bool)
    catalogue = np.load(PREPARED / "catalogue.npy").astype(bool)
    if footprint.shape != GRID.shape or catalogue.shape != GRID.shape:
        raise SystemExit("prepared footprint or catalogue is not on the competition grid")
    approved, support, stage1_receipt = _load_physical_q10(footprint)

    feature_meta = json.loads(FEATURE_META.read_text())
    if feature_meta.get("candidate_id") != "GEMSDOE51-K2-08-conductive-ribbon":
        raise SystemExit("K2 feature metadata does not match the preregistered candidate")
    if feature_meta.get("feature_names") != FEATURE_NAMES:
        raise SystemExit("K2 feature channels changed after the frozen holdout")

    hd_names = ["lidrel_facecoh09", "lidrel_facecoh21",
                "detelev_facecoh09", "detelev_facecoh21"]
    hh_names = ["hh_endpoint", "hh_bridge", "hh_bridge_cond",
                "hh_bridge_surface", "hh_endpoint_concordance"]
    hd_extra = _load_extra(PREPARED / "arm_hd.dat", PREPARED / "arm_hd_names.json", hd_names)
    hh_extra = _load_extra(PREPARED / "arm_hh.dat", PREPARED / "arm_hh_names.json", hh_names)
    k2_extra = _load_extra(PREPARED / "arm_k2.dat", PREPARED / "arm_k2_names.json", FEATURE_NAMES)
    stack = Stack(PREPARED)
    distance_to_known = ndi.distance_transform_edt(~catalogue)
    allowed = footprint & support & approved & (distance_to_known > 2.0)
    n_dots = int(round(MASS_RATIO * G_HIDDEN_PLANNING_ESTIMATE))
    area_share = float(approved.sum() / max(int(footprint.sum()), 1))

    if existing_output:
        # Resume only the receipt step for the exact tagged artifact written by
        # this script before an earlier JSON serialization interruption.
        with rasterio.open(OUTPUT) as src:
            tags = src.tags()
            prediction = src.read(1)
        if (tags.get("CANDIDATE_ID") != "GEMSDOE51-K2-08-conductive-ribbon"
                or tags.get("ARTIFACT_STATUS") != "RESEARCH ONLY — DO NOT SUBMIT"
                or tags.get("SAFE_TO_SUBMIT") != "NO"
                or tags.get("HOLDOUT_RECEIPT") != "evidence/k2_spatial_holdout_20261008.json"):
            raise SystemExit(f"refusing to reuse an unrecognized existing artifact: {OUTPUT}")
        final = verify(OUTPUT, footprint)
        if not final["checks"]["format_valid"]:
            raise SystemExit("existing tagged research TIFF no longer passes the local verifier")
    else:
        # Fixed, label-visible supervised fit. The seeds and hidden-mass estimate
        # are recorded; the latter is inherited planning metadata, not a score.
        field_hd = _fit_full_field(stack, footprint, catalogue, hd_extra, 17, "H-D")
        field_hh_k2 = _fit_full_field(stack, footprint, catalogue,
                                      hd_extra + hh_extra + k2_extra, 19, "H-H+K2")
        field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                 + 0.5 * np.nan_to_num(field_hh_k2, nan=0.0)).astype(np.float32)
        field[~footprint] = np.nan
        del field_hd, field_hh_k2

        ys, xs = _emit_like_holdout(field, allowed, n_dots)
        if len(ys) != n_dots:
            raise SystemExit(f"fixed emitter placed {len(ys)} of {n_dots} planned research dots")
        prediction = np.zeros(GRID.shape, dtype=np.float32)
        prediction[ys, xs] = 1.0
        if np.any((prediction > 0) & ~allowed):
            raise SystemExit("range/domain guard: an emitted point lies outside the physical q10 allowed domain")
        if not np.isfinite(prediction[footprint]).all():
            raise SystemExit("range guard: non-finite in-footprint value")
        if prediction[footprint].min() < 0.0 or prediction[footprint].max() > 1.0:
            raise SystemExit("range guard: in-footprint predictions escaped [0,1]")

        # Construct exactly one fresh, one-band Float32 file. NaN is used only
        # outside the official footprint; local checks validate serialized bytes.
        DOCS.mkdir(parents=True, exist_ok=True)
        staging = DOCS / f".{OUTPUT.stem}.staging.tif"
        try:
            rec = write_tif(staging, prediction, footprint, outside=np.nan, nodata=np.nan)
            if not rec["checks"]["format_valid"]:
                raise SystemExit("staging GeoTIFF failed the local official-format verifier")
            with rasterio.open(staging, "r+") as dst:
                dst.set_band_description(1, "fault point indicator — RESEARCH ONLY — DO NOT SUBMIT")
                dst.update_tags(
                    CANDIDATE_ID="GEMSDOE51-K2-08-conductive-ribbon",
                    ARTIFACT_STATUS="RESEARCH ONLY — DO NOT SUBMIT",
                    SAFE_TO_SUBMIT="NO",
                    HOLDOUT_STATUS=holdout["status"],
                    HOLDOUT_RECEIPT="evidence/k2_spatial_holdout_20261008.json",
                    PHYSICAL_STAGE1="q10 20 km tile gate; all emitted points confined",
                    PREDICTION_ENCODING="binary STE point support, float32 0/1 inside footprint",
                    PORTAL_VALIDATION="NOT PERFORMED",
                )
            rec = verify(staging, footprint)
            if not rec["checks"]["format_valid"]:
                raise SystemExit("tagged staging GeoTIFF failed the local format verifier")
            if not rec["checks"]["outside_footprint_nan"]:
                raise SystemExit("format guard: expected NaN/null outside the footprint")
            if rec["checks"]["min_value"] < 0.0 or rec["checks"]["max_value"] > 1.0:
                raise SystemExit("format guard: serialized in-footprint values violate [0,1]")
            with rasterio.open(staging) as src:
                serialized = src.read(1)
                if not np.isfinite(serialized[footprint]).all():
                    raise SystemExit("serialized range guard: non-finite value inside footprint")
                if np.any((serialized[footprint] < 0.0) | (serialized[footprint] > 1.0)):
                    raise SystemExit("serialized range guard: value outside [0,1] inside footprint")
                if not np.isnan(serialized[~footprint]).all():
                    raise SystemExit("serialized footprint guard: outside cells must be NaN/null")
                if int(np.count_nonzero(serialized[footprint] > 0)) != n_dots:
                    raise SystemExit("serialized footprint guard: emitted point count changed on write")
            staging.replace(OUTPUT)
        finally:
            if staging.exists():
                staging.unlink()
        final = verify(OUTPUT, footprint)
    with rasterio.open(OUTPUT) as src:
        prediction = src.read(1)

    if np.any((prediction > 0) & ~allowed):
        raise SystemExit("artifact contains a point outside the physical q10 allowed domain")
    if not np.isfinite(prediction[footprint]).all():
        raise SystemExit("serialized range guard: non-finite value inside footprint")
    if np.any((prediction[footprint] < 0.0) | (prediction[footprint] > 1.0)):
        raise SystemExit("serialized range guard: value outside [0,1] inside footprint")
    if not np.isnan(prediction[~footprint]).all():
        raise SystemExit("serialized footprint guard: outside cells must be NaN/null")

    inside = int(((prediction > 0) & approved).sum())
    emitted_share = inside / max(n_dots, 1)
    if int(np.count_nonzero(prediction[footprint] > 0)) != n_dots or inside != n_dots:
        raise SystemExit("physical q10 confinement or serialized point-count guard failed")
    lift = emitted_share / max(area_share, 1e-12)
    if lift > 1.5:
        raise SystemExit(f"Stage-1 non-dominance guard failed: lift={lift:.6f}")

    final = verify(OUTPUT, footprint)
    final_json = dict(final)
    if final_json.get("nodata") is not None and np.isnan(final_json["nodata"]):
        final_json["nodata"] = "NaN"
    receipt = dict(
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        status="RESEARCH_ONLY_DO_NOT_SUBMIT",
        safe_to_download_for_inspection=True,
        safe_to_submit=False,
        upload_ready=False,
        portal_validated=False,
        explicit_label="RESEARCH ONLY — DO NOT SUBMIT; local format pass is not portal acceptance",
        candidate_id="GEMSDOE51-K2-08-conductive-ribbon",
        file=str(OUTPUT.relative_to(ROOT)),
        sha256=final["sha256"],
        bytes=final["bytes"],
        holdout=dict(
            receipt="evidence/k2_spatial_holdout_20261008.json",
            status=holdout["status"],
            promoted=holdout.get("promoted_local_proxy_only", False),
            frozen_best=holdout["baseline"]["frozen_hh_hd_ungated_mean_dti"],
            fresh_q10_baseline=holdout["baseline"]["physical_q10_gated_mean_dti"],
            candidate_q10_mean=holdout["candidate_result"]["physical_q10_gated_mean_dti"],
            paired_q10_delta=holdout["candidate_result"]["paired_mean_q10_delta_vs_fresh_hh_hd"],
            positive_folds=holdout["candidate_result"]["positive_q10_folds"],
        ),
        stage1=dict(
            receipt="evidence/physical_stage1_holdout_20261008.json",
            full_map_approved_area_share=area_share,
            emitted_points_inside_approved=inside,
            emitted_points_total=n_dots,
            emitted_share_inside_approved=emitted_share,
            lift_over_area_share=lift,
            full_map_prior=stage1_receipt["full_map_prior"]["cached_arrays"],
            mean_whole_trace_holdout_lift=stage1_receipt["summary"]["mean_held_trace_lift"],
            mean_whole_trace_uniform_dti_delta=stage1_receipt["summary"]["paired_mean_uniform_dti_delta"],
        ),
        model=dict(
            detector="HistGradientBoostingClassifier",
            max_iter=250, negative_samples=250_000,
            seeds=dict(hd=17, hh_plus_k2=19),
            probability_blend="0.5 H-D + 0.5 H-H+K2",
            h_d_features=hd_names,
            h_h_features=hd_names + hh_names,
            k2_features=FEATURE_NAMES,
            k2_feature_metadata="data/prepared/arm_k2_metadata.json",
            k2_source_sha256=feature_meta["source_sha256"],
            k2_feature_store_sha256=sha256(PREPARED / "arm_k2.dat"),
        ),
        emission=dict(
            method="holdout-matched STE",
            sigmas=[1.0, 2.0, 3.5], line_length=9,
            continuity_exponent=0.35, spacing_px=2.4,
            catalogue_exclusion_px=2.0,
            mass_ratio=MASS_RATIO,
            planning_hidden_mass_estimate=G_HIDDEN_PLANNING_ESTIMATE,
            hidden_mass_is_organizer_published=False,
            requested_dots=n_dots, emitted_dots=int((prediction[footprint] > 0).sum()),
        ),
        format=dict(
            verifier=final_json,
            range_guard="serialized Float32 values in footprint finite and min/max in [0,1]; outside footprint all NaN",
            single_band_float32_epsg32611_grid=True,
        ),
        download_notice=("Safe to download for research inspection. NOT SAFE TO SUBMIT. "
                         "No competition slot authorized; portal validation was not performed."),
        timing_seconds=round(time.time() - t0, 1),
    )
    evidence_path = ROOT / "evidence" / "k2_research_artifact_20261008.json"
    evidence_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(
        status=receipt["status"], file=receipt["file"], sha256=receipt["sha256"],
        bytes=receipt["bytes"], predicted_px=final["checks"]["predicted_px"],
        stage1_area_share=area_share, stage1_lift=lift,
        format_checks=final["checks"], receipt=str(evidence_path.relative_to(ROOT)),
        safe_to_submit=False, portal_validated=False,
    ), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
