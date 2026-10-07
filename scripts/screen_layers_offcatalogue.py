#!/usr/bin/env python3
"""Which supplied/derived layers actually predict *unmapped* structure?

Question
--------
The competition truth is a fault **missing from the published catalogue**, and the organizer removes
known catalogue pixels from the scored domain.  A layer can therefore only be useful if its high
values concentrate where structure exists but the catalogue does not.

Instruments (independent of the competition's hidden labels)
------------------------------------------------------------
* **S** -- USGS SGMC state-map faults that are not in the competition catalogue (>2 px).  The sibling's
  live-calibrated instrument of this kind is the best ranker of live leaderboard scores measured in
  this project (Spearman +0.54, n=12).
* **L** -- 1-m-DEM scarp-crest pixels (``lid_upface_max``/``lid_lappos_max`` >= p99) further than 2 px
  from the catalogue.

For every layer in the prepared stack (and for the two- and three-way rank fusions named on the command
line) this script emits the exact dense binary DTI of its top-N pixels, at N = 12,691 (the sibling's
fitted hidden-truth size) and at matched mass for the strongest layers.  This is a *screen*: the top-N
emission is a diagnostic probe, not a submission.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/screen_layers_offcatalogue.py --top-n 12691
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.stack import lineament_bank  # noqa: E402

P = ROOT / "data" / "prepared"


def topn_mask(field: np.ndarray, allowed: np.ndarray, n: int) -> np.ndarray:
    """Binary mask of the top-n ranked pixels of ``field`` inside ``allowed``."""
    ys, xs = np.nonzero(allowed)
    if n >= ys.size:
        out = np.zeros(field.shape, bool)
        out[ys, xs] = True
        return out
    v = field[ys, xs]
    thr = np.partition(v, -n)[-n]
    keep = v >= thr
    out = np.zeros(field.shape, bool)
    out[ys[keep], xs[keep]] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=12691)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "layer_screen_offcatalogue.json"))
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r",
                   shape=(len(names), *GRID.shape))
    dcat = ndi.distance_transform_edt(~catalogue)
    off = footprint & (dcat > 2.0)

    truth_s = (np.asarray(mm[names.index("sgmc_fault")], np.float32) > 0.5) & off
    up = np.asarray(mm[names.index("lid_upface_max")], np.float32)
    lp = np.asarray(mm[names.index("lid_lappos_max")], np.float32)
    fin = np.isfinite(up) & np.isfinite(lp)
    thr = np.percentile(up[footprint & fin], 99.0)
    truth_l = fin & (up >= thr) & (lp > 0) & off
    print(f"truth S {int(truth_s.sum()):,} px | truth L {int(truth_l.sum()):,} px")

    rows = {}
    for nm in names:
        if nm in ("sgmc_fault", "lid_upface_max", "lid_lappos_max"):
            continue                      # instrument inputs are excluded by construction
        f = np.asarray(mm[names.index(nm)], np.float32)
        m = footprint & np.isfinite(f)
        if m.sum() < 50_000:
            continue
        sel = topn_mask(f, m, a.top_n)
        s = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
        l = dti_binary(sel, truth_l, valid=footprint, known=catalogue)
        rows[nm] = dict(S=float(s["dti"]), L=float(l["dti"]), px=int(sel.sum()))
        print(f"  {nm:32s} S={s['dti']:.4f} L={l['dti']:.4f}", flush=True)

    order = sorted(rows, key=lambda k: -(rows[k]["S"] + rows[k]["L"]))
    print("\nTop 15 by S+L:")
    for k in order[:15]:
        print(f"  {k:32s} S={rows[k]['S']:.4f} L={rows[k]['L']:.4f}")

    Path(a.out).write_text(json.dumps(dict(schema_version=1, top_n=a.top_n,
                                           truth_S_px=int(truth_s.sum()),
                                           truth_L_px=int(truth_l.sum()),
                                           layers=rows, ranked=order), indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
