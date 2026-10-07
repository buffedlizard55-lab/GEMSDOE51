#!/usr/bin/env python3
"""Retired legacy uniqueness checker.

Its thresholds and reference collection differ from the current source-aware
pre-write guard. Do not use it to qualify a submission or bypass the builder.
"""


def main() -> int:
    raise SystemExit(
        "scripts/run_uniqueness_gate.py is retired; it is not the current uniqueness "
        "gate. No candidate is eligible for submission."
    )


if __name__ == "__main__":
    main()
