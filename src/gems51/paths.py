"""Filesystem layout for GEMSDOE51.

Data is NEVER committed.  `scripts/fetch_data.py` restores every byte from a hash-pinned
public mirror and fails closed on any digest mismatch (see registry/data_manifest.json and
registry/irregularities.json IR-51-DATA-01: the mirrors are owner-supplied copies of the
organizer's files, so the pins prove consistency, not organizer authentication).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Where the hash-pinned rasters/CSVs live.  Outside `data/` by default so the repository
#: never accidentally commits them; override with GEMS51_DATA_DIR.
DATA_DIR = Path(os.environ.get("GEMS51_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK_DIR = Path(os.environ.get("GEMS51_WORK_DIR", ROOT / "work"))
EVIDENCE_DIR = ROOT / "evidence"
REGISTRY_DIR = ROOT / "registry"
DOCS_DIR = ROOT / "docs"
DOWNLOADS_DIR = DOCS_DIR / "downloads"

FEATURES = DATA_DIR / "training_features.tif"
LABELS = DATA_DIR / "labels.tif"
EXISTING_FAULTS = DATA_DIR / "existing_faults.tif"
SAMPLE_SUBMISSION = DATA_DIR / "sample_submission.tif"

EXTERNAL = DATA_DIR / "external"
SCORED = DATA_DIR / "scored"
QFAULT_TRACES = EXTERNAL / "gdr_qfaults_traces.csv"
WELLSPRING = EXTERNAL / "gdr_wellspring_in_footprint.csv"
VOLCANIC_VENTS = EXTERNAL / "gdr_volcanic_vents_in_footprint.csv"
LIDAR_SCARP = EXTERNAL / "lidar_scarp_features_u8.tif"
GEODAWN_RAD = EXTERNAL / "geodawn_rad_u8.tif"
GEODAWN_EXT = EXTERNAL / "geodawn_extensions_u8.tif"
SGMC_FAULTS = EXTERNAL / "derived_sgmc_faults_100m_u8.tif"


def ensure_dirs() -> None:
    for d in (DATA_DIR, WORK_DIR, EVIDENCE_DIR, REGISTRY_DIR, DOCS_DIR, DOWNLOADS_DIR):
        d.mkdir(parents=True, exist_ok=True)
