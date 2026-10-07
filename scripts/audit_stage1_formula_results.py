#!/usr/bin/env python3
"""Build a reproducible side-by-side audit of the Stage-1 formula sensitivities.

Inputs are the four already-run five-split trace-holdout records. This script
never reruns the expensive holdout; it preserves the exact input records and
summarizes their paired deterministic ranking metrics separately from the
single-draw, unpaired random-emission DTI diagnostic.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "vertical_unknown_normal": "data/stage1_vertical_assume.json",
    "fault_plane_unknown_normal": "data/stage1_fault_plane_assume.json",
    "vertical_known_sense_only": "data/stage1_vertical_known_sense_only.json",
    "fault_plane_known_sense_only": "data/stage1_fault_plane_known_sense_only.json",
}


def metric(record, name, q=None):
    key = f"{name}_q{q}" if q is not None else name
    val = record["summary"][key]
    return {"mean": val["mean"], "per_split": val["per_split"]}


def paired_delta(a, b):
    deltas = [x - y for x, y in zip(a, b)]
    return {
        "a_minus_b_per_split": deltas,
        "mean_delta": sum(deltas) / len(deltas),
        "a_wins": sum(x > 0 for x in deltas),
        "n_splits": len(deltas),
    }


def main() -> int:
    loaded = {key: json.loads((ROOT / path).read_text())
              for key, path in INPUTS.items()}
    rows = []
    comparisons = {}
    for key, record in loaded.items():
        s = record["summary"]
        row = {
            "scenario": key,
            "rate_convention": record["config"]["rate_convention"],
            "assume_unknown_normal": record["config"]["assume_unknown_normal"],
            "n_splits": record["config"]["n_splits"],
            "heldout_trace_pixel_counts": [r["n_truth"] for r in record["per_split"]],
            "spearman_deficit": metric(record, "spearman_deficit"),
            "spearman_geodetic_only": metric(record, "spearman_geodetic_only"),
            "deficit_q50": {
                "area_share": metric(record, "deficit_area", "50"),
                "truth_recall": metric(record, "deficit_recall", "50"),
                "lift": metric(record, "deficit_lift", "50"),
                "random_dot_proxy_dti": metric(record, "deficit_dti", "50"),
            },
            "geodetic_only_q50": {
                "area_share": metric(record, "geodetic_only_area", "50"),
                "truth_recall": metric(record, "geodetic_only_recall", "50"),
                "lift": metric(record, "geodetic_only_lift", "50"),
                "random_dot_proxy_dti": metric(record, "geodetic_only_dti", "50"),
            },
            "deficit_q70": {
                "area_share": metric(record, "deficit_area", "70"),
                "truth_recall": metric(record, "deficit_recall", "70"),
                "lift": metric(record, "deficit_lift", "70"),
                "random_dot_proxy_dti": metric(record, "deficit_dti", "70"),
            },
            "geodetic_only_q70": {
                "area_share": metric(record, "geodetic_only_area", "70"),
                "truth_recall": metric(record, "geodetic_only_recall", "70"),
                "lift": metric(record, "geodetic_only_lift", "70"),
                "random_dot_proxy_dti": metric(record, "geodetic_only_dti", "70"),
            },
            "uniform_random_dot_proxy_dti": metric(record, "uniform_dti"),
            "input": INPUTS[key],
        }
        rows.append(row)
        comparisons[key] = {
            "q50_deficit_minus_geodetic_only_lift": paired_delta(
                s["deficit_lift_q50"]["per_split"],
                s["geodetic_only_lift_q50"]["per_split"]),
            "q70_deficit_minus_geodetic_only_lift": paired_delta(
                s["deficit_lift_q70"]["per_split"],
                s["geodetic_only_lift_q70"]["per_split"]),
            "spearman_deficit_minus_geodetic_only": paired_delta(
                s["spearman_deficit"]["per_split"],
                s["spearman_geodetic_only"]["per_split"]),
        }

    stage1 = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema_version": 1,
        "evaluation": {
            "stage": "Stage 1 only; no Stage-2 detector or learned point ranking",
            "design": "five random trace-level splits; the same five held-out trace groups are reused in all four formula scenarios",
            "tile_size": "100 x 100 pixels = 10 x 10 km at the 100 m grid",
            "thresholds": {"q50": "top half of eligible tile ranking", "q70": "top 30% of eligible tile ranking"},
            "dot_budget": "round(3.47 * 12,700) = 44,069 random dots per split; 12,700 is a planning proxy inherited from an unverified prior-project density scenario, not a measured hidden truth count",
            "dot_budget_basis": "Sensitivity/budget-control constant only. No public leaderboard row identifies an artifact or reveals hidden K; the earlier 0.2600-to-0.2778 natural-experiment rationale was withdrawn.",
            "truth": "owner-mirrored visible USGS/INGENIOUS catalogue traces; proxy only, not organizer labels",
            "limitations": [
                "Trace-level holdout is intentionally not a contiguous spatial block: withholding a whole spatial block would erase the catalogue-derived budget term in that block and reduce the deficit to the raw geodetic field.",
                "The score is a catalogue-proxy diagnostic, not an organizer score and not a test of hidden-fault discovery.",
                "Each approved-area random-dot DTI is one seeded realization per split. These DTI draws are not paired across different masks/scenarios; do not read small DTI differences as a precise effect. Area, recall, lift, and Spearman comparisons are deterministic on the same held-out trace splits.",
                "The five split results are a small sample and were not used to tune a new Stage-1 model.",
            ],
        },
        "formula": {
            "source": "Kreemer et al. (2000), On the determination of a global strain rate model, Earth, Planets and Space 52, 765-770, Eq. (3)",
            "source_url": "https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf",
            "source_formula": "epsilon_dot_ij = (1/2) * sum_k [(L_k * u_dot_k) / (A * sin(delta_k))] * m_ij^k",
            "source_formula_equivalent": "epsilon_dot_ij = 1/(2A) * sum_k [L_k * u_dot_k / sin(delta_k)] * m_ij^k",
            "terms": {
                "A": "tile area",
                "L_k": "catalogue trace length represented by fault segment k",
                "u_dot_k": "slip-rate component passed by the source table (component semantics unresolved)",
                "delta_k": "dip angle (not present as a numeric field in the local CSV; code uses an explicit 60-degree normal-fault assumption and 90-degree strike-slip assumption)",
                "m_ij": "unit moment tensor defined by fault orientation and unit slip vector, as specified by the paper",
            },
            "implementation_components": {
                "normal_fault_vertical_rate_assumption": "L * u_dot_vertical * cot(delta) / A",
                "normal_fault_total_fault_plane_rate_assumption": "L * u_dot_plane * cos(delta) / A",
                "strike_slip_shear": "L * u_dot / (2A), with RL and LL signs opposite",
                "horizontal_invariant": "sqrt(exx^2 + eyy^2 + 2*exy^2)",
                "rate_unit_conversion": "local CSV numeric value multiplied by 1e-3 (working mm/yr-to-m/yr assumption)",
            },
        },
        "source_field_audit": {
            "gdr_landing_page": "https://gdr.openei.org/submissions/1391",
            "gdr_landing_page_takeaway": "GDR identifies the public INGENIOUS compilation, DOI 10.15121/1881483 and CC BY 4.0; it says Quaternary Faults v2 supersedes v1 and includes a field-definition text document.",
            "usgs_rest_layer": "https://earthquake.usgs.gov/arcgis/rest/services/haz/Qfaults/MapServer/21?f=pjson",
            "usgs_rest_layer_takeaway": "USGS layer 21 exposes slip_rate as a string field with alias 'Slip Rate(mm/year)' and null coded-value domain; the alias supports a unit label but does not establish the component/convention of the local decimal values.",
            "local_csv": "data/raw/external/gdr_qfaults_traces.csv",
            "local_csv_observation": "1126 rows; slip_rate parses as float64, has 49 distinct values and no missing values (computed from the owner-mirrored CSV).",
            "unresolved": [
                "The GDR v2 archive's field-definition text was not extracted in this run (the direct archive fetch failed), so the numeric values' exact field semantics/precision are not authenticated here.",
                "The local CSV does not resolve whether slip_rate is vertical displacement, total fault-plane slip, or another component; both vertical and fault-plane conversions are tested as assumptions.",
                "Missing slip_sense is handled in two explicit cases: assume unknown is normal, or exclude unknown-sense contributions. Neither fallback is source-authenticated.",
                "dip_direct is an azimuth/direction label, not a numeric dip angle; it is not used as a dip angle by the code.",
            ],
        },
        "assumption_audit": {
            "normal_dip_degrees": 60,
            "strike_slip_dip_degrees": 90,
            "mu_pa": 30000000000,
            "mu_cancels_from_rate_equation": True,
            "h_seis_m_default": 15000,
            "h_seis_role": "used only in a reported scalar moment-rate proxy; it does not enter the strain-tensor components or Stage-1 ranking, so the old description of a seismogenic-thickness sensitivity for this strain calculation was misleading.",
            "unknown_sense_modes": ["assume normal (Basin-and-Range fallback)", "exclude unknown-sense contributions"],
            "dip_direction": "not used as an inclination angle; local strike is estimated from catalogue raster geometry",
        },
        "scenarios": rows,
        "paired_deterministic_comparisons": comparisons,
        "interpretation": {
            "bottom_line": "Changing the total-slip versus vertical-slip convention and the unknown-sense fallback moves the deficit's measured quantile-space performance only modestly; none of the four settings makes the deficit outperform the raw geodetic-only ranking on mean Spearman correlation or q50/q70 recall-per-area lift.",
            "physical_caution": "Subtracting mapped-fault strain is not guaranteed to isolate uncatalogued faulting: mapped faults can spatially covary with unmapped faults, and uncertainty in the slip table, dip, rake, assignments, and geodetic tensor convention is large relative to this coarse residual.",
            "usage_decision": "Keep the deficit as a low-confidence broad-tile prior/diagnostic only; do not use it as a fine-scale point placer or hard Stage-2 gate. Report Stage 1 separately from the Stage-2 blocked holdout.",
        },
    }
    out = ROOT / "evidence" / "stage1_formula_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stage1, indent=2) + "\n")
    print(json.dumps({
        "output": str(out),
        "scenarios": [{
            "scenario": r["scenario"],
            "spearman_deficit": r["spearman_deficit"]["mean"],
            "spearman_geodetic_only": r["spearman_geodetic_only"]["mean"],
            "q50_lift_deficit": r["deficit_q50"]["lift"]["mean"],
            "q50_lift_geodetic_only": r["geodetic_only_q50"]["lift"]["mean"],
            "q50_dti_deficit": r["deficit_q50"]["random_dot_proxy_dti"]["mean"],
            "q50_dti_geodetic_only": r["geodetic_only_q50"]["random_dot_proxy_dti"]["mean"],
        } for r in rows],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
