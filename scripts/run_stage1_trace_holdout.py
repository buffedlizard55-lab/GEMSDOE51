#!/usr/bin/env python3
"""Stage 1 evaluated on a TRACE-level holdout -- the design the deficit actually needs.

Why a different design from the detector's blocked holdout
----------------------------------------------------------
The deficit is  Q(observed geodetic) - Q(fault-accommodated), and the
fault-accommodated term is computed *from the catalogue*.  If we hold out a
contiguous spatial block, then inside that block there is no catalogue at all,
the fault term is identically zero, and the deficit collapses to the raw geodetic
field.  That measures the wrong quantity.

The right design holds out a random subset of *traces* scattered across the whole
region, so that the remaining catalogue still covers everywhere and the deficit
is a genuine residual everywhere. There is no learned detector, but the fault-budget
term is catalogue-derived: all table rows assigned to held-out traces are removed
before computing it, so held-out trace attributes cannot enter the prior.

Scoring
-------
Uniform random dots inside the approved tiles versus uniform random dots over the
whole footprint, at identical mass.  The ratio
    lift = recall(truth in approved) / area(approved)
is reported as well: it is the cleanest single number for "is this prior worth
anything", and it is independent of the emission rule.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.emission import rasterise  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"


def load_observed():
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        out = {}
        for nm in ["geod_2ndinv", "geod_shearrate", "geod_dilaterate"]:
            a = s.read(descs.index(nm) + 1).astype(np.float64)
            a[a <= -1e38] = np.nan
            out[nm] = a
    return out


def upsample(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:GRID.shape[0], :GRID.shape[1]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--thresholds", default="40,50,60,70,80")
    ap.add_argument("--ratio", type=float, default=3.47)
    ap.add_argument("--g-hidden", type=int, default=12_700,
                    help="planning constant only; hidden truth size is unknown")
    ap.add_argument("--rate-convention", choices=("vertical", "fault_plane"),
                    default="vertical", help="Interpret source rate as vertical or total fault-plane slip")
    ap.add_argument("--assume-unknown-normal", action=argparse.BooleanOptionalAction,
                    default=True, help="Use explicit normal-fault fallback for unknown slip sense")
    ap.add_argument("--output", default="data/stage1_trace_holdout.json")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--min-heldout", type=int, default=2000)
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()
    cfg = sb.BudgetConfig(tile_px=a.tile_px,
                          rate_convention=a.rate_convention,
                          assume_unknown_normal=a.assume_unknown_normal)

    ys, xs, tid = sb.trace_assignments(catalogue, df)
    uniq = np.unique(tid)
    rng = np.random.default_rng(a.seed)
    perm = rng.permutation(uniq)
    chunks = np.array_split(perm, a.n_splits)
    thresholds = [float(t) for t in a.thresholds.split(",")]
    n_dots = int(round(a.ratio * a.g_hidden))

    rows = []
    t0 = time.time()
    for k, held in enumerate(chunks):
        held = set(held.tolist())
        is_held = np.zeros(ys.size, bool)
        for i, t in enumerate(tid):
            if t in held:
                is_held[i] = True
        truth = np.zeros(GRID.shape, bool)
        truth[ys[is_held], xs[is_held]] = True
        known = np.zeros(GRID.shape, bool)
        known[ys[~is_held], xs[~is_held]] = True
        if truth.sum() < a.min_heldout:
            print(f"  split {k}: only {truth.sum()} held-out px, skipped")
            continue

        # Remove whole Qfault attribute rows associated with any held-out
        # catalogue pixels, not only the held-out raster cells.
        df_budget = df.loc[~df.index.isin(held)]
        exx, eyy, exy, lent, npix, asg, mom, tshape, meta = sb.kostrov_tiles(
            known, df_budget, cfg, area_mask=footprint)
        II_f = sb.invariant(exx, eyy, exy, "II")
        obsII = sb.observed_tiles(obs["geod_2ndinv"], footprint, a.tile_px)
        obsDIL = sb.observed_tiles(obs["geod_dilaterate"], footprint, a.tile_px)
        obsSH = sb.observed_tiles(obs["geod_shearrate"], footprint, a.tile_px)
        dom = sb.observed_tiles(np.ones(GRID.shape, np.float32), footprint, a.tile_px)
        ok_t = np.isfinite(dom) & (dom > 0.05)
        q_f = sb.quantile_map(np.where(ok_t, II_f, np.nan))
        q_o = sb.quantile_map(np.where(ok_t, obsII, np.nan))
        deficit = q_o - q_f
        geo_only = q_o                      # control: geodetic field with no budget
        # The competition's scalar dilation/shear layers are separate diagnostics;
        # do not subtract the fault second invariant from unlike quantities.
        dil_only = sb.quantile_map(np.where(ok_t, obsDIL, np.nan))
        shear_only = sb.quantile_map(np.where(ok_t, obsSH, np.nan))

        row = dict(split=k, n_truth=int(truth.sum()), n_known=int(known.sum()),
                   n_budget_trace_rows=int(len(df_budget)),
                   frac_budget_rows_excluded=float(1.0 - len(df_budget) / max(len(df), 1)))
        for nm, field_t in [("deficit", deficit), ("geodetic_only", geo_only),
                            ("dilatation_only", dil_only), ("shear_only", shear_only)]:
            big = upsample(field_t, a.tile_px)
            b = big[footprint]
            fin = np.isfinite(b)
            tl = sb.observed_tiles(truth.astype(np.float64), footprint, a.tile_px)
            ok2 = ok_t & np.isfinite(tl)
            if ok2.sum() > 5:
                row[f"spearman_{nm}"] = float(spearmanr(field_t[ok2], tl[ok2]).statistic)
            for q in thresholds:
                thr = np.nanpercentile(b[fin], q)
                appr = np.zeros(GRID.shape, bool)
                tmp = np.zeros(GRID.shape, bool)
                tmp[footprint] = fin & (b >= thr)
                appr = tmp
                # area share and truth recall
                ar = float(appr.sum() / footprint.sum())
                rc = float(truth[appr].sum() / max(truth.sum(), 1))
                row[f"{nm}_area_q{q:g}"] = ar
                row[f"{nm}_recall_q{q:g}"] = rc
                row[f"{nm}_lift_q{q:g}"] = rc / max(ar, 1e-9)
                # uniform-random dots inside approved vs everywhere
                yy, xx = np.nonzero(appr & ~known)
                if yy.size > n_dots:
                    sel = rng.choice(yy.size, size=n_dots, replace=False)
                    r = dti_binary(rasterise(yy[sel], xx[sel]) > 0, truth,
                                   valid=footprint, known=known)
                    row[f"{nm}_dti_q{q:g}"] = r["dti"]
        yy, xx = np.nonzero(footprint & ~known)
        sel = rng.choice(yy.size, size=min(n_dots, yy.size), replace=False)
        r = dti_binary(rasterise(yy[sel], xx[sel]) > 0, truth, valid=footprint, known=known)
        row["uniform_dti"] = r["dti"]
        print(f"  split {k}: truth={int(truth.sum()):6d}  "
              + "  ".join(f"q{q:g}:lift={row.get(f'deficit_lift_q{q:g}', float('nan')):.3f}"
                          for q in thresholds)
              + f"  rho_def={row.get('spearman_deficit', float('nan')):.3f}"
              + f"  uniform={row['uniform_dti']:.4f}  ({time.time()-t0:.0f}s)", flush=True)
        rows.append(row)

    out = {}
    for key in rows[0]:
        v = [r[key] for r in rows if key in r]
        if v and isinstance(v[0], (int, float, np.floating)) and key not in ("split",):
            out[key] = dict(mean=float(np.mean(v)), per_split=[float(x) for x in v])
    p = Path(a.output)
    if not p.is_absolute():
        p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(config=vars(a), per_split=rows, summary=out), indent=1))
    print(json.dumps(out, indent=1))
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
