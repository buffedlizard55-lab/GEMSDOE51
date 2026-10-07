import pytest

from gems51 import strain


@pytest.mark.parametrize(
    "call",
    [
        strain.deficit_table,
        strain.stage_a_holdout,
        strain.stage_a_independent_test,
        strain.gate_comparison,
    ],
)
def test_legacy_scalar_stage1_reporters_fail_closed(call):
    with pytest.raises(RuntimeError, match="deprecated scalar prototype"):
        call()
