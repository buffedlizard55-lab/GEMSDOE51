#!/usr/bin/env python3
"""Second-pass screen: matched-mass random controls, AUCs, band restriction, Stage-1 confinement.

Follows ``scripts/screen_layers_offcatalogue.py``.  Answers four questions:

1. Matched-mass random control -- is any layer's top-N instrument DTI better than a *random* emission
   of the same size drawn from the same domain?  (Without this control the first screen cannot be read.)
2. Kernel AUC -- rank separation of each layer between instrument-truth neighbourhoods and the rest,
   which is mass-free.
3. Band restriction -- the hidden truth is expected to lie near, but not on, the published catalogue,
   so selection is restricted to ``2 < d_cat <= band`` px and compared with the unrestricted domain.
4. Stage-1 confinement -- what fraction of each selection falls inside the approved deficit tiles.

Usage:
    PYTHONPATH=src .venv/bin/python scripts/screen_lidar_family.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape
CAND = ["lid_relief_s15_lin", "lid_relief_s40_lin", "tmi_s15_lin", "lid_lapneg_max",
        "lid_ex_max", "lid_ex_mean", "lid_downface_max", "lid_step_max", "lid_cross_max",
        "comp_det_elev_slope", "lid_relief", "det_elev_s40_lin"]
N = 12691


def topn(field, allowed, n):
    ys, xs = np.nonzero(allowed)
    v = field[ys, xs]
    k = min(n, ys.size)
    thr = np.partition(v, -k)[-k]
    keep = v >= thr
    out = np.zeros(field.shape, bool)
    out[ys[keep], xs[keep]] = True
    return out


def main() -> int:
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r", shape=(len(names), H, W))
    dcat = ndi.distance_transform_edt(~catalogue).astype(np.float32)

    def get(nm):
        return np.asarray(mm[names.index(nm)], np.float32)

    off2 = footprint & (dcat > 2.0)
    sgmc = get("sgmc_fault") > 0.5
    up, lp = get("lid_upface_max"), get("lid_lappos_max")
    fin = np.isfinite(up) & np.isfinite(lp)
    thr99 = np.percentile(up[footprint & fin], 99.0)
    truth_s = sgmc & off2
    truth_l = fin & (up >= thr99) & (lp > 0) & off2
    # kernel-weighted truth neighbourhoods for AUC (within the 3 px metric radius)
    k3 = np.ones((7, 7), bool)
    near_s = ndi.binary_dilation(truth_s, structure=k3)
    near_l = ndi.binary_dilation(truth_l, structure=k3)
    print(f"S truth {int(truth_s.sum()):,} | L truth {int(truth_l.sum()):,}", flush=True)

    # ---- stage-1 approved tiles (reuse the coarse deficit construction) -------
    import pandas as pd
    from gems51 import strain_budget as sb
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    cfg = sb.BudgetConfig(tile_px=100)
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        obs = s.read(descs.index("geod_2ndinv") + 1).astype(np.float64)
    obs[obs <= -1e38] = np.nan
    exx, eyy, exy, _L, _n, _a, _m, tshape, _meta = sb.kostrov_tiles(catalogue, df, cfg)
    f_ii = sb.invariant(exx, eyy, exy, "II")
    o_t = sb.observed_tiles(obs, footprint, cfg.tile_px)
    okk = np.isfinite(o_t) & (o_t > 0)
    qf, qo = sb.quantile_map(np.where(okk, f_ii, np.nan)), sb.quantile_map(np.where(okk, o_t, np.nan))
    resid = qo - qf
    finr = np.isfinite(resid)
    thr = np.quantile(resid[finr], 0.10)
    approved_t = finr & (resid >= thr)
    approved = np.repeat(np.repeat(approved_t, cfg.tile_px, 0), cfg.tile_px, 1)[:H, :W] & footprint
    print(f"approved tiles: {approved.sum()/footprint.sum():.4f} of footprint", flush=True)

    rng = np.random.default_rng(11)
    ys, xs = np.nonzero(off2)
    rand_stats = []
    for i in range(6):
        pick = rng.choice(ys.size, N, replace=False)
        m = np.zeros_like(footprint)
        m[ys[pick], xs[pick]] = True
        s_ = dti_binary(m, truth_s, valid=footprint, known=catalogue)
        l_ = dti_binary(m, truth_l, valid=footprint, known=catalogue)
        rand_stats.append((float(s_["dti"]), float(l_["dti"])))
    rs = np.array(rand_stats)
    print(f"random control (n={N}): S {rs[:,0].mean():.4f}±{rs[:,0].std():.4f} "
          f"L {rs[:,1].mean():.4f}±{rs[:,1].std():.4f}", flush=True)

    out = {"schema_version": 1, "top_n": N,
           "random_control": {"S_mean": float(rs[:, 0].mean()), "S_sd": float(rs[:, 0].std()),
                              "L_mean": float(rs[:, 1].mean()), "L_sd": float(rs[:, 1].std()),
                              "draws": 6},
           "approved_frac_of_footprint": float(approved.sum() / footprint.sum()),
           "layers": {}}

    def auc(field, mask, near, domain):
        a = field[domain]
        lab = near[domain]
        if lab.sum() == 0 or lab.sum() == lab.size:
            return float("nan")
        order = np.argsort(a, kind="stable")
        ranks = np.empty(a.size, float)
        ranks[order] = np.arange(1, a.size + 1)
        n1, n0 = float(lab.sum()), float((~lab).sum())
        return float((ranks[lab].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))

    for nm in CAND:
        f = get(nm)
        m_ok = footprint & np.isfinite(f)
        dom_off = off2 & np.isfinite(f)
        rec = {}
        sel = topn(f, dom_off, N)
        s_ = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
        l_ = dti_binary(sel, truth_l, valid=footprint, known=catalogue)
        rec["off2_S"] = float(s_["dti"]); rec["off2_L"] = float(l_["dti"])
        rec["frac_in_approved"] = float((sel & approved).sum() / max(int(sel.sum()), 1))
        rec["auc_S_off2"] = auc(f, near_s, near_s, dom_off)
        rec["auc_L_off2"] = auc(f, near_l, near_l, dom_off)
        # band-restricted: 2 < d_cat <= 10 px (the near-field band where hidden truth is expected)
        band = dom_off & (dcat <= 10.0)
        if band.sum() > N:
            selb = topn(f, band, N)
            sb_ = dti_binary(selb, truth_s, valid=footprint, known=catalogue)
            lb_ = dti_binary(selb, truth_l, valid=footprint, known=catalogue)
            rec["band10_S"] = float(sb_["dti"]); rec["band10_L"] = float(lb_["dti"])
            rec["band10_frac_approved"] = float((selb & approved).sum() / max(int(selb.sum()), 1))
        out["layers"][nm] = rec
        print(f"  {nm:24s} off2 S={rec['off2_S']:.4f} L={rec['off2_L']:.4f} "
              f"| band10 S={rec.get('band10_S', float('nan')):.4f} L={rec.get('band10_L', float('nan')):.4f} "
              f"| AUC S={rec['auc_S_off2']:.3f} L={rec['auc_L_off2']:.3f} "
              f"| appr={rec['frac_in_approved']:.2f}", flush=True)

    # ---- rank fusion of the best independent families -------------------------
    def rank01(a, m):
        o = np.zeros(a.shape, np.float32)
        v = a[m]
        idx = np.argsort(np.argsort(v, kind="stable"), kind="stable")
        o[m] = idx / max(1, v.size - 1)
        return o

    fam = {"lidar": ["lid_relief_s15_lin", "lid_lapneg_max", "lid_ex_max", "lid_step_max"],
           "mag": ["tmi_s15_lin", "comp_tmi_hg", "comp_rtp"],
           "elev": ["comp_det_elev_slope", "det_elev_s40_lin"]}
    acc = np.zeros((H, W), np.float64)
    for k, chans in fam.items():
        sub = np.zeros((H, W), np.float64)
        for c in chans:
            f = get(c)
            sub += rank01(f, off2 & np.isfinite(f))
        acc += sub / len(chans)
    fuse = (acc / len(fam)).astype(np.float32)
    sel = topn(fuse, off2 & np.isfinite(fuse), N)
    s_ = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
    l_ = dti_binary(sel, truth_l, valid=footprint, known=catalogue)
    out["fusion_3fam"] = {"S": float(s_["dti"]), "L": float(l_["dti"]),
                          "band10_S": None, "frac_in_approved": float((sel & approved).sum() / max(int(sel.sum()), 1))}
    print(f"fusion(3 families) S={s_['dti']:.4f} L={l_['dti']:.4f}", flush=True)
    Path(ROOT / "evidence" / "layer_screen_controls.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/layer_screen_controls.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
