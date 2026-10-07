"""Feature stack construction for the GEMS fault-discovery detector.

Layer inventory
---------------
A. Competition ``training_features.tif`` (19 float32 bands, EPSG:32611, 100 m):
   the band names and descriptions below are read straight from the GeoTIFF's
   own band descriptions (see ``registry/prepared_manifest.json``), not guessed.

B. Owner-supplied external mirrors, all hash-pinned in ``registry/data_manifest.json``:
   ``external/lidar_scarp_features_u8.tif``  (12 bands, 1 m DEM derived)
   ``external/geodawn_rad_u8.tif``           (K, Th, U, TC)
   ``external/derived_sgmc_faults_100m_u8.tif`` (USGS SGMC faults rasterised)

C. Point observations from GDR submission 1391 (https://gdr.openei.org/submissions/1391):
   wells/springs and volcanic vents, clipped to the footprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .grid import GRID, SENTINEL, read_band

# ---- band order of data/raw/training_features.tif (1-based, from the file itself)
COMPETITION_BANDS = [
    ("mag_anom", "Magnetic anomaly - deviation from expected Earth's magnetic field"),
    ("rtp", "Reduced to pole magnetic data - magnetic anomaly corrected for latitude effects"),
    ("tmi_hg", "Total magnetic intensity horizontal gradient"),
    ("geod_2ndinv", "Geodetic second invariant - magnitude of the strain rate tensor"),
    ("iso_grav_anom_slope", "Isostatic gravity anomaly slope"),
    ("tc", "Tilt angle or total curvature - magnetic field derivative for edge detection"),
    ("geod_shearrate", "Geodetic shear rate - angular deformation rate from GPS/InSAR"),
    ("geod_dilaterate", "Geodetic dilatation rate - volumetric strain rate"),
    ("tmi_vg", "Total magnetic intensity vertical gradient"),
    ("deq_n100a15", "Distance to earthquake (n=100 km radius, a=15 deg azimuth)"),
    ("iso_grav_anom_vg", "Isostatic gravity anomaly vertical gradient"),
    ("det_elev", "Detrended elevation - topography with regional trends removed"),
    ("iso_grav_anom", "Isostatic gravity anomaly"),
    ("tmi", "Total magnetic intensity"),
    ("depth_to_base_surf", "Depth to basement surface - thickness of sedimentary cover"),
    ("ieq_n100a15", "Earthquake intensity or density (n=100 km radius, a=15 deg)"),
    ("cond_surf", "Conductivity surface - electrical conductivity of the subsurface"),
    ("iso_grav_anom_hg", "Isostatic gravity anomaly horizontal gradient"),
    ("det_elev_slope", "Detrended elevation slope"),
]

# ---- band order of data/raw/external/lidar_scarp_features_u8.tif
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]

# ---- band order of data/raw/external/geodawn_rad_u8.tif
RAD_BANDS = ["K", "Th", "U", "TC"]

GEODETIC = {"geod_2ndinv": 3, "geod_shearrate": 6, "geod_dilaterate": 7}  # 0-based index


@dataclass
class Stack:
    """A stack of aligned rasters.  ``data`` is (n, H, W) float32 with NaN = invalid."""
    names: list
    data: np.ndarray          # np.memmap or ndarray, float32, (n, H, W)
    footprint: np.ndarray     # bool (H, W)

    def __post_init__(self):
        assert self.data.shape[0] == len(self.names)
        assert self.data.shape[1:] == self.footprint.shape

    def index(self, name: str) -> int:
        return self.names.index(name)

    def get(self, name: str) -> np.ndarray:
        return self.data[self.index(name)]


def clean_band(arr: np.ndarray, nodata=None) -> np.ndarray:
    """float32 -> float32 with the competition sentinel and non-finite cells as NaN."""
    a = np.asarray(arr, dtype=np.float32)
    out = np.where(np.isfinite(a), a, np.nan).astype(np.float32)
    if nodata is not None and np.isfinite(nodata):
        out[out == np.float32(nodata)] = np.nan
    out[out <= SENTINEL / 2.0] = np.nan
    return out


def robust_standardise(a: np.ndarray, mask: np.ndarray, lo=2.0, hi=98.0) -> np.ndarray:
    """Median/IQR-ish standardisation computed only on ``mask``; NaN elsewhere."""
    v = a[mask & np.isfinite(a)]
    med = np.median(v)
    p_lo, p_hi = np.percentile(v, lo), np.percentile(v, hi)
    scale = max((p_hi - p_lo) / 2.0, 1e-9)
    out = (a - med) / scale
    out[~np.isfinite(out)] = np.nan
    return np.clip(out, -8.0, 8.0).astype(np.float32)


def rank_transform(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Empirical-CDF (rank) transform to [0, 1] computed on ``mask``.

    Rank transform is the right default for heavy-tailed geophysical layers:
    it is monotone, immune to outliers, and gives a tree/GBDT model a
    well-conditioned input without ever seeing the test-fold distribution.
    """
    from scipy.stats import rankdata

    out = np.full(a.shape, np.nan, dtype=np.float32)
    valid = mask & np.isfinite(a)
    v = a[valid]
    if v.size == 0:
        return out
    ranks = (rankdata(v, method="average") / v.size).astype(np.float32)
    out[valid] = ranks
    out[~mask] = np.nan
    return out



def load_competition_stack(raw: Path) -> tuple[list, np.ndarray, np.ndarray]:
    """Load the 19 competition bands; returns (names, (19,H,W) f32 with NaN, footprint)."""
    import rasterio
    path = raw / "training_features.tif"
    names, arrs = [], []
    with rasterio.open(path) as src:
        assert (src.height, src.width) == GRID.shape, "unexpected feature raster shape"
        descs = list(src.descriptions)
        for i in range(src.count):
            nm = COMPETITION_BANDS[i][0]
            if descs and descs[i]:
                nm = descs[i].split(" - ")[0].strip()
            names.append(nm)
            arrs.append(clean_band(src.read(i + 1), src.nodata))
    data = np.stack(arrs).astype(np.float32)
    footprint = np.isfinite(data).all(axis=0)
    return names, data, footprint
