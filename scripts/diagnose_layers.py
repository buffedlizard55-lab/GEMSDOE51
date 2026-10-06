#!/usr/bin/env python3
"""Diagnostic only: how much single-layer signal is there for catalogue faults?

This is NOT a score and NOT a validation: it is measured on the full grid with no
spatial blocking, so it is leak-contaminated by construction.  Its only purpose
is to rank layers for inclusion in the feature stack.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems51.grid import GRID  # noqa: E402

P = ROOT / "data" / "prepared"
foot = np.load(P / "footprint.npy")
cat = np.load(P / "catalogue.npy")
anal = np.load(P / "analysable.npy")


def auc(a, m):
    v = a[m]
    y = cat[m]
    if y.sum() < 50 or np.isfinite(v).sum() < 1000:
        return float("nan"), int(np.isfinite(v).sum())
    ok = np.isfinite(v)
    if ok.sum() < 1000:
        return float("nan"), int(ok.sum())
    return float(roc_auc_score(y[ok], v[ok])), int(ok.sum())


def main():
    rows = []
    names = [b[0] for b in __import__("gems51.features", fromlist=["x"]).COMPETITION_BANDS]
    mm = np.memmap(P / "comp_rank.dat", dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    for i, nm in enumerate(names):
        a, n = auc(mm[i], foot)
        rows.append(("comp", nm, a, n))
    del mm

    for tag, bn in [("lidar", ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
                               "downface_max", "upface_max", "cross_max", "relief", "coh100",
                               "strike", "valid"]),
                    ("rad", ["K", "Th", "U", "TC"]),
                    ("sgmc", ["sgmc_fault"])]:
        f = P / f"{tag}_raw.dat"
        if not f.exists():
            continue
        import rasterio
        with rasterio.open(ROOT / "data" / "raw" / "external" /
                           {"lidar": "lidar_scarp_features_u8.tif", "rad": "geodawn_rad_u8.tif",
                            "sgmc": "derived_sgmc_faults_100m_u8.tif"}[tag]) as s:
            nb = s.count
        mm = np.memmap(f, dtype=np.float32, mode="r", shape=(nb, *GRID.shape))
        for i in range(nb):
            a, n = auc(mm[i], foot)
            rows.append((tag, bn[i] if i < len(bn) else f"{tag}_{i}", a, n))
        del mm

    rows.sort(key=lambda r: (r[2] is None or np.isnan(r[2]), -(r[2] if r[2] == r[2] else 0)))
    print(f"{'stack':7s} {'layer':22s} {'AUC':>7s} {'n_valid':>10s}")
    for s_, nm, a, n in rows:
        print(f"{s_:7s} {nm:22s} {a:7.4f} {n:>10,}")
    (ROOT / "data" / "layer_auc.json").write_text(
        json.dumps([dict(stack=s_, layer=nm, auc=None if a != a else a, n=n) for s_, nm, a, n in rows],
                   indent=1))


if __name__ == "__main__":
    main()
