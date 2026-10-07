#!/usr/bin/env python3
"""Retired legacy writer; do not use it to create submission artifacts.

This script predates the current NaN-outside writer and promotion/uniqueness gates.
No submission is eligible today. Use scripts/build_submission.py only after a new,
substantively distinct candidate has preregistered evidence and all gates pass.
"""


def main() -> int:
    raise SystemExit(
        "scripts/rebuild_submission.py is retired: it uses the legacy emission path "
        "and can overwrite submission evidence. No current candidate is eligible."
    )


if __name__ == "__main__":
    main()
