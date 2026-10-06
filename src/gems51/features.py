"""Feature stack for Stage B.

Sources (all hash-pinned, restored by scripts/fetch_data.py):
  * 19 official bands of `training_features.tif` (organizer download; band tags read from the file)
  * 12 lidar scarp-proxy bands  (external/lidar_scarp_features_u8.tif, uint8, 0-255, 0 = nodata)
  * 4 GeoDAWN radiometric bands (external/geodawn_rad_u8.tif: K, Th, U, TC)
  * 4 GeoDAWN extension bands   (external/geodawn_extensions_u8.tif: ThK, UK, UTh, TMI_up150)
  * 1 SGMC fault raster         (external/derived_sgmc_faults_100m_u8.tif, binary)

Derived transforms (computed here, documented in the site):
  * log_det_elev        difference of Gaussians of the detrended elevation (scarp sharpness)
  * ridge_det_elev      structure-tensor ridge-ness of detrended elevation (curvilinear edges)
  * edge_tc             gradient magnitude of the `tc` tilt-angle / curvature magnetic edge band
  * dist_sgmc           distance (px) to the SGMC fault raster

The stack is written ONE CHANNEL AT A TIME into a memory-mapped .npy file (43 x 3730 x 3292
float32 = 2.1 GB on disk) so that building it, sampling it for training and predicting from it
never require the whole tensor in RAM.  Honest note: this module used to build the stack in
memory and was OOM-killed in this sandbox at 43 channels; the memmap form is the fix.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, sobel

from . import grid
from .paths import GEODAWN_EXT, GEODAWN_RAD, LIDAR_SCARP, SGMC_FAULTS, WORK_DIR

#: 12 bands.  The first six names are read from the file's own band descriptions; bands 7-12
#: carry no description in the mirrored file, so they are carried as unlabelled placeholders and
#: flagged in registry/irregularities.json IR-51-10 rather than guessed at.
LIDAR_BAND_NAMES = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
                    "band07_unlabelled", "band08_unlabelled", "band09_unlabelled",
                    "band10_unlabelled", "band11_unlabelled", "band12_unlabelled")
RAD_BAND_NAMES = ("K", "Th", "U", "TC")
EXT_BAND_NAMES = ("ThK", "UK", "UTh", "TMI_up150")

FEATURE_NAMES: tuple[str, ...] = (
    *grid.BAND_NAMES,
    *(f"lidar_{n}" for n in LIDAR_BAND_NAMES),
    *(f"rad_{n}" for n in RAD_BAND_NAMES),
    *(f"ext_{n}" for n in EXT_BAND_NAMES),
    "sgmc", "log_det_elev", "ridge_det_elev", "edge_tc", "dist_sgmc",
)
N_CHANNELS = len(FEATURE_NAMES)
STACK_PATH = WORK_DIR / "feature_stack.npy"


def _u8(path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(band).astype(np.float32)
        nod = ds.nodata
    if nod is not None:
        a[a == nod] = np.nan
    return a


def _ridge_ness(x: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Structure-tensor ridge-ness: |lambda_max - lambda_min| of the smoothed Hessian."""
    xs = gaussian_filter(np.nan_to_num(x, nan=0.0).astype(np.float32), sigma)
    gx = sobel(xs, axis=1, mode="nearest")
    gy = sobel(xs, axis=0, mode="nearest")
    jxx = gaussian_filter(gx * gx, sigma)
    jyy = gaussian_filter(gy * gy, sigma)
    jxy = gaussian_filter(gx * gy, sigma)
    tr, det = jxx + jyy, jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    return np.abs(2.0 * disc).astype(np.float32)


def channel_generators() -> Iterator[tuple[str, object]]:
    """Yield (name, callable) lazily so only one channel is in RAM at a time."""
    for n in grid.BAND_NAMES:
        yield n, (lambda n=n: grid.read_band(n))
    for i, nm in enumerate(LIDAR_BAND_NAMES, start=1):
        yield f"lidar_{nm}", (lambda i=i: _u8(LIDAR_SCARP, i))
    for i, nm in enumerate(RAD_BAND_NAMES, start=1):
        yield f"rad_{nm}", (lambda i=i: _u8(GEODAWN_RAD, i))
    for i, nm in enumerate(EXT_BAND_NAMES, start=1):
        yield f"ext_{nm}", (lambda i=i: _u8(GEODAWN_EXT, i))
    yield "sgmc", (lambda: _u8(SGMC_FAULTS, 1).astype(np.float32))

    def _dog():
        det = np.nan_to_num(grid.read_band("det_elev"), nan=0.0).astype(np.float32)
        return (gaussian_filter(det, 1.0) - gaussian_filter(det, 4.0)).astype(np.float32)

    def _tc_edge():
        tc = np.nan_to_num(grid.read_band("tc"), nan=0.0).astype(np.float32)
        return np.hypot(sobel(tc, axis=1, mode="nearest"),
                        sobel(tc, axis=0, mode="nearest")).astype(np.float32)

    def _dist_sgmc():
        s = _u8(SGMC_FAULTS, 1)
        return distance_transform_edt(~(s > 0)).astype(np.float32)

    yield "log_det_elev", _dog
    yield "ridge_det_elev", (lambda: _ridge_ness(grid.read_band("det_elev")))
    yield "edge_tc", _tc_edge
    yield "dist_sgmc", _dist_sgmc


def build_stack(path=None, verbose: bool = True) -> str:
    path = path or STACK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                   shape=(N_CHANNELS, *grid.SHAPE))
    names = []
    for k, (name, fn) in enumerate(channel_generators()):
        arr = fn()
        mm[k] = arr
        names.append(name)
        del arr
        if verbose and (k % 10 == 0 or k == N_CHANNELS - 1):
            print(f"[features] {k + 1}/{N_CHANNELS} {name}", flush=True)
    mm.flush()
    del mm
    if tuple(names) != FEATURE_NAMES:
        missing = set(FEATURE_NAMES) ^ set(names)
        raise AssertionError(f"channel/name mismatch ({len(names)} vs {N_CHANNELS}); "
                             f"symmetric difference: {sorted(missing)[:6]}")
    return str(path)


def load_or_build(verbose: bool = True):
    """Return a read-only memmap of the stack, building it if missing or stale."""
    if STACK_PATH.exists():
        try:
            mm = np.load(STACK_PATH, mmap_mode="r")
            if mm.shape[0] == N_CHANNELS and mm.shape[1:] == grid.SHAPE:
                return mm
        except ValueError:
            pass
    build_stack(verbose=verbose)
    return np.load(STACK_PATH, mmap_mode="r")
