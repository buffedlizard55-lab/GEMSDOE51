#!/usr/bin/env python3
"""Historical H-H/H-D + STE GeoTIFF writer, currently fail-closed.

The old blend and emission recipe are retained for audit/reproducibility only.
It predates the q10 all-points-inside allowed-domain requirement, and the
reported portal range error remains unresolved. The current manifest explicitly
blocks any new file from this writer; a historical local proxy promotion is not
upload authorization. A future build requires a new, explicit manifest decision
recording a promoted holdout, q10 confinement, and Stage-1 non-dominance.
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51 import trace_emission as te  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.submission import verify, write_tif  # noqa: E402
from gems51.uniqueness import run_gate  # noqa: E402
from scripts.build_submission import (  # noqa: E402
    G_HIDDEN_ESTIMATE,
    prior_rasters,
    require_family_reference_coverage,
    require_unique_support,
)

P = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"


def load_observed() -> dict[str, np.ndarray]:
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as src:
        descs = [d.split(" - ")[0] for d in src.descriptions]
        out = {}
        for name in ("geod_2ndinv", "geod_shearrate", "geod_dilaterate"):
            a = src.read(descs.index(name) + 1).astype(np.float64)
            a[a <= -1e38] = np.nan
            out[name] = a
    return out


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def stage1_prior(catalogue: np.ndarray, footprint: np.ndarray, df, obs,
                 tile_px: int = 100, q: float = 70.0) -> dict:
    """Build the current signed/rate-selectable Stage-1 diagnostic.

    The tensor invariant is ranked against the geodetic second invariant.  The
    dilatation and shear fields are retained as separate raw/rank diagnostics;
    they are not mixed into the fine detector because their source convention
    and exact invariant definition are not authenticated.  This keeps Stage 1 a
    coarse prior as required by the method brief.
    """
    cfg = sb.BudgetConfig(tile_px=tile_px, rate_convention="vertical",
                          assume_unknown_normal=True)
    exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
        catalogue, df, cfg, area_mask=footprint)
    fault_ii = sb.invariant(exx, eyy, exy, "II")
    observed = {
        name: sb.observed_tiles(value, footprint, tile_px)
        for name, value in obs.items()
    }
    dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, tile_px)
    ok = np.isfinite(dom) & (dom > 0.05)
    q_fault = sb.quantile_map(np.where(ok, fault_ii, np.nan))
    q_ii = sb.quantile_map(np.where(ok, observed["geod_2ndinv"], np.nan))
    q_dil = sb.quantile_map(np.where(ok, observed["geod_dilaterate"], np.nan))
    q_shear = sb.quantile_map(np.where(ok, observed["geod_shearrate"], np.nan))
    deficit = q_ii - q_fault
    dil_residual = q_dil - q_fault
    shear_residual = q_shear - q_fault
    residual_stack = np.stack([deficit, dil_residual, shear_residual])
    residual_prior = np.full_like(deficit, np.nan, dtype=np.float64)
    for residual_field in residual_stack:
        valid = np.isfinite(residual_field)
        update = valid & (~np.isfinite(residual_prior) |
                          (residual_field > residual_prior))
        residual_prior[update] = residual_field[update]
    # The tested/recorded artifact uses the geodetic second-invariant deficit
    # for its q70 diagnostic. The other two residuals remain auditable controls;
    # selecting their max would be a new Stage-1 experiment, not a silent change.
    big = upsample(deficit, tile_px)
    finite = footprint & np.isfinite(big)
    threshold = float(np.nanpercentile(big[finite], q))
    approved = finite & (big >= threshold)
    return dict(
        approved=approved,
        deficit_tiles=deficit,
        deficit_pixels=big,
        threshold=threshold,
        fault_ii=fault_ii,
        observed_ii=observed["geod_2ndinv"],
        observed_dilatation=observed["geod_dilaterate"],
        observed_shear=observed["geod_shearrate"],
        ranked_dilatation=q_dil,
        ranked_shear=q_shear,
        dilatation_residual=dil_residual,
        shear_residual=shear_residual,
        combined_residual_prior=residual_prior,
        ranked_fault=q_fault,
        meta=meta,
        formula=("Kreemer et al. (2000), Eq. 3: eps_ij = 1/2 sum_k "
                 "[L_k u_dot_k/(A sin(delta_k))] m_ij^k"),
        residual_policy=("rank-space q(geodetic) - q(fault tensor II) is a coarse "
                         "diagnostic only; no absolute dilation/shear subtraction "
                         "is claimed because source conventions are unresolved"),
    )


def selected_extras(stack: Stack, names: list[str], footprint: np.ndarray,
                    arm: str) -> tuple[list[np.ndarray], list[str]]:
    """Load exactly the H-D and H-H static features used by the locked holdout."""
    if not (P / "extras_static.dat").exists():
        raise SystemExit("data/prepared/extras_static.dat is missing; run prepare/build_extras")
    all_names = json.loads((P / "extras_static_names.json").read_text())
    mm = np.memmap(P / "extras_static.dat", dtype=np.float32, mode="r",
                   shape=(len(all_names), *GRID.shape))
    keys = ["facecoh"] if arm == "H_D" else ["facecoh", "hh_"]
    keep = [i for i, name in enumerate(all_names) if any(key in name for key in keys)]
    return [np.asarray(mm[i], dtype=np.float32) for i in keep], [all_names[i] for i in keep]


def fit_full_field(stack: Stack, footprint: np.ndarray, catalogue: np.ndarray,
                   extras: list[np.ndarray], seed: int, neg: int = 250_000,
                   max_iter: int = 250) -> np.ndarray:
    pool = footprint & ~catalogue
    rng = np.random.default_rng(seed)
    X, y = stack.sample(catalogue & footprint, pool, neg, rng, extra=extras)
    model = fit_detector(X, y, seed=seed, max_iter=max_iter)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras)


def strike_emit(field: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray,
                n_dots: int, excl_radius: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the fixed STE L9/w=.35/s=2.4 rule and return support + score."""
    dom = footprint & np.isfinite(field)
    exclude = ndi.distance_transform_edt(~catalogue) <= excl_radius
    candidate = dom & ~exclude
    score, theta = te.strike_coherent_score(
        field, dom, sigmas=(1.0, 2.0, 3.5), line_len=9,
        n_orient=12, w_cont=0.35)
    ys, xs = te.spaced_dots(score, candidate, n_dots, spacing=2.4)
    support = np.zeros(GRID.shape, dtype=bool)
    support[ys, xs] = True
    return support, score, theta


