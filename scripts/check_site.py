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
