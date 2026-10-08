#!/usr/bin/env python3
"""Build the frozen H53-A finite-lag cross-physics feature family.

Inputs are only the hash-pinned competition bands already in data/prepared.
This operation is label-blind and does not read any TIFF prediction or holdout
truth.  It writes a regenerable float32 memmap under ignored data/prepared/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.h53_features import finite_lag_edge_features  # noqa: E402

P = ROOT / "data" / "prepared"


def main() -> int:
    footprint = np.load(P / "footprint.npy")
    stack = Stack(P)
    needed = ("comp_det_elev", "comp_iso_grav_anom")
    absent = [name for name in needed if name not in stack.names]
    if absent:
        raise SystemExit(f"prepared stack lacks H53-A inputs: {absent}")
    elevation = np.asarray(stack.data[stack.names.index(needed[0])], dtype=np.float32)
    gravity = np.asarray(stack.data[stack.names.index(needed[1])], dtype=np.float32)
    valid = footprint & np.isfinite(elevation) & np.isfinite(gravity)
    features = finite_lag_edge_features(
        elevation, gravity, valid, sigmas=(2.0, 5.0), max_lag_px=8
    )
    names = list(features)
    if names != [
        "h53_zero_coedge_s20", "h53_offset_coedge_s20", "h53_signed_lag_s20",
        "h53_zero_coedge_s50", "h53_offset_coedge_s50", "h53_signed_lag_s50",
    ]:
        raise SystemExit(f"unexpected preregistered H53-A feature names: {names}")
    out = P / "arm_h53a.dat"
    mm = np.memmap(out, dtype=np.float32, mode="w+", shape=(len(names), *GRID.shape))
    for i, name in enumerate(names):
        layer = np.asarray(features[name], dtype=np.float32)
        inside = footprint & valid
        if not np.isfinite(layer[inside]).all():
            raise SystemExit(f"H53-A layer {name} has nonfinite values inside valid inputs")
        finite = layer[inside]
        if name.startswith("h53_signed_lag"):
            if finite.size and (float(finite.min()) < -1.000001 or float(finite.max()) > 1.000001):
                raise SystemExit(f"H53-A lag feature {name} escaped [-1,1]")
        elif finite.size and (float(finite.min()) < -1e-7 or float(finite.max()) > 1.000001):
            raise SystemExit(f"H53-A response {name} escaped [0,1]")
        mm[i] = layer
        print(f"{name}: finite={int(np.isfinite(layer).sum()):,}; "
              f"min={float(np.nanmin(layer)):.6g}; max={float(np.nanmax(layer)):.6g}",
              flush=True)
        del layer
    mm.flush()
    del mm
    (P / "arm_h53a_names.json").write_text(json.dumps(names, indent=1) + "\n")
    print(f"wrote {out} with {len(names)} H53-A features", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
