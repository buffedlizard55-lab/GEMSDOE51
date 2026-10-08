#!/usr/bin/env python3
"""R1 regeneration builder: promoted blend with upload-legal geometry.

Fail-closed on the preregistered receipt (knowledge/preregistration-2026-10-08.md,
evidence/r1_holdout_20261008.json).  The promotion rule is re-derived here from
the raw per-fold numbers; the verdict string in the receipt is never trusted
directly.  If the rule failed, the builder only writes a RESEARCH ONLY artifact
(and only with --allow-research), never an upload recommendation.

Geometry (no new geology relative to the promoted procedure)
-------------------------------------------------------------
  Stage 1: Kreemer-et-al-(2000)-Eq-3 Kostrov deficit over 10 km tiles,
           q10 threshold (about 90 % of the footprint approved). Weight 0.0;
           it defines the allowed domain only and never places a point.
  Stage 2: full-field H-D (seed 17) + H-H (seed 19), fixed 50/50 probability
           blend, STE L9 / w_cont 0.35 / spacing 2.4 emission, catalogue
           exclusion 2.0 px, mass M = round(3.47 x 12700) = 44069 dots.
  Confinement operator (restrict|relocate) selected by the holdout receipt.
  Encoding: float32, exact template CRS/shape/affine, every cell finite in
           [0,1], zeros outside the footprint, NO NoData tag.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems51 import strain_budget as sb                          # noqa: E402
from gems51.detector import Stack                               # noqa: E402
from gems51.grid import GRID                                    # noqa: E402
from gems51.submission import verify, write_tif                 # noqa: E402
from gems51.uniqueness import run_gate                          # noqa: E402
from scripts.build_submission import (                          # noqa: E402
    G_HIDDEN_ESTIMATE, prior_rasters,
    require_family_reference_coverage, require_unique_support)
from scripts.build_submission_hh_blend import (                 # noqa: E402
    fit_full_field, load_observed, selected_extras, stage1_prior)
from scripts.evaluate_hh_blend import ste_emit                  # noqa: E402
from scripts.run_r1_holdout import (                            # noqa: E402
    FROZEN_PER_FOLD, REPRO_TOL, relocate_dots, SPACING)

P = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"
RECEIPT = ROOT / "evidence" / "r1_holdout_20261008.json"

RATIO = 3.47
N_DOTS = int(round(RATIO * G_HIDDEN_ESTIMATE))   # 44069


def reverify_promotion(receipt: dict) -> dict:
    """Re-derive the frozen rule from raw per-fold values; fail closed.

    Instrument anchor per preregistration Amendment A1: the archived frozen-best
    fields were never committed, so `base` is instead verified against the
    2026-10-07 P1 receipt's baseline_ungated values (identical procedure and
    pipeline state; fold 0 matched today's refit to all 15 printed digits).
    """
    per = receipt.get("per_fold", {})
    folds = sorted(int(k) for k in per)
    if folds != [0, 1, 2, 3, 4, 5]:
        raise SystemExit("receipt must contain exactly folds 0..5")
    p1 = json.loads((ROOT / "evidence" / "p1_holdout_20261007.json").read_text())
    p1_rows = {int(r["fold"]): r for r in p1.get("rows", [])}
    if sorted(p1_rows) != [0, 1, 2, 3, 4, 5]:
        raise SystemExit("p1_holdout_20261007.json must contain exactly folds 0..5")
    p1_base = [p1_rows[i]["scores"]["baseline_ungated"]["dti"] for i in folds]
    base = [per[str(i)]["rules"]["base"]["dti"] for i in folds]
    max_dev = max(abs(b - p) for b, p in zip(base, p1_base))
    if max_dev > REPRO_TOL:
        raise SystemExit(
            f"instrument check failed: base vs P1 baseline_ungated max deviation "
            f"{max_dev:.2e} > {REPRO_TOL:.0e}; nothing built from this receipt is "
            "interpretable")
    variants = {}
    for name in ("restrict", "relocate"):
        vals = [per[str(i)]["rules"][name]["dti"] for i in folds]
        inside = [per[str(i)]["rules"][name]["dots_inside_approved"] for i in folds]
        dots = [per[str(i)]["rules"][name]["dots"] for i in folds]
        delta = float(np.mean(vals) - np.mean(base))
        wins = int(sum(v > b for v, b in zip(vals, base)))
        variants[name] = dict(
            mean=float(np.mean(vals)), mean_delta=delta, folds_won=wins,
            all_inside=bool(all(i == d for i, d in zip(inside, dots))),
            per_fold=vals)
    best = max(variants, key=lambda nm: variants[nm]["mean"])
    v = variants[best]
    promoted = (v["mean_delta"] >= 0.0 and v["folds_won"] >= 4 and v["all_inside"])
    dom = receipt.get("summary", {}).get("dominance_control", {})
    arch_dev = max(abs(b - f) for b, f in zip(base, FROZEN_PER_FOLD))
    return dict(variants=variants, best=best, promoted=bool(promoted),
                instrument_max_dev=float(max_dev),
                archived_continuity_max_dev=float(arch_dev),
                uniform_tiles_mean=receipt.get("summary", {})
                .get("uniform_tiles", {}).get("mean"),
                dominance_passed=bool(dom.get("passed", False)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-hd", type=int, default=17)
    ap.add_argument("--seed-hh", type=int, default=19)
    ap.add_argument("--neg", type=int, default=250_000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--stage1-q", type=float, default=10.0)
    ap.add_argument("--allow-research", action="store_true",
                    help="write a RESEARCH ONLY artifact even when not promoted")
    a = ap.parse_args()

    if not RECEIPT.exists():
        raise SystemExit("evidence/r1_holdout_20261008.json is required; run "
                         "scripts/run_r1_holdout.py first")
    receipt = json.loads(RECEIPT.read_text())
    gate = reverify_promotion(receipt)
    variant = gate["best"]
    upload_ok = gate["promoted"]
    if not upload_ok and not a.allow_research:
        raise SystemExit(
            "R1 promotion rule FAILED (see receipt). No upload-eligible artifact "
            "will be written. Re-run with --allow-research to write a RESEARCH ONLY "
            "diagnostic artifact (never upload-eligible).")
    print("[r1 gate]", json.dumps(dict(promoted=upload_ok, variant=variant,
                                        instrument_max_dev=gate["instrument_max_dev"],
                                        variants={k: {kk: vv for kk, vv in v.items()
                                                      if kk != "per_fold"}
                                                  for k, v in gate["variants"].items()}),
                                   indent=1), flush=True)

    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()

    # ---------------------------------------------------------------- Stage 1
    s1 = stage1_prior(catalogue, footprint, df, obs, tile_px=a.tile_px, q=a.stage1_q)
    approved = s1["approved"]
    area_share = float((approved & footprint).sum() / max(int(footprint.sum()), 1))
    # diagnostic-only q70 comparator (the archived artifact's threshold)
    big = np.repeat(np.repeat(s1["deficit_tiles"], a.tile_px, axis=0), a.tile_px, axis=1)
    big = big[:GRID.shape[0], :GRID.shape[1]]
    finite = footprint & np.isfinite(big)
    thr70 = float(np.nanpercentile(big[finite], 70.0))
    approved_q70 = finite & (big >= thr70)
    print(f"[stage1] q{a.stage1_q:g} approved {area_share:.4%} of footprint; "
          f"formula: {s1['formula']}", flush=True)

    # ---------------------------------------------------------------- Stage 2
    extras_hd, names_hd = selected_extras(stack, [], footprint, "H_D")
    extras_hh, names_hh = selected_extras(stack, [], footprint, "H_H")
    print(f"[stage2] H-D extras={names_hd}; H-H extras={names_hh}", flush=True)
    field_hd = fit_full_field(stack, footprint, catalogue, extras_hd,
                              a.seed_hd, a.neg, a.max_iter)
    field_hh = fit_full_field(stack, footprint, catalogue, extras_hh,
                              a.seed_hh, a.neg, a.max_iter)
    field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
             + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
    field[~footprint] = np.nan

    excl = ndi.distance_transform_edt(~catalogue) <= a.excl_radius
    dom = footprint & ~excl & np.isfinite(field)
    conf_dom = dom & approved
    if variant == "restrict":
        ys, xs = ste_emit(field, conf_dom, N_DOTS)
        move_stats = None
    elif variant == "relocate":
        ys, xs = ste_emit(field, dom, N_DOTS)
        ys, xs, move_stats = relocate_dots(ys, xs, conf_dom, SPACING)
    else:  # pragma: no cover
        raise SystemExit(f"unknown variant {variant}")
    support = np.zeros(GRID.shape, dtype=bool)
    support[ys, xs] = True
    n_placed = int(support.sum())
    if n_placed != N_DOTS:
        raise SystemExit(f"emitter placed {n_placed} of {N_DOTS} dots")
    inside = int((support & approved).sum())
    if inside != n_placed:
        raise SystemExit(f"confinement failed: {inside}/{n_placed} dots inside q10 tiles")
    inside_q70 = int((support & approved_q70).sum())
    lift_q10 = (inside / max(n_placed, 1)) / max(area_share, 1e-12)
    print(f"[emit] variant={variant}: {n_placed:,} dots, 100% inside q10 tiles; "
          f"q70-diagnostic share={inside_q70 / n_placed:.4f}; lift_q10={lift_q10:.4f}",
          flush=True)
    if move_stats:
        print(f"[relocate] moved={move_stats['moved']} mean={move_stats['mean_move_px']:.2f}px "
              f"p95={move_stats['p95_move_px']:.2f}px max={move_stats['max_move_px']:.2f}px",
              flush=True)

    # ---------------------------------------------------------------- gates
    # Uniqueness scope decision (documented, applies to both verdict paths):
    # the gate proves the candidate is not a re-issue of a *submission*.  The
    # local H-H/H-D benchmark TIFF is the never-uploaded predecessor of this
    # exact promoted procedure — a regeneration overlaps it by construction, and
    # counting it would make any regeneration of the promoted procedure
    # impossible.  It is therefore excluded from the verdict scope but its
    # overlap is still measured and reported (see manifest uniqueness.scope).
    priors = prior_rasters()
    ref_count = require_family_reference_coverage(priors)
    excluded_benchmark = {label: p for label, p in priors.items()
                          if "hh-hd-blend-ste-r347" in label}
    scoped_priors = {label: p for label, p in priors.items()
                     if label not in excluded_benchmark}
    unique_preflight = require_unique_support(support, scoped_priors)
    benchmark_overlap = []
    for label, p in excluded_benchmark.items():
        import rasterio as _rio
        with _rio.open(p) as src:
            arr = src.read(1)
        if arr.shape != support.shape:
            continue
        other = np.isfinite(arr) & (arr > 0)
        from gems51.uniqueness import jaccard, overlap_fraction
        benchmark_overlap.append(dict(
            label=label,
            jaccard=float(jaccard(support, other)),
            containment=float(overlap_fraction(support, other)),
            note=("never-submitted local benchmark of the same promoted "
                  "procedure; overlap expected by construction; excluded "
                  "from the verdict scope, reported for transparency")))
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    role_tag = "allfinite" if upload_ok else "research-only"
    base_name = f"gemsdoe51-r1-{variant}-{stamp}-{role_tag}"
    staging = DOCS / f".{base_name}.staging.tif"
    primary = DOCS / f"{base_name}.tif"
    DOCS.mkdir(parents=True, exist_ok=True)
    # Dominance is a measured property of the geometry, recorded for both
    # upload-eligible and research-only artifacts.
    uniform_control = dict(
        candidate_mean=gate["variants"][variant]["mean"],
        uniform_mean=gate["uniform_tiles_mean"])
    try:
        rec = write_tif(staging, support.astype(np.float32), footprint,
                        outside=0.0, nodata=None)
        if not rec["checks"]["format_valid"]:
            raise SystemExit("staged GeoTIFF failed the local official-format verifier")
        if rec["checks"]["nan_cells"] != 0 or not rec["checks"]["all_cells_finite_in_range"]:
            raise SystemExit("staged GeoTIFF must be all-finite in [0,1]")
        gate_rep = run_gate(staging, scoped_priors, support, footprint, approved,
                            hard_confined=True, uniform_control=uniform_control)
        if gate_rep.verdict != "PASS":
            raise SystemExit("staged GeoTIFF failed the uniqueness/dominance gate: "
                             + gate_rep.verdict)
        staging.replace(primary)
        rec = verify(primary, footprint)
        rec["file"] = primary.name
        gate_rep.candidate = primary.name
    finally:
        if staging.exists():
            staging.unlink()

    zip_path = DOCS / f"{base_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(primary, primary.name)

    status = ("UPLOAD_ELIGIBLE_LOCAL_GATES_PASSED" if upload_ok
              else "RESEARCH_ONLY_DO_NOT_SUBMIT")
    submission_name = f"GEMSDOE51-R1-{variant.upper()}-ALLFINITE-20261008"
    record = dict(
        id=f"R1_{variant.upper()}_{stamp}",
        role="PRIMARY" if upload_ok else "RESEARCH_ONLY",
        status=status,
        ok_to_download_and_submit=bool(upload_ok),
        file=primary.name,
        zip=zip_path.name,
        submission_name=submission_name,
        portal_note=("R1 regen of promoted HH/HD blend; q10 strain-budget confinement; "
                     "all-finite [0,1]; zeros outside footprint."
                     if upload_ok else
                     "RESEARCH ONLY: promotion rule failed; do not submit."),
        note=("R1 regeneration of the promoted H-H/H-D 50/50 blend + STE L9 with "
              "q10 strain-budget tile confinement (%s operator), all-finite [0,1] "
              "zeros-outside encoding. Passed the preregistered paired six-fold rule "
              "on the visible-catalogue proxy. No organizer score is claimed; portal "
              "acceptance is not verified." % variant
              if upload_ok else
              "RESEARCH ONLY diagnostic: same geometry as the R1 candidate but the "
              "preregistered promotion rule was not met. DO NOT SUBMIT."),
        sha256=rec["sha256"],
        bytes=rec["bytes"],
        format=rec,
        holdout=dict(
            receipt=str(RECEIPT.relative_to(ROOT)),
            rule=("PROMOTE iff base reproduces evidence/p1_holdout_20261007.json "
                  "baseline_ungated within 1e-5 (Amendment A1; archived 0.2853406 "
                  "fields were never committed and are continuity-only) AND "
                  "mean(confined)-mean(base)>=0 AND wins>=4/6 folds AND 100% inside q10"),
            frozen_best_mean_continuity_only=0.285340602656319,
            instrument_max_dev=gate["instrument_max_dev"],
            variant=variant,
            variant_mean=gate["variants"][variant]["mean"],
            mean_delta_vs_base=gate["variants"][variant]["mean_delta"],
            folds_won=gate["variants"][variant]["folds_won"],
            base_per_fold=[per["dti"] for per in
                           [receipt["per_fold"][str(i)]["rules"]["base"] for i in range(6)]],
            variant_per_fold=gate["variants"][variant]["per_fold"],
            uniform_tiles_mean=gate["uniform_tiles_mean"],
            proxy_truth="visible known-fault catalogue; not hidden organizer labels"),
        stage1=dict(
            q=float(a.stage1_q), tile_px=a.tile_px,
            formula=s1["formula"],
            residual_policy=s1["residual_policy"],
            meta=s1["meta"],
            approved_area_share=area_share,
            emitted_share_inside_approved=1.0,
            lift_over_area_share=lift_q10,
            q70_diagnostic_share=inside_q70 / n_placed,
            role="coarse domain constraint; stage1_weight=0.0; never places a point"),
        uniqueness=dict(
            prewrite=unique_preflight,
            staged=gate_rep.as_dict(),
            reference_count=ref_count,
            verdict_scope=dict(
                verdict_priors=len(scoped_priors),
                excluded_benchmarks=sorted(excluded_benchmark),
                rationale=("gemsdoe51-hh-hd-blend-ste-r347-* is the "
                           "never-submitted local predecessor of this exact "
                           "promoted procedure; a regeneration overlaps it by "
                           "construction and it is not a submission"),
                benchmark_overlap=benchmark_overlap),
            scope=("locally archived artifacts, data/prior, and 21 pinned family "
                   "references; not a global proof")),
        model=dict(
            detector="HistGradientBoostingClassifier",
            h_d_features=names_hd, h_h_features=names_hh,
            blend_weight_hh=0.5, negative_samples=a.neg, max_iter=a.max_iter,
            seeds=dict(hd=a.seed_hd, hh=a.seed_hh)),
        emission=dict(method="STE", line_length=9, continuity_weight=0.35,
                      spacing_px=2.4, sigmas=[1.0, 2.0, 3.5],
                      exclusion_radius_px=a.excl_radius,
                      requested_dots=N_DOTS, placed_dots=n_placed,
                      confinement=variant, move_stats=move_stats,
                      all_points_inside_approved_tiles=True),
    )
    prior_manifest = json.loads((ROOT / "data" / "submission_manifest.json").read_text())
    research_artifacts = list(prior_manifest.get("research_only_artifacts", []))
    # Demote the previous primary (the H-H/H-D benchmark) into research_only:
    # it stays downloadable and explicitly labeled, instead of silently
    # disappearing from the manifest-driven public download set.
    old_primary = prior_manifest.get("primary") or {}
    if str(old_primary.get("id", "")).startswith("H_H_HD_BLEND"):
        demoted = {k: old_primary[k] for k in (
            "id", "file", "zip", "checks_file", "sha256", "bytes",
            "submission_name", "note", "holdout", "format",
            "stage1_q10_domain_check") if k in old_primary}
        demoted.update(
            role="SUPERSEDED_AUDIT_BENCHMARK",
            status="SUPERSEDED_AUDIT_BENCHMARK_NOT_FOR_SUBMISSION",
            ok_to_download_and_submit=False,
            superseded_by=record["id"],
            demotion_note=("Superseded by the R1 regeneration. Never upload-eligible: "
                           "NaN outside the footprint and only 86.71% of points inside "
                           "the q10 approved domain. Downloadable for audit only."))
        research_artifacts = [r for r in research_artifacts
                              if r.get("id") != demoted["id"]] + [demoted]
    manifest = dict(
        schema_version=4,
        status=status,
        generated_utc=stamp,
        primary=record,
        artifacts=[record],
        research_only_artifacts=research_artifacts,
        research_comparisons=prior_manifest.get("research_comparisons", {}),
        promotion=record["holdout"],
        stage1_stats=record["stage1"],
        uniqueness=gate_rep.as_dict(),
        submission_readiness=dict(
            status=("CLEARED_FOR_UPLOAD_PENDING_PORTAL" if upload_ok
                    else "BLOCKED_NOT_FOR_UPLOAD"),
            upload_ok=bool(upload_ok),
            ok_to_download_and_submit=bool(upload_ok),
            reason=("Passed the preregistered six-fold paired rule, q10 confinement, "
                    "all-finite [0,1] encoding, family uniqueness gate, and Stage-1 "
                    "non-dominance control. Local proxy truth only; no organizer score "
                    "claimed; portal acceptance unverified."
                    if upload_ok else
                    "The preregistered promotion rule was not met. RESEARCH ONLY."),
            no_organizer_upload_or_score_claimed=True),
        limitations=[
            "Holdout truth is the visible known-fault catalogue, not hidden expert labels.",
            "The planning mass 12700 is not an organizer-published hidden-label count.",
            "Local mirrors are hash-checked but not organizer-authenticated.",
            "Slip-rate component (vertical vs fault-plane) and per-trace dips remain assumptions.",
            "Portal acceptance of the zeros-outside encoding is inferred from the published "
            "format, not from an accepted upload.",
        ],
    )
    (ROOT / "data" / "submission_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (DOCS / f"{base_name}-checks.json").write_text(json.dumps(manifest, indent=1) + "\n")
    record["checks_file"] = f"{base_name}-checks.json"
    (ROOT / "data" / "submission_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (DOCS / f"{base_name}-checks.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(dict(file=str(primary), zip=str(zip_path), status=status,
                          ok_to_download_and_submit=upload_ok,
                          submission_name=submission_name, sha256=rec["sha256"],
                          checks=rec["checks"], gate=gate_rep.as_dict()["verdict"],
                          stage1=record["stage1"]), indent=1))
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
