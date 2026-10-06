#!/usr/bin/env python3
"""DECISIVE PROTOCOL: leave-one-trace-out, with the hidden truth SPREAD across the map.

Why this protocol exists
------------------------
`run_holdout.py` uses a contiguous-quadrant holdout (Protocol P).  Its verdict was that
uniformly random dots beat the detector's dots.  That verdict is an artefact of the design:
with the truth confined to ONE quadrant, a dot placed anywhere else is a pure 0.2 cost and
returns nothing, so the arm that spreads dots most uniformly into the evaluated quadrant
wins regardless of whether its ranking carries information.  The real competition's hidden
faults are spread over the whole GeoDAWN region - the organisers say so - so the quadrant
protocol mis-specifies the task.

This protocol fixes that properly:
  * the mapped catalogue is split into CONNECTED COMPONENTS (individual fault traces);
  * a random 25 % of whole traces is held out as the hidden truth, so the truth is spread
    across the map exactly as the hidden set is, and whole structures are removed (no
    leakage from a retained pixel sitting next to a held-out one);
  * 4 independent draws give 4 folds;
  * the emission covers the whole footprint, and the RETAINED catalogue is the mask.

Arms, matched budget:
  A0  core + shell only
  A1  + dots from the unsteered Hessian-ridge field   <- candidate
  A2  + dots from the strike-steered field            <- ablation
  A3  + dots chosen uniformly at random               <- control
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from scipy import ndimage

from gems51 import emission, grid, scoring, stage1_strain as s1, stage2_emission as s2

ROOT = Path(__file__).resolve().parents[1]
ALL_BANDS = tuple(range(1, 20))
SUPPRESS_PX = 3
HOLDOUT_FRACTION = 0.25


def label_traces(cat: np.ndarray):
    """8-connected components of the catalogue; returns (labels, n)."""
    lab, n = ndimage.label(cat, structure=np.ones((3, 3), dtype=int))
    return lab, n


def build_emission(field, cat_model, valid, approved_tiles, *, lane, budget, tile,
                   shell_radius=1, shell_decay=0.6, seed=0, novel_buffer=0):
    core, shell = s2.catalogue_core_and_shell(cat_model, shell_radius_px=shell_radius,
                                              decay=shell_decay)
    # RESIDUALISATION.  Without it the detector's top-ranked dots sit immediately beside
    # the retained catalogue, because the strongest Hessian ridges ARE the mapped faults.
    # Those dots are not masked (the mask is pixel-exact on the catalogue raster), so each
    # one costs a full 0.2 and returns nothing for a fault that is somewhere else.  The
    # buffer forces the detector to compete on genuinely unmapped ground.
    if novel_buffer > 0:
        from scipy.ndimage import distance_transform_edt as _edt
        excl = _edt(~cat_model) <= float(novel_buffer)
    else:
        excl = core
    eligible = s1.upsampled_prior(approved_tiles, tile, cat_model.shape) & valid & (~excl)
    if lane == "random":
        rng = np.random.default_rng(seed)
        cand = np.flatnonzero(eligible.ravel())
        pick = rng.choice(cand, size=min(budget, cand.size), replace=False)
        picked = np.zeros_like(eligible)
        picked.ravel()[pick] = True
    elif lane == "weighted":
        # FIELD-WEIGHTED SAMPLING.  The metric's T term is a SUM over truth pixels, so
        # breadth of coverage beats per-dot precision (which is why uniform random beat the
        # detector's top-ranked peaks).  Sampling without replacement with probability
        # proportional to the field keeps the coverage of the random arm while biasing the
        # draw toward the detector's high-response ground.
        rng = np.random.default_rng(seed + 777)
        idx = np.flatnonzero(eligible.ravel())
        w = np.clip(field.ravel()[idx], 0.0, None).astype(np.float64)
        if w.sum() <= 0:
            w = np.ones_like(w)
        w = w / w.sum()
        n = min(budget, idx.size)
        pick = rng.choice(idx, size=n, replace=False, p=w)
        picked = np.zeros_like(eligible)
        picked.ravel()[pick] = True
    elif lane == "hybrid":
        # half detector peaks, half field-weighted sample
        rng = np.random.default_rng(seed + 999)
        half = budget // 2
        pk = emission.pack_by_threshold(field, eligible, half,
                                        suppression_px=SUPPRESS_PX)
        idx = np.flatnonzero(eligible.ravel() & ~pk.ravel())
        w = np.clip(field.ravel()[idx], 0.0, None).astype(np.float64)
        if w.sum() <= 0:
            w = np.ones_like(w)
        w = w / w.sum()
        n = min(budget - int(pk.sum()), idx.size)
        pick = rng.choice(idx, size=n, replace=False, p=w)
        picked = pk.copy()
        picked.ravel()[pick] = True
    elif lane == "none":
        picked = np.zeros_like(eligible)
    else:
        picked = emission.pack_by_threshold(field, eligible, budget,
                                            suppression_px=SUPPRESS_PX)
    values = emission.to_values(picked, core, shell, field=field)
    return values, picked, core, shell, eligible


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=4)
    ap.add_argument("--budget", type=int, default=44090)
    ap.add_argument("--shell", type=int, default=1)
    ap.add_argument("--decay", type=float, default=0.6)
    ap.add_argument("--tile", type=int, default=32)
    ap.add_argument("--approve-quantile", type=float, default=0.35)
    ap.add_argument("--novel-buffer", type=int, default=0,
                    help="px buffer around the retained catalogue excluded from novel dots")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "holdout_spread.json"))
    a = ap.parse_args()

    t0 = time.time()
    d = grid.data_root()
    tf = d / "training_features.tif"
    cat = grid.read_catalogue(d / "existing_faults.tif")
    valid = grid.valid_footprint(d / "sample_submission.tif")
    shear = grid.read_band(tf, 7)
    dil = grid.read_band(tf, 8)
    si = grid.read_band(tf, 4)
    lab, n_traces = label_traces(cat)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    print(f"[spread] {n_traces} connected traces in the catalogue")

    res = {"protocol": "leave-one-trace-out, truth spread across map",
           "holdout_fraction": HOLDOUT_FRACTION, "n_traces": int(n_traces),
           "n_components_ge_5px": int((sizes >= 5).sum()),
           "budget": a.budget, "shell_radius_px": a.shell,
           "novel_buffer_px": a.novel_buffer, "draws": [], "config": vars(a)}

    prov = lambda b: grid.read_band(tf, b)
    for draw in range(a.draws):
        rng = np.random.default_rng(1000 + draw)
        big = np.flatnonzero(sizes >= 3)          # ignore isolated single pixels
        rng.shuffle(big)
        n_hidden = int(HOLDOUT_FRACTION * big.size)
        hidden_ids = big[:n_hidden]
        hidden_mask = np.zeros_like(cat)
        hidden_mask.flat[np.isin(lab.ravel(), hidden_ids)] = True
        hidden = cat & hidden_mask
        model_cat = cat & (~hidden_mask)

        dep = s1.compute_stage1(model_cat, shear, dil, si, tile=a.tile,
                                approve_quantile=a.approve_quantile)
        f_plain = s2.steered_field_from_provider(prov, model_cat, valid, down=2,
                                                 sigma_px=2.0, bands=ALL_BANDS, steer=False)
        f_steer = s2.steered_field_from_provider(prov, model_cat, valid, down=2,
                                                 sigma_px=2.0, bands=ALL_BANDS, steer=True)
        arms = {
            "A0_core_shell_only": ("none", f_plain),
            "A1_hessianridge": ("pack", f_plain),
            "A2_steered": ("pack", f_steer),
            "A3_random": ("random", f_plain),
            "A5_weighted": ("weighted", f_plain),
            "A6_hybrid": ("hybrid", f_plain),
            "A7_buffered_peaks": ("pack", f_plain),
        }
        fold = {"draw": draw, "n_hidden_px": int(hidden.sum()),
                "n_model_px": int(model_cat.sum()), "n_approved_tiles": int(dep.approved.sum()),
                "arms": {}}
        for name, (lane, fld) in arms.items():
            values, picked, core, shell, elig = build_emission(
                fld, model_cat, valid, dep.approved, lane=lane, budget=a.budget,
                tile=dep.tile, shell_radius=a.shell, shell_decay=a.decay, seed=draw,
                novel_buffer=(a.novel_buffer if name == "A7_buffered_peaks" else 0))
            sc = scoring.score(values, hidden, model_cat, restrict_to_footprint=valid)
            # ranking diagnostics
            dts = ndimage.distance_transform_edt(~hidden).astype(np.float32)
            k = np.maximum(1.0 - dts / 3.0, 0.0)
            m = elig & np.isfinite(fld)
            labv = hidden[m]
            scv = fld[m]
            npos, nneg = int(labv.sum()), int((~labv).sum())
            auc = float("nan")
            if npos and nneg:
                order = np.argsort(scv, kind="mergesort")
                ranks = np.empty(scv.size, dtype=np.float64)
                ranks[order] = np.arange(1, scv.size + 1, dtype=np.float64)
                auc = float((ranks[labv].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))
            fold["arms"][name] = {
                "dti": sc["dti_masked"],
                "n_novel": int(picked.sum()),
                "mass": float(values.sum()),
                "credit_density_novel": float(k[picked].mean()) if picked.any() else 0.0,
                "frac_novel_within_3px": float((dts[picked] <= 3).mean()) if picked.any() else 0.0,
                "auc_field_vs_hidden": auc,
            }
        res["draws"].append(fold)
        print(f"[draw {draw}] hidden={fold['n_hidden_px']:,} px  " + "  ".join(
            f"{k2.split('_')[0]}={v['dti']:.4f}" for k2, v in fold["arms"].items()), flush=True)

    agg = {}
    for name in res["draws"][0]["arms"]:
        agg[name] = {}
        for key in ("dti", "credit_density_novel", "frac_novel_within_3px",
                    "auc_field_vs_hidden"):
            v = [f["arms"][name][key] for f in res["draws"]]
            agg[name][key] = {"mean": float(np.nanmean(v)),
                              "per_draw": [float(x) for x in v]}
    res["aggregate"] = agg
    con = {}
    for base in ("A3_random", "A2_steered", "A0_core_shell_only", "A1_hessianridge"):
        for key in ("dti", "credit_density_novel", "auc_field_vs_hidden"):
            v = [a_["arms"]["A1_hessianridge"][key] - a_["arms"][base][key]
                 for a_ in res["draws"]]
            con[f"A1 - {base} [{key}]"] = {
                "mean": float(np.nanmean(v)), "per_draw": [float(x) for x in v],
                "draws_positive": int(sum(1 for x in v if x > 0)), "n": len(v)}
    res["contrasts"] = con
    res["promotion_rule"] = (
        "DECLARED BEFORE THIS RUN: among {A1 peaks, A5 field-weighted sample, A6 hybrid, "
        "A7 buffered peaks} the shipped emission is the one with the highest mean DTI that "
        "also beats A3_random on >= 3 of 4 draws.  If none beats random, ship the arm with "
        "the highest mean DTI and say so.")
    # The declared rule: among the candidate emission rules, ship the one with the highest
    # mean DTI that also beats the uniform-random control on >= 3 of 4 draws.
    cands = [n for n in res["aggregate"] if n not in ("A0_core_shell_only", "A3_random")]
    ranked = sorted(cands, key=lambda n: -res["aggregate"][n]["dti"]["mean"])
    ship = None
    for n in ranked:
        v = [a_["arms"][n]["dti"] - a_["arms"]["A3_random"]["dti"] for a_ in res["draws"]]
        pos = sum(1 for x in v if x > 0)
        if pos >= max(3, a.draws - 1):
            ship = {"arm": n, "mean_dti": res["aggregate"][n]["dti"]["mean"],
                    "delta_vs_random_mean": float(np.nanmean(v)),
                    "draws_positive_vs_random": pos,
                    "n_draws": len(v)}
            break
    res["shipped_arm_evaluation"] = {
        "rule": res["promotion_rule"], "ranking_by_mean_dti": [
            {"arm": n, "mean_dti": res["aggregate"][n]["dti"]["mean"]} for n in ranked],
        "selected": ship,
    }
    res["promotion_pass"] = bool(ship is not None)
    res["elapsed_s"] = round(time.time() - t0, 1)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2, default=float))
    print(f"\n[spread] wrote {a.out} in {res['elapsed_s']} s")
    print(f"[spread] PROMOTION PASS = {res['promotion_pass']}")
    for k2, v in con.items():
        print(f"  {k2:44s} mean {v['mean']:+.5f}  draws +{v['draws_positive']}/{v['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
