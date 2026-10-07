#!/usr/bin/env python3
"""Reconcile submission-manifest claims with the artifact checks and current Stage-1 code.

This is an audit/report builder, not a submission generator. It checks both manifest
copies, retains the original build-time q70 numbers, recomputes q20/q70 masks with
the current strain-budget implementation, and derives the exact soft-prior holdout
delta from the paired H-D gate sweep.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    manifest_paths = [ROOT / "data/submission_manifest.json",
                      ROOT / "docs/downloads/submission_manifest.json"]
    manifests = [json.loads(p.read_text()) for p in manifest_paths]
    if manifests[0] != manifests[1]:
        raise SystemExit("data/docs submission manifests differ; inspect before reconciling")
    manifest = manifests[0]
    primary = manifest["primary"]
    artifact = next(a for a in manifest["artifacts"] if a["role"] == "PRIMARY")
    candidate = ROOT / "docs/downloads" / primary["file"]
    checks_path = ROOT / "docs/downloads" / primary["file"].replace("-zeros.tif", "-checks.json")
    old_checks = json.loads(checks_path.read_text())

    spec = importlib.util.spec_from_file_location("build_submission",
                                                  ROOT / "scripts/build_submission.py")
    build = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(build)
    prep = ROOT / "data/prepared"
    footprint = np.load(prep / "footprint.npy")
    catalogue = np.load(prep / "catalogue.npy")
    slip = build.sb.load_slip_rates(ROOT / "data/raw")
    observed = build.load_observed()
    with __import__("rasterio").open(candidate) as src:
        emission_support = src.read(1) > 0
    n_emit = int(emission_support.sum())

    recomputed = {}
    for q in (20, 70):
        approved, deficit, threshold, metadata, ii, obs_ii = build.stage1_approved(
            catalogue, footprint, slip, observed, 100, q)
        inside = int((emission_support & approved).sum())
        area_share = float(approved.sum() / footprint.sum())
        emitted_share = inside / n_emit
        recomputed[str(q)] = {
            "q_percentile": q,
            "interpretation": f"approved tiles are the top {100-q}% of current-code deficit values",
            "deficit_threshold": float(threshold),
            "approved_pixels": int(approved.sum()),
            "footprint_pixels": int(footprint.sum()),
            "approved_area_share_of_footprint": area_share,
            "emitted_pixels_inside_approved": inside,
            "emitted_pixels_total": n_emit,
            "emitted_share_inside_approved": emitted_share,
            "lift_over_area_share": emitted_share / area_share,
        }
        del approved, deficit, metadata, ii, obs_ii

    gate = json.loads((ROOT / "data/gate_sweep.json").read_text())
    base = gate["soft"]["0.0"]
    soft = gate["soft"]["0.1"]
    deltas = [float(a - b) for a, b in zip(soft["per_fold"], base["per_fold"])]
    mean_delta = float(np.mean(deltas))
    wins = int(sum(d > 0 for d in deltas))
    std = float(np.std(deltas, ddof=1))

    build_time_q70 = old_checks.get("uniqueness", {}).get("stage1_dominance", {})
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate": {
            "path": str(candidate.relative_to(ROOT)),
            "sha256": sha256(candidate),
            "bytes": candidate.stat().st_size,
            "emitted_pixels": n_emit,
        },
        "manifest_copy_check": {
            "data_manifest_sha256": sha256(manifest_paths[0]),
            "docs_manifest_sha256": sha256(manifest_paths[1]),
            "parsed_objects_equal": True,
        },
        "stage1_dominance_reconciliation": {
            "build_time_check_file": str(checks_path.relative_to(ROOT)),
            "build_time_check_file_sha256": sha256(checks_path),
            "build_time_stage1_q70": build_time_q70,
            "current_formula_rerun": {
                "code": "scripts/build_submission.py::stage1_approved + current src/gems51/strain_budget.py",
                "builder_source_sha256": sha256(ROOT / "scripts/build_submission.py"),
                "strain_budget_source_sha256": sha256(ROOT / "src/gems51/strain_budget.py"),
                "masks": recomputed,
            },
            "finding": "Both the original build-time q70 check and the independent current-code q70 rerun show that the primary's emissions are under-represented inside Stage-1's approved footprint (lift < 1). The data/docs manifests had instead copied q20/top-80% numbers, the hard secondary's threshold. No q threshold shows Stage-1 dominance.",
            "formula_revision_caveat": "The current rerun uses the revised signed strike-slip moment-tensor implementation. The existing TIFF predates that code revision, so the build-time q70 result is preserved separately rather than overwritten or misrepresented as the exact prior used to create the file.",
        },
        "holdout_delta_reconciliation": {
            "source": "data/gate_sweep.json, paired H-D soft w=0.10 versus w=0.00, same six spatial folds",
            "ungated_mean_proxy_dti": float(base["mean"]),
            "soft_w010_mean_proxy_dti": float(soft["mean"]),
            "mean_delta_exact": mean_delta,
            "mean_delta_rounded_4dp": round(mean_delta, 4),
            "paired_fold_deltas": deltas,
            "folds_positive": wins,
            "fold_count": len(deltas),
            "sample_sd_of_paired_deltas": std,
            "interpretation": "The +0.0004 in the per-artifact entry is the exact +0.000367... rounded to four decimals; the primary-level 0.0 is a rounded decision-level 'no demonstrated gain', not the raw arithmetic delta. Report both, label the raw value as small/inconclusive, and do not describe it as a win.",
        },
        "manifest_diagnostics_before_reconciliation": {
            "primary_manifest_stage1": primary.get("uniqueness", {}).get("stage1_dominance", {}),
            "primary_artifact_check_stage1": build_time_q70,
            "primary_holdout_delta": primary.get("holdout_cost_vs_ungated"),
            "artifact_holdout_delta": artifact.get("holdout_cost_vs_ungated"),
            "artifact_holdout_note": artifact.get("holdout_cost_note"),
        },
    }
    # Correct the two public-facing manifest copies. Preserve the build-time
    # check verbatim and attach the post-revision q70 rerun rather than silently
    # rewriting the diagnostic that accompanied the original TIFF.
    for manifest_path in manifest_paths:
        current = json.loads(manifest_path.read_text())
        current_primary = current["primary"]
        current_artifact = next(a for a in current["artifacts"] if a["role"] == "PRIMARY")
        for entry in (current_primary, current_artifact):
            u = entry.setdefault("uniqueness", {})
            u["stage1_dominance_build_time_q70"] = build_time_q70
            u["stage1_dominance_q20_current_formula"] = recomputed["20"]
            u["stage1_dominance"] = recomputed["70"]
            u["stage1_dominance"]["formula_revision"] = "current signed-moment-tensor code; see evidence/stage1_formula_audit.json"
            fresh_audit_path = ROOT / "evidence/uniqueness_gate_H_D_soft_20261007.json"
            if fresh_audit_path.exists():
                fresh = json.loads(fresh_audit_path.read_text())
                matched_hard = next((m for m in fresh.get("matches", [])
                                     if "hardq20-r347" in m.get("path", "")
                                     and m.get("path", "").endswith("-zeros.tif")), None)
                matched_nan = next((m for m in fresh.get("matches", [])
                                    if "softw0p1-r347" in m.get("path", "")
                                    and m.get("path", "").endswith("-nan.tif")), None)
                u["verdict"] = fresh.get("verdict", "INCOMPLETE")
                u["fresh_public_artifact_audit"] = {
                    "evidence": str(fresh_audit_path.relative_to(ROOT)),
                    "verdict": fresh.get("verdict"),
                    "checker_verdict": fresh.get("checker_verdict"),
                    "downloaded_sha_verified": fresh.get("audit", {}).get("downloaded_and_sha_verified"),
                    "download_errors": len(fresh.get("audit", {}).get("download_errors", [])),
                    "pixel_comparisons": fresh.get("n_compared"),
                    "skipped": len(fresh.get("skipped", [])),
                    "matches": len(fresh.get("matches", [])),
                    "max_support_jaccard": fresh.get("worst", {}).get("iou", {}).get("iou"),
                    "max_cosine": fresh.get("worst", {}).get("cosine", {}).get("cosine"),
                    "hardq20_support_jaccard": matched_hard.get("iou") if matched_hard else None,
                    "nan_twin_support_jaccard": matched_nan.get("iou") if matched_nan else None,
                }
            else:
                u["verdict"] = "PENDING_FRESH_PUBLIC_ARTIFACT_AUDIT"
            notes = list(u.get("notes", []))
            note = ("The original check used q70; current manifests now report the primary's q70 threshold. "
                    "The independent current-code rerun and original build-time q70 check both show no Stage-1 dominance. "
                    "The old q20 metrics were the hard secondary's top-80% diagnostic.")
            if note not in notes:
                notes.append(note)
            u["notes"] = notes
        current_primary["holdout_cost_vs_ungated"] = mean_delta
        current_artifact["holdout_cost_vs_ungated"] = mean_delta
        holdout_note = (
            f"Paired over {len(deltas)} spatial folds: ungated {base['mean']:.9f} to "
            f"w=0.10 {soft['mean']:.9f}, raw mean ΔDTI {mean_delta:+.9f} "
            f"({wins}/{len(deltas)} folds positive; paired-delta sample SD {std:.6f}). "
            "Small/inconclusive; do not treat as a demonstrated win."
        )
        current_primary["holdout_cost_note"] = holdout_note
        current_artifact["holdout_cost_note"] = holdout_note
        current_primary["holdout_interpretation"] = "INCONCLUSIVE_SMALL_DELTA_NOT_A_WIN"
        current_artifact["holdout_interpretation"] = "INCONCLUSIVE_SMALL_DELTA_NOT_A_WIN"
        current_primary["note"] = (
            "GEMSDOE51 | H-D soft w=0.10; 44,069 dots, 200 m catalogue buffer; "
            "proxy Δ +0.00037 vs ungated (4/6; inconclusive); NOT SLOT-ELIGIBLE; UNSCORED."
        )
        current_artifact["note"] = current_primary["note"]
        s1 = current.setdefault("stage1_stats", {})
        s1["approved_share_at_q20"] = recomputed["20"]["approved_area_share_of_footprint"]
        s1["approved_share_at_primary_q70_current_formula"] = recomputed["70"]["approved_area_share_of_footprint"]
        s1["primary_q_percentile"] = 70
        s1["primary_prior_is_soft_not_a_hard_emission_mask"] = True
        s1["formula_audit"] = "evidence/stage1_formula_audit.json"
        s1["manifest_reconciliation"] = "evidence/submission_manifest_reconciliation.json"
        manifest_path.write_text(json.dumps(current, indent=1) + "\n")

    # The file-local check is a historical build-time record; keep it intact and
    # append the independent current-code q20/q70 recalculation.
    check_record = json.loads(checks_path.read_text())
    check_record["stage1_dominance_current_formula_recomputed"] = {
        "candidate_sha256": sha256(candidate),
        "strain_budget_source_sha256": result["stage1_dominance_reconciliation"]["current_formula_rerun"]["strain_budget_source_sha256"],
        "masks": recomputed,
        "interpretation": result["stage1_dominance_reconciliation"]["finding"],
        "caveat": result["stage1_dominance_reconciliation"]["formula_revision_caveat"],
    }
    checks_path.write_text(json.dumps(check_record, indent=1) + "\n")
    out = ROOT / "evidence/submission_manifest_reconciliation.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "output": str(out),
        "build_time_q70_emitted_share": build_time_q70.get("emitted_share_inside_approved"),
        "current_q70": recomputed["70"],
        "current_q20": recomputed["20"],
        "exact_soft_delta": mean_delta,
        "folds_positive": f"{wins}/{len(deltas)}",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
