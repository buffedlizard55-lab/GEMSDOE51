#!/usr/bin/env python3
"""Build the H53 two-stage submission GeoTIFF — only after the frozen H53 gates pass.

Pipeline (two stages, as the method brief requires):

Stage 1 (coarse, never places a point)
    rank-space geodetic strain-budget deficit over 10 km tiles
    (``gems51.strain_budget``, Kreemer et al. 2000 Eq. 3), computed from the full
    published catalogue; approved domain = tiles at/above the q10 percentile.
    Reported separately, zero soft score weight, non-dominance limit lift <= 1.5.

Stage 2 (fine, places every point)
    belief field = 50/50 blend of the H-H arm (base + facecoh + hh_ extras)
    and the H-D arm (base + facecoh), trained on all published catalogue
    pixels as positives and 250k background pixels as negatives with NEW
    seeds (53/54, distinct from every archived build).  If the preregistered
    H53-A candidate promoted, the H-H arm additionally receives the six
    fine-scale strain-residual ridge features (``gems51.strain_residual``).
    Emission = the frozen STE L9 / w=0.35 / spacing 2.4 geometry, confined to
    the Stage-1 approved tiles, with the catalogue flank and mass taken from
    the preregistered H53-F operating-point decision.

Hard rules enforced in code, not by inspection:
  * the frozen H53 holdout receipt exists, is complete, and its baseline
    reproduced the frozen mean within 1e-5;
  * nothing is emitted outside the Stage-1 approved domain;
  * nothing is emitted within the preregistered flank of a catalogue pixel;
  * every emitted dot is unit mass, so no cell can leave [0, 1];
  * the written raster has zeros outside the footprint, no NaN anywhere and
    no NoData tag, so the portal's "values must be in range [0, 1]" validator
    cannot be triggered by this file (IR-51-21);
  * the support passes the pre-write uniqueness gate against every locally
    held prior (21 pinned family references + local priors + downloads +
    archive) BEFORE any TIFF byte is written;
  * the staged TIFF passes the source-aware uniqueness/Stage-1 gate before
    it is renamed into place.

Outputs (all under ``docs/downloads/`` so the site links them directly):
    <name>.tif / <name>.zip / <name>-checks.json
    data/submission_manifest.json   (primary demoted, candidate recommended)
    registry/submission_build_h53sr.json

Usage:
    .venv/bin/python scripts/build_submission_h53.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems51 import strain_budget as sb          # noqa: E402
from gems51 import trace_emission as te         # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID                    # noqa: E402
from gems51.live_metric import on_catalogue_mass  # noqa: E402
from gems51.paths import DOWNLOADS_DIR         # noqa: E402
from gems51.strain_residual import h53a_features, feature_names  # noqa: E402
from gems51.submission import verify, write_tif  # noqa: E402
from gems51.uniqueness import run_gate, sha256_file  # noqa: E402
from scripts.build_submission import (  # noqa: E402
    G_HIDDEN_ESTIMATE,
    prior_rasters,
    require_family_reference_coverage,
    require_unique_support,
)
from scripts.evaluate_hk1_holdout import _load_stage1_inputs  # noqa: E402

P = ROOT / "data" / "prepared"
HOLDOUT = ROOT / "evidence" / "h53_holdout_20261008.json"
ARM_KEYS = {"HH": ("facecoh", "hh_"), "HD": ("facecoh",)}
# Frozen local best (evidence/hh_blend_holdout.json): H-H/H-D 50/50 blend + STE
# L9 w0.35 spacing 2.4, six-fold visible-catalogue proxy mean DTI. UNGATED and
# not upload-eligible (86.71% of dots inside q10; NaN-outside encoding).
FROZEN_BEST = 0.285340602656319


def sha256(path: Path) -> str:
    return sha256_file(path)


def load_extras(arm: str):
    path = P / "extras_static.dat"
    names = json.loads((P / "extras_static_names.json").read_text())
    keep = [i for i, n in enumerate(names) if any(k in n for k in ARM_KEYS[arm])]
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def fit_full_field(stack, footprint, catalogue, extras, seed, neg=250_000,
                   max_iter=250):
    rng = np.random.default_rng(seed)
    X, y = stack.sample(catalogue & footprint, footprint & ~catalogue, neg, rng,
                        extra=extras)
    model = fit_detector(X, y, seed=seed, max_iter=max_iter)
    del X, y
    return predict_grid(model, stack, footprint, extra=extras)


def require_h53_gate() -> dict:
    """Fail closed unless the frozen H53 holdout receipt licenses this build."""
    if not HOLDOUT.is_file():
        raise SystemExit("REFUSING to build: evidence/h53sr_holdout_20261008.json is "
                         "missing; run scripts/run_h53_holdout.py first")
    rec = json.loads(HOLDOUT.read_text())
    if rec.get("status") not in ("COMPLETE", "COMPLETE_NOT_PROMOTED"):
        raise SystemExit("REFUSING to build: the H53 holdout receipt is incomplete")
    if len(rec.get("rows", [])) != 6:
        raise SystemExit("REFUSING to build: the H53 holdout receipt lacks six folds")
    base = rec.get("baseline", {})
    if not base.get("reproduced"):
        raise SystemExit("REFUSING to build: the fresh baseline did not reproduce the "
                         f"frozen mean within 1e-5 (drift {base.get('fresh_minus_frozen_mean')})")
    if not rec.get("stage1_non_dominance", {}).get("passed"):
        raise SystemExit("REFUSING to build: Stage-1 non-dominance gate failed")
    uc = rec.get("stage1_non_dominance", {}).get("uniform_control") or {}
    if not uc.get("passed"):
        raise SystemExit("REFUSING to build: the uniform-fill dominance control "
                         "failed -- the fine model does not beat a uniform fill of "
                         "the same approved tiles, so Stage 1 would be doing the work")
    if not all(r["candidate_stage1"]["emitted_share_inside_approved"] == 1.0
               for r in rec["rows"]):
        raise SystemExit("REFUSING to build: a fold's candidate points escaped the "
                         "approved Stage-1 tiles")
    f = rec.get("h53f_operating_point", {}).get("decision", {})
    if not f.get("adopted_arm"):
        raise SystemExit("REFUSING to build: the H53-F operating-point decision is missing")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="run every gate and stop before writing any TIFF byte")
    ap.add_argument("--seed-hd", type=int, default=53)
    ap.add_argument("--seed-hh", type=int, default=54)
    ap.add_argument("--seed-h53a", type=int, default=55)
    ap.add_argument("--tag", default="h53-twostage")
    args = ap.parse_args()

    t0 = time.time()
    rec = require_h53_gate()
    promoted = bool(rec.get("promoted"))
    f_dec = rec["h53f_operating_point"]["decision"]
    ratio = float(f_dec["adopted_arm"].split("_")[0][1:])
    flank = float(f_dec["adopted_arm"].split("_")[1][1:])
    n_dots = int(round(ratio * G_HIDDEN_ESTIMATE))
    print(f"[gate] H53 holdout complete; H53-A promoted={promoted}; "
          f"H53-F adopted arm={f_dec['adopted_arm']} -> ratio={ratio}, flank={flank} px, "
          f"mass={n_dots:,} dots", flush=True)

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    priors = prior_rasters()
    ref_count = require_family_reference_coverage(priors)
    print(f"[uniqueness] {ref_count} pinned family references + local priors", flush=True)

    # ---- Stage 2 belief field (new seeds -> new support) --------------------
    names_hd, mm_hd, keep_hd = load_extras("HD")
    names_hh, mm_hh, keep_hh = load_extras("HH")
    cache_hd = P / f"h53_full_field_H_D_seed{args.seed_hd}.npy"
    cache_hh = P / f"h53_full_field_H_H_seed{args.seed_hh}.npy"
    cache_h53 = P / f"h53_full_field_HH_h53a_seed{args.seed_h53a}.npy"
    cols_hd = [mm_hd[i] for i in keep_hd]
    cols_hh = [mm_hh[i] for i in keep_hh]
    if cache_hd.is_file():
        field_hd = np.load(cache_hd)
    else:
        print("[stage2] fitting full H-D field (seed", args.seed_hd, ")", flush=True)
        field_hd = fit_full_field(stack, footprint, catalogue, cols_hd, args.seed_hd)
        np.save(cache_hd, field_hd)
    if cache_hh.is_file():
        field_hh = np.load(cache_hh)
    else:
        print("[stage2] fitting full H-H field (seed", args.seed_hh, ")", flush=True)
        field_hh = fit_full_field(stack, footprint, catalogue, cols_hh, args.seed_hh)
        np.save(cache_hh, field_hh)
    if promoted:
        if cache_h53.is_file():
            field_h53 = np.load(cache_h53)
        else:
            df, _assign, observations = _load_stage1_inputs(footprint, catalogue)
            g = h53a_features(catalogue, footprint, df, observations)
            feat = [g[n] for n in feature_names()]
            print("[stage2] fitting full H-H+H53-A field (seed", args.seed_h53a, ")",
                  flush=True)
            field_h53 = fit_full_field(stack, footprint, catalogue,
                                       cols_hh + feat, args.seed_h53a)
            np.save(cache_h53, field_h53)
        field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                 + 0.5 * np.nan_to_num(field_h53, nan=0.0)).astype(np.float32)
        arm_note = "0.5 H-D + 0.5 (H-H + H53-A fine-scale strain-residual ridge)"
    else:
        field = (0.5 * np.nan_to_num(field_hd, nan=0.0)
                 + 0.5 * np.nan_to_num(field_hh, nan=0.0)).astype(np.float32)
        arm_note = "0.5 H-D + 0.5 H-H (regeneration of the promoted procedure)"
    field[~footprint] = np.nan
    del field_hd, field_hh
    print(f"[stage2] belief field: {arm_note}", flush=True)

    # ---- Stage 1 approved domain (full catalogue, q10) ----------------------
    df, _assign, observations = _load_stage1_inputs(footprint, catalogue)
    cfg = sb.BudgetConfig(tile_px=100, rate_convention="vertical",
                          assume_unknown_normal=True)
    exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
        catalogue, df, cfg, area_mask=footprint)
    fault_ii = sb.invariant(exx, eyy, exy, "II")
    obs_ii = sb.observed_tiles(observations["geod_2ndinv"], footprint, 100)
    support = sb.observed_tiles(np.ones(footprint.shape, dtype=np.float32),
                                footprint, 100)
    valid_tiles = np.isfinite(support) & (support > 0.05)
    q_fault = sb.quantile_map(np.where(valid_tiles, fault_ii, np.nan))
    q_obs = sb.quantile_map(np.where(valid_tiles, obs_ii, np.nan))
    deficit = q_obs - q_fault
    big = np.repeat(np.repeat(deficit, 100, axis=0), 100, axis=1)
    big = big[:GRID.shape[0], :GRID.shape[1]]
    finite = footprint & np.isfinite(big)
    threshold = float(np.nanpercentile(big[finite], 10.0))
    approved = finite & (big >= threshold)
    area_share = float(approved.sum() / max(int(footprint.sum()), 1))
    print(f"[stage1] q10 approved area={area_share:.6f}; diagnostic only, "
          "stage1_weight=0.0", flush=True)

    # ---- emission (STE L9 w=0.35 spacing 2.4, confined) ---------------------
    dom = footprint & np.isfinite(field)
    exclude = ndi.distance_transform_edt(~catalogue) <= flank
    allow = dom & ~exclude & approved
    score, theta = te.strike_coherent_score(field, allow, sigmas=(1.0, 2.0, 3.5),
                                            line_len=9, n_orient=12, w_cont=0.35)
    ys, xs = te.spaced_dots(score, allow, n_dots, spacing=2.4)
    support_mask = np.zeros(GRID.shape, dtype=bool)
    support_mask[ys, xs] = True
    if int(support_mask.sum()) != n_dots:
        raise SystemExit(f"emitter placed {int(support_mask.sum())} of {n_dots} dots")
    inside = int((support_mask & approved).sum())
    emitted_share = inside / max(int(support_mask.sum()), 1)
    lift = emitted_share / max(area_share, 1e-12)
    leak = on_catalogue_mass(support_mask, catalogue, valid=footprint)
    if leak["on_catalogue_px"]:
        raise SystemExit("REFUSING to write: emission overlaps published catalogue pixels")
    if emitted_share != 1.0:
        raise SystemExit("REFUSING to write: a dot escaped the approved Stage-1 tiles")
    if lift > 1.5:
        raise SystemExit(f"REFUSING to write: Stage-1 dominance lift={lift:.6f} > 1.5")
    print(f"[emit] STE placed {int(support_mask.sum()):,} dots; flank={flank} px; "
          f"approved share={emitted_share:.4f}; lift={lift:.4f}", flush=True)

    # ---- geometry audit ------------------------------------------------------
    rng = np.random.default_rng(0)
    yy, xx = np.nonzero(support_mask)
    d_cat = ndi.distance_transform_edt(~catalogue)
    if yy.size > 4000:
        sel = rng.choice(yy.size, size=4000, replace=False)
        sy, sx = yy[sel], xx[sel]
    else:
        sy, sx = yy, xx
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack([sy, sx]))
    dd, _ = tree.query(np.column_stack([sy, sx]), k=2)
    nn_median = float(np.median(dd[:, 1]))
    dvals = d_cat[yy, xx]
    geometry = dict(
        dots=int(yy.size),
        d_cat_p10=float(np.percentile(dvals, 10)),
        d_cat_median=float(np.percentile(dvals, 50)),
        d_cat_p90=float(np.percentile(dvals, 90)),
        frac_within_3px=float((dvals <= 3.0).mean()),
        frac_within_5px=float((dvals <= 5.0).mean()),
        frac_within_10px=float((dvals <= 10.0).mean()),
        spacing=dict(n=int(yy.size), nn_median=nn_median,
                     nn_p10=float(np.percentile(dd[:, 1], 10)),
                     nn_p90=float(np.percentile(dd[:, 1], 90))),
    )

    # ---- pre-write uniqueness gate (before any TIFF byte exists) ------------
    unique_preflight = require_unique_support(support_mask, priors)
    print("[preflight]", json.dumps({k: unique_preflight[k] for k in
          ("n_prior", "max_jaccard", "max_jaccard_prior", "max_containment",
           "max_containment_prior", "verdict")}, indent=1), flush=True)

    if args.dry_run:
        print("[dry-run] all gates passed; no TIFF written", flush=True)
        print(json.dumps(dict(n_dots=n_dots, flank_px=flank, ratio=ratio,
                              area_share=area_share, lift=lift,
                              geometry=geometry,
                              preflight=unique_preflight), indent=1))
        return 0

    # ---- write TIFF (staged), gate, rename -----------------------------------
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha8 = hashlib.sha256(np.ascontiguousarray(support_mask.view(np.uint8))
                          ).hexdigest()[:10]
    base = f"gemsdoe51-{args.tag}-{stamp}-{sha8}"
    staging = DOWNLOADS_DIR / f".{base}.staging.tif"
    primary = DOWNLOADS_DIR / f"{base}.tif"
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    values = support_mask.astype(np.float32)
    try:
        rec_fmt = write_tif(staging, values, footprint, outside=0.0, nodata=None)
        if not rec_fmt["checks"]["format_valid"]:
            raise SystemExit("staged GeoTIFF failed local official-format verifier")
        uniform_control = rec.get("stage1_non_dominance", {}).get("uniform_control")
        gate = run_gate(staging, priors, support_mask, footprint,
                        stage1_approved=approved, hard_confined=True,
                        uniform_control=uniform_control)
        if gate.verdict != "PASS":
            raise SystemExit("staged GeoTIFF failed source-aware uniqueness/Stage-1 "
                             "gate: " + gate.verdict)
        staging.replace(primary)
        rec_fmt = verify(primary, footprint)
        rec_fmt["file"] = primary.name
        gate.candidate = primary.name
    finally:
        if staging.exists():
            staging.unlink()
    zip_path = DOWNLOADS_DIR / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(primary, primary.name)

    # ---- Stage-2 dominance diagnostic (top-decile concentration) ------------
    field_in_allow = np.nan_to_num(field, nan=0.0)[allow]
    order = np.argsort(field_in_allow, kind="stable")
    ranks = np.empty(field_in_allow.size, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, field_in_allow.size, dtype=np.float32)
    top_decile = np.zeros(GRID.shape, bool)
    tmp = np.zeros(int(allow.sum()), bool)
    tmp[ranks >= 0.90] = True
    top_decile[allow] = tmp
    stage2_top_decile_share = float((support_mask & top_decile).sum()
                                    / max(int(support_mask.sum()), 1))

    # ---- manifest update -----------------------------------------------------
    hold = rec.get("candidate_result", {})
    base_h = rec.get("baseline", {})
    cand_mean = hold.get("stage1_q10_gated_mean_dti")
    gated_base_mean = base_h.get("stage1_q10_gated_mean_dti")
    # folds won by the arm the artifact actually uses: H53-A when promoted,
    # otherwise the regeneration of the fresh baseline (a tie, 0 folds).
    if promoted:
        folds_won = sum(
            1 for r in rec.get("rows", [])
            if r["outputs"]["h53a_blend_stage1_q10"]["dti"]
            > r["outputs"]["fresh_hd_hh_blend_stage1_q10"]["dti"])
    else:
        folds_won = 0
    built_mean = float(cand_mean) if promoted else float(gated_base_mean)
    cost_vs_frozen = built_mean - FROZEN_BEST
    submission_name = f"GEMSDOE51-{args.tag.upper()}-{stamp}"
    note = (f"Two-stage GEMSDOE51 H53 submission: coarse rank-space strain-budget "
            f"deficit (q10 approved tiles, {area_share*100:.1f}% of footprint) gating a "
            f"STE L9 emission of the {arm_note} belief field; {n_dots:,} unit dots, none "
            f"within {flank*100:.0f} m of the published catalogue, 100% inside approved "
            f"tiles; all cells finite in [0,1] with zeros outside the footprint; local "
            f"format/uniqueness/Stage-1 gates passed; H53-A promoted={promoted}; "
            f"no organizer score claimed.")
    record = dict(
        id=f"H53_{args.tag.upper()}_{stamp}",
        role="UPLOAD_CANDIDATE_LOCAL_GATES_PASSED",
        status="LOCAL_GATES_PASSED_NOT_ORGANIZER_SCORED_NOT_PORTAL_TESTED",
        file=primary.name,
        zip=zip_path.name,
        submission_name=submission_name,
        note=note,
        sha256=rec_fmt["sha256"],
        bytes=rec_fmt["bytes"],
        checks_file=f"{base}-checks.json",
        format=rec_fmt,
        stage1_dominance=dict(
            q=10.0, tile_px=100, approved_area_share=area_share,
            threshold=threshold, emitted_share_inside_approved=emitted_share,
            lift_over_area_share=lift,
            formula=("Kreemer et al. (2000), Eq. 3: eps_ij = 1/2 sum_k "
                     "[L_k u_dot_k/(A sin(delta_k))] m_ij^k"),
            residual_policy=("rank-space q(geodetic) - q(fault tensor II) is a coarse "
                             "diagnostic only; no absolute dilation/shear subtraction "
                             "is claimed because source conventions are unresolved"),
            role="coarse prior allowed-domain only; stage1_weight=0.0"),
        geometry_audit=geometry,
        uniqueness=dict(prewrite=unique_preflight, staged=gate.as_dict(),
                        reference_count=ref_count,
                        scope=("locally available archived files, data/prior, data/refs "
                               "and current downloads; not a global proof")),
        paired_holdout=dict(
            instrument=("six-fold contiguous spatial holdout (3x3, 12 px training "
                        "buffer); visible known-fault proxy truth; STE emission "
                        "restricted to the held-out block at matched mass"),
            comparator=("fresh same-fold H-H/H-D 50/50 blend, q10-gated "
                        "(evidence/h53sr_holdout_20261008.json)"),
            folds_evaluated=6,
            baseline_mean=float(gated_base_mean),
            baseline_reproduces_archived=bool(base_h.get("reproduced")),
            baseline_archived_max_abs_dev=float(base_h.get("fresh_max_abs_dev_vs_frozen", 0.0)),
            # What the BUILT FILE is expected to score: the H53-A geometry when
            # promoted, otherwise the freshly validated baseline procedure it
            # regenerates (a zero delta against the same-fold baseline).
            artifact_mean=built_mean,
            artifact_delta_vs_fresh_gated_baseline=built_mean - float(gated_base_mean),
            artifact_folds_won_vs_baseline=folds_won,
            # The H53-A hypothesis result, reported separately and in full.
            h53a_candidate_mean=float(cand_mean),
            h53a_paired_mean_delta=float(cand_mean - gated_base_mean),
            h53a_positive_folds=int(hold.get("positive_folds_vs_stage1_gated_hd_hh", 0)),
            frozen_ungated_best_mean=FROZEN_BEST,
            measured_cost_vs_frozen_ungated_best=cost_vs_frozen,
            h53a_promoted=bool(promoted),
            preregistered_verdict=("PROMOTED_LOCAL_PROXY_ONLY" if promoted
                                   else "NOT_PROMOTED_REGENERATION_OF_PROMOTED_PROCEDURE"),
            evidence="evidence/h53sr_holdout_20261008.json",
            note=("The candidate geometry is the q10-confined H53-A blend; its "
                  "measured proxy sits a small compliance cost below the frozen "
                  "UNGATED local best, which is itself not uploadable (fails q10 "
                  "confinement; NaN-outside encoding). Local proxy numbers are not "
                  "organizer scores."
                  if promoted else
                  "H53-A was not promoted; the artifact regenerates the freshly "
                  "validated H-H/H-D procedure with new seeds, so artifact_mean "
                  "equals the fresh q10-gated baseline (zero delta, 0 folds won) "
                  "and measured_cost_vs_frozen_ungated_best is the honest "
                  "compliance cost of q10 confinement vs the frozen ungated best. "
                  "The H53-A hypothesis numbers are reported separately under "
                  "h53a_*. Local proxy numbers are not organizer scores."),
        ),
        model=dict(
            detector="HistGradientBoostingClassifier",
            h_d_features=names_hd,
            h_h_features=names_hh,
            h53a_features=(feature_names() if promoted else []),
            blend_weight_hh=0.5,
            negative_samples=250000,
            max_iter=250,
            seeds=dict(hd=args.seed_hd, hh=args.seed_hh,
                       h53a=(args.seed_h53a if promoted else None)),
        ),
        emission=dict(method="STE", line_length=9, continuity_weight=0.35,
                      spacing_px=2.4, sigmas=[1.0, 2.0, 3.5],
                      flank_px=flank, ratio=ratio, g_hidden=G_HIDDEN_ESTIMATE,
                      requested_dots=n_dots, placed_dots=int(support_mask.sum())),
        stage2_dominance=dict(
            top_decile_share=stage2_top_decile_share,
            dots_per_approved_px=float(int(support_mask.sum()) / max(int(approved.sum()), 1)),
            note="a uniform fill would put 10% of dots in the top field decile"),
        limitations=[
            "Holdout truth is the visible known-fault catalogue, not hidden expert labels.",
            "The planning mass 12700 is not an organizer-published hidden-label count.",
            "Local mirrors are hash-checked but not organizer-authenticated.",
            "The Stage-1 rate field is provisionally interpreted as mm/yr; source component and dip are unresolved.",
            "No organizer upload, portal acceptance, or score is claimed.",
        ],
    )

    manifest_path = ROOT / "data" / "submission_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    # The previous primary (archived H-H/H-D blend) STAYS in place as the demoted,
    # audit-only local benchmark: it keeps every field the site's NOT-CLEARED card
    # renders (holdout, stage1 diagnostics, evidence), and its role/status/note now
    # record that the H53 artifact supersedes it as the upload candidate.  The four
    # existing research-only artifacts are retained unchanged.  The demotion is
    # idempotent: an already-demoted primary is left untouched.
    prev = manifest.get("primary") or {}
    if prev.get("role") == "ARCHIVED_LOCAL_BENCHMARK_NOT_UPLOADABLE":
        demoted = dict(prev)
    else:
        demoted = dict(prev)
        demoted["role"] = "ARCHIVED_LOCAL_BENCHMARK_NOT_UPLOADABLE"
        demoted["status"] = ("LOCAL_PROXY_BEST_NOT_UPLOADABLE_Q10_AND_PORTAL_RANGE_"
                             "BLOCKERS")
        demoted["note"] = (str(prev.get("note", "")).rstrip()
                           + " SUPERSEDED by the H53 two-stage artifact as the upload "
                             "candidate; remains research-only/audit — do not upload "
                             "(fails the q10 all-points-inside requirement; "
                             "NaN-outside encoding is the unresolved portal range "
                             "hazard).").strip()
    manifest["primary"] = demoted
    manifest["artifacts"] = [demoted]
    manifest["research_only_artifacts"] = list(
        manifest.get("research_only_artifacts", []))
    manifest["recommended_upload_candidate"] = record
    manifest["submission_readiness"] = {
        "status": "LOCAL_GATES_PASSED_NOT_PORTAL_TESTED",
        "upload_ok": True,
        "caveat": ("Every cell of the file is finite and in [0, 1] (zeros outside the "
                   "footprint, no NoData tag), verified by re-reading the bytes; this "
                   "cannot trigger the reported 'values must be in range [0, 1]' portal "
                   "error. Organizer acceptance and any score are unverified and are "
                   "not claimed. The entrant decides whether to spend a competition slot."),
    }
    manifest["status"] = "UPLOAD_CANDIDATE_LOCAL_GATES_PASSED_NOT_PORTAL_TESTED"
    manifest["candidate_screen"] = {
        "candidate": ("H53-A fine-scale geodetic strain-residual ridge features added "
                      "to the H-H arm" if promoted else
                      "H53-A NOT PROMOTED; artifact is the q10-confined regeneration of "
                      "the promoted H-H/H-D procedure"),
        "status": ("PROMOTED_LOCAL_PROXY_ONLY" if promoted else "NOT_PROMOTED_NO_H53A_TIFF"),
        "evidence": "evidence/h53sr_holdout_20261008.json",
        "reason": (f"H53-A q10-gated mean {cand_mean:.6f} vs frozen best "
                   f"{rec.get('baseline', {}).get('frozen_mean_dti'):.6f}; paired gated "
                   f"delta {hold.get('paired_mean_delta_vs_stage1_gated_hd_hh'):+.6f}; "
                   f"{hold.get('positive_folds_vs_stage1_gated_hd_hh', 0)}/6 folds"),
    }
    manifest["promotion"] = {
        "decision": ("H53-A PROMOTED; submission build authorized" if promoted else
                     "H53-A NOT PROMOTED; submission is the regeneration of the "
                     "promoted H-H/H-D procedure under the brief's constraints"),
        "rule": ("frozen registry/preregistration_h53sr_20261008.json; fresh ungated baseline "
                 "reproduces frozen mean within 1e-5; q10-gated candidate beats "
                 "frozen best with >= 4/6 folds; 100% confinement; lift <= 1.5"),
        "h53_a_promoted": promoted,
        "h53_f": f_dec,
        "portal_status": "NOT TESTED; no organizer upload or score claimed",
    }
    manifest["stage1_stats"] = (meta | dict(
        approved_px=int(approved.sum()), approved_share_of_footprint=area_share,
        emitted_share_inside_approved=emitted_share, lift_over_area_share=lift,
        threshold=threshold,
        formula=("Kreemer et al. (2000), Eq. 3: eps_ij = 1/2 sum_k "
                 "[L_k u_dot_k/(A sin(delta_k))] m_ij^k"),
        residual_policy=("rank-space q(geodetic) - q(fault tensor II) is a coarse "
                         "diagnostic only; no absolute dilation/shear subtraction is "
                         "claimed because source conventions are unresolved"),
        fault_median_II_nanostrain=float(np.nanmedian(fault_ii)),
        observed_median_II_nanostrain=float(np.nanmedian(obs_ii)),
        residual_controls=("dilatation and shear rank residuals were computed but not "
                           "used to place Stage-2 points"),
        rank_residual_holdout_receipt="evidence/stage1_q10_trace_holdout_20261007.json",
        rank_residual_convention=("rank(observed scalar) - rank(fault tensor II); "
                                  "diagnostic only, not an absolute strain subtraction"),
    ))
    manifest["uniqueness"] = gate.as_dict()
    manifest["latest_experiment"] = {
        "id": record["id"],
        "role": "UPLOAD_CANDIDATE",
        "status": "LOCAL_GATES_PASSED_NOT_PORTAL_TESTED",
        "file": primary.name,
        "zip": zip_path.name,
        "submission_name": submission_name,
        "note": note,
        "sha256": rec_fmt["sha256"],
        "bytes": rec_fmt["bytes"],
        "format": rec_fmt,
        "holdout": record["paired_holdout"],
        "holdout_promoted": promoted,
        "uniqueness": record["uniqueness"],
        "stage1_dominance": record["stage1_dominance"],
        "geometry_audit": geometry,
    }
    manifest["generated_utc"] = stamp
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")

    checks = dict(
        name=base, promoted_h53a=promoted, h53f_decision=f_dec,
        ratio=ratio, flank_px=flank, n_dots=n_dots, n_emitted=int(support_mask.sum()),
        stage1_q=10.0, tile_px=100, stage1_area_share=area_share,
        stage1_emitted_share=emitted_share, stage1_lift=lift,
        on_catalogue_px=int(leak["on_catalogue_px"]),
        stage2_top_decile_share=stage2_top_decile_share,
        geometry_audit=geometry,
        holdout=rec,
        field_extras_hh=names_hh, field_extras_hd=names_hd,
        grid=dict(shape=list(GRID.shape), transform=list(GRID.transform), epsg=GRID.epsg),
        format=rec_fmt, uniqueness=gate.as_dict(),
    )
    (DOWNLOADS_DIR / f"{base}-checks.json").write_text(json.dumps(checks, indent=1))

    build = dict(
        created_utc=stamp, name=base, promoted_h53a=promoted,
        config=dict(vars(args)),
        tif=dict(file=primary.name, bytes=primary.stat().st_size, sha256=sha256(primary)),
        zip=dict(file=zip_path.name, bytes=zip_path.stat().st_size, sha256=sha256(zip_path)),
        emitted_px=int(support_mask.sum()), on_catalogue_px=int(leak["on_catalogue_px"]),
        stage1_area_share=area_share, stage1_lift=lift,
        uniqueness_verdict=gate.verdict,
        holdout_receipt="evidence/h53sr_holdout_20261008.json",
        notes=("Two-stage H53 submission: coarse rank-space strain-budget prior "
               "(Stage 1, tiles only, q10 approved domain) + blended belief-field "
               "STE emission (Stage 2, every point inside the approved tiles). Local "
               "format and uniqueness checks only — no organizer score is claimed."),
    )
    (ROOT / "registry" / "submission_build_h53.json").write_text(
        json.dumps(build, indent=1))
    print(json.dumps(dict(
        file=str(primary), zip=str(zip_path), submission_name=submission_name,
        sha256=rec_fmt["sha256"], n_dots=n_dots, flank_px=flank, ratio=ratio,
        stage1_area_share=area_share, stage1_lift=lift,
        uniqueness=gate.verdict, promoted_h53a=promoted,
        artifact_holdout_mean=record["paired_holdout"]["artifact_mean"],
        h53a_holdout_mean=record["paired_holdout"]["h53a_candidate_mean"],
        baseline_gated_mean=gated_base_mean,
    ), indent=1))
    print(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
