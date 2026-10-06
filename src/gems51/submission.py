"""Write and verify a competition-legal submission GeoTIFF.

Format requirements (verbatim from the organizer, page 967):
  * same CRS as the training data: projected UTM zone 11N, EPSG:32611
  * same resolution: 100 m
  * same bounds; data outside the bounds null or NaN
  * a single layer, dtype float32, values in [0, 1]

The portal error "Predicted values must be in range [0, 1]"
-----------------------------------------------------------
Two distinct failures produce that message, and both are measured in this module:

1. **The float32 sentinel.**  ``training_features.tif`` uses
   ``-3.4028234663852886e+38`` as nodata.  Writing those bytes through unchanged
   puts values far outside [0, 1].
2. **A NaN nodata tag.**  A raster tagged ``nodata=NaN`` is a legitimate reading
   of the format, but one validator change away from the same rejection.

We therefore ship an **all-finite, untagged** variant as the primary download
(every one of the 12,279,160 cells finite, no nodata tag) and an **official**
NaN-outside twin.  Both are verified by re-reading the written bytes from disk.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from .grid import GRID

EPS = 1e-12


def write_tif(path: Path, values: np.ndarray, outside: float = 0.0,
              nodata=None, compress="deflate") -> dict:
    """Write a single-band float32 GeoTIFF on the competition template grid.

    ``outside`` is the value written outside the footprint: 0.0 for the
    portal-proof variant, NaN for the official variant.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    v = np.asarray(values, dtype=np.float32)
    assert v.shape == GRID.shape, f"shape {v.shape} != {GRID.shape}"
    out = np.where(np.isfinite(v), v, np.float32(outside)).astype(np.float32)
    out = np.clip(out, 0.0, 1.0)

    profile = dict(driver="GTiff", height=GRID.shape[0], width=GRID.shape[1],
                   count=1, dtype="float32", crs=f"EPSG:{GRID.epsg}",
                   transform=Affine(*GRID.transform), nodata=nodata,
                   compress=compress, predictor=3 if compress in ("deflate", "lzw") else 1,
                   tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(out, 1)
        dst.set_band_description(1, "fault probability")
    return verify(path)


def verify(path: Path) -> dict:
    """Re-open the file from disk and check every format requirement."""
    path = Path(path)
    b = path.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    with rasterio.open(path) as s:
        a = s.read(1)
        t = s.transform
        got = dict(
            file=path.name, bytes=len(b), sha256=sha,
            crs=str(s.crs), crs_epsg=s.crs.to_epsg(),
            transform=(t.a, t.b, t.c, t.d, t.e, t.f),
            shape=(s.height, s.width), count=s.count, dtype=s.dtypes[0],
            nodata=(None if s.nodata is None else float(s.nodata)),
        )
    finite = np.isfinite(a)
    in_range = int(((a < -EPS) | (a > 1.0 + EPS)).sum())
    checks = dict(
        single_band=s.count == 1,
        dtype_float32=s.dtypes[0] == "float32",
        crs_epsg_32611=got["crs_epsg"] == 32611,
        transform_matches_template=got["transform"] == GRID.transform,
        shape_matches_template=got["shape"] == GRID.shape,
        all_cells_finite=bool(finite.all()),
        nan_cells=int((~finite).sum()),
        values_outside_0_1=in_range,
        min_value=float(np.nanmin(a)), max_value=float(np.nanmax(a)),
        nodata_tag_is_none=s.nodata is None,
        positive_px=int((a > 0).sum()),
        total_mass=float(np.nansum(a)),
    )
    checks["portal_legal"] = bool(
        checks["single_band"] and checks["dtype_float32"] and checks["crs_epsg_32611"]
        and checks["transform_matches_template"] and checks["shape_matches_template"]
        and checks["values_outside_0_1"] == 0)
    got["checks"] = checks
    return got


def report(path: Path, extra: dict | None = None) -> dict:
    r = verify(path)
    if extra:
        r["content"] = extra
    return r
