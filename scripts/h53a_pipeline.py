"""Shared source-corrected Stage-1 helpers for the frozen H53-A experiment."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.strain_budget import observed_tiles  # noqa: E402
from gems51.vector_budget import budget, clip_segment, summaries  # noqa: E402
from gems51.vector_stage1 import approved_pixel_mask, residual_rank_prior  # noqa: E402

RAW = ROOT / "data" / "raw"
SEGMENTS_PATH = ROOT / "registry" / "official" / "trace_segments_utm11.csv"
TILE_PX = 100
NOMINAL_RATE_SCALE = 1e-8  # literal 10E-9/year in the source geodetic README
NORMAL_DIP_DEG = 60.0


def load_stage1_inputs(footprint: np.ndarray):
    """Read the original clipped official QFaults segments and geodetic bands."""
    if not SEGMENTS_PATH.is_file():
        raise FileNotFoundError(f"official trace segments are missing: {SEGMENTS_PATH}")
    rows = pd.read_csv(SEGMENTS_PATH)
    required = {"record_id", "x0", "y0", "x1", "y1", "slip_mm_yr", "sense"}
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"official trace segments lack required columns: {missing}")
    observations = {}
    wanted = {
        "dilatation": "geod_dilaterate",
        "shear": "geod_shearrate",
        "second_invariant": "geod_2ndinv",
    }
    with rasterio.open(RAW / "training_features.tif") as src:
        GRID.assert_matches(dict(transform=src.transform, height=src.height,
                                 width=src.width, crs=src.crs))
        names = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        for key, name in wanted.items():
            if names.count(name) != 1:
                raise ValueError(f"expected exactly one source band {name!r}; found {names.count(name)}")
            value = src.read(names.index(name) + 1).astype(np.float64)
            value[~np.isfinite(value) | (value <= -1e38)] = np.nan
            if value.shape != footprint.shape:
                raise ValueError(f"geodetic source {name} shape {value.shape} != {footprint.shape}")
            observations[key] = value
    return rows, observations


def make_vector_stage1(
    segment_rows: pd.DataFrame,
    observations: dict[str, np.ndarray],
    footprint: np.ndarray,
    *,
    excluded_record_ids=(),
    rate_scale: float = NOMINAL_RATE_SCALE,
    convention: str = "fault_plane",
    q: float = 10.0,
) -> dict:
    """Build tile tensor, absolute scalar residuals, rank prior, and q-mask."""
    tensor, budget_meta = budget(
        segment_rows,
        excluded=excluded_record_ids,
        tile_m=float(TILE_PX * GRID.transform[0]),
        convention=convention,
    )
    # ``vector_budget.budget`` intentionally enforces 10 km cells; the scalar
    # tile width is 100 pixels at 100 m. Keep that fixed physical contract.
    predicted = summaries(*tensor)
    obs_d = observed_tiles(observations["dilatation"], footprint, TILE_PX)
    obs_s = observed_tiles(observations["shear"], footprint, TILE_PX)
    tile_support = observed_tiles(np.ones(GRID.shape, dtype=np.float32), footprint, TILE_PX)
    valid = np.isfinite(tile_support) & (tile_support > 0.05)
    residuals = residual_rank_prior(
        obs_d,
        obs_s,
        predicted["dilatation"],
        predicted["shear"],
        valid,
        geodetic_rate_scale=rate_scale,
    )
    approved, threshold, area_share = approved_pixel_mask(
        residuals["prior_score"], footprint, tile_px=TILE_PX, q=q
    )
    return dict(
        tensor=tensor,
        predicted=predicted,
        observed_dilatation_tiles=obs_d,
        observed_shear_tiles=obs_s,
        valid_tiles=valid,
        residuals=residuals,
        approved=approved,
        threshold=threshold,
        approved_area_share=area_share,
        budget_meta=budget_meta,
        rate_scale=float(rate_scale),
        convention=convention,
        q=float(q),
    )


def record_ids_intersecting_block(segment_rows: pd.DataFrame, block: np.ndarray) -> list[int]:
    """Return whole official record IDs with a nonzero segment inside a raster block.

    Intersection is against the complete rectangle occupied by ``block``, not
    only its labelled pixels, so a held-out source segment cannot contribute to
    Stage 1 through a nearby pixel or an unlabelled portion of its trace.
    """
    yy, xx = np.nonzero(np.asarray(block, dtype=bool))
    if yy.size == 0:
        return []
    a, b, x_origin, d, e, y_origin = GRID.transform
    left = x_origin + int(xx.min()) * a
    right = x_origin + (int(xx.max()) + 1) * a
    top = y_origin + int(yy.min()) * e
    bottom = y_origin + (int(yy.max()) + 1) * e

    x0 = segment_rows["x0"].to_numpy(float)
    y0 = segment_rows["y0"].to_numpy(float)
    x1 = segment_rows["x1"].to_numpy(float)
    y1 = segment_rows["y1"].to_numpy(float)
    low_x, high_x = np.minimum(x0, x1), np.maximum(x0, x1)
    low_y, high_y = np.minimum(y0, y1), np.maximum(y0, y1)
    possible = np.flatnonzero((high_x >= left) & (low_x <= right)
                              & (high_y >= bottom) & (low_y <= top))
    record_ids = segment_rows["record_id"].to_numpy()
    excluded: set[int] = set()
    for i in possible:
        if clip_segment(x0[i], y0[i], x1[i], y1[i], left, bottom, right, top) is not None:
            excluded.add(int(record_ids[i]))
    return sorted(excluded)


def rasterize_records(segment_rows: pd.DataFrame, record_ids, footprint: np.ndarray) -> np.ndarray:
    """Rasterize source LineStrings for the requested official record IDs."""
    ids = {int(value) for value in record_ids}
    if not ids:
        return np.zeros(GRID.shape, dtype=bool)
    subset = segment_rows[segment_rows.record_id.astype(int).isin(ids)]
    shapes = [
        ({"type": "LineString", "coordinates": [(float(r.x0), float(r.y0)),
                                                    (float(r.x1), float(r.y1))]}, 1)
        for r in subset.itertuples(index=False)
        if np.isfinite([r.x0, r.y0, r.x1, r.y1]).all()
    ]
    if not shapes:
        return np.zeros(GRID.shape, dtype=bool)
    out = rasterize(
        shapes,
        out_shape=GRID.shape,
        transform=Affine(*GRID.transform),
        dtype="uint8",
        all_touched=False,
    ) > 0
    out &= np.asarray(footprint, dtype=bool)
    return out


def random_prediction(mask: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Sample ``n`` unique allowed pixels; fail instead of silently shrinking mass."""
    m = np.asarray(mask, dtype=bool)
    yy, xx = np.nonzero(m)
    if n < 0 or n > yy.size:
        raise ValueError(f"requested {n} random points from only {yy.size} allowed pixels")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(yy.size, size=int(n), replace=False)
    out = np.zeros(m.shape, dtype=bool)
    out[yy[chosen], xx[chosen]] = True
    return out
