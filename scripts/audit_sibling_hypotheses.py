#!/usr/bin/env python3
"""Fetch a bounded, public prior-art corpus from the 54 sibling GEMS repositories.

The inventory is intentionally a literature/document search, not a proof that a
hypothesis was never tried. It records which repositories/files were inspected,
search terms, failed reads, and matching excerpts so novelty claims remain
reviewable. Requires `gh` authentication configured by the environment.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "registry" / "sibling_tiff_inventory.json"
OUT = ROOT / "evidence" / "sibling_prior_art_audit_20261007.json"
OWNER = "buffedlizard55-lab"

TERMS = {
    "river_profile": re.compile(r"river|fluvial|knick.?point|stream.?gradient|drainage.?profile", re.I),
    "hydrothermal_geochemistry": re.compile(r"hydrothermal|geotherm|well.?spring|spring.?chem|water.?chem|geochem|hot.?spring|thermal.?fluid", re.I),
    "paleogeothermal": re.compile(r"paleogeothermal|sinter|tufa|silica.?deposit|travertine", re.I),
    "radiometric_lineament": re.compile(r"radiometric|potassium.?thorium|uranium.?thorium|k.?th|u.?th", re.I),
    "seismicity_lineament": re.compile(r"seismicity.?lineament|earthquake.?lineament|seismic.?lineament|earthquake swarm", re.I),
    "scarp_lineament": re.compile(r"scarp.?radiometric|scarp.?coherence|scarp.?persistence|scarp.?lineament", re.I),
    "stepover_relay": re.compile(r"step.?over|relay.?ramp|relay zone|fault.?tip continuation", re.I),
    "morphometric_texture": re.compile(r"roughness|variogram|semivariogram|ruggedness|topographic texture|surface texture|local variance", re.I),
    "focal_mechanism_stress": re.compile(r"focal mechanism|moment tensor|coulomb stress|resolved shear stress|slip tendency", re.I),
    "water_isotopes_chemistry": re.compile(r"stable isotope|isotope ratio|isotopic|boron|chloride|water chemistry|aqueous chemistry", re.I),
    "subsurface_hydrology": re.compile(r"hydraulic head|groundwater flow|hydraulic gradient|pore pressure|permeability", re.I),
    "tectonic_geomorphometry": re.compile(r"mountain.?front sinuosity|sinuosity index|valley.?floor width|hypsometric integral|basin asymmetry|triangular facet|mountain.?front", re.I),
    "thermal_remote_sensing": re.compile(r"landsat|aster|thermal infrared|land.?surface temperature|surface temperature anomaly|ndvi|vegetation anomaly", re.I),
    "scarp_profile_polarity": re.compile(r"up.?face|down.?face|scarp.?polarity|step.?polarity|step.?asymmetry|profile.?asymmetry|asymmetric.{0,30}scarp", re.I),
    "geophysical_edge_orientation_agreement": re.compile(r"cross.?layer.{0,40}(orientation|azimuth|gradient)|((orientation|azimuth|gradient).{0,40}(agreement|coherence|alignment)).{0,40}(gravity|magnet|conduct|basement)|((gravity|magnet|conduct|basement).{0,40}(orientation|azimuth|gradient).{0,40}(agreement|coherence|alignment))", re.I),
    "geothermometer_temperature_consensus": re.compile(r"geothermometer.{0,60}(consensus|temperature|quartz|chalcedony|cation)|((consensus|temperature).{0,60}geothermometer)", re.I),
}


def gh_text(endpoint: str, timeout: int = 30) -> tuple[str | None, str | None]:
    try:
        p = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw", endpoint],
            cwd=ROOT, text=True, capture_output=True, timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - network/runtime boundary
        return None, str(exc)
    if p.returncode:
        return None, (p.stderr.strip() or f"gh exit {p.returncode}")[:500]
    return p.stdout, None


def tree_for(repo: str, branch: str) -> dict:
    text, err = gh_text(f"repos/{OWNER}/{repo}/git/trees/{branch}?recursive=1", timeout=45)
    if err:
        return {"repo": repo, "branch": branch, "error": err, "files": []}
    try:
        obj = json.loads(text)
        entries = obj.get("tree", [])
        # Retain README, research, hypothesis, scoring, and analysis documents only.
        paths = []
        for item in entries:
            path = item.get("path", "")
            low = path.lower()
            if not (low.endswith((".md", ".rst", ".html"))):
                continue
            if (path.split("/")[-1].lower().startswith("readme")
                    or any(k in low for k in ("research", "hypoth", "ranking", "analysis",
                                                "strategy", "science", "ledger", "experiment",
                                                "prior-art", "prior_art"))):
                paths.append(path)
        return {"repo": repo, "branch": branch, "truncated": bool(obj.get("truncated")),
                "files": paths, "error": None}
    except Exception as exc:
        return {"repo": repo, "branch": branch, "error": f"bad tree JSON: {exc}", "files": []}


def fetch_doc(repo: str, branch: str, path: str) -> dict:
    qpath = path.replace(" ", "%20")
    text, err = gh_text(f"repos/{OWNER}/{repo}/contents/{qpath}?ref={branch}", timeout=30)
    if err:
        return {"repo": repo, "path": path, "error": err}
    hits = {}
    for name, rx in TERMS.items():
        snippets = []
        for m in list(rx.finditer(text))[:8]:
            lo, hi = max(0, m.start() - 100), min(len(text), m.end() + 160)
            snippets.append(re.sub(r"\s+", " ", text[lo:hi]).strip())
        if snippets:
            hits[name] = snippets
    return {"repo": repo, "path": path, "bytes": len(text.encode("utf-8")),
            "hits": hits, "error": None}


def main() -> int:
    if not INVENTORY.exists():
        raise SystemExit(f"missing {INVENTORY}")
    inv = json.loads(INVENTORY.read_text())
    repos = [{"repo": r["repo"], "branch": r.get("branch") or "main"}
             for r in inv.get("repos", [])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        trees = list(pool.map(lambda r: tree_for(r["repo"], r["branch"]), repos))
    tasks = []
    for t in trees:
        for path in t.get("files", []):
            tasks.append((t["repo"], t["branch"], path))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        docs = list(pool.map(lambda x: fetch_doc(*x), tasks))
    counts = {name: sorted({d["repo"] for d in docs if name in d.get("hits", {})})
              for name in TERMS}
    errors = [{"repo": x["repo"], "branch": x["branch"], "error": x.get("error")}
              for x in trees if x.get("error")]
    errors += [{"repo": d["repo"], "path": d["path"], "error": d["error"]}
               for d in docs if d.get("error")]
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": {
            "owner": OWNER, "repositories_in_inventory": len(repos),
            "trees_read": sum(not t.get("error") for t in trees),
            "selected_documents": len(tasks), "documents_read": sum(not d.get("error") for d in docs),
            "limitations": [
                "Public repository document search only; code, notebooks, branches other than the recorded default, external publications, and uncommitted work are not exhaustive.",
                "A term hit means prior art is documented, not necessarily implemented or scored.",
                "No global claim of novelty is made from this search alone.",
            ],
        },
        "terms": {name: rx.pattern for name, rx in TERMS.items()},
        "repository_hits_by_topic": counts,
        "tree_errors": errors,
        "documents": docs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"scope": result["scope"], "repository_hits_by_topic": counts,
                      "errors": len(errors), "output": str(OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
