#!/usr/bin/env python3
"""Retired legacy runner.

This pipeline used a deprecated scalar Stage-1 prototype and an obsolete
submission API. It is intentionally disabled. Use the dedicated current
experiment, holdout, site-build, and verification scripts documented in README.md.
"""


def main() -> int:
    raise SystemExit(
        "scripts/run_all.py is retired. No submission is currently eligible; "
        "use only the current scripts listed in README.md."
    )


if __name__ == "__main__":
    main()
