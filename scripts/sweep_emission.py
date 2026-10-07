#!/usr/bin/env python3
"""Retired legacy emission sweep; it could overwrite an obsolete result file."""


def main() -> int:
    raise SystemExit(
        "scripts/sweep_emission.py is retired. Its previous results are archived; "
        "use current data/gate_sweep.json and the preregistered holdout evidence."
    )


if __name__ == "__main__":
    main()
