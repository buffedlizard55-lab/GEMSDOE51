#!/usr/bin/env python3
"""Build the one frozen K2-08 static feature group, row-chunked for low RAM."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.k2_features import average_tie_rank01, conditioned_ribbon_features, normalized_gradient  # noqa: E402

RAW = ROOT / "data" / "raw" / "training_features.tif"
P = ROOT / "data" / "prepared"
SCALES = (2.0, 5.0)
FEATURE_NAMES = [
    "k2_cond_cross_rank_s20", "k2_cond_sign_persist_s20",
    "k2_cond_cross_rank_s50", "k2_cond_sign_persist_s50",
]
CHUNK_ROWS = 128
HALO = 36


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _band_indexes(src):
    descs = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
    if len(descs) != len(set(descs)):
        raise ValueError("training feature raster contains missing or duplicate descriptions")
    indexes = {}
    for name in ("depth_to_base_surf", "cond_surf"):
        if descs.count(name) != 1:
            raise ValueError(f"expected exactly one {name!r} band; got {descs.count(name)}")
        indexes[name] = descs.index(name) + 1
    return indexes


def _read_window(src, band: int, r0: int, r1: int):
    a = src.read(band, window=Window(0, r0, GRID.width, r1 - r0)).astype(np.float32)
    a[~np.isfinite(a) | (a <= -1e38)] = np.nan
    return a


def _edge_threshold(src, band, footprint, sigma, chunk_rows=CHUNK_ROWS, halo=HALO):
    """Exact q75 over finite-footprint gradient magnitudes via a temporary memmap."""
    scratch = P / f".k2_gradmag_s{int(sigma*10):02d}.dat"
    mag_mm = np.memmap(scratch, dtype=np.float32, mode="w+", shape=GRID.shape)
    mag_mm[:] = np.nan
    h, w = GRID.shape
    for start in range(0, h, chunk_rows):
        stop = min(start + chunk_rows, h)
        a0, a1 = max(0, start - halo), min(h, stop + halo)
        base = _read_window(src, band, a0, a1)
        valid = footprint[a0:a1] & np.isfinite(base)
        gx, gy = normalized_gradient(base, valid, sigma)
        mag = np.hypot(gx, gy)
        c0, c1 = start - a0, stop - a0
        mag_mm[start:stop] = mag[c0:c1]
        if start == 0 or stop == h or start // chunk_rows % 8 == 0:
            print(f"  q75 scale {sigma:g}: gradient rows {start}:{stop}", flush=True)
    mag_mm.flush()
    good = footprint & np.isfinite(mag_mm)
    threshold = float(np.nanpercentile(mag_mm[good], 75.0)) if good.any() else 0.0
    n_good = int(good.sum())
    del mag_mm
    scratch.unlink(missing_ok=True)
    return threshold, n_good


def main() -> int:
    P.mkdir(parents=True, exist_ok=True)
    footprint = np.load(P / "footprint.npy").astype(bool)
    if footprint.shape != GRID.shape:
        raise SystemExit("prepared footprint does not match the fixed competition grid")
    out_path = P / "arm_k2.dat"
    mm = np.memmap(out_path, dtype=np.float32, mode="w+",
                   shape=(len(FEATURE_NAMES), *GRID.shape))
    mm[:] = np.nan
    metadata = {
        "candidate_id": "GEMSDOE51-K2-08-conductive-ribbon",
        "preregistration": "registry/preregistration_k2_stage1_20261008.json",
        "source_raster": str(RAW.relative_to(ROOT)),
        "source_sha256": _sha256(RAW),
        "feature_names": FEATURE_NAMES,
        "sigma_pixels": list(SCALES),
        "cross_halfwidth_pixels": [1.5 * s for s in SCALES],
        "along_offsets_pixels": [-5.0, -2.5, 0.0, 2.5, 5.0],
        "edge_quantile": 75.0,
        "edge_thresholds_by_sigma": {},
        "footprint_pixels": int(footprint.sum()),
        "rank_scope": "average-tie empirical ranks among the retained q75 basement-edge centres; off-edge cells are zero; invalid sample cells are NaN",
        "chunk_rows": CHUNK_ROWS,
        "halo_rows": HALO,
    }
    t0 = time.time()
    with rasterio.open(RAW) as src:
        GRID.assert_matches(dict(transform=src.transform, height=src.height,
                                 width=src.width, crs=src.crs))
        indexes = _band_indexes(src)
        metadata["band_indexes"] = indexes
        metadata["band_descriptions"] = {
            "basement": src.descriptions[indexes["depth_to_base_surf"] - 1],
            "conductivity": src.descriptions[indexes["cond_surf"] - 1],
        }

        for scale_index, sigma in enumerate(SCALES):
            threshold, n_gradient = _edge_threshold(
                src, indexes["depth_to_base_surf"], footprint, sigma
            )
            metadata["edge_thresholds_by_sigma"][str(sigma)] = {
                "q75": threshold,
                "gradient_sample_scope": "exact finite-footprint pixels",
                "finite_gradient_pixels": n_gradient,
            }
            edge_mask = np.zeros(GRID.shape, dtype=bool)
            raw_feature_index = 2 * scale_index
            persistence_index = raw_feature_index + 1
            h, w = GRID.shape
            for start in range(0, h, CHUNK_ROWS):
                stop = min(start + CHUNK_ROWS, h)
                a0, a1 = max(0, start - HALO), min(h, stop + HALO)
                base = _read_window(src, indexes["depth_to_base_surf"], a0, a1)
                cond = _read_window(src, indexes["cond_surf"], a0, a1)
                valid = footprint[a0:a1] & np.isfinite(base) & np.isfinite(cond)
                feat = conditioned_ribbon_features(
                    base, cond, valid, sigma=sigma, edge_threshold=threshold,
                    along_offsets=(-5.0, -2.5, 0.0, 2.5, 5.0),
                    cross_half_width=1.5 * sigma,
                )
                c0, c1 = start - a0, stop - a0
                mm[raw_feature_index, start:stop] = feat["contrast"][c0:c1]
                mm[persistence_index, start:stop] = feat["persistence"][c0:c1]
                edge_mask[start:stop] = feat["edge_mask"][c0:c1]
                if start == 0 or stop == h or start // CHUNK_ROWS % 8 == 0:
                    print(f"  K2 scale {sigma:g}: feature rows {start}:{stop}", flush=True)

            contrast_row = mm[raw_feature_index]
            selected = footprint & edge_mask & np.isfinite(contrast_row)
            rank_missing = ~np.isfinite(contrast_row)
            contrast_rank = average_tie_rank01(contrast_row, selected)
            # Rank only complete edge contrasts, but preserve every original NaN
            # so missing support can never masquerade as an off-edge zero.
            contrast_rank[rank_missing] = np.nan
            mm[raw_feature_index] = contrast_rank
            edge_finite = selected
            metadata["edge_thresholds_by_sigma"][str(sigma)].update(
                retained_edge_centres=int(edge_mask.sum()),
                retained_edge_centres_with_complete_contrast=int(edge_finite.sum()),
                contrast_rank_min=float(np.nanmin(contrast_rank[edge_finite])) if edge_finite.any() else None,
                contrast_rank_max=float(np.nanmax(contrast_rank[edge_finite])) if edge_finite.any() else None,
                persistence_median=float(np.nanmedian(mm[persistence_index][edge_finite])) if edge_finite.any() else None,
            )
            del edge_mask, contrast_row, selected, contrast_rank
            mm.flush()

    for index, name in enumerate(FEATURE_NAMES):
        valid = np.isfinite(mm[index])
        metadata.setdefault("feature_valid_pixels", {})[name] = int(valid.sum())
        if np.any(np.isinf(mm[index, footprint])):
            raise RuntimeError(f"{name} contains infinity")
        if name.startswith("k2_cond_sign_persist"):
            vals = mm[index, footprint & np.isfinite(mm[index])]
            if vals.size and ((vals < -1e-6).any() or (vals > 1.0 + 1e-6).any()):
                raise RuntimeError(f"{name} escaped [0,1]")
    mm.flush()
    del mm
    metadata["grid"] = dict(
        shape=list(GRID.shape), epsg=int(GRID.epsg),
        transform=list(GRID.transform), pixel_size_m=100.0,
    )
    metadata["feature_store"] = dict(
        path=str(out_path.relative_to(ROOT)), dtype="float32",
        shape=[len(FEATURE_NAMES), *GRID.shape],
        bytes=int(out_path.stat().st_size), sha256=_sha256(out_path),
    )
    (P / "arm_k2_names.json").write_text(json.dumps(FEATURE_NAMES, indent=1) + "\n")
    (P / "arm_k2_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"features": FEATURE_NAMES,
                      "edge_thresholds": metadata["edge_thresholds_by_sigma"],
                      "output": str(out_path),
                      "seconds": round(time.time() - t0, 2)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
