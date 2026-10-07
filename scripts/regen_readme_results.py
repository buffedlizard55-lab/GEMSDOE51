#!/usr/bin/env python3
"""Retired: README.md is now the maintained project brief and evidence handoff.

The earlier generator encoded obsolete submission and leaderboard claims and must
not overwrite the current record. Update README.md only after validating the new
artifact data, then run the documentation and source-link checks.
"""


def main() -> int:
    raise SystemExit(
        "scripts/regen_readme_results.py is retired; it would write stale claims. "
        "Maintain README.md manually from verified current evidence."
    )


if __name__ == "__main__":
    main()
