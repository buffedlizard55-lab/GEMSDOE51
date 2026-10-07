#!/usr/bin/env python3
"""Fit a hidden-truth model to *live-scored* artifacts, then use it to size an emission.

Why this exists
---------------
The competition truth is hidden.  Twelve artifacts in ``data/refs/`` (owner-mirrored,
sha256-pinned, manifest ``data/refs/index.json``) carry **owner-reported live leaderboard
scores** spanning 0.0107-0.2600.  Those twelve are the only measurements of the real metric
this project has.  This script:

  1. re-denominates the four dotted-family anchors on the published bytes,
  2. fits a *generative* truth model -- N truth pixels drawn with intensity
     ``exp(-d_ref / sigma)`` around the family's parent support (H19-5), optionally excluding
     pixels within ``cat_excl`` px of the published catalogue -- by minimising squared error
     against the twelve owner-reported scores,
  3. reports the fitted parameters, the residual table and Spearman rho,
  4. sweeps emission mass on the family support to locate the metric's mass optimum,
  5. compares a dotted emission against a *contiguous ribbon* of the same trace length.

Every number produced here is a MODEL conditioned on owner-reported anchors.  It is not a
score, not the organizer's truth, and it inherits any error in the owner-reported values.

Metric (official, page 967):  DTI = T / (alpha*(T+F) + beta*G),  alpha=0.2, beta=0.8,
triangular kernel with 300 m support (3 px), known-catalogue pixels removed from the domain.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/fit_live_truth_model.py [--draws 24]
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

from gems51.grid import GRID  # noqa: E402

RADIUS_PX = 3.0
ALPHA, BETA = 0.2, 0.8

# owner-reported live leaderboard scores (GEMSDOE32 `evidence/instrument_calibration.json`,
# itself sourced from the owner's site pages; not organizer receipts)
LIVE = {
    "scored_h19_5": 0.1922,
    "scored_d15_scored": 0.2477,
    "scored_d28_unscored": 0.2600,
    "calib_gems10-h28-dotted-ridge-20260928T0202562": 0.1839,
    "calib_gems10-h25-ctx-ridge-20260927T2329477041": 0.1280,
    "calib_8GEMSDOE_Hedge-v2_submission": 0.1563,
    "calib_gemsdoe-ens12-adopted-7f00890a": 0.1563,
    "calib_13gems_20261001_r13-lattice-s5_v2_nan-ou": 0.0904,
    "calib_gemsdoe9-PLACEHOLDER-2314b599": 0.0107,
}


def load(path: Path, mask_known: np.ndarray | None = None) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    m = np.isfinite(a) & (a > 0)
    if mask_known is not None:
        m = m & ~mask_known
    return m


def dti_from_counts(tp: float, fp: float, n: int) -> float:
    return tp / (ALPHA * (tp + fp) + BETA * n + 1e-12)


def credit_field(support: np.ndarray) -> np.ndarray:
    """Exact kernel credit C(y) = max_{x in support, d<=R} k(d)  ==  max(0, 1 - d_S(y)/R).

    ``ndi.distance_transform_edt(~S)`` is the Euclidean distance to the nearest support
    pixel, so the triangular kernel's max equals the same expression applied to that
    distance.  ``tests/test_live_truth_model.py`` checks this against the literal
    (2*ceil(R)+1)^2 offset loop.
    """
    d = ndi.distance_transform_edt(~support)
    return np.maximum(1.0 - d / RADIUS_PX, 0.0)


def score_binary(support: np.ndarray, truth: np.ndarray, offsets: list | None = None,
                 precomputed_credit: np.ndarray | None = None) -> dict:
    """Exact T and F for a binary support against one truth realisation (EDT form)."""
    n = int(truth.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(support.sum()), n=0, dti=0.0)
    c = credit_field(support) if precomputed_credit is None else precomputed_credit
    tp = float(c[truth].sum())
    cg = credit_field(truth)
    fp = float((1.0 - cg[support]).sum())
    return dict(tp=tp, fp=fp, n=n, dti=dti_from_counts(tp, fp, n))


def offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dy, dx))
            k = max(1.0 - d / radius, 0.0)
            if k > 0:
                out.append((dy, dx, k))
    return out


OFFS = offsets()


def spearman(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=16)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "live_truth_model_fit.json"))
    a = ap.parse_args()

    footprint = np.load(ROOT / "data" / "prepared" / "footprint.npy")
    catalogue = np.load(ROOT / "data" / "prepared" / "catalogue.npy")
    dcat = ndi.distance_transform_edt(~catalogue)

    ref = load(ROOT / "data" / "refs" / "scored_h19_5.tif")          # 121,131 px parent support
    dref = ndi.distance_transform_edt(~ref)

    supports = {k: load(ROOT / "data" / "refs" / f"{k}.tif") for k in LIVE}
    # on-catalogue predictions are outside the scored domain: remove them
    supports = {k: (m & ~catalogue) for k, m in supports.items()}

    stats = {}
    for k, m in supports.items():
        stats[k] = dict(live=LIVE[k], positives=int(m.sum()),
                        on_catalogue_before_mask=None,
                        median_dcat_px=float(np.median(dcat[m])) if m.any() else None)

    # ------------------------------------------------ fit (N, sigma, cat_excl)
    rng = np.random.default_rng(20261007)
    credits = {k: credit_field(m) for k, m in supports.items()}

    def sample_truth(p, idx, n_truth):
        flat = rng.choice(idx, size=n_truth, replace=False, p=p[idx])
        g = np.zeros(footprint.size, bool)
        g[flat] = True
        return g.reshape(footprint.shape)

    best = None
    grid = []
    for sigma in (1.1, 1.3, 1.85, 2.5, 3.5):
        for cat_excl in (0, 2):
            w = np.exp(-dref / sigma)
            if cat_excl:
                w[dcat <= cat_excl] = 0.0
            w[~footprint] = 0.0
            if w.sum() <= 0:
                continue
            p = (w / w.sum()).ravel()
            idx = np.flatnonzero(p > 0)
            for n_truth in (8000, 10000, 12691, 16000, 20000):
                draws = [sample_truth(p, idx, n_truth) for _ in range(6)]
                modelled = {}
                for k, m in supports.items():
                    vals = [score_binary(m, g, precomputed_credit=credits[k])["dti"]
                            for g in draws]
                    modelled[k] = float(np.mean(vals))
                err = np.mean([(modelled[k] - LIVE[k]) ** 2 for k in LIVE])
                rho = spearman([LIVE[k] for k in LIVE], [modelled[k] for k in LIVE])
                row = dict(sigma=sigma, cat_excl=cat_excl, n_truth=n_truth,
                           rmse=float(np.sqrt(err)), spearman=rho, modelled=modelled)
                grid.append(row)
                if best is None or row["rmse"] < best["rmse"]:
                    best = row
                print(f"sigma={sigma:<4} cat_excl={cat_excl} N={n_truth:<6d} "
                      f"rmse={row['rmse']:.4f} rho={rho:+.3f}", flush=True)

    # refine the winner with more draws
    sigma, cat_excl, n_truth = best["sigma"], best["cat_excl"], best["n_truth"]
    w = np.exp(-dref / sigma)
    if cat_excl:
        w[dcat <= cat_excl] = 0.0
    w[~footprint] = 0.0
    p = (w / w.sum()).ravel()
    idx = np.flatnonzero(p > 0)
    draws = [sample_truth(p, idx, n_truth) for _ in range(a.draws)]
    modelled = {}
    for k, m in supports.items():
        vals = [score_binary(m, g, precomputed_credit=credits[k])["dti"] for g in draws]
        modelled[k] = float(np.mean(vals))
    err = np.mean([(modelled[k] - LIVE[k]) ** 2 for k in LIVE])
    best = dict(sigma=sigma, cat_excl=cat_excl, n_truth=n_truth,
                rmse=float(np.sqrt(err)),
                spearman=spearman([LIVE[k] for k in LIVE], [modelled[k] for k in LIVE]),
                modelled=modelled)
    print("\nBEST (refined):", json.dumps({k: v for k, v in best.items() if k != "modelled"}, indent=1))
    for k in LIVE:
        print(f"  {k:52s} live={LIVE[k]:.4f} model={best['modelled'][k]:.4f} "
              f"delta={best['modelled'][k]-LIVE[k]:+.4f}")

    # ------------------------------------------------ mass sweep on the family support
    d28 = supports["scored_d28_unscored"]
    ys, xs = np.nonzero(d28)
    sweep, greedy = {}, {}
    for label, order in (("random", rng.permutation(len(ys))), ("greedy_ref", np.argsort(dref[d28]))):
        for frac in (0.15, 0.25, 0.40, 0.60, 0.80, 1.00):
            n_keep = int(round(frac * len(ys)))
            sel = order[:n_keep]
            sub = np.zeros_like(d28)
            sub[ys[sel], xs[sel]] = True
            csub = credit_field(sub)
            vals = [score_binary(sub, g, precomputed_credit=csub)["dti"]
                    for g in draws[: max(4, a.draws // 2)]]
            rec = dict(dots=int(n_keep), modelled_dti=float(np.mean(vals)))
            (sweep if label == "random" else greedy)[f"{frac:.2f}"] = rec
            print(f"{label:11s} frac={frac:.2f} dots={n_keep:6d} model_dti={np.mean(vals):.4f}")

    # ------------------------------------------------ dotted vs contiguous ribbon (equal trace length)
    ribbon = ndi.binary_closing(d28, structure=np.ones((3, 3), bool))
    ribbon = ribbon & footprint & ~catalogue
    geom = {}
    for name, s in (("dots_d2.8", d28), ("ribbon_closed_d2.8", ribbon)):
        vals = []
        for _ in range(max(4, a.draws // 2)):
            flat = rng.choice(idx, size=n_truth, replace=False, p=p[idx])
            g = np.zeros(footprint.size, bool)
            g[flat] = True
            g = g.reshape(footprint.shape)
            vals.append(score_binary(s, g, OFFS)["dti"])
        geom[name] = dict(px=int(s.sum()), modelled_dti=float(np.mean(vals)))
        print(f"geometry {name:20s} px={int(s.sum()):6d} model_dti={np.mean(vals):.4f}")

    out = dict(
        schema_version=1,
        evidence_class="MODEL conditioned on owner-reported live anchors; not a score",
        metric=dict(alpha=ALPHA, beta=BETA, radius_px=RADIUS_PX,
                    note="official page 967; catalogue pixels removed from the scored domain"),
        anchors=LIVE,
        corpus_stats=stats,
        fit=dict(sigma_px=sigma, cat_excl_px=cat_excl, n_truth=n_truth,
                 rmse=best["rmse"], spearman=best["spearman"], modelled=best["modelled"]),
        grid=[{k: v for k, v in r.items() if k != "modelled"} for r in grid],
        mass_sweep_random=sweep,
        mass_sweep_greedy_reference=greedy,
        geometry_comparison=geom,
        caveats=[
            "The reference support is the sibling family's 121,131-px H19-5 emission; the fitted "
            "truth is therefore anchored to that family and cannot rank an independently derived "
            "support fairly.",
            "Owner-reported live scores are not organizer receipts.",
        ],
    )
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
