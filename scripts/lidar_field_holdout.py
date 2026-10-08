#!/usr/bin/env python3
"""Candidate H51-LIDAR: morphology-only emission, evaluated on both instruments at once.

Why this candidate exists
-------------------------
``scripts/screen_layers_offcatalogue.py`` and ``scripts/screen_lidar_family.py`` measured every layer
of the prepared stack against two instruments that are *independent of the organizers' hidden labels*:

* **S** - USGS SGMC state-map faults that are absent from the competition catalogue (>2 px away).
  The sibling's live-calibrated version of this instrument is the best ranker of live scores measured
  in this project (Spearman +0.537 over 12 live-scored artifacts).
* **L** - 1-m-DEM scarp-crest pixels (>p99 upface/positive-Laplacian) further than 2 px from the
  catalogue.

Result of that screen: the competition's ``comp_*`` feature bands are at chance on S
(top-12,691 DTI 0.001-0.016 vs. random control 0.0270+-0.0010), while two of the morphology layers
built in this repository - the along-strike anisotropy of 1-m lidar relief (``lid_relief_s15_lin``)
and the magnetic along-strike anisotropy (``tmi_s15_lin``) - reach 0.078 and 0.066.  The ranking is
mass-free (AUC) as well: ``lid_relief`` ranks SGMC-held-out faults at AUC 0.778.

This script asks the next question: does a *pure morphology* emission beat the incumbent when scored
on the repository's exact six-fold blocked proxy (the same folds, buffer, exclusion radius and
ratio used for the frozen H-H/H-D benchmark 0.285340602656319), and simultaneously on S and L?

Nothing here is fitted, so there is no train/test split inside the emission: the same field is used
in every fold and only the scoring domain changes.  That makes the proxy a test of *transfer to
unmapped blocks*, not of parameter fitting.

Usage
    PYTHONPATH=src .venv/bin/python scripts/lidar_field_holdout.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.emission import nms_dots, rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape
RATIO = 3.47
NMS_RADIUS = 2.4
EXCL_RADIUS = 2.0
MASSES = (8000, 16000, 32000, 44000)
FIELDS = ("lid_relief_s15_lin", "tmi_s15_lin", "lid_lapneg_max", "lid_step_max",
          "comp_det_elev_slope", "random")


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    o = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[mask] = (o / max(1, v.size - 1)).astype(np.float32)
    return out


def main() -> int:
    t0 = time.time()
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r", shape=(len(names), H, W))

    def get(nm):
        return np.asarray(mm[names.index(nm)], np.float32)

    rng = np.random.default_rng(5)
    raw = {f: get(f) for f in FIELDS if f != "random"}
    raw["random"] = rng.random((H, W)).astype(np.float32)

    # rank-normalise every field over the whole footprint (proxy protocol needs a global field)
    fields = {k: rank01(np.where(np.isfinite(v) & footprint, v, np.nan), footprint & np.isfinite(v))
              for k, v in raw.items()}
    # two morphology combinations on the same 0-1 scale
    fields["lin_relief+tmi"] = ((fields["lid_relief_s15_lin"] + fields["tmi_s15_lin"]) / 2).astype(np.float32)
    fields["lin_relief+lapneg+step"] = ((fields["lid_relief_s15_lin"] + fields["lid_lapneg_max"]
                                         + fields["lid_step_max"]) / 3).astype(np.float32)

    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3, min_truth=500)
    print(f"[folds] {len(folds)} : {[f.n_truth for f in folds]}", flush=True)

    out = {"schema_version": 1,
           "protocol": dict(ratio=RATIO, nms_radius=NMS_RADIUS, excl_radius=EXCL_RADIUS,
                            buffer_px=12, grid=3, min_truth=500, folds=len(folds),
                            comparator="HH-HD blend STE mean 0.285340602656319 (6 folds)",
                            frozen_per_fold=[0.28358474213082796, 0.27178387428750844,
                                             0.29027025890966246, 0.24335930706370568,
                                             0.30504916677291494, 0.3179962667732945]),
           "proxy": {}, "instruments": {}}

    # ---------------- six-fold blocked proxy (exact run_experiments protocol) --
    for fname, fld in fields.items():
        per = []
        for fold in folds:
            in_block = fold.block & footprint
            excl = ndi.distance_transform_edt(~fold.known) <= EXCL_RADIUS
            k = int(round(RATIO * fold.n_truth))
            ys, xs = nms_dots(fld, k, radius=NMS_RADIUS, exclude=excl | ~in_block, valid=footprint)
            r = dti_binary(rasterise(ys, xs) > 0, fold.truth, valid=footprint & fold.block,
                           known=fold.known)
            per.append(dict(fold=fold.index, n_truth=fold.n_truth, px=int(r["mass"]),
                            dti=float(r["dti"]), coverage=float(r["coverage"])))
        m = float(np.mean([p["dti"] for p in per]))
        out["proxy"][fname] = dict(mean=m, per_fold=per)
        print(f"[proxy] {fname:28s} mean={m:.6f} folds=" +
              " ".join(f"{p['dti']:.4f}" for p in per), flush=True)

    # ---------------- instrument S / L at matched mass ------------------------
    dcat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    off2 = footprint & (dcat > 2.0)
    sgmc = get("sgmc_fault") > 0.5
    up, lp = get("lid_upface_max"), get("lid_lappos_max")
    fin = np.isfinite(up) & np.isfinite(lp)
    thr = np.percentile(up[footprint & fin], 99.0)
    truth_s, truth_l = sgmc & off2, fin & (up >= thr) & (lp > 0) & off2
    allowed = off2.copy()
    for fname in ("lid_relief_s15_lin", "lin_relief+tmi", "lin_relief+lapneg+step", "random"):
        rec = {}
        for mass in MASSES:
            ys, xs = nms_dots(fields[fname], mass, radius=NMS_RADIUS, exclude=~allowed,
                              valid=footprint)
            sel = rasterise(ys, xs) > 0
            s_ = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
            l_ = dti_binary(sel, truth_l, valid=footprint, known=catalogue)
            rec[str(mass)] = dict(S=float(s_["dti"]), L=float(l_["dti"]),
                                  S_cov=float(s_["coverage"]), L_cov=float(l_["coverage"]),
                                  px=int(sel.sum()))
        out["instruments"][fname] = rec
        print(f"[instr] {fname:28s} " + " | ".join(
            f"{m}: S={r['S']:.4f} L={r['L']:.4f} S_cov={r['S_cov']:.3f}" for m, r in rec.items()),
            flush=True)

    Path(ROOT / "evidence" / "lidar_field_holdout.json").write_text(json.dumps(out, indent=1))
    print(f"wrote evidence/lidar_field_holdout.json ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
