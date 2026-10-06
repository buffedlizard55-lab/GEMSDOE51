#!/usr/bin/env python3
"""End-to-end submission pipeline: stage-1 strain-budget prior, stage-2 validated emission.

Run:
    GEMS_DATA_DIR=data PYTHONPATH=src python3 scripts/run_pipeline.py \
        --budget 44090 --shell 1 --out submissions/<name>.tif

Produces, in one pass:
    * the stage-1 geodetic strain-budget deficit tile map and the approved-tile prior,
    * the stage-2 unsteered Hessian-ridge rank field over all 19 supplied bands,
    * the emitted GeoTIFF, written in the competition's exact format,
    * `evidence/submission_<tag>.json` with every measured number,
    * a format audit produced by RE-READING the written bytes from disk.

SELECTION, STATED: the stage-2 detector is the unsteered Hessian-ridge rank fusion over
all 19 supplied bands, because that is what the spatially-blocked screen ranked highest
(mean AUC 0.8229, 4/4 folds above chance -- `evidence/detector_screen.json`) and what the
4-quadrant blocked holdout promoted over the random control.  The strike-steered variant
is retained in the code as a documented ablation that FAILED.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from gems51 import emission, grid, stage1_strain as s1, stage2_emission as s2

ROOT = Path(__file__).resolve().parents[1]
ALL_BANDS = tuple(range(1, 20))
SUPPRESS_PX = 3


def run(*, budget: int, shell_radius: int, shell_decay: float, tile: int,
        approve_quantile: float, out_path: Path, tag: str,
        slip_rate: float = s1.SLIP_RATE_DEFAULT_MM_YR,
        dip: float = s1.DIP_DEG_DEFAULT, down: int = 2, sigma: float = 2.0,
        seed: int = 51051, compress: str | None = "deflate",
        evidence_dir: Path | None = None) -> dict:
    t0 = time.time()
    d = grid.data_root()
    tf = d / "training_features.tif"
    cat = grid.read_catalogue(d / "existing_faults.tif")
    valid = grid.valid_footprint(d / "sample_submission.tif")
    ev = {"tag": tag, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "parameters": dict(budget=budget, shell_radius=shell_radius,
                             shell_decay=shell_decay, tile=tile,
                             approve_quantile=approve_quantile, down=down,
                             sigma_px=sigma, slip_rate_mm_yr=slip_rate, dip_deg=dip,
                             emission_seed=seed, compress=compress,
                             bands=list(ALL_BANDS))}

    # ---------- STAGE 1: geodetic strain-budget deficit (coarse prior) ----------
    shear = grid.read_band(tf, 7)
    dil = grid.read_band(tf, 8)
    si = grid.read_band(tf, 4)
    dep = s1.compute_stage1(cat, shear, dil, si, tile=tile,
                            slip_rate_mm_yr=slip_rate, dip_deg=dip,
                            approve_quantile=approve_quantile)
    del shear, dil, si
    prior = s1.upsampled_prior(dep.approved, dep.tile, cat.shape)
    ev["stage1"] = {
        "meta": dep.meta,
        "n_tiles": int(dep.approved.size),
        "n_approved_tiles": int(dep.approved.sum()),
        "approved_tile_area_px": int(dep.approved.sum()) * dep.tile * dep.tile,
        "approved_tile_area_fraction_of_footprint": float(
            dep.approved.sum() * dep.tile * dep.tile / max(1, valid.sum())),
        "deficit_min": float(np.nanmin(dep.deficits)),
        "deficit_max": float(np.nanmax(dep.deficits)),
        "deficit_median": float(np.nanmedian(dep.deficits)),
        "off_fault_reference": s1.off_fault_reference(),
    }

    # ---------- STAGE 2: validated fine-scale detector ----------
    prov = lambda b: grid.read_band(tf, b)
    field = s2.steered_field_from_provider(
        prov, cat, valid, down=down, sigma_px=sigma, bands=ALL_BANDS, steer=False)
    ev["stage2"] = {
        "detector": "unsteered Hessian-ridge rank fusion over all 19 supplied bands",
        "emission_rule": "field-weighted sampling without replacement (coverage-breadth rule)",
        "selection_evidence": "evidence/detector_screen.json (mean AUC 0.8229, 4/4 folds) and "
                              "evidence/holdout_spread.json (arm bake-off)",
        "field_min": float(field.min()), "field_max": float(field.max()),
        "field_mean_on_footprint": float(field[valid].mean()),
    }

    # ---------- composition ----------
    core, shell = s2.catalogue_core_and_shell(cat, shell_radius_px=shell_radius,
                                              decay=shell_decay)
    eligible = prior & valid & (~core)
    # SHIPPED EMISSION RULE: field-weighted sampling (see emission.weighted_sample for the
    # measurement that selects it over peak-packing and over uniform random).
    picked = emission.weighted_sample(field, eligible, budget, seed=seed)
    values = emission.to_values(picked, core, shell, field=field,
                               shell_gain=1.0, core_value=1.0)
    n_novel = int(picked.sum())

    ev["composition"] = {
        "core_px": int(core.sum()),
        "shell_px": int((shell > 0).sum()),
        "shell_radius_px": shell_radius,
        "shell_max_weight": float(shell.max()) if shell.size else 0.0,
        "eligible_px": int(eligible.sum()),
        "novel_px_requested": int(budget),
        "novel_px_selected": n_novel,
        "mass_total": float(values.sum()),
        "mass_on_core": float(values[core].sum()),
        "mass_on_shell": float(values[(shell > 0) & (~core)].sum()),
        "mass_on_novel": float(values[picked].sum()),
        "novel_mass_fraction": float(values[picked].sum() / max(1e-9, values.sum())),
        "novel_px_fraction_of_footprint": float(n_novel / max(1, valid.sum())),
        "fraction_of_field_within_approved_tiles": float(
            prior[valid].mean()),
    }

    # ---------- "not dominated by stage one's footprint" gate ----------
    # Stage 1 contributes an ALLOW-REGION, never a value.  The check is that the emitted
    # mass is nowhere near a solid fill of the approved tiles, and that stage 1 has no
    # direct mass at all.
    approved_area = int(prior.sum())
    gate = {
        "stage1_direct_mass": 0.0,
        "approved_tile_px": approved_area,
        "emitted_mass": float(values.sum()),
        "emitted_mass_over_approved_area": float(values.sum() / max(1, approved_area)),
        "solid_fill_of_approved_tiles_would_be_mass": float(approved_area),
        "not_a_solid_fill": bool(values.sum() < 0.5 * approved_area),
        "novel_mass_share_of_total": float(values[picked].sum() / max(1e-9, values.sum())),
        "verdict": ("PASS: stage 1 is a 0-mass allow-region; the emission is a sparse "
                    "point set, not the tile footprint")
        if values.sum() < 0.5 * approved_area else
        "FAIL: emission is close to a solid fill of the stage-1 prior",
    }
    ev["stage1_dominance_gate"] = gate

    # ---------- write + audit ----------
    # deflate keeps the file 46x smaller (1.03 MB vs 49 MB, measured) with IDENTICAL values
    # and metadata, which matters because the whole point of the site is a one-click download.
    audit = grid.write_submission(out_path, values, compress=compress)
    audit["sha256"] = grid.sha256_of(out_path)
    audit["bytes"] = out_path.stat().st_size
    ev["submission_format_audit"] = audit
    ev["elapsed_s"] = round(time.time() - t0, 1)

    ed = evidence_dir or (ROOT / "evidence")
    ed.mkdir(parents=True, exist_ok=True)
    (ed / f"submission_{tag}.json").write_text(json.dumps(ev, indent=2, default=float))

    print(f"[pipeline] {out_path}")
    print(f"  stage1 approved tiles  : {int(dep.approved.sum())} tiles "
          f"({gate['approved_tile_px']:,} px, "
          f"{100*gate['approved_tile_px']/max(1,valid.sum()):.1f}% of footprint)")
    print(f"  stage1 deficit range   : {ev['stage1']['deficit_min']:.3f} .. "
          f"{ev['stage1']['deficit_max']:.3f}")
    print(f"  core / shell px        : {int(core.sum()):,} / {int((shell>0).sum()):,}")
    print(f"  novel dots selected    : {n_novel:,} of {budget:,} requested")
    print(f"  total mass             : {values.sum():,.1f}")
    print(f"  stage1-dominance gate  : {gate['verdict']}")
    print(f"  format checks          : {sum(audit['checks'].values())}/{len(audit['checks'])} "
          f"PASS (all_pass={audit['all_pass']})")
    print(f"  min/max                : {audit['min']} / {audit['max']}  "
          f"n_nan={audit['n_nan']} nodata={audit['nodata']}")
    print(f"  sha256                 : {audit['sha256']}")
    return ev


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=44090)
    ap.add_argument("--shell", type=int, default=1, help="shell radius in px (0 = off)")
    ap.add_argument("--shell-decay", type=float, default=0.6)
    ap.add_argument("--tile", type=int, default=32)
    ap.add_argument("--approve-quantile", type=float, default=0.55)
    ap.add_argument("--down", type=int, default=2)
    ap.add_argument("--sigma", type=float, default=2.0)
    ap.add_argument("--slip-rate", type=float, default=s1.SLIP_RATE_DEFAULT_MM_YR)
    ap.add_argument("--dip", type=float, default=s1.DIP_DEG_DEFAULT)
    ap.add_argument("--seed", type=int, default=51051)
    ap.add_argument("--compress", type=str, default="deflate",
                    help="GTiff compression for the shipped file (deflate|none)")
    ap.add_argument("--tag", type=str, required=True)
    ap.add_argument("--out", type=str, required=True)
    a = ap.parse_args()
    run(budget=a.budget, shell_radius=a.shell, shell_decay=a.shell_decay, tile=a.tile,
        approve_quantile=a.approve_quantile, out_path=Path(a.out), tag=a.tag,
        slip_rate=a.slip_rate, dip=a.dip, down=a.down, sigma=a.sigma, seed=a.seed,
        compress=(None if a.compress in ("none", "") else a.compress))
