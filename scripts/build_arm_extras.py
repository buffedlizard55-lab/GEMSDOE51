#!/usr/bin/env python3
"""Build one static feature group to disk, group-by-group, so memory stays bounded.

Why this exists
---------------
``scripts/build_extras.py`` builds *every* hypothesis group in one process and
holds the result in a dict; measured in this sandbox (2 cores, ~3 GB RAM) that
process is OOM-killed while computing later groups. This script can build H-D
scarp-facing coherence or the H-H endpoint/relay bridge arm independently,
then writes each layer to a float32 memmap.

Output: ``data/prepared/arm_<group>.dat`` (float32 memmap, one layer per row) and
``data/prepared/arm_<group>_names.json``.

Usage::

    python3 scripts/build_arm_extras.py --group hd
    python3 scripts/build_arm_extras.py --group hh
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack                       # noqa: E402
from gems51.extras import _build_endpoint_bridge, facecoh_group  # noqa: E402
from gems51.grid import GRID                              # noqa: E402

P = ROOT / "data" / "prepared"

def h_h_group(get, footprint):
    return {**facecoh_group(get, footprint),
            **_build_endpoint_bridge(get, footprint)}


GROUPS = {"hd": facecoh_group, "hh": h_h_group}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="hd", choices=sorted(GROUPS))
    args = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    stack = Stack(P)
    get = lambda n: np.asarray(stack.data[stack.names.index(n)], dtype=np.float32)  # noqa: E731
    group = GROUPS[args.group](get, footprint)
    names = list(group)
    out = P / f"arm_{args.group}.dat"
    mm = np.memmap(out, dtype=np.float32, mode="w+", shape=(len(names), *GRID.shape))
    for i, nm in enumerate(names):
        mm[i] = np.asarray(group[nm], dtype=np.float32)
        print(f"  {nm}: finite={int(np.isfinite(group[nm]).sum()):,}", flush=True)
    mm.flush()
    del mm
    (P / f"arm_{args.group}_names.json").write_text(json.dumps(names, indent=1))
    print(f"wrote {out} with {len(names)} layers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
