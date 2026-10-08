#!/usr/bin/env python3
"""Leakage-controlled spatial holdout for H53-A's coarse physical prior only.

No Stage-2 detector is fit here. The script uses actual official vector segments,
excludes every source record intersecting the held block plus its buffer, and
reports componentwise dimensional residuals under the preregistered rate/unit
sensitivities. Only the fixed q10 mask for the primary scenario is saved for the
separate Stage-2 runner.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.stage1_residual import (  # noqa: E402
    approved_domain,
    combined_deficit_rank,
    component_residual,
    positive_empirical_rank,
    records_intersecting_block,
)
from gems51.strain_budget import block_reduce_sum, observed_tiles  # noqa: E402
from gems51.vector_budget import budget, summaries  # noqa: E402

P = ROOT / "data" / "prepared"
SEGMENTS_PATH = ROOT / "registry" / "official" / "trace_segments_utm11.csv"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "evidence" / "h53_stage1_holdout_20261008.json"
MASKS = P / "h53_stage1_fold_masks_20261008.npz"
TILE_PX = 100
BUFFER_PX = 12
Q = 10.0
PRIMARY_CONVENTION = "fault_plane"
PRIMARY_UNIT_FACTOR = 1e-8
SENSITIVITY = (
    ("fault_plane", 1e-8),
    ("vertical", 1e-8),
    ("fault_plane", 1e-9),
    ("vertical", 1e-9),
)


def _load_observations(footprint: np.ndarray) -> dict[str, np.ndarray]:
    path = RAW / "training_features.tif"
    with rasterio.open(path) as src:
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        result = {}
        for name in ("geod_dilaterate", "geod_shearrate"):
            if name not in descriptions:
                raise SystemExit(f"missing required geodetic band: {name}")
            values = src.read(descriptions.index(name) + 1).astype(np.float32)
            values[values <= -1e38] = np.nan
            if values.shape != footprint.shape:
                raise SystemExit(f"{name} shape differs from the competition grid")
            result[name] = values
    return result


def _folds_with_bounds(footprint: np.ndarray, catalogue: np.ndarray):
    """Recreate make_folds ordering while retaining full rectangular block bounds."""
    rows = np.array_split(np.arange(GRID.shape[0]), 3)
    cols = np.array_split(np.arange(GRID.shape[1]), 3)
    result = []
    for row_part in rows:
        for col_part in cols:
            r0, r1 = int(row_part[0]), int(row_part[-1]) + 1
            c0, c1 = int(col_part[0]), int(col_part[-1]) + 1
            block = np.zeros(GRID.shape, dtype=bool)
            block[r0:r1, c0:c1] = True
            block &= footprint
            truth = catalogue & block
            if int(truth.sum()) < 500:
                continue
            result.append(dict(bounds_rc=(r0, r1, c0, c1), block=block,
                               truth=truth, n_truth=int(truth.sum())))
    expected = make_folds(footprint, catalogue, buffer_px=BUFFER_PX,
                          n_rows=3, n_cols=3, min_truth=500)
    if len(result) != len(expected):
        raise SystemExit(f"spatial fold mismatch: stage1={len(result)}, stage2={len(expected)}")
    for index, (actual, frozen) in enumerate(zip(result, expected)):
        if not np.array_equal(actual["block"], frozen.block):
            raise SystemExit(f"fold {index}: Stage-1 block does not match Stage-2 frozen split")
        if not np.array_equal(actual["truth"], frozen.truth):
            raise SystemExit(f"fold {index}: Stage-1 truth does not match Stage-2 frozen split")
    return result


def _load_geodetic_tiles(footprint: np.ndarray):
    obs = _load_observations(footprint)
    observed_dil = observed_tiles(obs["geod_dilaterate"], footprint, TILE_PX)
    observed_shear = observed_tiles(obs["geod_shearrate"], footprint, TILE_PX)
    support = observed_tiles(np.ones(GRID.shape, dtype=np.float32), footprint, TILE_PX)
    valid = (np.isfinite(observed_dil) & np.isfinite(observed_shear)
             & np.isfinite(support) & (support > 0.05))
    return observed_dil, observed_shear, support, valid


def _tile_to_pixel(tile: np.ndarray) -> np.ndarray:
    full = np.repeat(np.repeat(tile, TILE_PX, axis=0), TILE_PX, axis=1)
    return full[:GRID.shape[0], :GRID.shape[1]]


def _tile_association(score_tile: np.ndarray, truth: np.ndarray,
                      fold_domain: np.ndarray, valid_tiles: np.ndarray) -> float:
    truth_count = block_reduce_sum(truth.astype(np.float64), TILE_PX)
    area_count = block_reduce_sum(fold_domain.astype(np.float64), TILE_PX)
    has_area = valid_tiles & (area_count > 0)
    if int(has_area.sum()) < 3:
        return float("nan")
    density = truth_count[has_area] / area_count[has_area]
    scores = score_tile[has_area]
    if np.unique(scores).size < 2 or np.unique(density).size < 2:
        return float("nan")
    return float(spearmanr(scores, density).statistic)


def _metrics(score_tile: np.ndarray, valid_tiles: np.ndarray,
             footprint: np.ndarray, fold: dict) -> dict:
    tile_score = np.where(valid_tiles, score_tile, np.nan).astype(np.float32)
    pixel_score = _tile_to_pixel(tile_score)
    approved, threshold = approved_domain(pixel_score, footprint, Q)
    block = fold["block"]
    truth = fold["truth"]
    fold_area = int((block & footprint).sum())
    approved_area = int((approved & block & footprint).sum())
    truth_px = int(truth.sum())
    recall = float((approved & truth).sum() / max(truth_px, 1))
    area_share = float(approved_area / max(fold_area, 1))
    return dict(
        threshold=float(threshold),
        approved_area_share_in_held_block=area_share,
        approved_area_share_full_footprint=float((approved & footprint).sum() / max(int(footprint.sum()), 1)),
        heldout_truth_pixels=truth_px,
        heldout_truth_recall=recall,
        recall_over_area_lift=float(recall / max(area_share, 1e-12)),
        tile_rank_spearman=_tile_association(score_tile, truth, block & footprint, valid_tiles),
    ), approved


def _scenario_scores(observed_dil: np.ndarray, observed_shear: np.ndarray,
                     modeled_summary: dict, valid_tiles: np.ndarray,
                     unit_factor: float) -> dict[str, np.ndarray]:
    dil_resid = component_residual(observed_dil, modeled_summary["dilatation"], unit_factor)
    shear_resid = component_residual(observed_shear, modeled_summary["shear"], unit_factor)
    dil_resid[~valid_tiles] = np.nan
    shear_resid[~valid_tiles] = np.nan
    combined = combined_deficit_rank(dil_resid, shear_resid, valid_tiles)
    geodetic_only = combined_deficit_rank(observed_dil, observed_shear, valid_tiles)
    return {
        "dilatation_residual": dil_resid,
        "shear_residual": shear_resid,
        "dilatation_only": positive_empirical_rank(dil_resid, valid_tiles),
        "shear_only": positive_empirical_rank(shear_resid, valid_tiles),
        "combined_residual_prior": combined,
        "geodetic_only_control": geodetic_only,
    }


def main() -> int:
    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool)
    folds = _folds_with_bounds(footprint, catalogue)
    segment_frame = pd.read_csv(SEGMENTS_PATH)
    segment_rows = segment_frame.to_dict(orient="records")
    observed_dil, observed_shear, support, valid_tiles = _load_geodetic_tiles(footprint)

    receipt_rows = []
    scenario_records: dict[str, list[dict]] = {}
    saved = {}
    t0 = datetime.now(timezone.utc)
    for fold_index, fold in enumerate(folds):
        excluded_ids = records_intersecting_block(
            segment_rows, fold["bounds_rc"], BUFFER_PX, GRID.transform, 100.0)
        if not excluded_ids:
            raise SystemExit(f"fold {fold_index}: no source records intersect the buffered block")
        scenarios = {}
        primary_approved = None
        primary_summary = None
        for convention in ("fault_plane", "vertical"):
            tensor, budget_meta = budget(segment_frame, excluded=excluded_ids,
                                         convention=convention)
            modeled = summaries(*tensor)
            for factor in (1e-8, 1e-9):
                key = f"{convention}_{factor:.0e}"
                fields = _scenario_scores(observed_dil, observed_shear, modeled,
                                          valid_tiles, factor)
                metrics = {}
                for metric_name in ("dilatation_only", "shear_only",
                                    "combined_residual_prior", "geodetic_only_control"):
                    values, approved = _metrics(fields[metric_name], valid_tiles,
                                                footprint, fold)
                    metrics[metric_name] = values
                    if convention == PRIMARY_CONVENTION and factor == PRIMARY_UNIT_FACTOR:
                        # Save only the preregistered combined prior for Stage 2.
                        if metric_name == "combined_residual_prior":
                            primary_approved = approved
                            primary_summary = fields
                residual_metrics = {}
                for name in ("dilatation_residual", "shear_residual"):
                    residual = fields[name][valid_tiles]
                    residual_metrics[name] = dict(
                        median=float(np.nanmedian(residual)),
                        positive_fraction=float(np.mean(residual > 0)),
                        p10=float(np.nanpercentile(residual, 10)),
                        p90=float(np.nanpercentile(residual, 90)),
                    )
                scenarios[key] = dict(
                    rate_convention=convention,
                    geodetic_unit_factor=factor,
                    budget_metadata=budget_meta,
                    raw_residual_summary=residual_metrics,
                    metrics=metrics,
                )
                scenario_records.setdefault(key, []).append(scenarios[key])
        if primary_approved is None or primary_summary is None:
            raise SystemExit(f"fold {fold_index}: primary scenario did not produce a Stage-1 mask")
        saved[f"approved_fold{fold_index}"] = primary_approved.astype(np.uint8)
        saved[f"score_fold{fold_index}"] = _tile_to_pixel(
            np.where(valid_tiles, primary_summary["combined_residual_prior"], np.nan)
        ).astype(np.float32)
        saved[f"tile_score_fold{fold_index}"] = primary_summary["combined_residual_prior"].astype(np.float32)
        primary = scenarios[f"{PRIMARY_CONVENTION}_{PRIMARY_UNIT_FACTOR:.0e}"]
        receipt_rows.append(dict(
            fold=fold_index,
            bounds_rc=list(fold["bounds_rc"]),
            heldout_truth_pixels=fold["n_truth"],
            buffered_source_records_excluded=len(excluded_ids),
            source_records_total=len({int(row["record_id"]) for row in segment_rows}),
            excluded_record_ids=sorted(int(x) for x in excluded_ids),
            primary_scenario=primary,
            sensitivities={key: value for key, value in scenarios.items()
                           if key != f"{PRIMARY_CONVENTION}_{PRIMARY_UNIT_FACTOR:.0e}"},
        ))
        print(f"fold {fold_index}: excluded_records={len(excluded_ids)} "
              f"primary_recall={primary['metrics']['combined_residual_prior']['heldout_truth_recall']:.4f} "
              f"lift={primary['metrics']['combined_residual_prior']['recall_over_area_lift']:.4f}",
              flush=True)

    summary = {}
    metric_names = ("dilatation_only", "shear_only", "combined_residual_prior", "geodetic_only_control")
    for key, rows_for_key in sorted(scenario_records.items()):
        summary[key] = {}
        for metric_name in metric_names:
            vals = [x["metrics"][metric_name] for x in rows_for_key]
            summary[key][metric_name] = {
                metric: float(np.nanmean([v[metric] for v in vals]))
                for metric in ("approved_area_share_in_held_block", "heldout_truth_recall",
                               "recall_over_area_lift", "tile_rank_spearman")
            }
        summary[key]["raw_residual_medians"] = {
            name: float(np.nanmean([x["raw_residual_summary"][name]["median"] for x in rows_for_key]))
            for name in ("dilatation_residual", "shear_residual")
        }

    receipt = dict(
        schema_version=1,
        generated_utc=t0.isoformat(timespec="seconds"),
        candidate="H53-A componentwise physical strain-budget residual prior",
        status="STAGE1_SPATIAL_HOLDOUT_COMPLETED; STAGE2_PENDING",
        instrument="Six truth-bearing contiguous blocks from the frozen 3x3 spatial split; visible known-fault catalogue proxy truth only.",
        preregistration="evidence/candidate_hypotheses_prereg_20261008.json",
        protocol=dict(
            tile_px=TILE_PX,
            buffer_px=BUFFER_PX,
            q_lower_percentile=Q,
            primary_rate_convention=PRIMARY_CONVENTION,
            primary_unit_factor=PRIMARY_UNIT_FACTOR,
            sensitivities=[dict(rate_convention=c, unit_factor=u) for c, u in SENSITIVITY],
            residual="observed scalar tile mean - source-matched modeled fault tensor scalar / unit_factor",
            combined_prior="equal-weight empirical ranks of positive dilatation and shear residuals",
            control="equal-weight positive ranks of observed dilatation and shear without modeled fault subtraction",
            heldout_budget_exclusion="exclude the whole official trace record if any actual source segment intersects the held spatial block plus 12 pixels",
            stage1_only=True,
        ),
        formula=dict(
            source="Kreemer et al. (2000), Eq. 3",
            url="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf",
            equation="eps_dot_ij = (1/2) sum_k [L_k*u_dot_k/(A*sin(delta_k))] * (n_i*m_j+n_j*m_i)",
            source_scalar_definitions="registry/official/geodetics_17_README.txt",
            interpretation="Scalar dilation/shear summaries are compared separately; this is not subtraction of full observed/model tensors and not a localized-fault map.",
        ),
        source_audit="evidence/official_attribute_audit_20261008.json",
        segment_count=len(segment_rows),
        valid_tiles=int(valid_tiles.sum()),
        valid_tile_fraction=float(valid_tiles.mean()),
        per_fold=receipt_rows,
        summary=summary,
        saved_masks=str(MASKS.relative_to(ROOT)),
        limitations=[
            "The holdout recovers only visible known-fault pixels; it cannot validate hidden expert labels or off-catalogue discovery.",
            "A residual may be off-fault, aseismic, due to slip-rate/dip/rake or source-unit errors, or geodetic/model error.",
            "The source notation 10E-9/yr is ambiguous; both 1e-8 and 1e-9 unit-factor cases are retained.",
            "Slip-rate component and per-trace dips/rakes are unresolved; primary SLIPSENSE is used, SECONDARY is not double-counted, and blank primary senses are omitted.",
            "The combined scalar ranks are a Stage-1 prior only; no Stage-2 performance or submission eligibility is inferred here."
        ],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    np.savez_compressed(MASKS, **saved)
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "masks": str(MASKS.relative_to(ROOT)),
        "primary": summary[f"{PRIMARY_CONVENTION}_{PRIMARY_UNIT_FACTOR:.0e}"]["combined_residual_prior"],
        "geodetic_only": summary[f"{PRIMARY_CONVENTION}_{PRIMARY_UNIT_FACTOR:.0e}"]["geodetic_only_control"],
        "scenario_summary": summary,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
