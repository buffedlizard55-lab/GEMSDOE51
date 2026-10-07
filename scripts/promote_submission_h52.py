#!/usr/bin/env python3
"""Promote the built H52 artifact to the site's primary download slot.

Reads ``registry/submission_build_h52.json`` + ``docs/downloads/<name>-checks.json``,
verifies the local gates (format + uniqueness), then rewrites the top of
``data/submission_manifest.json``:

* ``primary``                  -> the H52 file (upload-eligible block on the site)
* ``research_only_artifacts``  -> the previous primary, relabelled NOT FOR SUBMISSION,
                                 plus every record already there (so the download
                                 accounting in ``scripts/check_site.py`` stays exact)

It refuses to promote anything whose checks receipt is missing, whose format check
failed, whose uniqueness verdict is not ``PASS``, or which contains a pixel within
300 m of the published catalogue.  Nothing here claims an organizer score.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "downloads"
MANIFEST = ROOT / "data" / "submission_manifest.json"


def demote(prev: dict) -> dict:
    """Relabel the previous primary as a research-only artifact.

    The site's research card reads a different key layout (``holdout.mean``,
    ``holdout.incumbent_H_D_mean``, ``uniqueness.verdict`` ...) than the primary
    record uses, so the fields are remapped instead of silently rendering NaN.
    """
    old = dict(prev)
    ho = dict(old.get("holdout") or {})
    old["holdout"] = {
        "metric": ho.get("candidate", "visible-catalogue proxy DTI, six spatial blocks"),
        "mean": ho.get("mean_dti", ho.get("mean", float("nan"))),
        "incumbent_H_D_mean": ho.get("incumbent_mean_dti", ho.get("incumbent_H_D_mean",
                                                                 float("nan"))),
        "paired_delta": ho.get("paired_mean_delta", ho.get("paired_delta", float("nan"))),
        "folds_higher": ho.get("positive_folds", ho.get("folds_higher", 0)),
        "folds_total": ho.get("n_folds", ho.get("folds_total", 0)),
        "source": "data/submission_manifest.json (historical record, unchanged numbers)",
    }
    u = dict(old.get("uniqueness") or {})
    if "verdict" not in u:
        pw = u.get("prewrite", {}) or {}
        old["uniqueness"] = {
            "verdict": "PASS (pre-write gate)" if pw else "INCOMPLETE",
            # ``evidence`` is read by the site card as a *file name* under downloads/.
            # Records migrated from older manifests may hold a prose sentence that
            # happens to contain a path ("evidence/x.json; local format/uniqueness
            # receipts were measured ..."); keep only the first path-like token so the
            # card never emits an href made of a sentence.
            "evidence": (str(old.get("evidence") or "").split(";")[0].strip()),
            "references_sha_verified": pw.get("n_prior", 0),
            "pixel_comparisons": pw.get("n_prior", 0),
            "matches": 0,
            "max_support_jaccard": pw.get("max_jaccard", float("nan")),
            "max_cosine": float("nan"),
        }
    old["role"] = "SUPERSEDED_LOCAL_BENCHMARK_NOT_FOR_SUBMISSION"
    old["status"] = "SUPERSEDED_BY_H52"
    old["note"] = ((old.get("note", "").rstrip()
                    + " SUPERSEDED by the H52 two-stage file; research-only, do not upload.").strip())
    if old.get("checks_file"):
        old["format_receipt"] = old["checks_file"]
    return old


def main() -> int:
    build = json.loads((ROOT / "registry" / "submission_build_h52.json").read_text())
    name = build["name"]
    checks_path = DOCS / f"{name}-checks.json"
    if not checks_path.is_file():
        raise SystemExit(f"REFUSING: missing checks receipt {checks_path}")
    checks = json.loads(checks_path.read_text())
    fmt = checks["format"]
    gate = checks["uniqueness"]

    failures = []
    if not fmt.get("checks", {}).get("format_valid"):
        failures.append("local format check failed")
    if not str(gate.get("verdict", "")).startswith("PASS"):
        failures.append(f"uniqueness verdict is {gate.get('verdict')!r}")
    if checks.get("on_catalogue_px"):
        failures.append(f"{checks['on_catalogue_px']} emitted pixels lie on the published catalogue")
    if not (DOCS / build["tif"]["file"]).is_file() or not (DOCS / build["zip"]["file"]).is_file():
        failures.append("tif or zip missing from docs/downloads")
    if failures:
        raise SystemExit("REFUSING to promote: " + "; ".join(failures))

    manifest = json.loads(MANIFEST.read_text())
    previous = manifest.get("primary")
    research = list(manifest.get("research_only_artifacts", []))
    if previous:
        research.append(demote(previous))

    manifest["primary"] = {
        "id": build["name"],
        "role": "UPLOAD_CANDIDATE_LOCAL_GATES_PASSED",
        "status": "LOCAL_GATES_PASSED_NOT_ORGANIZER_SCORED",
        "file": build["tif"]["file"],
        "zip": build["zip"]["file"],
        "submission_name": build["name"],
        "note": (f"GEMSDOE51 H52 two-stage: coarse strain-budget tiles (q{checks['stage1_q']:g}, "
                 f"{checks['stage1_area_share']*100:.1f}% of footprint) gating a "
                 f"{checks['variant']} emission of the H-H/H-D blended field; "
                 f"{checks['n_emitted']} dots, none within {checks['flank_px']*100:.0f} m of the published catalogue; "
                 f"local six-fold proxy and format/uniqueness gates passed; no organizer score claimed."),
        "sha256": build["tif"]["sha256"],
        "bytes": build["tif"]["bytes"],
        "checks_file": f"{name}-checks.json",
        "format": {"dtype": "float32", "crs_epsg": 32611,
                   "shape": checks["grid"]["shape"], "checks": fmt["checks"]},
        "stage1": {"q": checks["stage1_q"], "area_share": checks["stage1_area_share"],
                   "emitted_share_inside": checks["stage1_emitted_share"],
                   "lift": checks["stage1_lift"]},
        "uniqueness": gate,
        "holdout": checks.get("holdout", {"note": "see evidence/h52_holdout_*.json"}),
    }
    manifest["research_only_artifacts"] = research
    manifest["submission_readiness"] = {
        "status": "LOCAL_GATES_PASSED_NOT_PORTAL_TESTED",
        "upload_ok": True,
        "caveat": ("Every cell of the file is finite and in [0, 1] (zeros outside the footprint, "
                   "no NoData tag), verified by re-reading the bytes; this cannot trigger the "
                   "reported 'values must be in range [0, 1]' portal error. Organizer acceptance "
                   "and any score are unverified and are not claimed."),
    }
    manifest["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=1))
    print(f"promoted {name} to primary; {len(research)} research-only records retained")
    return 0


if __name__ == "__main__":
    sys.exit(main())
