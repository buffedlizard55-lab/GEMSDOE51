"""Grid, masks and tiles for the GEMS Prize submission grid.

Verified grid facts (read out of the organizer rasters with rasterio on 2026-10-06, and
independently consistent with the sibling repositories' prepared_manifest.json):

    CRS        EPSG:32611 (UTM 11N)
    shape      3730 rows x 3292 cols, 100 m pixels
    transform  (100, 0, 243350, 0, -100, 4508550)
    bounds     E 243350..572550, N 4135550..4508550

Masks:
    footprint          = finite band 1 of training_features.tif              (5,165,852 px)
    submission_domain  = finite sample_submission.tif                        (5,167,373 px)
    catalogue          = labels.tif > 0                                      (60,988 px)

`labels.tif` and `existing_faults.tif` are byte-identical in the organizer download
(sha256 7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093); the repository
records that as a finding, not as a leak (see registry/irregularities.json IR-51-DATA-02).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from .paths import FEATURES, LABELS

NODATA_SENTINEL: float = -3.4028234663852886e38
EPSG: int = 32611
SHAPE: tuple[int, int] = (3730, 3292)          # (rows, cols)
PIXEL_M: float = 100.0
RADIUS_PX: float = 3.0

BAND_NAMES: tuple[str, ...] = (
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15",
    "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
)
BAND_INDEX: dict[str, int] = {n: i for i, n in enumerate(BAND_NAMES)}


@lru_cache(maxsize=32)
def read_band(name: str) -> np.ndarray:
    """Read one official band as float32 with the nodata sentinel mapped to NaN (cached)."""
    idx = BAND_INDEX[name] + 1
    with rasterio.open(FEATURES) as ds:
        a = ds.read(idx).astype(np.float32)
    a[a == NODATA_SENTINEL] = np.nan
    return a


def read_bands(names) -> np.ndarray:
    return np.stack([read_band(n) for n in names])


@lru_cache(maxsize=1)
def footprint() -> np.ndarray:
    """Boolean mask of the surveyed (finite) footprint."""
    with rasterio.open(FEATURES) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a != NODATA_SENTINEL)


def submission_domain() -> np.ndarray:
    from .paths import SAMPLE_SUBMISSION
    with rasterio.open(SAMPLE_SUBMISSION) as ds:
        a = ds.read(1)
    return np.isfinite(a)


@lru_cache(maxsize=1)
def catalogue() -> np.ndarray:
    """Boolean mask of the visible (USGS / INGENIOUS) catalogue labels."""
    with rasterio.open(LABELS) as ds:
        a = ds.read(1)
    return a > 0


@lru_cache(maxsize=1)
def catalogue_distance() -> np.ndarray:
    """Distance in pixels to the nearest catalogue pixel (0 inside the catalogue)."""
    cat = catalogue()
    return distance_transform_edt(~cat)


def tiles(tile_px: int = 250, min_footprint_px: int = 1):
    """Yield (i, j, sl_rows, sl_cols, coverage) for tiles covering the grid."""
    rows, cols = SHAPE
    fp = footprint()
    for i, r0 in enumerate(range(0, rows, tile_px)):
        for j, c0 in enumerate(range(0, cols, tile_px)):
            r1, c1 = min(r0 + tile_px, rows), min(c0 + tile_px, cols)
            cov = float(fp[r0:r1, c0:c1].mean())
            if cov * (r1 - r0) * (c1 - c0) >= min_footprint_px:
                yield i, j, slice(r0, r1), slice(c0, c1), cov


def tile_index(tile_px: int = 250) -> np.ndarray:
    """Int32 array giving the linear tile id of every pixel (-1 outside the footprint)."""
    rows, cols = SHAPE
    ti = np.full(SHAPE, -1, dtype=np.int32)
    fp = footprint()
    for i, j, rs, cs, _cov in tiles(tile_px):
        block = ti[rs, cs]
        block[fp[rs, cs]] = i * 1000 + j
        ti[rs, cs] = block
    return ti


@lru_cache(maxsize=8)
def spatial_blocks(n: int = 2, tile_px: int = 250) -> np.ndarray:
    """Spatially blocked folds: n x n super-tiles (default 4 quadrant-style blocks).

    Returns an int32 array of block ids on footprint pixels, -1 elsewhere.
    """
    rows, cols = SHAPE
    fp = footprint()
    bid = np.full(SHAPE, -1, dtype=np.int32)
    per_r = int(np.ceil(rows / n))
    per_c = int(np.ceil(cols / n))
    for bi in range(n):
        for bj in range(n):
            rs = slice(bi * per_r, min((bi + 1) * per_r, rows))
            cs = slice(bj * per_c, min((bj + 1) * per_c, cols))
            m = fp[rs, cs]
            blk = bid[rs, cs]
            blk[m] = bi * n + bj
            bid[rs, cs] = blk
    return bid


def write_float32(path, array: np.ndarray, nodata=None) -> dict:
    """Write a single-band float32 GeoTIFF on the official grid; return a format receipt."""
    from .paths import FEATURES as _F
    with rasterio.open(_F) as ds:
        profile = dict(driver="GTiff", height=ds.height, width=ds.width, count=1,
                       dtype="float32", crs=ds.crs, transform=ds.transform,
                       compress="deflate", predictor=2, tiled=False)
    arr = np.asarray(array, dtype=np.float32)
    profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
    return verify_float32(path)


def verify_float32(path) -> dict:
    """Re-open a written raster from disk and report the format receipt."""
    import hashlib
    with rasterio.open(path) as ds:
        a = ds.read(1)
        rec = dict(
            path=str(path), count=ds.count, dtype=ds.dtypes[0], shape=[ds.height, ds.width],
            crs=str(ds.crs), transform=[float(v) for v in ds.transform][:6],
            nodata=None if ds.nodata is None else float(ds.nodata),
            min=float(np.nanmin(a)), max=float(np.nanmax(a)),
            n_nan=int(np.isnan(a).sum()),
            n_below0=int((np.nan_to_num(a, nan=0.0) < 0).sum()),
            n_above1=int((np.nan_to_num(a, nan=0.0) > 1).sum()),
            n_positive=int((np.nan_to_num(a, nan=0.0) > 0).sum()),
            bytes=int(path.stat().st_size),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    rec["all_finite"] = rec["n_nan"] == 0
    rec["in_0_1"] = rec["n_below0"] == 0 and rec["n_above1"] == 0
    return rec
