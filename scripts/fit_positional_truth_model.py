#!/usr/bin/env python3
"""Positional-error truth model, fitted to live-scored anchors, then used for emission design.

Model
-----
The hidden expert-mapped faults are modelled as the visible-ish structural network plus a
*positional error*: N truth pixels are placed by drawing an anchor point uniformly from a reference
support and displacing it by an isotropic 2-D Gaussian of standard deviation ``sigma_px`` (in pixels,
100 m each).  Points that fall outside the footprint or on the published catalogue are rejected,
because the organizer removes known-fault pixels from the scored domain.

This is the "positional error" form of the owner's ``truth_model_mc`` description.  A pure
area-weighted ``exp(-d/sigma)`` sampler was tried first and rejected: over a 2-D area its mean offset
is ``2*sigma`` px, which is wide enough that added mass keeps raising the modelled index and the model
then contradicts the live board's thinning gradient (121,131 px -> 0.1922 vs 44,090 px -> 0.2600).

Validation target (owner-reported live scores, not organizer receipts):
    H19-5 121,131 px 0.1922 | d1.5 60,069 px 0.2477 | d2.8 44,090 px 0.2600

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/fit_positional_truth_model.py --draws 16
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

from fit_live_truth_model import (ALPHA, BETA, LIVE, RADIUS_PX, credit_field,  # noqa: E402
                                  dti_from_counts, spearman)

FAMILY = ["scored_h19_5", "scored_d15_scored", "scored_d28_unscored"]


def load_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=16)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "positional_truth_model.json"))
    a = ap.parse_args()

    footprint = np.load(ROOT / "data" / "prepared" / "footprint.npy")
    catalogue = np.load(ROOT / "data" / "prepared" / "catalogue.npy")
    H, W = footprint.shape

    ref = load_mask(ROOT / "data" / "refs" / "scored_h19_5.tif")
    ref_idx = np.argwhere(ref)                      # anchors: the 121,131-px dotted network
    supports = {k: (load_mask(ROOT / "data" / "refs" / f"{k}.tif") & ~catalogue) for k in LIVE}
    credits = {k: credit_field(m) for k, m in supports.items()}

    # B=1 / B=2 reconstruction on d2.8 (documented owner recipe: drop dots within B px of catalogue)
    dcat = ndi.distance_transform_edt(~catalogue)
    d28 = supports["scored_d28_unscored"]
    for b in (1, 2):
        m = d28 & (dcat > b)
        supports[f"B{b}_recon"] = m
        credits[f"B{b}_recon"] = credit_field(m)
    LIVE_B = {"B1_recon": 0.2708, "B2_recon": 0.2778}   # owner-reported (B=1) / user-reported (B=2)

    rng = np.random.default_rng(20261007)

    def draw_truth(n_truth: int, sigma: float) -> np.ndarray:
        for _ in range(200):
            sel = rng.integers(0, len(ref_idx), size=n_truth)
            dy = np.round(rng.normal(0.0, sigma, size=n_truth)).astype(np.int64)
            dx = np.round(rng.normal(0.0, sigma, size=n_truth)).astype(np.int64)
            yy = ref_idx[sel, 0] + dy
            xx = ref_idx[sel, 1] + dx
            ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
            yy, xx = yy[ok], xx[ok]
            keep = footprint[yy, xx] & ~catalogue[yy, xx]
            yy, xx = yy[keep], xx[keep]
            g = np.zeros(footprint.size, bool)
            g[yy * W + xx] = True
            if g.sum() >= 0.9 * n_truth:
                return g.reshape(footprint.shape)
        raise RuntimeError("could not place enough truth pixels")

    def score(support, credit, truth):
        return dti_from_counts(float(credit[truth].sum()),
                               float((1.0 - credit_field(truth)[support]).sum()),
                               int(truth.sum()))

    # ---------------------------------------------------------------- fit (N, sigma)
    keys = FAMILY + ["B1_recon", "B2_recon"] + [k for k in LIVE if k not in FAMILY]
    targets = dict(LIVE, **LIVE_B)
    best, grid = None, []
    for sigma in (1.0, 1.4, 1.85, 2.4, 3.0):
        for n_truth in (9000, 12691, 16000, 20000):
            draws = [draw_truth(n_truth, sigma) for _ in range(6)]
            modelled = {k: float(np.mean([score(supports[k], credits[k], g) for g in draws]))
                        for k in keys}
            err = float(np.sqrt(np.mean([(modelled[k] - targets[k]) ** 2 for k in keys])))
            rho = spearman([targets[k] for k in keys], [modelled[k] for k in keys])
            # the family ordering is the test the catalogue proxies fail
            fam_ok = all(modelled[FAMILY[i]] < modelled[FAMILY[i + 1]] for i in range(len(FAMILY) - 1))
            row = dict(sigma=sigma, n_truth=n_truth, rmse=err, spearman=rho,
                       family_order_ok=bool(fam_ok), modelled=modelled)
            grid.append(row)
            if best is None or row["rmse"] < best["rmse"]:
                best = row
            print(f"sigma={sigma:<5} N={n_truth:<6d} rmse={err:.4f} rho={rho:+.3f} "
                  f"family_order_ok={fam_ok}  modelled_family="
                  + ", ".join(f"{modelled[k]:.4f}" for k in FAMILY), flush=True)

    sigma, n_truth = best["sigma"], best["n_truth"]
    draws = [draw_truth(n_truth, sigma) for _ in range(a.draws)]
    modelled = {k: float(np.mean([score(supports[k], credits[k], g) for g in draws])) for k in keys}
    refit = dict(sigma=sigma, n_truth=n_truth,
                 rmse=float(np.sqrt(np.mean([(modelled[k] - targets[k]) ** 2 for k in keys]))),
                 spearman=spearman([targets[k] for k in keys], [modelled[k] for k in keys]),
                 modelled=modelled)
    print("\n=== refit best with", a.draws, "draws ===")
    for k in keys:
        t = targets.get(k, float("nan"))
        print(f"  {k:52s} live={t:.4f} model={modelled[k]:.4f} delta={modelled[k]-t:+.4f}")

    # ---------------------------------------------------------------- design answers
    # mass sweep on d2.8 (random decimation and reference-greedy decimation)
    ys, xs = np.nonzero(d28)
    dref = ndi.distance_transform_edt(~ref)
    sweeps = {}
    for label, order in (("random", rng.permutation(len(ys))), ("greedy_reference", np.argsort(dref[d28]))):
        rows = {}
        for frac in (0.25, 0.40, 0.60, 0.80, 1.00):
            sub = np.zeros_like(d28)
            sel = order[: int(round(frac * len(ys)))]
            sub[ys[sel], xs[sel]] = True
            v = float(np.mean([score(sub, credit_field(sub), g) for g in draws[: max(4, a.draws // 2)]]))
            rows[f"{frac:.2f}"] = dict(dots=int(sub.sum()), modelled_dti=v)
            print(f"  mass[{label}] frac={frac:.2f} dots={int(sub.sum()):6d} model_dti={v:.4f}", flush=True)
        sweeps[label] = rows

    ribbon = ndi.binary_closing(d28, structure=np.ones((3, 3), bool)) & footprint & ~catalogue
    geom = {}
    for name, s in (("dots_d2.8", d28), ("ribbon_closed_d2.8", ribbon)):
        v = float(np.mean([score(s, credit_field(s), g) for g in draws[: max(4, a.draws // 2)]]))
        geom[name] = dict(px=int(s.sum()), modelled_dti=v)
        print(f"  geometry {name:20s} px={int(s.sum()):6d} model_dti={v:.4f}")

    out = dict(
        schema_version=1,
        evidence_class="MODEL conditioned on owner-reported live anchors; not a score",
        model="anchors uniform on the 121,131-px H19-5 network + isotropic 2-D Gaussian positional error",
        targets=targets,
        fit={k: v for k, v in refit.items()},
        grid=[{k: v for k, v in r.items() if k != "modelled"} for r in grid],
        residuals={k: modelled[k] - targets[k] for k in keys},
        mass_sweeps=sweeps,
        geometry=geom,
        caveats=[
            "Reference support is the sibling family's H19-5 emission, so the fitted truth is anchored "
            "to that family; the model cannot fairly rank an independently derived support.",
            "Owner-reported scores are not organizer receipts; the hidden labels are unavailable.",
        ],
    )
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
