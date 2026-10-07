import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "attic" / "legacy-api" / "src" / "gems51" / "strain.py"


def _load_archived_module():
    spec = importlib.util.spec_from_file_location("gems51._legacy_strain", LEGACY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_scalar_stage1_prototype_is_not_in_active_package():
    assert not (ROOT / "src" / "gems51" / "strain.py").exists()


@pytest.mark.parametrize(
    "name",
    ["deficit_table", "stage_a_holdout", "stage_a_independent_test", "gate_comparison"],
)
def test_archived_scalar_stage1_reporters_fail_closed(name):
    legacy = _load_archived_module()
    with pytest.raises(RuntimeError, match="deprecated scalar prototype"):
        getattr(legacy, name)()
