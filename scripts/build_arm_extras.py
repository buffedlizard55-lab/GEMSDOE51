#!/usr/bin/env python3
"""Build one static feature group to disk, group-by-group, so memory stays bounded.

Why this exists
---------------
``scripts/build_extras.py`` builds *every* hypothesis group in one process and
holds the result in a dict; measured in this sandbox (2 cores, ~3 GB RAM) that
process is OOM-killed while computing the later groups. This helper builds the
baseline H-D face-coherence group or H-H endpoint/bridge group separately. Both
functions are the same group builders used by ``gems51.extras.build_static``.

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

from gems51.detector import Stack            # noqa: E402
from gems51.extras import facecoh_group, _build_endpoint_bridge  # noqa: E402
from gems51.grid import GRID                 # noqa: E402

P = ROOT / "data" / "prepared"
GROUPS = {"hd": facecoh_group, "hh": _build_endpoint_bridge}


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
