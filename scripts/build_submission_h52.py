#!/usr/bin/env python3
"""Build the H52 submission GeoTIFF (two stages, one coarse prior, one fine model).

Pipeline
--------
Stage 1 (coarse, never places a point)
    rank-space strain-budget deficit over 10 km tiles (``gems51.stage1``), from the
    full published catalogue; approved domain = tiles at/above the q-th percentile.
Stage 2 (fine, places every point)
    belief field = 50/50 blend of the H-H arm (base + facecoh + hh_ extras) and the
    H-D arm (base + facecoh) of ``gems51.detector``, trained on all published
    catalogue pixels as positives and 500k background pixels as negatives;
    emission = the geometry that passed ``registry/preregistration_h52.json``.

Hard rules enforced in code, not by inspection:
  * nothing is emitted outside the Stage-1 approved domain;
  * nothing is emitted within ``--flank`` pixels of a published catalogue pixel
    (design evidence: gems51.live_metric docstring);
  * every emitted dot is unit mass, so no cell can leave [0, 1];
  * the written raster has zeros outside the footprint, no NaN anywhere and no
    NoData tag, so the portal's "values must be in range [0, 1]" validator cannot
    be triggered by this file.

Outputs (all under ``docs/downloads/`` so the site links them directly)
    <name>.tif          single-band float32 GeoTIFF, portal-format verified
    <name>.zip          one-file ZIP of the identical bytes
    <name>-checks.json  full local verification receipt
    registry/submission_build_h52.json   build provenance + SHA-256

Usage
-----
    .venv/bin/python scripts/build_submission_h52.py --variant V4 --n-dots 42424
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import emission2 as em2          # noqa: E402
from gems51 import tip_model as tm           # noqa: E402
from gems51 import strain_budget as sb       # noqa: E402
from gems51 import stage1 as st1             # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID                 # noqa: E402
from gems51.live_metric import on_catalogue_mass  # noqa: E402
from gems51.paths import DOWNLOADS_DIR       # noqa: E402
from gems51.submission import write_tif      # noqa: E402
from gems51.uniqueness import run_gate, sha256_file  # noqa: E402

P = ROOT / "data" / "prepared"
ARM_KEYS = {"HH": ("facecoh", "hh_"), "HD": ("facecoh",)}


def load_extras(arm: str):
    path = P / "extras_static.dat"
    names = json.loads((P / "extras_static_names.json").read_text())
    keep = [i for i, n in enumerate(names) if any(k in n for k in ARM_KEYS[arm])]
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [names[i] for i in keep], mm, keep


def train_field(stack, footprint, catalogue, arm, negatives, seed):
    names, mm, keep = load_extras(arm)
    # memmap views, not materialised copies (memory discipline on a 3 GB box).
    cols = [mm[i] for i in keep]
    rng = np.random.default_rng(seed)
    X, y = stack.sample(catalogue, footprint & ~catalogue, negatives, rng, extra=cols)
    print(f"    [field {arm}] {len(names)} extras, X={X.shape}, positives={int(y.sum())}", flush=True)
    model = fit_detector(X, y, seed=seed)
    del X, y
    f = predict_grid(model, stack, footprint, extra=cols)
    print(f"    [field {arm}] predicted on {int(np.isfinite(f).sum()):,} pixels", flush=True)
    return f, names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="auto",
                    choices=("auto", "V7", "V6", "V4", "V5", "V2", "V3"),
                    help="emission geometry; V6 = validated STE, V7 = STE inside the "
                         "Stage-1 approved domain (the geometry licensed by "
                         "registry/preregistration_h52_amendment2.json). V2-V5 are the "
                         "pass-1 geometries, kept for reproducibility only.")
    ap.add_argument("--n-dots", type=int, default=44069,
                    help="emitted mass; default = round(3.47 x 12,700) = 44,069, the exact "
                         "mass of the validated research artifact in docs/downloads, so the "
                         "new file is mass-matched with the benchmark it will be compared to")
    ap.add_argument("--flank", type=float, default=2.0,
                    help="published-catalogue clearance in pixels (100 m each); 2.0 is the "
                         "value of the validated STE artifact and is a superset of the "
                         "owner-reported live-verified 1 px (100 m) clearance")
    ap.add_argument("--tip-kappa", type=float, default=0.0,
                    help="strength of the structural-inheritance boost "
                         "field*(1+kappa*prior); 0 disables it (frozen by "
                         "registry/preregistration_h52_amendment3.json)")
    ap.add_argument("--tip-corridor", type=int, default=40)
    ap.add_argument("--tip-half-width", type=float, default=2.0)
    ap.add_argument("--tip-tau", type=float, default=12.0)
    ap.add_argument("--tip-bridge-gap", type=float, default=40.0)
    ap.add_argument("--nms-radius", type=float, default=2.8)
    ap.add_argument("--stage1-q", type=float, default=None,
                    help="Stage-1 approved-domain quantile; default = the value chosen by "
                         "evidence/h52_emission_pass2_*.json (preregistration A4)")
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--negatives", type=int, default=250_000,
                    help="background negatives per arm; 250k is the value of the validated "
                         "H-H/H-D recipe (scripts/evaluate_hh_blend.py)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--force-fields", action="store_true",
                    help="retrain the belief field even if the cached blend exists")
    ap.add_argument("--holdout-ledger", default="",
                    help="evidence/h52_tip_holdout_*.json whose control arms anchor the "
                         "Stage-2 dominance test; default = newest file found")
    args = ap.parse_args()

    t0 = time.time()
    holdout_rec, holdout_path = None, None
    ledgers = ([Path(args.holdout_ledger)] if args.holdout_ledger
               else sorted((ROOT / "evidence").glob("h52_tip_holdout_*.json")))
    if ledgers and Path(ledgers[-1]).is_file():
        holdout_path = Path(ledgers[-1])
        holdout_rec = json.loads(holdout_path.read_text())
        print(f"    structural-prior ledger: {holdout_path.name}")
    p2_path = None
    p2_files = ([Path(args.holdout_ledger)] if args.holdout_ledger
                else sorted((ROOT / "evidence").glob("h52_emission_pass2_*.json")))
    promo = {}
    if args.holdout_ledger:
        p2_files = []
    if p2_files and p2_files[-1].is_file():
        p2_path = p2_files[-1]
        p2 = json.loads(p2_path.read_text())
        p2_summary = p2.get("summary", {})
        promo = p2.get("promotion", {}) or {}
        print(f"    emission ledger: {p2_path.name} -> emitter={promo.get('emitter')} "
              f"chosen_domain q={promo.get('chosen_domain')} "
              f"write_tiff={promo.get('write_tiff')}")
        if args.variant == "auto":
            args.variant = "V7" if str(promo.get("emitter", "")).startswith("STE") else "V4"
        if args.stage1_q is None:
            args.stage1_q = (float(promo["chosen_domain"])
                             if promo.get("chosen_domain") is not None else 10.0)
        if promo.get("harness_ok") is False:
            raise SystemExit("REFUSING to build: the emission ledger reports harness_ok=false; "
                             "preregistration A2 forbids any promotion arithmetic that rests on "
                             "an unvalidated instrument (see registry/irregularities.json "
                             "IR-H52-06)")
        if promo.get("hard_stop_triggered"):
            raise SystemExit("REFUSING to build: the preregistered hard-stop branch "
                             "(net proxy DTI more than 0.0050 below the incumbent) fired")
        if not promo.get("write_tiff"):
            raise SystemExit("REFUSING to build: the emission comparison licensed no file")
    if args.stage1_q is None:
        args.stage1_q = 10.0
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)

    cache = P / f"h52_full_field_blend_seed{args.seed}_neg{args.negatives}.npy"
    names_hh = names_hd = []
    if cache.is_file() and not args.force_fields:
        blend = np.load(cache)
        print(f"[1/6] belief field loaded from cache {cache.name} "
              f"({int(np.isfinite(blend).sum()):,} finite pixels)")
    else:
        print("[1/6] belief field (H-H / H-D 50/50 blend, trained on the full catalogue)")
        f_hh, names_hh = train_field(stack, footprint, catalogue, "HH", args.negatives, args.seed)
        f_hd, names_hd = train_field(stack, footprint, catalogue, "HD", args.negatives,
                                     args.seed + 1)
        blend = (0.5 * (f_hh + f_hd)).astype(np.float32)
        del f_hh, f_hd
        np.save(cache, blend)
        print(f"    cached the blend to {cache.name} (reruns reuse it; --force-fields retrains)")

    print("[2/6] Stage 1 strain-budget deficit (full catalogue) -> approved domain")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = st1.load_observed()
    cfg = sb.BudgetConfig(tile_px=args.tile_px)
    s1 = st1.stage1_field(catalogue, footprint, df, obs, cfg)
    approved = st1.approved_mask(s1["deficit"], footprint, args.tile_px, args.stage1_q)
    area_share = float(approved.sum() / max(int(footprint.sum()), 1))
    print(f"    approved area share of footprint: {area_share:.4f}")

    print(f"[3/6] emission {args.variant}: {args.n_dots:,} dots, flank {args.flank} px, "
          f"tip_kappa={args.tip_kappa}")
    forbid = em2.catalogue_flank_zone(catalogue, args.flank)
    allow = footprint & approved if args.variant in ("V4", "V5", "V7") else footprint
    score = blend
    prior_info = {}
    if args.tip_kappa > 0:
        prior_res = tm.tip_prior(catalogue, corridor_px=args.tip_corridor,
                                 half_width_px=args.tip_half_width, tau_px=args.tip_tau,
                                 bridge_gap_px=args.tip_bridge_gap, exclude=forbid)
        score = tm.boosted_score(blend, prior_res["prior"], args.tip_kappa)
        prior_info = dict(n_tips=int(prior_res["tips"]["n_tips"]),
                          n_bridges=int(prior_res["n_bridges"]),
                          corridor_px=int(args.tip_corridor),
                          half_width_px=float(args.tip_half_width),
                          tau_px=float(args.tip_tau),
                          bridge_gap_px=float(args.tip_bridge_gap),
                          kappa=float(args.tip_kappa),
                          prior_coverage=float(((prior_res["prior"] > 0.1)
                                                & footprint).mean()))
        print(f"    structural prior: tips={prior_info['n_tips']:,} "
              f"bridges={prior_info['n_bridges']:,} "
              f"coverage={prior_info['prior_coverage']:.5f} of footprint")
    if args.variant in ("V4", "V2"):
        # ``score`` equals the plain blend when the structural prior is off (kappa = 0),
        # which is the configuration the preregistrations licence.
        ys, xs = em2.nms_topn(score, args.n_dots, radius=args.nms_radius,
                              forbid=forbid, allow=allow, valid=footprint)
    elif args.variant in ("V6", "V7"):
        ys, xs = em2.ste_topn(score, args.n_dots, forbid=forbid, allow=allow)
    else:
        cos_c, sin_c, sup_c = em2.axis_from_catalogue(catalogue, 2.0, 3.0)
        cos_f, sin_f, sup_f = em2.axis_from_field(blend, 1.0, 5.0)
        support = sup_c | sup_f
        cos_a = np.where(sup_c, cos_c, cos_f).astype(np.float32)
        sin_a = np.where(sup_c, sin_c, sin_f).astype(np.float32)
        ys, xs = em2.sale_lines(blend, args.n_dots, cos_a, sin_a, forbid=forbid,
                                allow=allow, line_half=5, spacing=2.4, seed_sep=6.0,
                                axis_min_strength=support)
    values = em2.rasterise(ys, xs, GRID.shape)
    n_emitted = int((values > 0).sum())
    leak = on_catalogue_mass(values > 0, catalogue, valid=footprint)
    inside_s1 = int(((values > 0) & approved).sum())
    lift = (inside_s1 / max(n_emitted, 1)) / max(area_share, 1e-9)
    print(f"    emitted={n_emitted:,} on_catalogue={leak['on_catalogue_px']} "
          f"stage1_emitted_share={inside_s1/max(n_emitted,1):.4f} lift={lift:.3f}")
    if leak["on_catalogue_px"]:
        raise SystemExit("REFUSING to write: emission overlaps published catalogue pixels")

    print("[4/6] write GeoTIFF + ZIP (zeros outside footprint, no NaN, no nodata tag)")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha8 = hashlib.sha256(np.ascontiguousarray(values)).hexdigest()[:10]
    tag = f"-{args.tag}" if args.tag else ""
    tip = f"-tip{args.tip_kappa:g}" if args.tip_kappa > 0 else ""
    # Idempotent rebuild: the file name carries the raster hash, so a rerun of the same
    # deterministic emission must adopt the artifact that already exists instead of
    # writing a second copy. Without this, the uniqueness gate legitimately fails a
    # fresh copy against its own predecessor, and a run that dies *after* the byte
    # write (as the 2026-10-07 21:32Z build did) leaves an orphan that poisons every
    # later gate. Duplicates of the identical raster are pruned here, before the gate.
    suffix = f"-{sha8}{tag}"
    prior_same = sorted(q for q in DOWNLOADS_DIR.glob("gemsdoe51-h52-*.tif")
                        if q.stem.endswith(suffix))
    if prior_same:
        tif = prior_same[0]
        name = tif.stem
        stamp = name.rsplit("-", 2)[-2]
        for orphan in prior_same[1:]:
            for q in (orphan, orphan.with_suffix(".zip"),
                      orphan.with_name(orphan.stem + "-checks.json")):
                if q.exists():
                    q.unlink()
                    print(f"    pruned duplicate of the identical raster: {q.name}")
        print(f"    adopting existing artifact for this raster: {tif.name}")
    else:
        name = f"gemsdoe51-h52-{args.variant.lower()}-strainconf{tip}-{stamp}-{sha8}{tag}"
        tif = DOWNLOADS_DIR / f"{name}.tif"
    rec = write_tif(tif, values, footprint, outside=0.0, nodata=None)
    if not rec["checks"]["format_valid"]:
        raise SystemExit(f"REFUSING to ship: local format check failed: {rec['checks']}")
    zip_path = DOWNLOADS_DIR / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)

    print("[5/6] Stage-2 dominance diagnostics + uniqueness gate")
    # Deviation statement (preregistration A4): the shipped file carries its own
    # promotion arithmetic, in plain words, into the site card.
    dev = ("Preregistration note: the parent rule GEMSDOE51-H52-PREREG-1 asked the confined "
           "candidate to beat the incumbent NMS emission by +0.0020 on the six-fold proxy. "
           "Amendment A4 replaced that single net bar with (i) a +0.0020 bar on the emitter "
           "change itself, (ii) a <= 0.0050 limit on the measured cost of the brief-mandated "
           "confinement and (iii) a hard stop if the shipped file ends up more than 0.0050 "
           "below the incumbent. ")
    if promo:
        cost = float("nan")
        for d in promo.get("domains", []):
            if d.get("q") == promo.get("chosen_domain"):
                cost = float(d.get("confinement_cost", float("nan")))
        dev += (f"Measured on the identical cached fields ({p2_path.name}): incumbent NMS "
                f"{float(promo.get('incumbent_nms_mean', float('nan'))):.6f}, STE unconfined "
                f"{float(promo.get('ste_unconfined_mean', float('nan'))):.6f}, geometry delta "
                f"{float(promo.get('geometry_delta', float('nan'))):+.6f} in "
                f"{promo.get('geometry_folds_positive')}/6 folds. Emitter shipped: "
                f"{promo.get('emitter')}. Stage-1 domain: q{promo.get('chosen_domain'):g} "
                f"(approved tiles at or above that percentile of the rank-space deficit); "
                f"confinement cost {cost:+.6f} versus the same emitter unconfined; net versus "
                f"the in-instrument incumbent "
                f"{float(promo.get('net_vs_incumbent', float('nan'))):+.6f}. ")
    dev += ("This is a labelled deviation, recorded in registry/irregularities.json, not a "
            "silent exception.")

    # Uniform-in-domain null (A3): how much of the proxy DTI could the approved tiles buy
    # without any field at all?
    uniform_control = None
    if promo:
        lab = promo.get("chosen_label")
        u_lab = f"U_q{promo['chosen_domain']:g}" if promo.get("chosen_domain") is not None else None
        if lab in p2_summary and u_lab in p2_summary:
            uniform_control = dict(
                candidate_arm=lab,
                candidate_mean=float(p2_summary[lab]["dti_B_mean"]),
                uniform_mean=float(p2_summary[u_lab]["dti_B_mean"]),
                uniform_block_mean=float(p2_summary["U_block"]["dti_B_mean"]),
                ledger=p2_path.name,
            )
            print(f"    Stage-2 dominance control: {lab} {uniform_control['candidate_mean']:.6f} "
                  f"vs uniform fill {uniform_control['uniform_mean']:.6f} "
                  f"(whole block {uniform_control['uniform_block_mean']:.6f})")

    # Stage 2 is doing the work if the dots concentrate on the top-ranked pixels
    # *inside* the allowed domain: a uniform fill would put 10 % in the top decile.
    field_in_allow = blend[allow]
    rank_in_allow = np.empty_like(field_in_allow)
    rank_in_allow[np.argsort(field_in_allow, kind="stable")] = np.linspace(
        0.0, 1.0, field_in_allow.size, dtype=np.float32)
    top_decile = np.zeros_like(allow)
    tmp = np.zeros(int(allow.sum()), bool)
    tmp[rank_in_allow >= 0.90] = True
    top_decile[allow] = tmp
    dots_on = values > 0
    stage2_top_decile_share = float((dots_on & top_decile).sum() / max(int(dots_on.sum()), 1))
    approved_px = int((allow & approved).sum())
    print(f"    allowed pixels={int(allow.sum()):,} approved-in-footprint={approved_px:,} "
          f"dots in top field decile={stage2_top_decile_share*100:.1f}% (uniform = 10.0%)")

    priors = {}
    for p in sorted((ROOT / "data" / "prior").glob("*.tif")):
        priors[f"local:{p.name}"] = p
    for p in sorted((DOWNLOADS_DIR).glob("*.tif")):
        if p.name != tif.name:
            priors[f"downloads:{p.name}"] = p
    for p in sorted((ROOT / ".cache" / "siblings").glob("*.tif")):
        priors[f"sibling:{p.name}"] = p
    gate = run_gate(tif, priors, values > 0, footprint, stage1_approved=approved,
                    hard_confined=args.variant in ("V7", "V4"),
                    uniform_control=uniform_control)

    checks = dict(
        name=name, variant=args.variant, n_dots=int(args.n_dots), n_emitted=n_emitted,
        flank_px=args.flank, nms_radius=args.nms_radius, stage1_q=args.stage1_q,
        tile_px=int(args.tile_px), deviation_statement=dev,
        structural_prior=prior_info,
        stage1_area_share=area_share, stage1_emitted_share=inside_s1 / max(n_emitted, 1),
        stage1_lift=lift, on_catalogue_px=leak["on_catalogue_px"],
        stage2_top_decile_share=stage2_top_decile_share,
        stage2_dots_per_approved_px=n_emitted / max(approved_px, 1),
        uniform_control=uniform_control or {},
        holdout=holdout_rec.get("summary") if holdout_rec else None,
        field_extras_hh=names_hh, field_extras_hd=names_hd,
        grid=dict(shape=list(GRID.shape), transform=list(GRID.transform), epsg=GRID.epsg),
        format=rec, uniqueness=gate.as_dict(),
    )
    (DOWNLOADS_DIR / f"{name}-checks.json").write_text(json.dumps(checks, indent=1))

    print("[6/6] build provenance")
    build = dict(created_utc=stamp, name=name, variant=args.variant, config=vars(args),
                 tif=dict(file=tif.name, bytes=tif.stat().st_size, sha256=sha256_file(tif)),
                 zip=dict(file=zip_path.name, bytes=zip_path.stat().st_size,
                          sha256=sha256_file(zip_path)),
                 emitted_px=n_emitted, on_catalogue_px=leak["on_catalogue_px"],
                 stage1_area_share=area_share, stage1_lift=lift,
                 uniqueness_verdict=gate.verdict,
                 notes=("Two-stage H52 submission: coarse rank-space strain-budget prior "
                        "(Stage 1, tiles only) + H-H/H-D blended belief field emission "
                        "(Stage 2, every point inside the approved tiles). Local format "
                        "and uniqueness checks only — no organizer score is claimed."))
    (ROOT / "registry" / "submission_build_h52.json").write_text(json.dumps(build, indent=1))
    print(json.dumps({k: v for k, v in checks.items()
                      if k not in ("field_extras_hh", "field_extras_hd")}, indent=1)[:4000])
    print(f"\nTIFF   {tif}  ({tif.stat().st_size:,} bytes)")
    print(f"ZIP    {zip_path}  ({zip_path.stat().st_size:,} bytes)")
    print(f"checks {DOWNLOADS_DIR / (name + '-checks.json')}")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
