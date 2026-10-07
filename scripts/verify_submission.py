#!/usr/bin/env python3
"""Compatibility alias for the current local format verifier.

The former checker treated the raster as all-finite and did not validate NaN-outside
footprint handling. It has been retired. Use scripts/check_submission.py instead.
"""
from check_submission import main


if __name__ == "__main__":
    raise SystemExit(main())
