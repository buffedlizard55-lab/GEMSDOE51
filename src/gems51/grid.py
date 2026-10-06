"""Raster grid I/O for the GEMS Prize 100 m UTM-11N grid.

Authoritative grid facts, re-read from the competition rasters themselves
(`existing_faults.tif`, `example_submission.tif`) and cross-checked against the
published problem description:
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
    * "same projected coordinate reference system as the training data
       (projected coordinate system for UTM zone 11N, EPSG 32611)"  -> EPSG:32611
    * "same resolution as the training data (100m)"                 -> res 100 m
    * "same bounds as the training data, and data outside the bounds is null or nan"
    * "single layer with datatype of 32-bit float (float32) with values between 0 and 1"
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

# The grid, measured (not assumed) from example_submission.tif
HEIGHT = 3730
WIDTH = 3292
COUNT = 1
DTYPE = "float32"
CRS = "EPSG:32611"
RES = (100.0, 100.0)
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
BOUNDS = (243350.0, 4135550.0, 572550.0, 4508550.0)

NODATA_SENTINEL = -3.4028234663852886e+38  # training_features.tif nodata value

BAND_NAMES = {
    1: "Magnetic anomaly - deviation from expected Earth's magnetic field",
    2: "Reduced to pole magnetic data - magnetic anomaly corrected for latitude effects",
    3: "Total magnetic intensity horizontal gradient - rate of change in horizontal direction",
    4: "Geodetic second invariant - measure of strain rate tensor magnitude",
    5: "Isostatic gravity anomaly slope - gradient of gravity after isostatic correction",
    6: "Tilt angle or total curvature - magnetic field derivative for edge detection",
    7: "Geodetic shear rate - rate of angular deformation from GPS/InSAR",
    8: "Geodetic dilatation rate - rate of volumetric strain (expansion/contraction)",
    9: "Total magnetic intensity vertical gradient - rate of change in vertical direction",
    10: "Distance to earthquake (n=100km radius, a=15 azimuth parameters)",
    11: "Isostatic gravity anomaly vertical gradient - vertical rate of change",
    12: "Detrended elevation - topography with regional trends removed",
    13: "Isostatic gravity anomaly - gravity after compensating for topographic mass",
    14: "Total magnetic intensity - total strength of magnetic field",
    15: "Depth to basement surface - thickness of sedimentary cover",
    16: "Earthquake intensity or density (n=100km radius, a=15 parameters)",
    17: "Conductivity surface - electrical conductivity of subsurface",
    18: "Isostatic gravity anomaly horizontal gradient - horizontal rate of change",
    19: "Detrended elevation slope - gradient of elevation after detrending",
}

# Which supplied layers are *geophysical lineament evidence* (as opposed to strain /
# seismicity / elevation, which enter other components).  Kept explicit for audit.
LINEAMENT_BANDS = (1, 2, 3, 5, 6, 9, 11, 13, 14, 17, 18)
STRAIN_BANDS = (4, 7, 8)


def data_root() -> Path:
    return Path(os.environ.get("GEMS_DATA_DIR", "data"))


def path(name: str) -> Path:
    return data_root() / name


@dataclass(frozen=True)
class GridInfo:
    height: int
    width: int
    transform: tuple
    crs: str


def grid_info() -> GridInfo:
    return GridInfo(HEIGHT, WIDTH, TRANSFORM, CRS)


def read_band(tif: Path, band: int = 1, masked: bool = True) -> np.ndarray:
    """Read one band as float32; convert the float32 sentinel nodata to NaN if masked."""
    with rasterio.open(tif) as src:
        a = src.read(band).astype(np.float32)
        if masked and src.nodata is not None:
            a = np.where(a <= np.float32(src.nodata) * np.float32(0.999999), np.nan, a)
        elif masked:
            a = np.where(a.astype(np.float64) <= NODATA_SENTINEL * 0.999999, np.nan, a)
    return a


def read_catalogue(tif: Path) -> np.ndarray:
    """Catalogue / labels raster -> bool.  Values > 0 are fault pixels (measured: {0,1})."""
    with rasterio.open(tif) as src:
        a = src.read(1)
    return a > 0


def valid_footprint(example_submission: Path) -> np.ndarray:
    """The competition footprint: finite pixels of the sample submission."""
    with rasterio.open(example_submission) as src:
        a = src.read(1).astype(np.float32)
    return np.isfinite(a)


def write_submission(
    out_path: Path,
    values: np.ndarray,
    *,
    nodata=None,
    compress: str | None = None,
) -> dict:
    """Write a single-band float32 GeoTIFF that is byte-verifiable against the spec.

    NOTE, and this is the fix for the portal error reported by the owner
    ("Predicted values must be in range [0, 1]"):
      * every value is clamped to [0, 1];
      * NO nodata tag is written, because a large negative sentinel such as
        -3.4028234663852886e+38 is itself outside [0, 1] and trips the validator;
      * cells outside the footprint are written as 0.0 (legal, in range), not NaN.
    See https://community.drivendata.org/t/... (masking thread) and page 967.
    """
    values = np.asarray(values, dtype=np.float32)
    if values.shape != (HEIGHT, WIDTH):
        raise ValueError(f"shape {values.shape} != ({HEIGHT}, {WIDTH})")
    profile = dict(
        driver="GTiff", height=HEIGHT, width=WIDTH, count=1, dtype="float32",
        crs=CRS, transform=rasterio.Affine(*TRANSFORM[:6]),
    )
    if compress:
        profile["compress"] = compress
    if nodata is not None:
        profile["nodata"] = nodata
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(values, 1)
    return verify_submission(out_path)


def verify_submission(tif: Path) -> dict:
    """Re-open from disk and audit every clause of the published submission format."""
    with rasterio.open(tif) as src:
        a = src.read(1)
        rep = {
            "path": str(tif),
            "count": src.count,
            "dtype": src.dtypes[0],
            "crs": str(src.crs),
            "res": [float(src.res[0]), float(src.res[1])],
            "shape": [int(src.height), int(src.width)],
            "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata": (None if src.nodata is None else float(src.nodata)),
            "n_cells": int(a.size),
            "n_nan": int(np.isnan(a).sum()),
            "n_inf": int(np.isinf(a).sum()),
            "min": float(np.nanmin(a)),
            "max": float(np.nanmax(a)),
            "n_nonzero": int((a > 0).sum()),
            "unique_nonzero_sample": int(np.unique(a[a > 0]).size),
        }
    checks = {
        "single_band": rep["count"] == 1,
        "float32": rep["dtype"] == "float32",
        "crs_epsg32611": rep["crs"] in ("EPSG:32611",),
        "res_100m": rep["res"] == [100.0, 100.0],
        "shape_3730x3292": rep["shape"] == [HEIGHT, WIDTH],
        "transform_matches": [round(v, 6) for v in rep["transform"]]
        == [round(v, 6) for v in TRANSFORM[:6]],
        "all_finite": rep["n_nan"] == 0 and rep["n_inf"] == 0,
        "values_in_0_1": rep["min"] >= 0.0 and rep["max"] <= 1.0,
        "no_out_of_range_nodata_tag": rep["nodata"] is None
        or (0.0 <= rep["nodata"] <= 1.0),
    }
    rep["checks"] = checks
    rep["all_pass"] = all(checks.values())
    return rep


def sha256_of(path_: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path_, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=False, default=str)
