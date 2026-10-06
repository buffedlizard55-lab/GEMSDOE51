#!/usr/bin/env python3
"""Resolve the sign disagreement between the two Stage-A instruments (IR-51-04).

strain.stage_a_independent_test() averages the geodetic band over the WHOLE tile (every finite
pixel, including cells outside the data footprint, which are stored as 0), while
strain.gate_comparison() averages over footprint cells only.  Those two conventions give opposite
signs for the same correlation against the lidar scarp layer (which is what an independent
instrument must not do).  This script computes both conventions side by side on identical tiles and
writes evidence/stage_a_instrument_consistency.json, so the reported number is the defensible one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import grid, strain  # noqa: E402


def main() -> None:
    fp = grid.footprint()
    cat = grid.catalogue()
    d_cat = grid.catalogue_distance()
    layers = strain._independent_layers()
    band = "geod_2ndinv"
    field = grid.read_band(band)

    rows = []
    for (i, j, rs, cs, _cov) in grid.tiles(strain.TILE_PX):
        sel = fp[rs, cs]
        if sel.sum() < 100:
            continue
        whole = field[rs, cs]
        whole = whole[np.isfinite(whole)]
        inside = field[rs, cs][sel]
        inside = inside[np.isfinite(inside)]
        if inside.size == 0 or inside.mean() <= 0:
            continue
        rows.append(dict(
            tile_i=i, tile_j=j,
            geod_whole=np.nanmean(whole) if whole.size else np.nan,
            geod_footprint=float(inside.mean()),
            n_footprint_px=int(sel.sum()), n_whole_px=int(whole.size),
            scarp=float(layers["lidar_scarp"][rs, cs][sel].mean()) if "lidar_scarp" in layers else np.nan,
            sgmc_offcat=float((layers["sgmc"][rs, cs] & (d_cat[rs, cs] >= 2.0))[sel].mean())
            if "sgmc" in layers else np.nan,
            cat_density=float(cat[rs, cs][sel].mean()),
        ))

    out = dict(tile_px=strain.TILE_PX, band=band, n_tiles=len(rows),
               convention_note="whole = mean over every finite cell of the tile (out-of-footprint "
                               "cells are 0, which drags the mean down for edge tiles); footprint = "
                               "mean over footprint cells only, the convention the gate itself uses.")
    for conv in ("geod_whole", "geod_footprint"):
        x = np.array([r[conv] for r in rows], float)
        rec = {}
        for key in ("scarp", "sgmc_offcat", "cat_density"):
            y = np.array([r[key] for r in rows], float)
            ok = np.isfinite(x) & np.isfinite(y)
            rec[key] = dict(spearman_rho=float(spearmanr(x[ok], y[ok]).statistic),
                            n=int(ok.sum()))
        out[conv] = rec
    pooled = np.array([r["n_footprint_px"] / max(1, r["n_whole_px"]) for r in rows])
    out["footprint_fraction_of_tile"] = dict(median=float(np.median(pooled)),
                                             p10=float(np.percentile(pooled, 10)))
    (ROOT / "evidence" / "stage_a_instrument_consistency.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
