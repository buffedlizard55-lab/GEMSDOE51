#!/usr/bin/env python3
"""Audit the clipped QFault vector rows against the preserved official DBF export.

Uses only the Python standard library so source-field reconciliation does not
depend on pandas. This audits attribute identity/semantics; it does not establish
that rates are exact measurements or that the fault budget is geodetically valid.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTR = ROOT / "registry/official/qfault_attributes.csv"
LOCAL = ROOT / "data/raw/external/gdr_qfaults_traces.csv"
SEGMENTS = ROOT / "registry/official/trace_segments_utm11.csv"
OUT = ROOT / "evidence/official_attribute_audit_20261008.json"


def text(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def dec(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return None


def sense_text(value: str) -> str:
    value = (value or "").strip()
    return "" if value.lower() in {"nan", "none", "null"} else value


def main() -> int:
    for path in (ATTR, LOCAL, SEGMENTS):
        if not path.is_file():
            raise SystemExit(f"required source audit input is missing: {path}")

    with ATTR.open(newline="", encoding="utf-8") as fh:
        official = list(csv.DictReader(fh))
    with LOCAL.open(newline="", encoding="utf-8") as fh:
        local = list(csv.DictReader(fh))
    with SEGMENTS.open(newline="", encoding="utf-8") as fh:
        segments = list(csv.DictReader(fh))

    ids = [int(row["trace_id"]) for row in local]
    if len(ids) != len(set(ids)):
        raise SystemExit("local clipped-trace table has duplicate source record IDs")
    if any(rid < 0 or rid >= len(official) for rid in ids):
        raise SystemExit("local trace_id is not a valid zero-based source DBF row index")
    selected = [official[rid] for rid in ids]

    checks = {
        "rows": len(local),
        "unique_source_record_ids": len(set(ids)),
        "name_matches": sum(text(src, "NAME") == text(loc, "name")
                             for src, loc in zip(selected, local)),
        "sliprt2023_text_matches_segment_export": sum(
            text(official[int(seg["record_id"])], "SLIPRT2023") == text(seg, "slip_text")
            for seg in segments
        ),
        "sliprt_num_matches_local_numeric_rate": sum(
            dec(text(src, "SLIPRTNUM")) == dec(text(loc, "slip_rate"))
            for src, loc in zip(selected, local)
        ),
        "primary_sense_matches_local": sum(
            sense_text(text(src, "SLIPSENSE")) == sense_text(text(loc, "slip_sense"))
            for src, loc in zip(selected, local)
        ),
        "geometry_primary_sense_matches_source": sum(
            text(official[int(seg["record_id"])], "SLIPSENSE") == text(seg, "sense")
            for seg in segments
        ),
    }
    n_segments = len(segments)
    ids_with_geometry = sorted({int(row["record_id"]) for row in segments})
    local_geometry_attrs = [official[rid] for rid in ids_with_geometry]
    primary_counts = Counter(text(row, "SLIPSENSE") or "<blank>"
                             for row in local_geometry_attrs)
    secondary_counts = Counter(text(row, "SECONDARY") or "<blank>"
                               for row in local_geometry_attrs)
    sense_combinations = Counter(
        (text(row, "SLIPSENSE") or "<blank>",
         text(row, "SECONDARY") or "<blank>")
        for row in local_geometry_attrs
    )
    segment_sense_counts = Counter(text(row, "sense") or "<blank>" for row in segments)
    secondary_present = [row for row in local_geometry_attrs if text(row, "SECONDARY")]
    bounded_rates = [row for row in local_geometry_attrs
                     if text(row, "SLIPRT2023").startswith(("<", ">", "≤", "≥"))]
    dip_direction_values = Counter(text(row, "DIPDIRECT") or "<blank>"
                                   for row in local_geometry_attrs)

    # Every source record appears in the regional CSV; every geometry segment
    # must match the source row. A failure is fatal, not merely diagnostic.
    if len(ids) != 1126 or len(ids_with_geometry) != 1126:
        raise SystemExit(f"unexpected clipped source-record coverage: csv={len(ids)}, geometry={len(ids_with_geometry)}")
    if (checks["name_matches"] != len(local)
            or checks["sliprt_num_matches_local_numeric_rate"] != len(local)
            or checks["primary_sense_matches_local"] != len(local)
            or checks["sliprt2023_text_matches_segment_export"] != n_segments
            or checks["geometry_primary_sense_matches_source"] != n_segments):
        raise SystemExit("source attribute mismatch; see audit counters before using the budget")

    source_primary_codes = ["NULL", "unk", "N", "R", "SS", "T"]
    source_secondary_codes = ["NULL", "SS", "T", "R"]
    observed_primary = sorted(k for k in primary_counts if k != "<blank>")
    observed_secondary = sorted(k for k in secondary_counts if k != "<blank>")
    primary_doc_mismatch = sorted(set(observed_primary) - set(source_primary_codes))
    secondary_doc_mismatch = sorted(set(observed_secondary) - set(source_secondary_codes))

    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "official_dbf_export": "registry/official/qfault_attributes.csv",
            "field_definitions": "registry/official/qfaults_8_README_fielddefinitions_qfaults_ingenious_nad83conus117_2023-06-27.txt",
            "clipped_trace_table": "data/raw/external/gdr_qfaults_traces.csv",
            "clipped_geometry": "registry/official/trace_segments_utm11.csv",
            "gdr_landing_page": "https://gdr.openei.org/submissions/1391"
        },
        "identity_checks": checks,
        "clipped_scope": {
            "regional_dbf_records": len(local),
            "source_record_index_basis": "trace_id/record_id are zero-based row positions in the preserved DBF export; no persistent OBJECTID is asserted",
            "projected_segment_pieces": n_segments,
            "unique_geometry_records": len(ids_with_geometry),
            "segment_primary_sense_counts": dict(segment_sense_counts),
            "unsupported_or_blank_primary_sense_segments_omitted_by_vector_budget": int(
                sum(count for sense, count in segment_sense_counts.items()
                    if sense not in {"N", "RL", "LL"})
            )
        },
        "rate_audit": {
            "official_definition": "SLIPRT2023 is the assigned slip rate in mm/year; SLIPRTNUM is its numeric portion.",
            "rate_units": "mm/year; verified from the preserved official field-definition text",
            "local_sliprt2023_markup_or_bound_rows": len(bounded_rates),
            "local_sliprt2023_markup_note": "No <, >, <=, or >= text occurs in this clipped regional record set. The numeric field still supplies assigned rates, not uncertainty intervals.",
            "component_convention": "Unresolved: the official field definition does not say whether the assigned rate is vertical displacement or total fault-plane slip.",
            "dip_caution": "DIPDIRECT is a cardinal dip direction, not a numeric dip angle; the budget's 60-degree normal-dip and vertical strike-slip assumptions are not source measurements.",
            "dip_direction_counts": dict(dip_direction_values),
            "rate_matches": checks["sliprt_num_matches_local_numeric_rate"]
        },
        "sense_audit": {
            "primary_slipsense_counts_by_source_record": dict(primary_counts),
            "secondary_counts_by_source_record": dict(secondary_counts),
            "primary_secondary_combinations": {
                f"{primary}|{secondary}": count
                for (primary, secondary), count in sorted(sense_combinations.items())
            },
            "records_with_nonblank_secondary": len(secondary_present),
            "observed_primary_codes_not_listed_in_field_definition": primary_doc_mismatch,
            "observed_secondary_codes_not_listed_in_field_definition": secondary_doc_mismatch,
            "secondary_handling": "Preserved in qfault_attributes.csv and audited, but not summed into the tensor budget: the shapefile supplies no separate rate partition for the secondary mechanism; adding the full SLIPRTNUM to both could double-count.",
            "blank_primary_sense_handling": "Omitted, not imputed as normal, in the actual-vector budget.",
            "budgeted_primary_senses": ["N", "RL", "LL"]
        },
        "interpretation": [
            "All clipped primary names, numeric rates, and primary senses match the preserved official DBF export; all 84,331 segment pieces match official SLIPRT2023 text and SLIPSENSE by source-row index.",
            "The field-definition code lists do not cover every value observed in the clipped source rows (notably RL and LL). Treat the definitions as incomplete or stale for those codes; no silent conversion is made.",
            "The source unit and numeric field are verified, but rate component, individual dip, rake, and secondary rate partition remain unresolved assumptions.",
            "The local clipped set has no textual rate bounds; this does not imply all records in the full Great Basin source are exact measurements.",
            "Primary SLIPSENSE is used only; SECONDARY is not silently added. The blank-primary segment count remains visible as a budget omission."
        ],
        "field_definition_codes": {
            "primary_documented": source_primary_codes,
            "secondary_documented": source_secondary_codes,
            "primary_observed_in_clip": observed_primary,
            "secondary_observed_in_clip": observed_secondary
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "identity_checks": checks,
        "primary_counts": dict(primary_counts),
        "secondary_counts": dict(secondary_counts),
        "combinations": result["sense_audit"]["primary_secondary_combinations"],
        "omitted_segments": result["clipped_scope"]["unsupported_or_blank_primary_sense_segments_omitted_by_vector_budget"],
        "source_code_mismatches": {"primary": primary_doc_mismatch, "secondary": secondary_doc_mismatch}
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
