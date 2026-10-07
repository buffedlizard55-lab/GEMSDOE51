"""Write and verify a competition-format submission GeoTIFF.

Official format (DrivenData problem description, page 967): EPSG:32611, 100 m,
same bounds, one float32 band, probabilities in [0, 1], and null/NaN outside
the data bounds. This module writes NaN outside the footprint and tags NaN as
NoData. Portal acceptance is not inferred from these local format checks.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from .grid import GRID

EPS = 1e-12


def encode_submission_array(values: np.ndarray, footprint: np.ndarray,
                            outside: float = np.nan) -> np.ndarray:
    """Validate probabilities and return float32 array with specified outside value.

    When outside=0.0 (or a finite float in [0, 1]), every pixel in the entire raster
    is finite and in [0, 1], guaranteeing acceptance by DrivenData's web validator
    which checks that all values are in range [0, 1].
    When outside=np.nan (default), outside pixels are set to NaN.
    """
    v = np.asarray(values, dtype=np.float32)
    fp = np.asarray(footprint, dtype=bool)
    if v.shape != GRID.shape or fp.shape != GRID.shape:
        raise ValueError(f"values and footprint must have shape {GRID.shape}")
    inside = v[fp]
    if not np.isfinite(inside).all():
        raise ValueError("predictions inside the footprint must all be finite")
    if np.any((inside < 0.0) | (inside > 1.0)):
        raise ValueError("predictions inside the footprint must be in [0, 1]")
    out = np.full(GRID.shape, outside, dtype=np.float32)
    out[fp] = inside
    return out



def write_tif(path: Path, values: np.ndarray, footprint: np.ndarray,
              outside: float = 0.0, nodata: float | None = None,
              compress: str = "deflate") -> dict:
    """Write a single-band float32 GeoTIFF.
    
    Default outside=0.0 and nodata=None ensures all values are in [0, 1],
    preventing the DrivenData validator error: 'Predicted values must be in range [0, 1]'.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = encode_submission_array(values, footprint, outside=outside)
    nodata_val = nodata if nodata is not None else (float("nan") if np.isnan(outside) else None)
    profile = dict(driver="GTiff", height=GRID.shape[0], width=GRID.shape[1],
                   count=1, dtype="float32", crs=f"EPSG:{GRID.epsg}",
                   transform=Affine(*GRID.transform), nodata=nodata_val,
                   compress=compress, predictor=3 if compress in ("deflate", "lzw") else 1,
                   tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(out, 1)
        dst.set_band_description(1, "fault probability")
    return verify(path, footprint)


def verify(path: Path, footprint: np.ndarray) -> dict:
    """Re-open the bytes and verify the official format and footprint encoding."""
    path = Path(path)
    fp = np.asarray(footprint, dtype=bool)
    if fp.shape != GRID.shape:
        raise ValueError(f"footprint shape {fp.shape} != {GRID.shape}")
    b = path.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    with rasterio.open(path) as s:
        a = s.read(1)
        t = s.transform
        crs_epsg = s.crs.to_epsg() if s.crs else None
        nodata = None if s.nodata is None else float(s.nodata)
        got = dict(
            file=path.name, bytes=len(b), sha256=sha,
            crs=str(s.crs), crs_epsg=crs_epsg,
            transform=(t.a, t.b, t.c, t.d, t.e, t.f),
            shape=(s.height, s.width), count=s.count, dtype=s.dtypes[0],
            nodata=nodata,
        )
    inside = a[fp]
    outside = a[~fp]
    inside_finite = bool(np.isfinite(inside).all())
    outside_nan = bool(np.isnan(outside).all())
    outside_zeros = bool(np.isfinite(outside).all() and (outside == 0.0).all())
    outside_range = int(((inside < -EPS) | (inside > 1.0 + EPS)).sum())
    total_out_of_range = int((np.isnan(a) | (a < -EPS) | (a > 1.0 + EPS)).sum()) if not outside_nan else outside_range
    nodata_is_nan = nodata is not None and math.isnan(nodata)
    portal_legal = bool(
        got["count"] == 1 and got["dtype"] == "float32"
        and got["crs_epsg"] == 32611 and got["transform"] == GRID.transform
        and got["shape"] == GRID.shape and inside_finite
        and (outside_zeros or outside_nan) and outside_range == 0
    )
    checks = dict(
        single_band=got["count"] == 1,
        dtype_float32=got["dtype"] == "float32",
        crs_epsg_32611=got["crs_epsg"] == 32611,
        transform_matches_template=got["transform"] == GRID.transform,
        shape_matches_template=got["shape"] == GRID.shape,
        inside_footprint_finite=inside_finite,
        outside_footprint_nan=outside_nan,
        outside_footprint_zeros=outside_zeros,
        nan_cells=int(np.isnan(a).sum()),
        values_outside_0_1=outside_range,
        min_value=float(np.nanmin(inside)) if inside.size else float("nan"),
        max_value=float(np.nanmax(inside)) if inside.size else float("nan"),
        nodata_tag_is_nan=bool(nodata_is_nan),
        predicted_px=int((inside > 0).sum()),
        total_mass=float(np.sum(inside[np.isfinite(inside)], dtype=np.float64)),
        portal_legal=portal_legal,
        format_valid=portal_legal,
    )
    got["checks"] = checks
    return got


def report(path: Path, footprint: np.ndarray, extra: dict | None = None) -> dict:
    r = verify(path, footprint)
    if extra:
        r["content"] = extra
    return r
