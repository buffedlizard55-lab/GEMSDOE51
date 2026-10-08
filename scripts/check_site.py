#!/usr/bin/env python3
"""Check local links and that the built download state matches the manifest."""
from __future__ import annotations

import html.parser
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.values.append(value)


def main() -> int:
    failures: list[str] = []
    pages = sorted(DOCS.glob("*.html"))
    if not pages:
        failures.append("docs/ contains no HTML pages")
    for page in pages:
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for value in parser.values:
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            local_path = unquote(parsed.path)
            suffix = Path(local_path).suffix.lower()
            if ("archive/submissions/" in local_path.lstrip("./")
                    and suffix in {".tif", ".tiff", ".zip"}):
                failures.append(f"{page.relative_to(ROOT)} links an archived candidate: {value}")
            target = (page.parent / local_path).resolve()
            if not target.is_file() and not target.is_dir():
                failures.append(f"{page.relative_to(ROOT)} -> {value}")

    try:
        manifest = json.loads((ROOT / "data" / "submission_manifest.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"cannot read current submission manifest: {exc}")
        manifest = {}
    download_dir = DOCS / "downloads"
    public_downloads = ({p.name for p in download_dir.iterdir()
                         if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}}
                        if download_dir.exists() else set())
    allowed_current = set()
    for record in ([manifest.get("primary")] if manifest.get("primary") else []):
        for key in ("file", "zip"):
            value = record.get(key)
            if value:
                allowed_current.add(Path(value).name)
    allowed_research = set()
    for record in manifest.get("research_only_artifacts", []):
        for key in ("file", "zip"):
            value = record.get(key)
            if value:
                allowed_research.add(Path(value).name)
    allowed_candidate = set()
    candidate = manifest.get("recommended_upload_candidate") or {}
    for key in ("file", "zip"):
        value = candidate.get(key)
        if value:
            allowed_candidate.add(Path(value).name)
    allowed_downloads = allowed_current | allowed_research | allowed_candidate
    if public_downloads != allowed_downloads:
        failures.append(f"public TIFF/ZIPs do not match manifest: found={sorted(public_downloads)}, "
                        f"allowed={sorted(allowed_downloads)}")
    index = (DOCS / "index.html").read_text(encoding="utf-8")
    latest_overall = manifest.get("latest_experiment", {}) or {}
    cand_rec = manifest.get("recommended_upload_candidate") or {}
    cand_id = cand_rec.get("id")
    # Merged state: the latest experiment is the recommended upload candidate
    # (H53-SR artifact); K2-08 remains recorded as the parallel sessions' latest
    # overall COMPLETED candidate (research-only).
    if latest_overall.get("id") not in {"K2_08_CONDUCTIVE_RIBBON_20261008", cand_id}:
        failures.append("manifest latest_experiment must be the recommended candidate "
                        "or the retained K2-08 record")
    research_ids = {r.get("id") for r in manifest.get("research_only_artifacts", [])}
    if "K2_08_CONDUCTIVE_RIBBON_20261008" not in research_ids:
        failures.append("manifest must retain K2-08 as a research-only record")
    latest_page_for_identity = (DOCS / "latest.html").read_text(encoding="utf-8") if (DOCS / "latest.html").is_file() else ""
    if "K2-08" not in latest_page_for_identity:
        failures.append("latest report must retain the K2-08 research record")
    if cand_id and "H53-SR" not in latest_page_for_identity:
        failures.append("latest report must render the H53-SR recommended candidate")
    readiness = manifest.get("submission_readiness", {}).get("status", "")
    if manifest.get("primary"):
        for name in allowed_current:
            if f'href="downloads/{name}"' not in index:
                failures.append(f"primary artifact is not linked from index: {name}")
        if readiness == "PORTAL_ACCEPTED":
            if "Portal-validated submission file" not in index:
                failures.append("portal-accepted primary is not prominently marked in index")
        elif candidate:
            # Third state: a constraint-compliant candidate exists that has never been
            # uploaded.  The page must say so in those words, must still mark the
            # audit-only benchmark as not cleared, and must link the candidate bytes.
            if "RECOMMENDED UPLOAD CANDIDATE" not in index:
                failures.append("recommended candidate is not prominently marked in index")
            if "NOT YET PORTAL-VALIDATED" not in index.upper():
                failures.append("recommended candidate is not marked NOT YET PORTAL-VALIDATED")
            if "NOT CLEARED FOR UPLOAD" not in index.upper():
                failures.append("audit-only benchmark is not marked NOT CLEARED FOR UPLOAD")
            for name in allowed_candidate:
                if f'href="downloads/{name}"' not in index:
                    failures.append(f"recommended candidate is not linked from index: {name}")
        else:
            index_upper = index.upper()
            if ("NO UPLOAD-ELIGIBLE ARTIFACT" not in index_upper
                    or "NOT CLEARED FOR UPLOAD" not in index_upper):
                failures.append("blocked local benchmark is not prominently marked NOT FOR UPLOAD in index")
            if manifest.get("submission_readiness", {}).get("upload_ok") is not False:
                failures.append("manifest says no candidate, but upload_ok is not explicitly false")
            howto = (DOCS / "how-to-submit.html").read_text(encoding="utf-8")
            if "No file is cleared to upload" not in howto or "no weekly competition slot is authorized" not in howto.lower():
                failures.append("submission guide does not explicitly block upload/slot while no candidate is cleared")
            for rec in manifest.get("research_only_artifacts", []):
                if rec.get("id") in {"H51_N2_PHYSICAL_CREDITTHIN", "H52_V4_STRAINCONF_20261007"}:
                    name = Path(rec.get("file", "")).name
                    if f'href="downloads/{name}"' not in index:
                        failures.append(f"research-only candidate is not linked from index: {name}")
                    if "NOT FOR SUBMISSION" not in index:
                        failures.append("research-only candidate is not marked NOT FOR SUBMISSION")
    else:
        if ("No eligible submission file" not in index
                and "No upload-eligible submission file" not in index):
            failures.append("index page does not state that no eligible file exists")

    latest_h53 = manifest.get("latest_h53_experiment", {}) or {}
    if latest_h53.get("hypothesis_id") == "H53-A":
        if (latest_h53.get("prediction_tiff_generated") is not False
                or latest_h53.get("file") or latest_h53.get("zip")):
            failures.append("latest H53 record must explicitly report no H53-A candidate TIFF/ZIP")
        if latest_h53.get("stage2", {}).get("status") != "NOT_RUN_BLOCKED_BEFORE_CANDIDATE_FIT_OR_SCORING":
            failures.append("latest H53 record does not preserve the fail-closed Stage-2 blocker")
        # The blocked H53-A baseline-gate record must never be upload-eligible.  This
        # is scoped to that record: a DIFFERENT artifact (this session's H53-SR
        # two-stage candidate, IR-H53-05) may legitimately hold upload_ok=true.
        cand_rec = manifest.get("recommended_upload_candidate") or {}
        if (cand_rec.get("id") == latest_h53.get("research_identifier")
                or cand_rec.get("submission_name") == latest_h53.get("research_identifier")
                or (latest_h53.get("file") and cand_rec.get("file") == latest_h53.get("file"))):
            failures.append("the blocked H53-A baseline-gate record must not be the "
                            "recommended upload candidate")
        latest_page = (DOCS / "latest.html").read_text(encoding="utf-8") if (DOCS / "latest.html").is_file() else ""
        latest_upper = latest_page.upper()
        for required in ("FINITE-LAG H53-A", "NO FINITE-LAG H53-A CANDIDATE TIFF",
                         "NOT RUN — BLOCKED BEFORE CANDIDATE FIT/SCORING",
                         "SEPARATE COMPONENTWISE BUDGET-Q10 H53-A VARIANT",
                         "SUBMIT TO THE COMPETITION: NO"):
            if required not in latest_upper:
                failures.append(f"latest report omits or conflates H53 operationalization/status: {required}")
        for name in ("h53a_stage1_holdout_20261008.json", "h53a_baseline_provenance_20261008.json",
                     "hypothesis-slate-20261008.md", "preregistration_h53.json"):
            if not (download_dir / name).is_file():
                failures.append(f"H53 evidence download missing: {name}")
            if f'href="downloads/{name}"' not in latest_page and name not in {"hypothesis-slate-20261008.md", "preregistration_h53.json"}:
                failures.append(f"latest experiment page does not link H53 evidence: {name}")
        allowed_h53_research = set()
        for record in manifest.get("research_only_artifacts", []):
            if record.get("id") in {"H53_K2X_Q10_RESEARCH_20261008", "H53A_BUDGET_Q10_RESEARCH_20261008"}:
                for key in ("file", "zip"):
                    if record.get(key):
                        allowed_h53_research.add(Path(record[key]).name)
        cand_h53 = manifest.get("recommended_upload_candidate") or {}
        for key in ("file", "zip"):
            if cand_h53.get(key):
                allowed_h53_research.add(Path(cand_h53[key]).name)
        h53_rasters = {p.name for p in download_dir.iterdir()
                       if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}
                       and "h53" in p.name.lower()}
        unexpected_h53_rasters = h53_rasters - allowed_h53_research
        if unexpected_h53_rasters:
            failures.append("unmanifested H53 raster/ZIP exists without a scored candidate: "
                            f"{sorted(unexpected_h53_rasters)}")
        if "NO FINITE-LAG H53-A CANDIDATE TIFF EXISTS" not in index.upper():
            failures.append("executive summary does not distinguish the absent finite-lag H53-A TIFF")
        if "H53-K2X" not in index.upper() or "SUBMIT: NO" not in index.upper():
            failures.append("executive summary does not distinguish the H53-K2x research TIFF from H53-A")

    budget_variant = next((r for r in manifest.get("research_only_artifacts", [])
                           if r.get("id") == "H53A_BUDGET_Q10_RESEARCH_20261008"), None)
    if not budget_variant:
        failures.append("separate budget-q10 H53-A research record is missing from the manifest")
    else:
        if budget_variant.get("safe_to_submit") is not False:
            failures.append("budget-q10 H53-A variant must remain safe_to_submit=false")
        if not str(budget_variant.get("uniqueness", {}).get("verdict", "")).startswith("FAIL"):
            failures.append("budget-q10 H53-A broad-family containment failure is missing")
        if budget_variant.get("file") == (manifest.get("latest_h53_experiment", {}) or {}).get("file"):
            failures.append("budget-q10 TIFF must not be attributed to the finite-lag H53-A record")
        latest_page = (DOCS / "latest.html").read_text(encoding="utf-8") if (DOCS / "latest.html").is_file() else ""
        latest_upper = latest_page.upper()
        for required in ("FINITE-LAG H53-A", "BUDGET-Q10 H53-A VARIANT",
                         "NOT THE FINITE-LAG H53-A RESULT", "RESEARCH ONLY / DO NOT SUBMIT"):
            if required not in latest_upper:
                failures.append(f"latest report must clearly separate budget-q10 from finite-lag H53-A: {required}")
        for name in (Path(budget_variant.get("file", "")).name,
                     "h53_stage1_holdout_20261008.json", "h53_stage2_holdout_20261008.json",
                     "h53_public_uniqueness_20261008.json",
                     "candidate-hypotheses-budget-q10-2026-10-08.md",
                     "candidate_hypotheses_budget_q10_prereg_20261008.json"):
            if not name or not (download_dir / name).is_file():
                failures.append(f"budget-q10 H53-A evidence download missing: {name}")
        if budget_variant.get("file") and f'href="downloads/{Path(budget_variant["file"]).name}"' not in latest_page:
            failures.append("latest report does not link the separate budget-q10 H53-A TIFF")

    if allowed_research:
        if "NOT FOR SUBMISSION" not in index:
            failures.append("research-only download is not prominently marked NOT FOR SUBMISSION")
        for name in allowed_research:
            if f'href="downloads/{name}"' not in index:
                failures.append(f"research-only artifact is not linked from index: {name}")
    elif not manifest.get("primary") and 'href="downloads/' in index:
        failures.append("index page links to a download despite an empty artifact manifest")

    for rel in ("data/leaderboard.json", "registry/leaderboard.json",
                "registry/leaderboard_reads.json", "registry/leaderboard_snapshot.json",
                "registry/scored_submissions.json"):
        if (ROOT / rel).exists():
            failures.append(f"{rel} must not mirror leaderboard standings")
    if failures:
        print("SITE CHECK FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print(f"SITE CHECK PASSED: {len(pages)} pages, local links resolve, download state matches manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