def promotion_receipt() -> dict:
    """Return the exact fixed 50/50 blend + STE holdout receipt and fail closed."""
    path = ROOT / "evidence" / "hh_blend_holdout.json"
    if not path.exists():
        raise SystemExit("evidence/hh_blend_holdout.json is required")
    d = json.loads(path.read_text())
    if float(d.get("config", {}).get("weight_hh", -1)) != 0.5:
        raise SystemExit("promotion requires the pre-declared 50/50 H-H/H-D blend")
    ste = d.get("summary", {}).get("ste", {})
    folds = np.asarray(ste.get("per_fold", []), dtype=float)
    incumbent = json.loads((ROOT / "data" / "holdout_H_D.json").read_text())
    baseline = np.asarray(incumbent["summary"]["dti_r3.47"]["per_fold"], dtype=float)
    if folds.shape != (6,) or baseline.shape != (6,):
        raise SystemExit("promotion requires six paired folds")
    delta = folds - baseline
    mean = float(folds.mean())
    base_mean = float(baseline.mean())
    positive = int((delta > 0).sum())
    if not (mean > base_mean and mean > 0.2817 and positive >= 4):
        raise SystemExit(
            f"H-H/H-D blend failed frozen promotion: mean={mean:.6f}, "
            f"incumbent={base_mean:.6f}, positive={positive}/6")
    return dict(
        candidate="H-H/H-D fixed 50/50 probability blend + STE L9 w=0.35 spacing=2.4",
        mean_dti=mean,
        incumbent_mean_dti=base_mean,
        paired_mean_delta=float(delta.mean()),
        positive_folds=positive,
        n_folds=6,
        per_fold=[float(x) for x in folds],
        incumbent_per_fold=[float(x) for x in baseline],
        rule="mean > H-D and > 0.2817; positive in >=4/6 folds",
        evidence="evidence/hh_blend_holdout.json",
        proxy_truth="visible known-fault catalogue; not hidden organizer labels",
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def require_build_authorization(manifest_path: Path | None = None) -> dict:
    """Require an explicit promotion and q10-domain clearance before any build work."""
    path = manifest_path or (ROOT / "data" / "submission_manifest.json")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"submission build blocked: cannot read manifest {path}: {exc}") from exc
    readiness = manifest.get("submission_readiness", {})
    candidate = manifest.get("candidate_screen", {})
    if readiness.get("status") != "CLEARED_FOR_NEW_BUILD":
        raise SystemExit(
            "submission build blocked: manifest is not CLEARED_FOR_NEW_BUILD; "
            f"current status={readiness.get('status', 'MISSING')!r}. "
            "A local proxy promotion does not clear the portal/q10 blockers."
        )
    if candidate.get("status") != "PROMOTED":
        raise SystemExit(
            "submission build blocked: candidate_screen.status must be PROMOTED; "
            f"current status={candidate.get('status', 'MISSING')!r}."
        )
    q10 = candidate.get("holdout_q10_domain", {})
    if q10.get("all_points_inside_approved") is not True:
        raise SystemExit(
            "submission build blocked: candidate has no passing q10 holdout proof "
            "that every emitted Stage-2 point lies inside approved tiles."
        )
    if candidate.get("stage1_non_dominance_pass") is not True:
        raise SystemExit(
            "submission build blocked: candidate has no passing Stage-1 non-dominance receipt."
        )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--g-hidden", type=int, default=G_HIDDEN_ESTIMATE)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--stage1-q", type=float, default=70.0)
    ap.add_argument("--stage1-weight", type=float, default=0.0)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--neg", type=int, default=250000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--seed-hd", type=int, default=17)
    ap.add_argument("--seed-hh", type=int, default=19)
    ap.add_argument("--tag", default="hh-hd-blend-ste-r347")
    ap.add_argument("--skip-cache", action="store_true")
    a = ap.parse_args()
    require_build_authorization()
    if a.g_hidden != G_HIDDEN_ESTIMATE or abs(a.ratio - 3.47) > 1e-12:
        raise SystemExit("only the holdout-validated ratio 3.47 and planning mass 12700 are eligible")
    if abs(a.stage1_weight) > 1e-12:
        raise SystemExit("Stage-1 soft weight is locked to 0.0: current Stage-1 gate sweep did not improve H-H")
    if a.tag != "hh-hd-blend-ste-r347":
        raise SystemExit("tag is fixed so the candidate identity cannot be relabeled")
    promotion = promotion_receipt()
    priors = prior_rasters()
    ref_count = require_family_reference_coverage(priors)
    print("[promotion]", json.dumps(promotion, indent=1), flush=True)
    print(f"[uniqueness] {ref_count} commit-pinned family references plus local prior rasters", flush=True)

    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()
    s1 = stage1_prior(catalogue, footprint, df, obs, tile_px=a.tile_px, q=a.stage1_q)
    approved = s1["approved"]
    area_share = float((approved & footprint).sum() / max(int(footprint.sum()), 1))
    print(f"[stage1] q{a.stage1_q:g} approved area={area_share:.6f}; "
          "diagnostic only, no fine-scale gate", flush=True)

    extras_hd, names_hd = selected_extras(stack, [], footprint, "H_D")
    extras_hh, names_hh = selected_extras(stack, [], footprint, "H_H")
    if not a.skip_cache or not (P / "field_final_H_D.npy").exists():
        print("[stage2] fitting full H-D field", flush=True)
        field_hd = fit_full_field(stack, footprint, catalogue, extras_hd,
                                  a.seed_hd, a.neg, a.max_iter)
        np.save(P / "field_final_H_D.npy", field_hd)
    else:
        field_hd = np.load(P / "field_final_H_D.npy")
    if not a.skip_cache or not (P / "field_final_H_H.npy").exists():
        print("[stage2] fitting full H-H field", flush=True)
        field_hh = fit_full_field(stack, footprint, catalogue, extras_hh,
                                  a.seed_hh, a.neg, a.max_iter)
        np.save(P / "field_final_H_H.npy", field_hh)
    else:
        field_hh = np.load(P / "field_final_H_H.npy")
    field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
             + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
    field[~footprint] = np.nan

    n_dots = int(round(a.ratio * a.g_hidden))
    support, emission_score, theta = strike_emit(
        field, footprint, catalogue, n_dots=n_dots, excl_radius=a.excl_radius)
    if int(support.sum()) != n_dots:
        raise SystemExit(f"emitter placed {int(support.sum())} of {n_dots} requested dots")
    print(f"[emit] STE placed {int(support.sum()):,} dots; stage1 weight={a.stage1_weight:g}", flush=True)

    # Pre-write support gate.  It intentionally happens before the staging TIFF
    # is created, so a duplicate cannot be presented as an eligible download.
    unique_preflight = require_unique_support(support, priors)
    inside = int((support & approved).sum())
    emitted_share = inside / max(int(support.sum()), 1)
    lift = emitted_share / max(area_share, 1e-12)
    if lift > 1.5:
        raise SystemExit(f"Stage-1 dominance failed before write: lift={lift:.6f}")
    print("[preflight]", json.dumps(dict(
        max_support_jaccard=unique_preflight["max_jaccard"],
        max_support_containment=unique_preflight["max_containment"],
        approved_area_share=area_share,
        emitted_share_inside_approved=emitted_share,
        lift_over_area_share=lift), indent=1), flush=True)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"gemsdoe51-{a.tag}-{stamp}"
    staging = DOCS / f".{base}.staging.tif"
    primary = DOCS / f"{base}.tif"
    DOCS.mkdir(parents=True, exist_ok=True)
    try:
        rec = write_tif(staging, support.astype(np.float32), footprint, outside=np.nan, nodata=np.nan)
        if not rec["checks"]["format_valid"]:
            raise SystemExit("staged GeoTIFF failed local official-format verifier")
        gate = run_gate(staging, priors, support, footprint, approved)
        if gate.verdict != "PASS":
            raise SystemExit("staged GeoTIFF failed source-aware uniqueness/Stage-1 gate: " + gate.verdict)
        staging.replace(primary)
        rec = verify(primary, footprint)
        # The gate ran on a hidden staging path; receipts exposed to users must
        # identify the final bytes, not the temporary filename.
        rec["file"] = primary.name
        gate.candidate = primary.name
    finally:
        if staging.exists():
            staging.unlink()

    zip_path = DOCS / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(primary, primary.name)

    record = dict(
        id="H_H_HD_BLEND_STE_20261007",
        role="PRIMARY",
        status="HOLDOUT_PROMOTED_UNSCORED",
        file=primary.name,
        zip=zip_path.name,
        submission_name="GEMSDOE51-HH-HD-BLEND-STE-R347-20261007",
        note=("H-H potential-field edge-termination/conductive-relay features plus H-D, "
              "fixed 50/50 probability blend, STE L9 w0.35 spacing 2.4; "
              "holdout-promoted but no organizer score claimed."),
        gate_mode="H-H/H-D 50/50 + STE",
        description=("Unique H-H/H-D probability blend; Stage 1 retained as a diagnostic "
                     "and stage1_weight=0.0 in the emitted artifact."),
        holdout_cost_vs_ungated=None,
        sha256=rec["sha256"],
        bytes=rec["bytes"],
        format=rec,
        holdout=promotion,
        stage1_dominance=dict(
            q=float(a.stage1_q), approved_area_share=area_share,
            emitted_share_inside_approved=emitted_share,
            lift_over_area_share=lift,
            role="coarse prior diagnostic only; stage1_weight=0.0"),
        uniqueness=dict(
            prewrite=unique_preflight,
            staged=gate.as_dict(),
            reference_count=ref_count,
            scope="locally available archived files, data/prior, and 21 pinned family references; not a global proof"),
        model=dict(
            detector="HistGradientBoostingClassifier",
            h_d_features=names_hd,
            h_h_features=names_hh,
            blend_weight_hh=0.5,
            negative_samples=a.neg,
            max_iter=a.max_iter,
            seeds=dict(hd=a.seed_hd, hh=a.seed_hh)),
        emission=dict(method="STE", line_length=9, continuity_weight=0.35,
                      spacing_px=2.4, sigmas=[1.0, 2.0, 3.5],
                      exclusion_radius_px=a.excl_radius,
                      requested_dots=n_dots, placed_dots=int(support.sum())),
        evidence=("evidence/hh_blend_holdout.json; local format/uniqueness receipts "
                  "were measured from the final bytes; no DrivenData score or acceptance is claimed"),
    )
    prior_manifest = json.loads((ROOT / "data" / "submission_manifest.json").read_text())
    manifest = dict(
        schema_version=3,
        status="HOLDOUT_PROMOTED_UNSCORED",
        generated_utc=stamp,
        primary=record,
        artifacts=[record],
        research_only_artifacts=prior_manifest.get("research_only_artifacts", []),
        research_comparisons=prior_manifest.get("research_comparisons", {}),
        promotion=promotion,
        stage1_stats=s1["meta"] | dict(
            approved_px=int(approved.sum()), approved_share_of_footprint=area_share,
            emitted_share_inside_approved=emitted_share, lift_over_area_share=lift,
            threshold=s1["threshold"], formula=s1["formula"],
            residual_policy=s1["residual_policy"],
            fault_median_II_nanostrain=float(np.nanmedian(s1["fault_ii"])),
            observed_median_II_nanostrain=float(np.nanmedian(s1["observed_ii"])),
            residual_controls=("dilatation and shear rank residuals were computed "
                              "but not used to place Stage-2 points"),
            rank_residual_holdout_receipt="data/stage1_trace_holdout.json",
            rank_residual_convention=("rank(observed scalar) - rank(fault tensor II); "
                                      "diagnostic only, not an absolute strain subtraction")),
        uniqueness=gate.as_dict(),
        limitations=[
            "Holdout truth is the visible known-fault catalogue, not hidden expert labels.",
            "The planning mass 12700 is not an organizer-published hidden-label count.",
            "Local mirrors are hash-checked but not organizer-authenticated.",
            "The Stage-1 rate field is provisionally interpreted as mm/yr; source component and dip are unresolved.",
        ],
    )
    (ROOT / "data" / "submission_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (DOCS / f"{base}-checks.json").write_text(json.dumps(manifest, indent=1) + "\n")
    record["checks_file"] = f"{base}-checks.json"
    # Re-write after checks_file is known.
    (ROOT / "data" / "submission_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (DOCS / f"{base}-checks.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(dict(file=str(primary), zip=str(zip_path), submission_name=record["submission_name"],
                         note=record["note"], sha256=rec["sha256"], checks=rec["checks"],
                         promotion=promotion, stage1=record["stage1_dominance"],
                         uniqueness=gate.as_dict()), indent=1))
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
