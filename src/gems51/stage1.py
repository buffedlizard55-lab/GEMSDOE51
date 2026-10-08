"""Stage 1 as a reusable module: the coarse strain-budget deficit and its approved domain.

This is the same construction that ``scripts/run_two_stage.py`` implements inline
(``stage1_field`` / ``def_big`` / ``appr`` in that file).  It is factored out here
so that the H52 holdout and the H52 submission builder evaluate *exactly* the same
Stage-1 object, rather than two drifting copies.  The definition is unchanged:

    deficit(tile) = Q( observed geodetic 2nd-invariant tile mean )
                  - Q( mapped-trace Kostrov tile invariant )

with ``Q`` the empirical quantile (rank) map over tiles that have footprint
support.  Rank space is used because the three geodetic bands are internally
consistent only up to an unknown monotone convention (see
``gems51.strain_budget``), and because the mapped-trace tensor's rate units and
rate-component convention remain provisional (IR-51-12).  The approved domain at
quantile ``q`` is every tile whose deficit is at or above the q-th percentile,
so ``q=10`` approves the 90 % of the footprint with the largest deficit.

One difference from the older driver is deliberate and is *not* a change of
definition: the trace rows assigned to the held-out block are removed from the
slip-rate table before the tensor is built, exactly as
``scripts/run_two_stage.py`` does, so the fold-specific Stage 1 never sees the
traces it is being asked to help find.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from . import strain_budget as sb
from .grid import GRID
from .paths import FEATURES

GEODETIC_BANDS = ("geod_2ndinv", "geod_shearrate", "geod_dilaterate")


def load_observed(features_path: Path | None = None) -> dict:
    """Tile-independent observed geodetic layers, sentinel-coded to NaN."""
    path = Path(features_path) if features_path is not None else FEATURES
    with rasterio.open(path) as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        out = {}
        for nm in GEODETIC_BANDS:
            a = s.read(descs.index(nm) + 1).astype(np.float64)
            a[a <= -1e38] = np.nan
            out[nm] = a
    return out


def stage1_field(catalogue_known: np.ndarray, footprint: np.ndarray, df: pd.DataFrame,
                 obs: dict, cfg: sb.BudgetConfig) -> dict:
    """Rank-space deficit over broad tiles, from the fold-visible catalogue only."""
    exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
        catalogue_known, df, cfg, area_mask=footprint)
    II_f = sb.invariant(exx, eyy, exy, "II")
    obsII = sb.observed_tiles(obs["geod_2ndinv"], footprint, cfg.tile_px)
    dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, cfg.tile_px)
    ok_t = np.isfinite(dom) & (dom > 0.05)
    q_f = sb.quantile_map(np.where(ok_t, II_f, np.nan))
    q_o = sb.quantile_map(np.where(ok_t, obsII, np.nan))
    deficit = q_o - q_f
    return dict(deficit=deficit, II_fault=II_f, II_obs=obsII, trace_len=lent,
                ok_tiles=ok_t, meta=meta)


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    nt_y, nt_x = tiles.shape
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def approved_mask(deficit_tiles: np.ndarray, footprint: np.ndarray, tile_px: int,
                  q: float) -> np.ndarray:
    """Tile mask with deficit at/above the q-th percentile, upsampled to the raster."""
    big = upsample(deficit_tiles, tile_px)
    finite = np.isfinite(big) & footprint
    if not finite.any():
        raise ValueError("no tiles carry a finite deficit")
    thr = float(np.nanpercentile(big[finite], q))
    return finite & (big >= thr)
