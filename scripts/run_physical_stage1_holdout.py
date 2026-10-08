#!/usr/bin/env python3
"""Audit physical dilatation/shear residual Stage 1 on a whole-trace holdout.

This is distinct from ``run_stage1_trace_holdout.py``: this runner uses actual
Kreemer-style clipped source vectors and subtracts source-definition-matched
physical dilation/shear scalars under explicit rate-component and unit scenarios.
It emits no fault points. The q10 output is a broad tile prior only.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.emission import rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.physical_stage1 import observed_tile_mean, physical_residual_prior  # noqa: E402
from gems51.vector_budget import prepare_segments_in_support  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
ROWS_PATH = ROOT / "registry" / "official" / "trace_segments_utm11.csv"


def load_observations():
    path = RAW / "training_features.tif"
    with rasterio.open(path) as src:
        GRID.assert_matches(dict(transform=src.transform, height=src.height,
                                 width=src.width, crs=src.crs))
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        out = {}
        for name in ("geod_dilaterate", "geod_shearrate"):
            if descriptions.count(name) != 1:
                raise ValueError(f"expected exactly one {name!r} band")
            values = src.read(descriptions.index(name) + 1).astype(np.float64)
            values[~np.isfinite(values) | (values <= -1e38)] = np.nan
            out[name] = values
    return out


def _random_dti(mask, truth, support, known, n_dots, seed):
    ys, xs = np.nonzero(mask & ~known)
    if not ys.size:
        return dict(dti=0.0, dots=0)
    rng = np.random.default_rng(seed)
    k = min(int(n_dots), int(ys.size))
    chosen = rng.choice(ys.size, size=k, replace=False)
    pred = rasterise(ys[chosen], xs[chosen]) > 0
    result = dti_binary(pred, truth, valid=support, known=known)
    return dict(dti=float(result["dti"]), dots=int(k),
                tp=float(result["tp"]), fp=float(result["fp"]))


def _stage1_fold(prepared, observed, support, catalogue, held_records,
                 split_index, repeats, ratio, tile_px, quantile):
    held_set = set(int(x) for x in held_records)
    truth = prepared.rasterize_records(held_set) & support
    known = (catalogue & support) & ~truth
    prior = physical_residual_prior(
        prepared,
        observed["geod_dilaterate"],
        observed["geod_shearrate"],
        support,
        excluded_records=held_set,
        approved_quantile=quantile,
    )
    n_truth = int(truth.sum())
    n_dots = int(round(ratio * n_truth))
    area_share = float(prior["approved_mask"].sum() / max(int(support.sum()), 1))
    recall = float((truth & prior["approved_mask"]).sum() / max(n_truth, 1))
    truth_density = observed_tile_mean(truth.astype(np.float64), support, tile_px)
    valid_tiles = prior["tile_valid"] & np.isfinite(truth_density)
    rho = None
    if int(valid_tiles.sum()) > 5:
        statistic = float(spearmanr(prior["score"][valid_tiles],
                                    truth_density[valid_tiles]).statistic)
        if np.isfinite(statistic):
            rho = statistic

    controls = {"uniform_in_approved": [], "uniform_in_support": []}
    approved_allowed = prior["approved_mask"] & support
    for rep in range(repeats):
        seed = 510_000 + split_index * 100 + rep
        controls["uniform_in_approved"].append(
            _random_dti(approved_allowed, truth, support, known, n_dots, seed)
        )
        controls["uniform_in_support"].append(
            _random_dti(support, truth, support, known, n_dots, seed + 50_000)
        )
    return dict(
        split=int(split_index),
        held_trace_records=int(len(held_set)),
        held_trace_record_ids=sorted(held_set),
        truth_pixels=n_truth,
        matched_dot_mass=int(n_dots),
        approved_area_fraction=area_share,
        held_trace_recall=recall,
        held_trace_lift=recall / max(area_share, 1e-12),
        spearman_residual_score_vs_held_trace_density=rho,
        uniform_controls=controls,
        uniform_in_approved_mean_dti=float(np.mean([x["dti"] for x in controls["uniform_in_approved"]])),
        uniform_in_support_mean_dti=float(np.mean([x["dti"] for x in controls["uniform_in_support"]])),
        physical_scenarios=prior["scenario_results"],
        threshold=prior["threshold"],
    )


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tile-px", type=int, default=200)
    ap.add_argument("--quantile", type=float, default=10.0)
    ap.add_argument("--splits", type=int, default=5)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--uniform-repeats", type=int, default=5)
    ap.add_argument("--mass-ratio", type=float, default=3.47)
    ap.add_argument("--out", default="evidence/physical_stage1_holdout_20261008.json")
    args = ap.parse_args()
    if args.tile_px != 200:
        raise SystemExit("the frozen physical Stage-1 tile is 200 pixels (20 km)")
    if args.splits != 5 or args.seed != 51:
        raise SystemExit("the frozen trace holdout uses five splits with seed 51")
    if args.uniform_repeats != 5:
        raise SystemExit("the frozen uniform-control count is five repeats")

    t0 = time.time()
    footprint = np.load(PREPARED / "footprint.npy").astype(bool)
    catalogue = np.load(PREPARED / "catalogue.npy").astype(bool)
    observed = load_observations()
    support = footprint & np.isfinite(observed["geod_dilaterate"]) \
        & np.isfinite(observed["geod_shearrate"])
    rows = pd.read_csv(ROWS_PATH)
    prepared = prepare_segments_in_support(rows, support, tile_px=args.tile_px)
    trace_ids = prepared.supported_record_ids.astype(np.int32)
    if trace_ids.size < args.splits:
        raise SystemExit(f"only {trace_ids.size} source records intersect common support")
    permuted = np.random.default_rng(args.seed).permutation(trace_ids)
    chunks = np.array_split(permuted, args.splits)

    split_rows = []
    for i, chunk in enumerate(chunks):
        result = _stage1_fold(prepared, observed, support, catalogue, chunk,
                              i, args.uniform_repeats, args.mass_ratio,
                              args.tile_px, args.quantile)
        split_rows.append(result)
        print(
            f"Stage1 trace split {i}: records={result['held_trace_records']} "
            f"truth_px={result['truth_pixels']:,} area={result['approved_area_fraction']:.3f} "
            f"recall={result['held_trace_recall']:.3f} lift={result['held_trace_lift']:.3f} "
            f"uniform DTI approved/support="
            f"{result['uniform_in_approved_mean_dti']:.4f}/"
            f"{result['uniform_in_support_mean_dti']:.4f} ({time.time()-t0:.0f}s)",
            flush=True,
        )

    full = physical_residual_prior(
        prepared,
        observed["geod_dilaterate"],
        observed["geod_shearrate"],
        support,
        excluded_records=(),
        approved_quantile=args.quantile,
    )
    cache_path = PREPARED / f"physical_stage1_full_q{int(args.quantile)}_t{args.tile_px}.npz"
    np.savez_compressed(cache_path, score=full["score"],
                        approved_tiles=full["approved_tiles"],
                        approved_mask=full["approved_mask"],
                        support=support)

    def mean(key):
        return float(np.mean([r[key] for r in split_rows]))

    rho_values = [r["spearman_residual_score_vs_held_trace_density"]
                  for r in split_rows
                  if r["spearman_residual_score_vs_held_trace_density"] is not None]
    summary = dict(
        mean_approved_area_fraction=mean("approved_area_fraction"),
        mean_held_trace_recall=mean("held_trace_recall"),
        mean_held_trace_lift=mean("held_trace_lift"),
        mean_spearman_residual_score_vs_held_trace_density=(
            float(np.mean(rho_values)) if rho_values else None
        ),
        mean_uniform_in_approved_dti=float(np.mean([r["uniform_in_approved_mean_dti"] for r in split_rows])),
        mean_uniform_in_support_dti=float(np.mean([r["uniform_in_support_mean_dti"] for r in split_rows])),
        paired_mean_uniform_dti_delta=float(np.mean([
            r["uniform_in_approved_mean_dti"] - r["uniform_in_support_mean_dti"]
            for r in split_rows
        ])),
    )
    receipt = dict(
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status="MEASURED_LOCAL_PHYSICAL_STAGE1_TRACE_HOLDOUT",
        instrument="five deterministic whole-QFault-record splits over source trace geometry in the common valid geodetic footprint; uniform points scored against held trace pixels with remaining known-catalogue pixels masked",
        config=vars(args),
        formula="eps_dot_ij=1/2 sum L*u/(A*sin(dip))*(n_i*m_j+n_j*m_i); Kreemer et al. (2000), Eq. 3",
        formula_source="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf",
        geodetic_scalar_source="GDR INGENIOUS regional geodetic README: dilation=e1+e2; shear=min(abs(e1),abs(e2)) only for opposite-sign principal rates; units recorded as 10E-9/yr, preserved as 1e-9 and 1e-8 scenarios",
        source="https://gdr.openei.org/submissions/1391",
        geometry_audit=prepared.meta,
        common_valid_support_pixels=int(support.sum()),
        footprint_pixels=int(footprint.sum()),
        geodetic_source_band_descriptions={"dilatation": "geod_dilaterate", "shear": "geod_shearrate"},
        full_map_prior=dict(
            approved_area_fraction=full["approved_area_fraction"],
            approved_tile_fraction=full["approved_tile_fraction"],
            threshold=full["threshold"],
            excluded_trace_records=0,
            scenario_results=full["scenario_results"],
            cached_arrays=str(cache_path.relative_to(ROOT)),
        ),
        per_split=split_rows,
        summary=summary,
        explicit_decision="Stage 1 is a broad q10 tile prior only. It places no points. Whether its use is justified depends on this separate proxy holdout; Stage 2 must independently outperform a same-mask uniform control.",
        limitations=[
            "Visible QFault geometry and the visible competition catalogue are proxy truth, not the hidden expert fault map.",
            "This is scattered whole-trace cross-validation, not an independent geographic holdout.",
            "Per-trace dips/rakes and source rate-component convention remain assumptions; both normal-rate conventions are evaluated.",
            "The source geodetic README uses the ambiguous literal unit notation 10E-9/yr; both 1e-9 and 1e-8 scales are retained.",
            "Positive scalar residual can reflect off-fault strain, aseismic deformation, geodetic smoothing, omitted/unknown-sense faults, catalogue completeness, or model error; it does not locate a new fault by itself.",
            "Only the 1,126 QFault source records represented in the clipped regional source geometry are available in this input table; 1,394 of 84,331 segment rows have unknown sense and are omitted from tensors but retained in holdout trace geometry.",
            "A q10 threshold approves roughly 90% of tiles; it is intentionally broad and must not dominate the Stage-2 map.",
        ],
    )
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "summary": summary,
                      "full_map_area": full["approved_area_fraction"],
                      "receipt": str(out.relative_to(ROOT)),
                      "cache": str(cache_path.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
