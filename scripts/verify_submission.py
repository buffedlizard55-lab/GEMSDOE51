#!/usr/bin/env python3
"""Independent re-read of a written submission GeoTIFF, in a fresh process.

Deliberately does NOT import gems51.submission.verify -- the point is to check the
bytes with a second, independent code path so a bug in the writer cannot hide
behind a bug in the checker.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "prepared"
EXPECT = dict(shape=(3730, 3292), epsg=32611,
              transform=(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0))


def main(path: str) -> int:
    p = Path(path)
    b = p.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    with rasterio.open(p) as s:
        a = s.read(1)
        t = s.transform
        prof = dict(count=s.count, dtype=s.dtypes[0], epsg=s.crs.to_epsg(),
                    nodata=s.nodata, shape=(s.height, s.width),
                    transform=(t.a, t.b, t.c, t.d, t.e, t.f))
    checks = {
        "sha256": sha,
        "single_band": prof["count"] == 1,
        "float32": prof["dtype"] == "float32",
        "epsg_32611": prof["epsg"] == 32611,
        "shape_3730x3292": prof["shape"] == EXPECT["shape"],
        "transform_matches": prof["transform"] == EXPECT["transform"],
        "nodata_tag_none": prof["nodata"] is None,
        "all_finite": bool(np.isfinite(a).all()),
        "min_ge_0": bool(a.min() >= 0.0),
        "max_le_1": bool(a.max() <= 1.0),
        "n_cells": int(a.size),
        "positive_px": int((a > 0).sum()),
        "total_mass": float(a.sum()),
    }
    foot = np.load(P / "footprint.npy")
    cat = np.load(P / "catalogue.npy")
    sup = a > 0
    d = ndi.distance_transform_edt(~cat)
    checks.update(
        all_supported_inside_footprint=bool((sup & ~foot).sum() == 0),
        min_distance_to_catalogue_px=float(d[sup].min()) if sup.any() else None,
        frac_supported_within_2px_of_catalogue=float((d[sup] <= 2.0).mean()) if sup.any() else None,
        outside_footprint_all_zero=bool((a[~foot] == 0).all()),
    )
    # 8-connectivity structure of the support
    lab, n = ndi.label(sup, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())[1:]
    checks["n_connected_components"] = int(n)
    checks["frac_singleton_dots"] = float((sizes == 1).mean()) if n else None
    checks["portal_legal"] = all([checks["single_band"], checks["float32"], checks["epsg_32611"],
                                  checks["shape_3730x3292"], checks["transform_matches"],
                                  checks["min_ge_0"], checks["max_le_1"]])
    print(json.dumps(checks, indent=1))
    out = ROOT / "data" / f"independent_checks_{p.stem}.json"
    out.write_text(json.dumps(checks, indent=1))
    print("wrote", out)
    return 0 if checks["portal_legal"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
