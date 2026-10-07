#!/usr/bin/env python3
"""Build a two-stage GeoTIFF proposal only after all current gates are eligible.

Decisions this script makes, and where each comes from:
  * which hypothesis arm's features to use ....... --arm (chosen on the holdout)
  * the emitted mass ............................. --ratio x |G| estimate (holdout argmax)
  * the Stage 1 approval threshold ............... --stage1-q (holdout, Stage 1 scored alone)
  * the exclusion radius around known faults ..... --excl-radius (2.0 px in the
                                                    evaluated proxy configuration; not an
                                                    organizer-calibrated value)

The only new proposal to clear the numeric holdout screen (H-D, soft w=0.20) failed
support uniqueness before any GeoTIFF was written. The builder refuses to rerun that exact
configuration from the recorded failure; a new preregistered candidate and holdout result are
required before a build can be considered.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.submission import verify, write_tif  # noqa: E402
from gems51.uniqueness import jaccard, overlap_fraction, run_gate  # noqa: E402

P = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"

# The hidden truth mass |G| is not published. This inherited value is only a
# provisional working point for an illustrative full-map dot budget; it is not an
# organizer label count or a measured truth size. Any future build needs a
# documented sensitivity analysis over plausible masses.
G_HIDDEN_ESTIMATE = 12_700


def load_observed():
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        out = {}
        for nm in ["geod_2ndinv", "geod_shearrate", "geod_dilaterate"]:
            a = s.read(descs.index(nm) + 1).astype(np.float64)
            a[a <= -1e38] = np.nan
            out[nm] = a
    return out


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def stage1_approved(catalogue: np.ndarray, footprint: np.ndarray, df, obs,
                    tile_px: int, q: float):
    cfg = sb.BudgetConfig(tile_px=tile_px)
    exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
        catalogue, df, cfg, area_mask=footprint)
    II_f = sb.invariant(exx, eyy, exy, "II")
    obsII = sb.observed_tiles(obs["geod_2ndinv"], footprint, tile_px)
    dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, tile_px)
    ok_t = np.isfinite(dom) & (dom > 0.05)
    q_f = sb.quantile_map(np.where(ok_t, II_f, np.nan))
    q_o = sb.quantile_map(np.where(ok_t, obsII, np.nan))
    deficit = q_o - q_f
    big = upsample(deficit, tile_px)
    thr = np.nanpercentile(big[footprint & np.isfinite(big)], q)
    approved = footprint & np.isfinite(big) & (big >= thr)
    return approved, deficit, thr, meta, II_f, obsII


def require_holdout_promotion(arm: str, gate_mode: str, gate_weight: float,
                              ratio: float, stage1_q: float, nms_radius: float,
                              excl_radius: float, tile_px: int, g_hidden: int) -> dict:
    """Fail closed unless the exact build configuration passed the frozen screen.

    H-D with soft weight 0.20 cleared the numeric proxy holdout rule, but it is
    not fully promoted: the recorded positive-pixel support fails uniqueness.
    No submission configuration is currently eligible. This numeric screen is
    local known-fault proxy evidence, not an organizer score.
    """
    expected = (arm == "H_D" and gate_mode == "soft"
                and abs(gate_weight - 0.2) < 1e-12
                and abs(ratio - 3.47) < 1e-12
                and abs(stage1_q - 50.0) < 1e-12
                and abs(nms_radius - 2.4) < 1e-12
                and abs(excl_radius - 2.0) < 1e-12
                and tile_px == 100 and g_hidden == G_HIDDEN_ESTIMATE)
    if not expected:
        raise SystemExit(
            "No stored promotion evidence for this exact build configuration. "
            "H-D / soft weight 0.2 / ratio 3.47 / q50 cleared only the numeric screen and is "
            "rejected by uniqueness; no submission is currently eligible."
        )
    path = ROOT / "data" / "gate_sweep.json"
    if not path.exists():
        raise SystemExit("data/gate_sweep.json is required for the promotion gate")
    report = json.loads(path.read_text())
    sweep_config = report.get("config", {})

    def same_number(key, expected):
        try:
            return bool(np.isclose(float(sweep_config[key]), expected, rtol=0, atol=1e-12))
        except (KeyError, TypeError, ValueError):
            return False

    try:
        folds_match = int(sweep_config.get("folds", 0)) == 6
        tile_match = int(sweep_config.get("tile_px", -1)) == tile_px
    except (TypeError, ValueError):
        folds_match = tile_match = False
    if (sweep_config.get("arm") != arm or not folds_match or not tile_match
            or not same_number("nms_radius", nms_radius)
            or not same_number("excl_radius", excl_radius)):
        raise SystemExit("gate-sweep configuration does not match the requested build")
    try:
        sweep_ratios = [float(value) for value in str(sweep_config.get("ratios", "")).split(",")]
    except ValueError as exc:
        raise SystemExit("gate-sweep ratios are not parseable") from exc
    if len(sweep_ratios) != 1 or abs(sweep_ratios[0] - ratio) > 1e-12:
        raise SystemExit("gate-sweep ratio does not match the requested build")
    candidate = report.get("soft", {}).get("0.2")
    baseline = report.get("soft", {}).get("0.0")
    if not candidate or not baseline:
        raise SystemExit("gate sweep is missing the candidate or ungated comparison")
    candidate_folds = np.asarray(candidate.get("per_fold", []), dtype=float)
    baseline_folds = np.asarray(baseline.get("per_fold", []), dtype=float)
    if candidate_folds.shape != (6,) or baseline_folds.shape != (6,):
        raise SystemExit("promotion requires exactly six paired holdout folds")
    mean = float(candidate_folds.mean())
    delta = candidate_folds - baseline_folds
    positive = int((delta > 0).sum())
    incumbent = json.loads((ROOT / "data" / "holdout_H_D.json").read_text())
    incumbent_config = incumbent.get("config", {})
    incumbent_summary = incumbent.get("summary", {})
    try:
        incumbent_ratios = [float(value) for value in
                            str(incumbent_config.get("ratios", "")).split(",")]
        incumbent_folds = len(incumbent_summary.get("auc_per_fold", []))
        incumbent_nms = float(incumbent_config.get("nms_radius"))
        incumbent_excl = float(incumbent_config.get("excl_radius"))
    except (TypeError, ValueError):
        raise SystemExit("incumbent holdout configuration is incomplete")
    if (incumbent_config.get("arm") != arm or incumbent_folds != 6
            or not any(np.isclose(value, ratio, rtol=0, atol=1e-12)
                       for value in incumbent_ratios)
            or not np.isclose(incumbent_nms, nms_radius, rtol=0, atol=1e-12)
            or not np.isclose(incumbent_excl, excl_radius, rtol=0, atol=1e-12)):
        raise SystemExit("incumbent holdout configuration does not match the requested build")
    incumbent_key = f"dti_r{ratio:g}"
    if incumbent_key not in incumbent_summary:
        raise SystemExit(f"incumbent holdout is missing {incumbent_key}")
    incumbent_mean = float(incumbent_summary[incumbent_key]["mean"])
    if not (mean > incumbent_mean and mean > 0.2817 and positive >= 4):
        raise SystemExit(
            f"Candidate failed the frozen promotion rule: mean={mean:.6f}, "
            f"incumbent={incumbent_mean:.6f}, positive_folds={positive}/6"
        )
    return dict(mean_dti=mean, incumbent_mean_dti=incumbent_mean,
                mean_paired_delta=float(delta.mean()),
                positive_folds=positive, n_folds=6,
                promotion_rule="mean > H-D incumbent and > 0.2817; positive in >=4/6 folds")


def prior_rasters() -> dict[str, Path]:
    """Return every locally available prior submission raster for uniqueness checks."""
    paths = {}
    roots = (ROOT / "data" / "prior", ROOT / "docs" / "downloads",
             ROOT / "submissions", ROOT / "archive" / "submissions")
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.tif")):
            if p.name.startswith("."):
                continue
            paths[p.relative_to(ROOT).as_posix()] = p
    return paths


def require_unique_support(candidate_support: np.ndarray, prior_paths: dict,
                           max_jaccard: float = 0.50,
                           max_containment: float = 0.60) -> dict:
    """Check a proposed support against all available local prior TIFFs before writing.

    The metric intentionally operates on positive-pixel support rather than TIFF
    bytes so that changing a filename, NoData encoding, or metadata cannot turn a
    duplicate map into a unique submission.
    """
    rows = []
    import rasterio
    for label, path in prior_paths.items():
        try:
            with rasterio.open(path) as src:
                arr = src.read(1)
            if arr.shape != candidate_support.shape:
                continue
            other = np.isfinite(arr) & (arr > 0)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"cannot verify prior raster {path}: {exc}") from exc
        rows.append(dict(label=label, jaccard=float(jaccard(candidate_support, other)),
                         containment=float(overlap_fraction(candidate_support, other))))
    if not rows:
        raise SystemExit("no prior rasters were available; uniqueness cannot be verified")
    worst_j = max(rows, key=lambda row: row["jaccard"])
    worst_c = max(rows, key=lambda row: row["containment"])
    report = dict(n_prior=len(rows), max_jaccard=worst_j["jaccard"],
                  max_jaccard_prior=worst_j["label"],
                  max_containment=worst_c["containment"],
                  max_containment_prior=worst_c["label"],
                  limits=dict(jaccard=max_jaccard, containment=max_containment),
                  prior_supports=rows, verdict="PASS")
    if worst_j["jaccard"] > max_jaccard or worst_c["containment"] > max_containment:
        report["verdict"] = "FAIL"
        raise SystemExit("proposed support is too similar to an available prior; "
                         + json.dumps(report, indent=1))
    return report


def matches_recorded_uniqueness_failure(config: dict, manifest: dict) -> bool:
    """Whether this is the exact configuration already rejected before TIFF writing."""
    result = manifest.get("decision", {}).get("h_d_soft_w020", {})
    if result.get("uniqueness", {}).get("promotion") != "FAIL_UNIQUENESS":
        return False
    recorded = result.get("config", {})
    keys = ("arm", "gate_mode", "gate_weight", "ratio", "g_hidden_estimate",
            "stage1_q", "tile_px", "nms_radius", "excl_radius")
    if not all(key in recorded and key in config for key in keys):
        return False
    for key in keys:
        expected, actual = recorded[key], config[key]
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            try:
                if abs(float(expected) - float(actual)) > 1e-12:
                    return False
            except (TypeError, ValueError):
                return False
        elif expected != actual:
            return False
    return True


def require_not_repeating_known_failure(config: dict) -> None:
    path = ROOT / "data" / "submission_manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {}
    if matches_recorded_uniqueness_failure(config, manifest):
        raise SystemExit(
            "This exact H-D soft-w=0.20 configuration already failed support uniqueness "
            "before writing a TIFF. Do not rerun it unchanged; preregister and evaluate a "
            "substantively distinct candidate before another build."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H_D")
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--g-hidden", type=int, default=G_HIDDEN_ESTIMATE)
    ap.add_argument("--stage1-q", type=float, default=50.0)
    ap.add_argument("--gate-mode", default="soft", choices=["soft","hard"])
    ap.add_argument("--gate-weight", type=float, default=0.20)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--excl-radius", type=float, default=2.0)
    ap.add_argument("--neg", type=int, default=400000)
    ap.add_argument("--max-iter", type=int, default=400)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--n-models", type=int, default=3)
    ap.add_argument("--reuse-field", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    require_not_repeating_known_failure(dict(
        arm=a.arm, gate_mode=a.gate_mode, gate_weight=a.gate_weight,
        ratio=a.ratio, g_hidden_estimate=a.g_hidden, stage1_q=a.stage1_q,
        tile_px=a.tile_px, nms_radius=a.nms_radius, excl_radius=a.excl_radius))
    promotion = require_holdout_promotion(
        a.arm, a.gate_mode, a.gate_weight, a.ratio, a.stage1_q,
        a.nms_radius, a.excl_radius, a.tile_px, a.g_hidden)
    print("[promotion gate]", json.dumps(promotion, indent=1), flush=True)

    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()

    # ---------------------------------------------------------------- Stage 1
    approved, deficit, thr, meta, II_f, obsII = stage1_approved(
        catalogue, footprint, df, obs, a.tile_px, a.stage1_q)
    deficit_big = upsample(deficit, a.tile_px)
    area_share = float(approved.sum() / footprint.sum())
    print(f"[stage1] deficit tile prior @ q={a.stage1_q}: threshold {thr:.4f}, "
          f"approved {int(approved.sum()):,} px = {area_share:.1%} of the footprint", flush=True)

    # ---------------------------------------------------------------- Stage 2
    ex_path = P / "extras_static.dat"
    extra_cols, ex_names = [], []
    # arm -> static extra name prefixes (kept identical to run_experiments.ARMS)
    armmap = {"H_E": ["base_s", "cond_s", "grav2_s", "base_step_coh"],
              "H_D": ["facecoh"],
              "H_ALL": ["base_s", "cond_s", "grav2_s", "base_step_coh", "facecoh"],
              "base": [], "H_C": []}
    keys = armmap.get(a.arm, [])
    if keys and ex_path.exists():
        names = json.loads((P / "extras_static_names.json").read_text())
        mm = np.memmap(ex_path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
        for i, n in enumerate(names):
            if any(k in n for k in keys):
                extra_cols.append(np.asarray(mm[i], dtype=np.float32))
                ex_names.append(n)
    if a.arm in ("H_C", "H_ALL"):
        from gems51.extras import build_catalogue_dependent
        cd = build_catalogue_dependent(stack, footprint, catalogue)
        extra_cols.append(cd["d_tip"])
        ex_names.append("d_tip")
    print(f"[stage2] arm {a.arm}: +{len(ex_names)} extra features: {ex_names}", flush=True)

    # Bagged ensemble: the negatives are drawn at random from 5.1 M candidates, so
    # a single draw is only one view of the background.  Averaging a few draws
    # reduces the variance of the ranking without touching the bias, which is the
    # cheap part of the detector to improve.
    neg_pool = footprint & ~catalogue
    if a.reuse_field and (P / "field_final.npy").exists():
        field = np.load(P / "field_final.npy")
        print("[stage2] reusing cached field_final.npy", flush=True)
    else:
      field = np.zeros(GRID.shape, np.float32)
      for m in range(max(1, a.n_models)):
        rng = np.random.default_rng(a.seed + 101 * m)
        X, y = stack.sample(catalogue & footprint, neg_pool, a.neg, rng, extra=extra_cols)
        if m == 0:
            print(f"[stage2] training on {X.shape[0]:,} rows ({int(y.sum()):,} positives, "
                  f"{X.shape[1]} features) x {a.n_models} bag(s)", flush=True)
        model = fit_detector(X, y, seed=a.seed + m, max_iter=a.max_iter)
        del X, y
        field += predict_grid(model, stack, footprint, extra=extra_cols)
        print(f"[stage2] bag {m + 1}/{a.n_models} done ({time.time()-t0:.0f}s)", flush=True)
      field /= float(max(1, a.n_models))
      np.save(P / "field_final.npy", field)

    # ---------------------------------------------------------------- emission
    # Holdout-gated build: only H-D soft w=0.20 is allowed past the frozen
    # promotion check. The prior remains a multiplicative rank nudge over the
    # full footprint; there is no hard spatial exclusion by Stage 1.
    n_dots = int(round(a.ratio * a.g_hidden))
    excl = ndi.distance_transform_edt(~catalogue) <= a.excl_radius
    zv = deficit_big[footprint & np.isfinite(deficit_big)]
    z = np.clip((deficit_big - zv.mean()) / max(zv.std(), 1e-9), -4.0, 4.0)

    def emit(mode, weight, q):
        if mode == "soft":
            sc = field * (1.0 + weight * z) if weight else field
            keep = footprint
            used_w, used_q = weight, None
        else:
            sc = field
            thr = np.nanpercentile(zv, q)
            keep = footprint & np.isfinite(deficit_big) & (deficit_big >= thr)
            used_w, used_q = None, q
        ys, xs = nms_dots(sc, n_dots, radius=a.nms_radius,
                          exclude=excl | ~keep, valid=footprint)
        return rasterise(ys, xs), used_w, used_q

    pred, used_w, used_q = emit(a.gate_mode, a.gate_weight, a.stage1_q)
    print(f"[emit] mode={a.gate_mode} w={used_w} q={used_q}: "
          f"requested {n_dots:,} dots, placed {int((pred > 0).sum()):,}", flush=True)

    # Fail closed before any GeoTIFF is created if the emitted support duplicates
    # a prior local candidate or the coarse prior is steering placement too strongly.
    support = pred > 0
    priors = prior_rasters()
    unique_preflight = require_unique_support(support, priors)
    area_share = float(approved.sum() / max(int(footprint.sum()), 1))
    emitted_inside = int((support & approved).sum())
    emitted_share = emitted_inside / max(int(support.sum()), 1)
    stage1_lift = emitted_share / max(area_share, 1e-9)
    if stage1_lift > 1.5:
        raise SystemExit(f"Stage 1 dominance preflight failed: lift={stage1_lift:.3f} > 1.5")
    print("[support preflight]", json.dumps(dict(
        uniqueness=unique_preflight, approved_area_share=area_share,
        emitted_share_inside_approved=emitted_share,
        stage1_lift_over_area=stage1_lift), indent=1), flush=True)

    # ---------------------------------------------------------------- GeoTIFF
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = a.tag or (f"{a.arm.lower()}-softw{a.gate_weight:g}-r{a.ratio:g}"
                    if a.gate_mode == "soft"
                    else f"{a.arm.lower()}-hardq{int(a.stage1_q)}-r{a.ratio:g}")
    if not tag or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in tag):
        raise SystemExit("submission tag must contain only letters, numbers, dot, underscore, or hyphen")
    base = f"gemsdoe51-{tag}-{stamp}"
    primary_file = DOCS / f"{base}.tif"
    staging_file = DOCS / f".{base}.staging.tif"
    try:
        rec = write_tif(staging_file, pred, footprint)
        if not rec["checks"]["format_valid"]:
            raise SystemExit("staged GeoTIFF failed the official-format re-read checks")
        rep = run_gate(staging_file, priors, support, footprint, approved)
        if rep.verdict != "PASS":
            raise SystemExit("staged GeoTIFF failed the full uniqueness/Stage-1 gate")
        staging_file.replace(primary_file)
        rec = verify(primary_file, footprint)
        rep.candidate = primary_file.name
        print("[uniqueness]", json.dumps(rep.as_dict(), indent=1), flush=True)
    finally:
        if staging_file.exists():
            staging_file.unlink()
    zp = DOCS / f"{base}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(primary_file, primary_file.name)

    # ---------------------------------------------------------------- manifest
    primary_record = dict(
        role="PRIMARY", gate_mode=a.gate_mode,
        description=("H-D detector with the weak 10 km geodetic strain-budget "
                     "deficit as a soft multiplicative prior (w=0.20)"),
        holdout_cost_vs_ungated=promotion["mean_paired_delta"],
        file=primary_file.name, zip=zp.name, checks_file=f"{base}-checks.json",
        sha256=rec["sha256"],
        submission_name="GEMSDOE51-HD-SOFT-W020-R347",
        note=(f"GEMSDOE51 H-D soft-prior w=0.20; {int(support.sum()):,} dots, "
              f"2.4 px NMS, >=200 m from known faults; holdout +"
              f"{promotion['mean_paired_delta']:.5f}, {promotion['positive_folds']}/6; UNSCORED"),
        format=("single band, float32, EPSG:32611, 100 m, "
                f"{GRID.shape[0]}x{GRID.shape[1]}, finite [0,1] values inside "
                "the footprint, NaN outside, nodata=NaN"),
        checks=rec["checks"], uniqueness=rep.as_dict(),
        evidence=("format and uniqueness checks were measured by re-reading the staged bytes; "
                  "no organizer score or portal acceptance is claimed"),
    )
    primary_record["format_table"] = [
        ["single band", str(rec["checks"]["single_band"])],
        ["dtype float32", str(rec["checks"]["dtype_float32"])],
        ["CRS EPSG:32611", str(rec["checks"]["crs_epsg_32611"])],
        ["geotransform matches template", str(rec["checks"]["transform_matches_template"])],
        ["3730 x 3292", str(rec["checks"]["shape_matches_template"])],
        ["inside footprint finite", str(rec["checks"]["inside_footprint_finite"])],
        ["outside footprint NaN", str(rec["checks"]["outside_footprint_nan"])],
        ["values inside [0, 1]", str(rec["checks"]["values_outside_0_1"] == 0)],
        ["nodata tag is NaN", str(rec["checks"]["nodata_tag_is_nan"])],
        ["positive pixels", f"{rec['checks']['predicted_px']:,}"],
        ["total emitted mass", f"{rec['checks']['total_mass']:,.0f}"],
    ]
    man = dict(
        status="HOLDOUT_PROMOTED_UNSCORED",
        generated_utc=stamp,
        promotion=promotion,
        config=dict(arm=a.arm, ratio=a.ratio, g_hidden_estimate=a.g_hidden,
                    stage1_q=a.stage1_q, gate_mode=a.gate_mode,
                    gate_weight=a.gate_weight, tile_px=a.tile_px,
                    nms_radius=a.nms_radius, excl_radius=a.excl_radius,
                    n_dots=int(support.sum()), extra_features=ex_names),
        stage1_stats=dict(approved_px=int(approved.sum()),
                          approved_share_of_footprint=area_share,
                          emitted_share_inside_approved=emitted_share,
                          lift_over_area=stage1_lift,
                          threshold=float(thr),
                          fault_median_II_nanostrain=float(np.nanmedian(II_f)),
                          obs_median_II_nanostrain=float(np.nanmedian(obsII)),
                          kostrov_meta=meta),
        primary=primary_record,
        artifacts=[primary_record],
        uniqueness=rep.as_dict(),
    )
    (ROOT / "data" / "submission_manifest.json").write_text(json.dumps(man, indent=1))
    (DOCS / f"{base}-checks.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: v for k, v in primary_record.items() if k != "format_table"}, indent=1))
    print(f"done in {time.time()-t0:.0f}s -> {primary_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
