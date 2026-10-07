#!/usr/bin/env python3
"""Retired spatial holdout runner.

The older quadrant protocol and output names can overwrite current holdout evidence.
Use scripts/run_experiments.py for the current blocked known-fault proxy design.
"""


def main() -> int:
    raise SystemExit(
        "scripts/run_holdout.py is retired; use scripts/run_experiments.py and "
        "the current preregistered fold definitions."
    )


if __name__ == "__main__":
    main()
