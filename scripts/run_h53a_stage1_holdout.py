#!/usr/bin/env python3
"""Run the separately preregistered five-split H53-A coarse Stage-1 audit.

This script does not fit the detector and never emits a fault point: Stage 1
only approves broad 10 km tiles. It evaluates known-catalogue proxy recovery
for whole official QFaults records held out from the source-segment budget.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from h53a_pipeline import (  # noqa: E402
    NOMINAL_RATE_SCALE,
    load_stage1_inputs,
    make_vector_stage1,
    random_prediction,
    rasterize_records,
)

P = ROOT / "data" / "prepared"
OUT = ROOT / "evidence" / "h53a_stage1_holdout_20261008.json"
SPLITS = 5
SPLIT_SEED = 5308
MASS_RATIO = 3.47


def _mean(values):
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite frozen H53-A Stage-1 result: {OUT}")
    prereg = json.loads((ROOT / "registry" / "preregistration_h53.json").read_text())
    if prereg.get("status") != "FROZEN_BEFORE_SCORING":
        raise SystemExit("H53 preregistration is not in its frozen pre-score state")

    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool)
    if footprint.shape != GRID.shape or catalogue.shape != GRID.shape:
        raise SystemExit("prepared footprint/catalogue do not match the frozen competition grid")
    segment_rows, observations = load_stage1_inputs(footprint)
    unique_ids = np.sort(segment_rows["record_id"].dropna().astype(np.int64).unique())
    if unique_ids.size < SPLITS:
        raise SystemExit("too few distinct official trace records for five whole-record splits")
    permuted = np.random.default_rng(SPLIT_SEED).permutation(unique_ids)
    groups = [np.asarray(g, dtype=np.int64) for g in np.array_split(permuted, SPLITS)]
    group_hashes = [hashlib.sha256(g.astype("<i8").tobytes()).hexdigest() for g in groups]

    split_rows = []
    receipt = dict(
        schema_version=1,
        id="GEMSDOE51-H53-A-STAGE1-20261008",
        status="IN_PROGRESS",
        preregistration="registry/preregistration_h53.json",
        instrument="Five whole-official-record holdouts; visible QFaults pixel raster is proxy truth, not hidden organizer labels.",
        config=dict(
            split_count=SPLITS,
            split_seed=SPLIT_SEED,
            split_rule="sorted unique record_id values; default_rng(seed).permutation; numpy.array_split",
            split_group_sha256=group_hashes,
            mass_ratio=MASS_RATIO,
            random_dti_seed_rule="5300 + split_index",
            tile_px=100,
            nominal_rate_scale=NOMINAL_RATE_SCALE,
            nominal_slip_component="fault-plane rate; 60-degree normal dip; unknown sense omitted",
            sensitivities=[
                {"rate_scale": 1e-9, "convention": "fault_plane"},
                {"rate_scale": 1e-8, "convention": "vertical"},
            ],
        ),
        per_split=split_rows,
        limitations=[
            "The visible catalogue is proxy truth, not expert-held-out organizer truth.",
            "A Stage-1 residual can also reflect off-fault or aseismic deformation, rate/component uncertainty, dip/rake assumptions, unit convention, or interpolation.",
            "Uniform-in-mask DTI is one seeded random realization per split and must not be read as a stable performance estimate.",
        ],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)

    sensitivity_specs = (
        ("nominal", NOMINAL_RATE_SCALE, "fault_plane"),
        ("unit_1e-9", 1e-9, "fault_plane"),
        ("vertical_rate", NOMINAL_RATE_SCALE, "vertical"),
    )
    for split_index, held_ids in enumerate(groups):
        held_ids_set = {int(v) for v in held_ids}
        held_truth = rasterize_records(segment_rows, held_ids_set, footprint)
        if not held_truth.any():
            raise SystemExit(f"split {split_index} has no rasterized in-footprint trace pixels")
        # Other catalogue pixels remain known to the metric; the held-out set is
        # the only proxy truth presented to this Stage-1-only experiment.
        known = catalogue & ~held_truth
        n_truth = int(held_truth.sum())
        n_target = int(round(MASS_RATIO * n_truth))

        cases = {}
        for case_name, rate_scale, convention in sensitivity_specs:
            excluded_ids = set(held_ids_set)
            stage1 = make_vector_stage1(
                segment_rows,
                observations,
                footprint,
                excluded_record_ids=excluded_ids,
                rate_scale=rate_scale,
                convention=convention,
                q=10.0,
            )
            approved = stage1["approved"]
            recall = float((approved & held_truth).sum() / max(n_truth, 1))
            area_share = float(stage1["approved_area_share"])
            case = dict(
                rate_scale=float(rate_scale),
                convention=convention,
                excluded_record_ids=int(len(excluded_ids)),
                used_segment_length_m=float(stage1["budget_meta"]["used_length_m"]),
                omitted_segments=int(stage1["budget_meta"]["omitted_segments"]),
                valid_tile_count=int(stage1["valid_tiles"].sum()),
                q10_threshold=float(stage1["threshold"]),
                approved_area_share=area_share,
                heldout_truth_pixels=n_truth,
                heldout_pixels_in_approved=int((approved & held_truth).sum()),
                heldout_recall=recall,
                recall_area_lift=float(recall / max(area_share, 1e-12)),
            )
            if case_name == "nominal":
                seed = 5300 + split_index
                control_results = {}
                for label, domain in (
                    ("uniform_in_approved", approved & ~known),
                    ("uniform_in_footprint", footprint & ~known),
                ):
                    prediction = random_prediction(domain, n_target, seed)
                    score = dti_binary(
                        prediction,
                        held_truth,
                        valid=footprint,
                        known=known,
                    )
                    control_results[label] = dict(
                        seed=seed,
                        n_emitted=int(prediction.sum()),
                        dti=float(score["dti"]),
                        tp=float(score["tp"]),
                        fp=float(score["fp"]),
                    )
                case["matched_mass_random_controls"] = control_results
            cases[case_name] = case
            del stage1, approved

        split_rows.append(dict(
            split=int(split_index),
            held_record_count=int(len(held_ids)),
            held_record_ids_sha256=group_hashes[split_index],
            heldout_truth_pixels=n_truth,
            other_known_catalogue_pixels=int(known.sum()),
            cases=cases,
        ))
        receipt["per_split"] = split_rows
        OUT.write_text(json.dumps(receipt, indent=1) + "\n")
        nominal = cases["nominal"]
        ctrl = nominal["matched_mass_random_controls"]
        print(
            f"split {split_index}: records={len(held_ids)}, truth_px={n_truth}, "
            f"area={nominal['approved_area_share']:.3f}, recall={nominal['heldout_recall']:.3f}, "
            f"lift={nominal['recall_area_lift']:.3f}, "
            f"random DTI approved/full={ctrl['uniform_in_approved']['dti']:.6f}/"
            f"{ctrl['uniform_in_footprint']['dti']:.6f}",
            flush=True,
        )

    summary = {}
    for case_name, _, _ in sensitivity_specs:
        values = [r["cases"][case_name] for r in split_rows]
        summary[case_name] = dict(
            mean_approved_area_share=_mean([v["approved_area_share"] for v in values]),
            mean_heldout_recall=_mean([v["heldout_recall"] for v in values]),
            mean_recall_area_lift=_mean([v["recall_area_lift"] for v in values]),
            per_split_approved_area_share=[v["approved_area_share"] for v in values],
            per_split_heldout_recall=[v["heldout_recall"] for v in values],
            per_split_recall_area_lift=[v["recall_area_lift"] for v in values],
        )
        if case_name == "nominal":
            for control_name in ("uniform_in_approved", "uniform_in_footprint"):
                dv = [v["matched_mass_random_controls"][control_name]["dti"] for v in values]
                summary[case_name][f"{control_name}_mean_dti"] = _mean(dv)
                summary[case_name][f"{control_name}_per_split_dti"] = dv

    receipt["summary"] = summary
    receipt["status"] = "COMPLETE_STAGE1_ONLY"
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
