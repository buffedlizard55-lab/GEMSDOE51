#!/usr/bin/env python3
"""Build a format-valid H-G+H-D research TIFF without replacing the current primary.

The matched six-block holdout for H-G+H-D was slightly below H-D. This script exists
only to materialize the tested feature recipe for audit/education and a uniqueness
comparison; it does not authorize a competition upload or overwrite the primary
manifest. The hidden truth size is unknown: 12,700 is only the project's historical
planning proxy used with M/|G|=3.47 to set a comparable dot budget (44,069).
"""
from __future__ import annotations

import argparse
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

from gems51 import strain_budget as sb  # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.extras import build_magnetic_gravity_intersections  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.submission import write_tif  # noqa: E402

from build_submission import load_observed, stage1_approved, upsample  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
DOWNLOADS = ROOT / "docs" / "downloads"
ARTIFACT_DIR = ROOT / "evidence"
MASS_RATIO = 3.47
TRUTH_MASS_PROXY = 12_700  # planning constant only; not a measured hidden-label size
N_DOTS = round(MASS_RATIO * TRUTH_MASS_PROXY)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--basename",
        help="optional deterministic output basename (without .tif/.zip suffixes); defaults to UTC timestamp",
    )
    args = parser.parse_args()
    if args.basename and Path(args.basename).name != args.basename:
        parser.error("--basename must be a filename component, not a path")

    footprint = np.load(PREPARED / "footprint.npy")
    catalogue = np.load(PREPARED / "catalogue.npy")
    stack = Stack(PREPARED)

    # Stage 1 only contributes the soft tile-rank multiplier; it does not hard-mask
    # fine-scale emissions. The formula/rate assumptions are audited separately.
    slip_rates = sb.load_slip_rates(ROOT / "data" / "raw")
    observed = load_observed()
    approved, deficit, threshold, _, _, _ = stage1_approved(
        catalogue, footprint, slip_rates, observed, tile_px=100, q=70.0)
    deficit_big = upsample(deficit, 100)
    prior_values = deficit_big[footprint & np.isfinite(deficit_big)]
    z = np.clip((deficit_big - prior_values.mean()) / max(prior_values.std(), 1e-9), -4.0, 4.0)

    # H-D's four LiDAR coherence channels, plus the two locked H-G TMI/gravity
    # crossing channels. No catalogue-derived predictors are added.
    names = json.loads((PREPARED / "extras_static_names.json").read_text())
    static = np.memmap(PREPARED / "extras_static.dat", dtype=np.float32, mode="r",
                       shape=(len(names), *GRID.shape))
    hd_cols, hd_names = [], []
    for i, name in enumerate(names):
        if "facecoh" in name:
            hd_cols.append(np.asarray(static[i], dtype=np.float32))
            hd_names.append(name)
    if len(hd_cols) != 4:
        raise RuntimeError(f"expected four H-D coherence channels; found {hd_names}")
    hg = build_magnetic_gravity_intersections(stack, footprint)
    feature_names = hd_names + list(hg)
    extra_cols = hd_cols + list(hg.values())

    # Match the production bagging scheme; no holdout labels enter this fit.
    field = np.zeros(GRID.shape, dtype=np.float32)
    neg_pool = footprint & ~catalogue
    n_models, n_neg, max_iter, seed = 3, 400_000, 400, 17
    for m in range(n_models):
        rng = np.random.default_rng(seed + 101 * m)
        X, y = stack.sample(catalogue & footprint, neg_pool, n_neg, rng,
                            extra=extra_cols)
        model = fit_detector(X, y, seed=seed + m, max_iter=max_iter)
        del X, y
        field += predict_grid(model, stack, footprint, extra=extra_cols)
        print(f"[fit] bag {m + 1}/{n_models} complete", flush=True)
    field /= float(n_models)

    score = field * (1.0 + 0.10 * z)
    excluded = ndi.distance_transform_edt(~catalogue) <= 2.0
    ys, xs = nms_dots(score, N_DOTS, radius=2.4,
                      exclude=excluded, valid=footprint)
    pred = rasterise(ys, xs)
    if int((pred > 0).sum()) != N_DOTS:
        raise RuntimeError(f"requested {N_DOTS} points; emitted {(pred > 0).sum()}")

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    basename = args.basename or f"gemsdoe51-hg-hd-xing-experimental-r347-{stamp}"
    tif = DOWNLOADS / f"{basename}-zeros.tif"
    record = write_tif(tif, np.where(footprint, pred, 0.0), outside=0.0, nodata=None)
    zip_path = DOWNLOADS / f"{basename}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(tif, tif.name)

    support = pred > 0
    area_share = float(approved.sum() / footprint.sum())
    emitted_share = float((support & approved).sum() / max(int(support.sum()), 1))
    hd_holdout = json.loads((ROOT / "data" / "holdout_H_D.json").read_text())["summary"]
    matched_holdout = json.loads((ROOT / "evidence" / "holdout_H_G_plus_H_D.json").read_text())["summary"]
    hd_mean = hd_holdout["dti_r3.47"]["mean"]
    matched_mean = matched_holdout["dti_r3.47"]["mean"]
    fold_deltas = [m - h for h, m in zip(
        hd_holdout["dti_r3.47"]["per_fold"],
        matched_holdout["dti_r3.47"]["per_fold"],
    )]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "EXPERIMENTAL_NOT_SLOT_ELIGIBLE",
        "decision": "Do not upload: the matched spatial-block holdout did not beat H-D.",
        "holdout_evidence": "evidence/holdout_H_G_plus_H_D.json",
        "holdout_comparator": "data/holdout_H_D.json",
        "holdout_result": {
            "H_G_plus_H_D_proxy_dti_mean": matched_mean,
            "H_D_proxy_dti_mean": hd_mean,
            "paired_delta": matched_mean - hd_mean,
            "fold_deltas": fold_deltas,
            "folds_higher": sum(delta > 0 for delta in fold_deltas),
            "folds_total": len(fold_deltas),
            "H_G_plus_H_D_auc_mean": matched_holdout["auc_mean"],
            "H_D_auc_mean": hd_holdout["auc_mean"],
            "comparability_caveat": "The blocked holdout compares the Stage-2 feature arm at matched mass; this full-raster build also applies the separately inconclusive Stage-1 soft prior. The output is therefore an experimental realization of a non-promoted recipe, not a winner or slot-ready candidate.",
        },
        "recipe": {
            "arm": "H-G added to H-D",
            "features": feature_names,
            "stage1": "current-code q70 diagnostic; soft w=0.10 rank multiplier; no hard tile mask",
            "mass_ratio": MASS_RATIO,
            "truth_mass_proxy": TRUTH_MASS_PROXY,
            "truth_mass_proxy_caveat": "Planning constant only; true hidden truth size is unknown and this is not an estimate inferred from a verified score.",
            "requested_dots": N_DOTS,
            "models": n_models,
            "negative_samples_per_model": n_neg,
            "max_iter": max_iter,
            "seed": seed,
            "nms_radius_px": 2.4,
            "catalogue_exclusion_radius_px": 2.0,
        },
        "artifact": {
            "file": tif.name,
            "zip": zip_path.name,
            "sha256": record["sha256"],
            "bytes": record["bytes"],
            "submission_name": "GEMSDOE51-HG-HD-XING-EXPERIMENT",
            "note": "H-G TMI-gravity crossings + H-D; experimental only, matched holdout below H-D; NOT SLOT-ELIGIBLE.",
            "format": record,
        },
        "stage1_dominance_q70": {
            "threshold": float(threshold),
            "approved_pixels": int(approved.sum()),
            "footprint_pixels": int(footprint.sum()),
            "approved_area_share": area_share,
            "emitted_pixels": int(support.sum()),
            "emitted_share_inside_approved": emitted_share,
            "lift": emitted_share / max(area_share, 1e-12),
            "interpretation": "Diagnostic only; the soft prior does not restrict emissions to approved tiles.",
        },
        "caveat": "All local holdout results use the visible catalogue as proxy truth, not authenticated competition labels.",
    }
    out = ARTIFACT_DIR / "experimental_H_G_plus_H_D_artifact.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"file": str(tif.relative_to(ROOT)), "sha256": record["sha256"],
                      "positive_px": record["checks"]["positive_px"],
                      "portal_legal": record["checks"]["portal_legal"],
                      "stage1_q70": report["stage1_dominance_q70"],
                      "manifest": str(out.relative_to(ROOT))}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
