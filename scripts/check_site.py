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

    latest = manifest.get("latest_experiment", {}) or {}
    if latest.get("hypothesis_id") == "H53-A":
        if latest.get("prediction_tiff_generated") is not False or latest.get("file") or latest.get("zip"):
            failures.append("H53 manifest must explicitly report no candidate TIFF/ZIP")
        if latest.get("stage2", {}).get("status") != "NOT_RUN_BLOCKED_BEFORE_CANDIDATE_FIT_OR_SCORING":
            failures.append("H53 manifest does not preserve the fail-closed Stage-2 blocker")
        if manifest.get("submission_readiness", {}).get("upload_ok") is not False:
            failures.append("H53 baseline blocker cannot be upload-eligible")
        latest_page = (DOCS / "latest.html").read_text(encoding="utf-8") if (DOCS / "latest.html").is_file() else ""
        for required in ("FEATURE-LAG H53-A DOWNLOAD FOR RESEARCH: NO", "SUBMIT TO THE COMPETITION: NO",
                         "NOT RUN — BLOCKED BEFORE CANDIDATE FIT/SCORING", "No finite-lag H53-A TIFF",
                         "Separate componentwise strain-budget q10 variant",
                         "not the current finite-lag H53-A candidate above",
                         "Stage 1 — coarse componentwise residual",
                         "Stage 2 — fine placement, separate six-fold holdout"):
            if required.lower() not in latest_page.lower():
                failures.append(f"latest experiment page omits H53 operationalization/status wording: {required}")
        for name in ("h53a_stage1_holdout_20261008.json", "h53a_baseline_provenance_20261008.json",
                     "hypothesis-slate-20261008.md", "preregistration_h53.json"):
            if not (download_dir / name).is_file():
                failures.append(f"H53 evidence download missing: {name}")
            if f'href="downloads/{name}"' not in latest_page and name not in {"hypothesis-slate-20261008.md", "preregistration_h53.json"}:
                failures.append(f"latest experiment page does not link H53 evidence: {name}")
        budget_variant = next((r for r in manifest.get("research_only_artifacts", [])
                               if r.get("id") == "H53A_BUDGET_Q10_RESEARCH_20261008"), None)
        allowed_h53_files = set()
        if budget_variant:
            for key in ("file", "zip"):
                value = budget_variant.get(key)
                if value:
                    allowed_h53_files.add(Path(value).name)
        h53_rasters = [p.name for p in download_dir.iterdir()
                       if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}
                       and p.name.lower().startswith("h53") and p.name not in allowed_h53_files]
        if h53_rasters:
            failures.append(f"unregistered H53 raster/ZIP exists despite the finite-lag candidate being blocked: {h53_rasters}")
        if "NO TIFF FOR THAT CANDIDATE EXISTS" not in index.upper():
            failures.append("executive summary must distinguish the missing finite-lag H53-A TIFF")
        if budget_variant:
            if budget_variant.get("safe_to_submit") is not False:
                failures.append("H53-A budget-q10 variant must remain safe_to_submit=false")
            if not str(budget_variant.get("uniqueness", {}).get("verdict", "")).startswith("FAIL"):
                failures.append("H53-A budget-q10 public-family failure is missing from the manifest")

    if allowed_research:
        if "NOT FOR SUBMISSION" not in index and "DO NOT SUBMIT" not in index:
            failures.append("research-only download is not prominently marked NOT FOR SUBMISSION / DO NOT SUBMIT")
        for name in allowed_research:
            if f'href="downloads/{name}"' not in index:
                failures.append(f"research-only artifact is not linked from index: {name}")
        h53 = next((r for r in manifest.get("research_only_artifacts", [])
                    if r.get("id") == "H53A_BUDGET_Q10_RESEARCH_20261008"), None)
        if h53:
            if h53.get("safe_to_submit") is not False:
                failures.append("H53-A budget-q10 variant must remain explicitly marked safe_to_submit=false")
            if not str(h53.get("uniqueness", {}).get("verdict", "")).startswith("FAIL"):
                failures.append("H53-A budget-q10 public-family uniqueness failure is missing from the manifest")
            latest = (DOCS / "latest.html").read_text(encoding="utf-8")
            if "H53-A" not in latest or "DO NOT SUBMIT" not in latest:
                failures.append("latest report does not prominently show H53-A DO NOT SUBMIT")
            if "Stage 1" not in latest or "Stage 2" not in latest:
                failures.append("latest report does not report Stage 1 and Stage 2 separately")
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
