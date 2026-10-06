"""Grid handling for the competition raster (EPSG:32611, 100 m, 3730 x 3292)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import rasterio

TEMPLATE_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
TEMPLATE_SHAPE = (3730, 3292)
TEMPLATE_EPSG = 32611
SENTINEL = -3.4028234663852886e+38


@dataclass(frozen=True)
class Grid:
    height: int = TEMPLATE_SHAPE[0]
    width: int = TEMPLATE_SHAPE[1]
    transform: tuple = TEMPLATE_TRANSFORM
    epsg: int = TEMPLATE_EPSG

    @property
    def shape(self):
        return (self.height, self.width)

    def assert_matches(self, profile: dict) -> None:
        t = profile.get("transform")
        got = (t.a, t.b, t.c, t.d, t.e, t.f)
        assert (self.height, self.width) == (profile["height"], profile["width"]), "shape mismatch"
        assert got == self.transform, f"geotransform mismatch: {got} != {self.transform}"
        crs = profile.get("crs")
        assert crs is not None and crs.to_epsg() == self.epsg, f"CRS mismatch: {crs}"


GRID = Grid()


def read_band(path, band=1) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def read_profile(path) -> dict:
    with rasterio.open(path) as src:
        return dict(transform=src.transform, height=src.height, width=src.width,
                    crs=src.crs, count=src.count, dtype=src.dtypes[0], nodata=src.nodata)


def open_memmap(path: Path, shape, dtype=np.float32, mode="r+"):
    return np.memmap(path, dtype=dtype, mode=mode, shape=shape)


def create_memmap(path: Path, shape, dtype=np.float32) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(path, dtype=dtype, mode="w+", shape=shape)
    mm.flush()
    return mm


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str))
