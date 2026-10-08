#!/usr/bin/env python3
"""H53-X5 screen: radiometric K/Th alteration concordance on magnetic lineaments,
conditioned on distance from the catalogued faults.

Hypothesis (knowledge/preregistration-2026-10-08.md, slate rank 2)
-------------------------------------------------------------------
Hydrothermal fluid pathways alter surface radioelement concentrations (K
enrichment relative to Th) along structures.  Where a potassium excess
coincides with a magnetic lineament crest and the catalogue has no fault
nearby, the structure is more likely to be a genuinely unmapped fault than a
mapped contact.  This is a screen on the two off-catalogue proxy instruments
(S = SGMC faults absent from the catalogue; L = lidar scarp crests away from
the catalogue), not a submission.

Preregistered decision (before running)
---------------------------------------
PROCEED to a six-fold paired test only if the best X5 fusion's S exceeds BOTH:
  * the matched random control mean by >= 3 standard deviations, AND
  * the best single input layer's S (tmi_s15_lin, S=0.0648 at top-12,691 in
    evidence/layer_screen_offcatalogue.json) by >= 0.005 absolute.
Otherwise X5 is REJECTED for this cycle and recorded with numbers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems51.grid import GRID          # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from scripts.screen_layers_offcatalogue import topn_mask  # noqa: E402

P = ROOT / "data" / "prepared"


def rank01(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype=np.float32)
    v = np.where(valid, a, np.nan)
    flat = v[valid]
    order = np.argsort(flat, kind="mergesort")
    ranks = np.empty(flat.size, dtype=np.float32)
    ranks[order] = (np.arange(1, flat.size + 1, dtype=np.float32) / flat.size)
    out[valid] = ranks
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=12691)
    ap.add_argument("--mass", type=int, default=44090)
    ap.add_argument("--offcat-px", type=float, default=2.0)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "x5_screen_20261008.json"))
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r",
                   shape=(len(names), *GRID.shape))

    dcat = ndi.distance_transform_edt(~catalogue)
    off = footprint & (dcat > a.offcat_px)

    truth_s = (np.asarray(mm[names.index("sgmc_fault")], np.float32) > 0.5) & off
    up = np.asarray(mm[names.index("lid_upface_max")], np.float32)
    lp = np.asarray(mm[names.index("lid_lappos_max")], np.float32)
    fin = np.isfinite(up) & np.isfinite(lp)
    thr = np.percentile(up[footprint & fin], 99.0)
    truth_l = fin & (up >= thr) & (lp > 0) & off
    print(f"truth S {int(truth_s.sum()):,} px | truth L {int(truth_l.sum()):,} px")

    rk = np.asarray(mm[names.index("rad_K")], np.float32)
    rth = np.asarray(mm[names.index("rad_Th")], np.float32)
    tmi_lin = np.asarray(mm[names.index("tmi_s15_lin")], np.float32)
    valid = footprint & np.isfinite(rk) & np.isfinite(rth) & np.isfinite(tmi_lin)
    print(f"valid px {int(valid.sum()):,}")

    # log K/Th ratio (Th stabilises the denominator; both positive in the mirror)
    eps = 1e-6
    kth = np.log((np.nan_to_num(rk) + eps) / (np.nan_to_num(rth) + eps))
    kth[~valid] = np.nan
    rk_r = rank01(kth, valid)
    lin_r = rank01(tmi_lin, valid)
    fusions = {
        "x5_kth_x_tmilin": np.sqrt(rk_r * lin_r),
        "x5_kth_only": rk_r,
        "x5_tmilin_only": lin_r,
    }
    allowed = valid & off
    rows = {}
    for name, f in fusions.items():
        for n, tag in ((a.top_n, "top12691"), (a.mass, "mass44090")):
            sel = topn_mask(np.nan_to_num(f, nan=-1.0), allowed, n)
            s = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
            l = dti_binary(sel, truth_l, valid=footprint, known=catalogue)
            rows[f"{name}_{tag}"] = dict(S=float(s["dti"]), L=float(l["dti"]),
                                           px=int(sel.sum()))
            print(f"  {name:22s} {tag:10s} S={s['dti']:.4f} L={l['dti']:.4f}", flush=True)

    # matched random control inside the same allowed domain
    rng = np.random.default_rng(20261008)
    cand = np.argwhere(allowed)
    controls = []
    for trial in range(5):
        idx = rng.choice(cand.shape[0], size=a.top_n, replace=False)
        sel = np.zeros(GRID.shape, bool)
        sel[cand[idx, 0], cand[idx, 1]] = True
        s = dti_binary(sel, truth_s, valid=footprint, known=catalogue)
        controls.append(float(s["dti"]))
    ctrl = dict(mean=float(np.mean(controls)), std=float(np.std(controls)),
                trials=controls)
    print("random control S:", ctrl)

    fusion_s = rows["x5_kth_x_tmilin_top12691"]["S"]
    single_best = max(rows["x5_tmilin_only_top12691"]["S"],
                      rows["x5_kth_only_top12691"]["S"])
    proceed = (fusion_s >= ctrl["mean"] + 3 * max(ctrl["std"], 1e-6)
               and fusion_s >= single_best + 0.005)
    out = dict(schema_version=1, hypothesis="H53-X5", top_n=a.top_n,
               offcat_px=a.offcat_px, rows=rows, random_control=ctrl,
               decision=dict(fusion_S=fusion_s, best_single_S=single_best,
                             rule="fusion S >= random mean+3sd AND >= best single + 0.005",
                             proceed=bool(proceed)))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["decision"], indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
