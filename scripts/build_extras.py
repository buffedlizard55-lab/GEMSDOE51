#!/usr/bin/env python3
"""Compute the catalogue-independent hypothesis feature groups once, to disk."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack  # noqa: E402
from gems51.extras import build_static  # noqa: E402
from gems51.grid import GRID  # noqa: E402

P = ROOT / "data" / "prepared"


def main():
    footprint = np.load(P / "footprint.npy")
    stack = Stack(P)
    g = build_static(stack, footprint)
    names = list(g.keys())
    mm = np.memmap(P / "extras_static.dat", dtype=np.float32, mode="w+",
                   shape=(len(names), *GRID.shape))
    for i, n in enumerate(names):
        mm[i] = np.asarray(g[n], dtype=np.float32)
        print("  ", n, flush=True)
    mm.flush()
    del mm
    (P / "extras_static_names.json").write_text(json.dumps(names, indent=1))
    print(f"wrote {P/'extras_static.dat'} with {len(names)} layers")


if __name__ == "__main__":
    main()
