#!/usr/bin/env python3
"""Retired scalar Stage-1 diagnostic; its receipt is preserved in archive/evidence/."""


def main() -> int:
    raise SystemExit(
        "scripts/check_stage_a_convention.py is retired because it depends on the "
        "deprecated scalar strain prototype. Use strain_budget.py and the current "
        "trace-held-out Stage-1 report."
    )


if __name__ == "__main__":
    main()
