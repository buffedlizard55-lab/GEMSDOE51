#!/usr/bin/env python3
"""Retired legacy GeoTIFF generator.

This pipeline used a superseded Stage-1 method, an obsolete emission recipe, and
pre-reconciliation promotion assumptions. It is disabled to prevent generating a
file outside the current fail-closed gates. Historical outputs are in archive/.
"""


def main() -> int:
    raise SystemExit(
        "scripts/run_pipeline.py is retired. No current GeoTIFF is eligible; "
        "do not generate or submit an archived output."
    )


if __name__ == "__main__":
    main()
