"""Shared test fixtures.

The metric tests need no data at all.  The submission/format tests read the shipped raster, which
IS committed.  Tests that need the 557 MB hash-pinned dataset skip themselves when it has not been
restored, so CI stays green without a data download: run `python3 scripts/fetch_data.py --group all`
to make them run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _data_present() -> bool:
    try:
        from gems51 import paths
        return (paths.DATA_DIR / "training_features.tif").exists()
    except Exception:
        return False


requires_data = pytest.mark.skipif(
    not _data_present(),
    reason="hash-pinned dataset not restored (run scripts/fetch_data.py --group all)")
