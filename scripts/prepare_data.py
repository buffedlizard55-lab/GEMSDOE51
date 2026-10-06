#!/usr/bin/env python3
"""Prepare the competition rasters into analysis-ready, memory-mapped arrays.

Inputs  : data/raw/{training_features.tif, labels.tif, sample_submission.tif}
          data/raw/external/*.tif            (owner-supplied, hash-pinned mirrors)
Outputs : data/prepared/*.dat / *.npy + data/prepared/prepared_manifest.json

Everything is written as float32 / bool and NaN-coded so that downstream code
never has to remember the competition's -3.4028234663852886e+38 sentinel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.features import (  # noqa: E402
    clean_band, load_competition_stack, rank_transform, robust_standardise,
    LIDAR_BANDS, RAD_BANDS,
)
from gems51.grid import GRID, SENTINEL, read_band  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "prepared"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    # ---------------------------------------------------------------- template grid
    with rasterio.open(RAW / "sample_submission.tif") as s:
        ss = s.read(1)
        GRID.assert_matches(dict(transform=s.transform, height=s.height, width=s.width, crs=s.crs))
    footprint = np.isfinite(ss)
    report["footprint_pixels"] = int(footprint.sum())
    report["grid"] = dict(shape=list(GRID.shape), transform=list(GRID.transform), epsg=GRID.epsg)

    # ---------------------------------------------------------------- labels
    labels = read_band(RAW / "labels.tif").astype(np.int8)
    catalogue = (labels == 1) & footprint
    report["catalogue_pixels"] = int(catalogue.sum())
    report["labels_outside_footprint_are_minus1"] = bool(
        ((labels == -1) == ~footprint).all() and not (labels[footprint] == -1).any())
    report["sample_submission_equals_labels_in_footprint"] = bool(
        np.array_equal(ss[footprint].astype(np.int8), labels[footprint]))
    np.save(OUT / "footprint.npy", footprint)
    np.save(OUT / "catalogue.npy", catalogue)

    # ---------------------------------------------------------------- 19 competition bands
    names, data, all_finite = load_competition_stack(RAW)
    H, W = GRID.shape
    n = len(names)
    mm = np.memmap(OUT / "comp_rank.dat", dtype=np.float32, mode="w+", shape=(n, H, W))
    mz = np.memmap(OUT / "comp_z.dat", dtype=np.float32, mode="w+", shape=(n, H, W))
    band_report = []
    for i, nm in enumerate(names):
        a = data[i]
        valid = np.isfinite(a) & footprint
        mm[i] = rank_transform(a, valid)
        mz[i] = robust_standardise(a, valid)
        v = a[valid]
        band_report.append(dict(index=i + 1, name=nm, finite_in_footprint=int(valid.sum()),
                                sentinel_in_footprint=int(footprint.sum() - valid.sum()),
                                min=float(v.min()), p05=float(np.percentile(v, 5)),
                                median=float(np.median(v)), p95=float(np.percentile(v, 95)),
                                max=float(v.max())))
        print(f"  band {i + 1:2d} {nm:22s} finite={valid.sum():>9,}  "
              f"[{v.min():.4g}, {v.max():.4g}]", flush=True)
    mm.flush(); mz.flush()
    report["competition_bands"] = band_report
    # a pixel is analysable only if every band is finite there
    analysable = footprint & all_finite
    np.save(OUT / "analysable.npy", analysable)
    report["analysable_pixels"] = int(analysable.sum())
    report["footprint_pixels_missing_any_band"] = int(footprint.sum() - analysable.sum())
    del data, mm, mz

    # ---------------------------------------------------------------- external stacks
    for rel, band_names, tag in [
        ("external/lidar_scarp_features_u8.tif", LIDAR_BANDS, "lidar"),
        ("external/geodawn_rad_u8.tif", RAD_BANDS, "rad"),
        ("external/derived_sgmc_faults_100m_u8.tif", ["sgmc_fault"], "sgmc"),
    ]:
        p = RAW / rel
        if not p.exists():
            print(f"  skip {rel} (absent)")
            continue
        with rasterio.open(p) as src:
            arrs = [clean_band(src.read(i + 1), src.nodata) for i in range(src.count)]
        arr = np.stack(arrs).astype(np.float32)
        names_e = band_names[:arr.shape[0]]
        out = np.memmap(OUT / f"{tag}_raw.dat", dtype=np.float32, mode="w+", shape=arr.shape)
        out[:] = arr
        out.flush()
        report[f"{tag}_bands"] = [
            dict(name=nm, finite=int(np.isfinite(arr[i] & footprint).sum() if False
                                     else (np.isfinite(arr[i]) & footprint).sum()))
            for i, nm in enumerate(names_e)]
        print(f"  external {tag}: {arr.shape} -> {OUT}/{tag}_raw.dat", flush=True)
        del arr, out

    (OUT / "prepared_manifest.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "competition_bands"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
