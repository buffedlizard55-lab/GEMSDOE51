#!/usr/bin/env python3
"""Emission-geometry design under the live-anchored truth model.

The model (``evidence/live_truth_model_fit.json``) draws N truth pixels with intensity
``exp(-d_ref / sigma)`` around the dotted-family parent support and scores an emission with the
official metric.  This script answers three design questions that the catalogue proxies cannot:

  1. **Mass.**  Given a support, what emitted mass maximises the modelled index?
  2. **Geometry.**  Is a dotted emission or a contiguous 1-px ribbon better at equal trace length?
  3. **Ceiling.**  What does a *leave-one-draw-out greedy max-coverage* emission score at the model's
     own optimum (an optimistic upper bound for anything that knows the truth model)?

Everything is a MODEL conditioned on owner-reported live anchors.  It is not a score.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/design_emission_geometry.py --draws 12
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fit_live_truth_model import ALPHA, BETA, RADIUS_PX, credit_field, dti_from_counts  # noqa: E402

REF_SIGMA = 1.85          # owner-fitted positional scatter (GEMSDOE32 truth_model_mc.json)
REF_N = 12691             # owner-fitted hidden truth size
CAND_MAX_DREF = 12.0      # truncate candidates where exp(-d/sigma) < 1.5e-3


def load_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=12)
    ap.add_argument("--sigma", type=float, default=REF_SIGMA)
    ap.add_argument("--n-truth", type=int, default=REF_N)
    ap.add_argument("--candidate", default="")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "emission_geometry_live_model.json"))
    a = ap.parse_args()

    footprint = np.load(ROOT / "data" / "prepared" / "footprint.npy")
    catalogue = np.load(ROOT / "data" / "prepared" / "catalogue.npy")
    ref = load_mask(ROOT / "data" / "refs" / "scored_h19_5.tif")
    dref = ndi.distance_transform_edt(~ref)

    cand = footprint & (dref <= CAND_MAX_DREF)
    w = np.exp(-dref / a.sigma)
    w[~cand] = 0.0
    p = (w / w.sum()).ravel()
    idx = np.flatnonzero(p > 0)
    print(f"candidate pixels {idx.size:,} (dref <= {CAND_MAX_DREF} px), "
          f"pixels carrying 90% of the mass: "
          f"{np.searchsorted(np.sort(p[idx])[::-1].cumsum(), 0.9) + 1:,}")

    rng = np.random.default_rng(4242)
    draws = []
    for _ in range(a.draws):
        flat = rng.choice(idx, size=a.n_truth, replace=False, p=p[idx])
        g = np.zeros(footprint.size, bool)
        g[flat] = True
        draws.append(g.reshape(footprint.shape))
    print(f"{len(draws)} truth draws of {a.n_truth:,} px")

    def score(support: np.ndarray, subset=None) -> float:
        c = credit_field(support)
        vals = []
        for g in (draws if subset is None else subset):
            vals.append(dti_from_counts(float(c[g].sum()),
                                        float((1.0 - credit_field(g)[support]).sum()),
                                        int(g.sum())))
        return float(np.mean(vals))

    d28 = load_mask(ROOT / "data" / "refs" / "scored_d28_unscored.tif") & ~catalogue
    ys, xs = np.nonzero(d28)
    res: dict = {"model": dict(sigma=a.sigma, n_truth=a.n_truth, draws=len(draws),
                               candidate_px=int(idx.size)),
                 "anchors": {"d2.8_dots": int(d28.sum()), "d2.8_modelled_dti": score(d28)}}
    print(f"anchor d2.8: {int(d28.sum())} px model_dti={res['anchors']['d2.8_modelled_dti']:.4f}")

    # ---- mass sweeps ------------------------------------------------------
    sweeps = {}
    for label, order in (("random", rng.permutation(len(ys))),
                         ("greedy_reference", np.argsort(dref[d28]))):
        rows = {}
        for frac in (0.10, 0.15, 0.25, 0.35, 0.50, 0.70, 1.00):
            n_keep = int(round(frac * len(ys)))
            sub = np.zeros_like(d28)
            sel = order[:n_keep]
            sub[ys[sel], xs[sel]] = True
            v = score(sub)
            rows[f"{frac:.2f}"] = dict(dots=n_keep, modelled_dti=v)
            print(f"  mass[{label}] frac={frac:.2f} dots={n_keep:6d} model_dti={v:.4f}", flush=True)
        sweeps[label] = rows
    res["mass_sweeps"] = sweeps

    # ---- geometry: dotted vs contiguous ribbon at equal trace length ------
    ribbon = ndi.binary_closing(d28, structure=np.ones((3, 3), bool)) & footprint & ~catalogue
    geom = {"dots_d2.8": dict(px=int(d28.sum()), modelled_dti=res["anchors"]["d2.8_modelled_dti"]),
            "ribbon_closed_d2.8": dict(px=int(ribbon.sum()), modelled_dti=score(ribbon))}
    # match mass: thin the ribbon back to the dotted mass, keeping its top-|d2.8| pixels by
    # proximity to the reference support (mass-matched comparison)
    ry, rx = np.nonzero(ribbon)
    take = np.argsort(dref[ribbon])[: int(d28.sum())]
    thin = np.zeros_like(ribbon)
    thin[ry[take], rx[take]] = True
    geom["ribbon_massmatched"] = dict(px=int(thin.sum()), modelled_dti=score(thin))
    for k, v in geom.items():
        print(f"  geometry {k:22s} px={v['px']:6d} model_dti={v['modelled_dti']:.4f}")
    res["geometry"] = geom

    # ---- ceiling: leave-one-draw-out greedy max-coverage ------------------
    # rank candidate pixels by mean credit over the OTHER draws, then take the top-M,
    # sweeping M: an optimistic "what if the emitter ranked positions by the truth model"
    ceil_rows = {}
    for frac in (0.10, 0.20, 0.35, 0.50):
        m = int(round(frac * a.n_truth))
        vals = []
        for i, g in enumerate(draws):
            others = [h for j, h in enumerate(draws) if j != i]
            acc = np.zeros(footprint.shape, np.float32)
            for h in others:
                acc += credit_field(h)
            acc[~footprint] = -1
            flat = np.argpartition(acc.ravel(), -m)[-m:]
            s = np.zeros(footprint.size, bool)
            s[flat] = True
            s = s.reshape(footprint.shape)
            vals.append(dti_from_counts(float(credit_field(s)[g].sum()),
                                        float((1.0 - credit_field(g)[s]).sum()), int(g.sum())))
        ceil_rows[f"{frac:.2f}"] = dict(dots=m, modelled_dti=float(np.mean(vals)))
        print(f"  ceiling greedy-LOO frac/N={frac:.2f} dots={m:6d} model_dti={np.mean(vals):.4f}",
              flush=True)
    res["ceiling_greedy_loo"] = ceil_rows

    # ---- optional: an independently built candidate ------------------------
    if a.candidate:
        cp = Path(a.candidate)
        cm = load_mask(cp)
        cm = cm & ~catalogue
        res["candidate"] = dict(path=str(cp), px=int(cm.sum()), modelled_dti=score(cm),
                                median_dcat_px=float(np.median(
                                    ndi.distance_transform_edt(~catalogue)[cm])) if cm.any() else None)
        print(f"  candidate {cp.name}: px={int(cm.sum())} "
              f"model_dti={res['candidate']['modelled_dti']:.4f}")

    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
