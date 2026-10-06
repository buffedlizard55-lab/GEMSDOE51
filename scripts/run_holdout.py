#!/usr/bin/env python3
"""PREREGISTERED spatially-blocked holdout: does the stage-2 field actually carry signal?

Arms, all at MATCHED novel-emission budget and matched eligibility (stage-1 approved tiles
computed leave-block-out), scored with the official metric:

  A0  core + shell only, no novel dots          (the "do nothing new" control)
  A1  + novel dots from the STEERED Hessian field        <- the candidate
  A2  + novel dots from the UNSTEERED Hessian field      <- ablation of the steer
  A3  + novel dots in the SAME NUMBER but chosen at random inside the eligible area
  A4  + novel dots from the steered field, but with the stage-1 gate REMOVED
                                                          <- ablation of the prior
Reported per fold, under both Protocol O (emit in-block) and Protocol P (whole map).

Promotion rule, frozen before running (maximise P(win): a candidate that has not beaten
the control on the blocked holdout must not consume a weekly slot):
  PROMOTE iff  mean(A1 - A2) > 0 AND mean(A1 - A3) > 0 AND folds_positive(A1 - A3) >= 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from gems51 import emission, grid, scoring, stage1_strain as s1, stage2_emission as s2

ROOT = Path(__file__).resolve().parents[1]
NOVEL_BUDGET = 44090   # matched to the incumbent's live mass, so placement is the variable
SUPPRESS_PX = 3        # the kernel radius


def ranking_diagnostics(field, picked, truth, eligible):
    """Sensitive, low-variance measures of ranking quality (the DTI is diluted by the
    shared core+shell mass, which is identical across arms)."""
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(~truth).astype(np.float32)
    k = np.maximum(1.0 - d / 3.0, 0.0)
    out = {}
    if picked.any():
        out["credit_density_novel"] = float(k[picked].mean())
        out["frac_novel_within_3px"] = float((d[picked] <= 3).mean())
    else:
        out["credit_density_novel"] = 0.0
        out["frac_novel_within_3px"] = 0.0
    # AUC of the field on the eligible area against the held-out truth
    m = eligible & np.isfinite(field)
    lab = truth[m]
    sc = field[m]
    npos, nneg = int(lab.sum()), int((~lab).sum())
    if npos and nneg:
        order = np.argsort(sc)
        ranks = np.empty(sc.size, dtype=np.float64)
        ranks[order] = np.arange(1, sc.size + 1)
        out["auc_field_vs_block_truth"] = float(
            (ranks[lab].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))
    else:
        out["auc_field_vs_block_truth"] = float("nan")
    return out


def load(n: int | None = None):
    d = grid.data_root()
    cat = grid.read_catalogue(d / "existing_faults.tif")
    valid = grid.valid_footprint(d / "sample_submission.tif")
    if n is None:
        return cat, valid
    return cat[:n, :n], valid[:n, :n]


def read_strain():
    d = grid.data_root()
    tf = d / "training_features.tif"
    return (grid.read_band(tf, 7), grid.read_band(tf, 8), grid.read_band(tf, 4))


ALL_BANDS = tuple(range(1, 20))


def make_field(cat_model, valid, tf_path, steer=True, down=2, bands=None):
    prov = lambda b: grid.read_band(tf_path, b)
    return s2.steered_field_from_provider(
        prov, cat_model, valid, down=down, sigma_px=2.0,
        bands=(bands if bands is not None else ALL_BANDS), steer=steer
    )


def build_emission(field, cat_model, valid, approved_tiles, *, lane, budget=NOVEL_BUDGET,
                   eligible_override=None, seed=0, tile=None,
                   shell_radius=1, shell_decay=0.6):
    core, shell = s2.catalogue_core_and_shell(cat_model, shell_radius_px=shell_radius,
                                              decay=shell_decay)
    if eligible_override is not None:
        eligible = eligible_override
    else:
        eligible = s1.upsampled_prior(approved_tiles, tile, cat_model.shape)
    eligible = eligible & valid & (~core)
    if lane == "random":
        rng = np.random.default_rng(seed)
        cand = np.flatnonzero(eligible.ravel())
        pick = rng.choice(cand, size=min(budget, cand.size), replace=False)
        picked = np.zeros_like(eligible)
        picked.ravel()[pick] = True
    else:
        picked = emission.pack_by_threshold(field, eligible, budget,
                                            suppression_px=SUPPRESS_PX)
    values = emission.to_values(picked, core, shell, field=field)
    return values, picked, core, shell, eligible


def run(n_crop=None, folds=4, out_path=None, budget=NOVEL_BUDGET,
        shell_radius=1, shell_decay=0.6):
    t0 = time.time()
    d = grid.data_root()
    tf = d / "training_features.tif"
    cat, valid = load(n_crop)
    shear, dil, si = read_strain()
    if n_crop:
        shear, dil, si = shear[:n_crop, :n_crop], dil[:n_crop, :n_crop], si[:n_crop, :n_crop]

    # Precompute BOTH fields once on the FULL catalogue (used by A1/A2/A4 and by the
    # whole-map arms).  The leave-block-out refit is done per fold for the model inputs
    # that matter (strike field is recomputed inside make_field via cat_model).
    results = {"budget": budget, "suppress_px": SUPPRESS_PX, "folds": [], "config": {
        "n_crop": n_crop, "folds": folds, "novel_budget": budget,
        "shell_radius_px": shell_radius, "shell_decay": shell_decay,
    }}

    for name, block, exclusion in scoring.quadrant_blocks(cat.shape, n=2, buffer_px=30):
        if len(results["folds"]) >= folds:
            break
        cat_model = cat & (~exclusion)
        truth = cat & exclusion
        # known mask = the catalogue the SCORER would know: everything outside the block
        known = cat & (~exclusion)

        res_fold = {"fold": name, "arms": {}}
        dep = s1.compute_stage1(cat_model, shear, dil, si, tile=32)
        # fields must be built on the model catalogue only (no leakage)
        f_plain = make_field(cat_model, valid, tf, steer=False)   # CANDIDATE
        f_steer = make_field(cat_model, valid, tf, steer=True)    # ablation

        whole = np.ones_like(cat, dtype=bool)
        arms = {
            "A0_core_shell_only": dict(lane="none", field=f_plain, elig=None),
            "A1_hessianridge_gated": dict(lane="pack", field=f_plain, elig=None),
            "A2_steered_gated": dict(lane="pack", field=f_steer, elig=None),
            "A3_random_gated": dict(lane="random", field=f_plain, elig=None),
            "A4_hessianridge_ungated": dict(lane="pack", field=f_plain, elig=whole),
        }
        for arm, cfg in arms.items():
            field = cfg["field"]
            if arm == "A0_core_shell_only":
                values, picked, core, shell, elig = build_emission(
                    field, cat_model, valid, dep.approved, lane="none", budget=0,
                    tile=dep.tile, shell_radius=shell_radius, shell_decay=shell_decay)
            else:
                ov = (whole & valid) if cfg["elig"] is not None else None
                values, picked, core, shell, elig = build_emission(
                    cfg["field"], cat_model, valid, dep.approved,
                    lane=cfg["lane"], budget=budget, tile=dep.tile,
                    eligible_override=ov, shell_radius=shell_radius,
                    shell_decay=shell_decay)
            # Protocol P: whole-map emission, truth = the held-out block
            pP = scoring.score(values, truth, known, restrict_to_footprint=valid)
            # Protocol O: emit only inside the block
            inblock = np.zeros_like(values)
            inblock[block] = values[block]
            pO = scoring.score(inblock, truth, known, restrict_to_footprint=valid)
            res_fold["arms"][arm] = {
                "n_novel": int(picked.sum()),
                "mass": float(values.sum()),
                "P": pP, "O": pO,
                "diag": ranking_diagnostics(field, picked, truth, elig),
            }
        res_fold["n_truth_block"] = int(truth.sum())
        res_fold["approved_tiles"] = int(dep.approved.sum())
        res_fold["approved_area_px"] = int(dep.approved.sum()) * dep.tile * dep.tile
        results["folds"].append(res_fold)
        print(f"[{name}] truth={res_fold['n_truth_block']:,} "
              f"approved_tiles={dep.approved.sum()} "
              f"P(A0)={res_fold['arms']['A0_core_shell_only']['P']['dti_masked']:.4f} "
              f"P(A1)={res_fold['arms']['A1_hessianridge_gated']['P']['dti_masked']:.4f} "
              f"P(A2)={res_fold['arms']['A2_steered_gated']['P']['dti_masked']:.4f} "
              f"P(A3)={res_fold['arms']['A3_random_gated']['P']['dti_masked']:.4f} "
              f"P(A4)={res_fold['arms']['A4_hessianridge_ungated']['P']['dti_masked']:.4f}")

    # ---- aggregate
    def agg(arm, proto):
        v = [f["arms"][arm][proto]["dti_masked"] for f in results["folds"]]
        return float(np.mean(v)), v

    aggout = {}
    for arm in results["folds"][0]["arms"]:
        for proto in ("P", "O"):
            m, v = agg(arm, proto)
            aggout.setdefault(arm, {})[proto] = {"mean": m, "per_fold": v}
    contrasts = {}
    for proto in ("P", "O"):
        for base in ("A2_steered_gated", "A3_random_gated", "A0_core_shell_only",
                     "A4_hessianridge_ungated"):
            key = f"A1_hessianridge_gated - {base} [{proto}]"
            diffs = [a - b for a, b in zip(aggout["A1_hessianridge_gated"][proto]["per_fold"],
                                           aggout[base][proto]["per_fold"])]
            contrasts[key] = {
                "mean": float(np.mean(diffs)),
                "per_fold": [float(x) for x in diffs],
                "folds_positive": int(sum(1 for x in diffs if x > 0)),
                "n_folds": len(diffs),
            }
    results["aggregate"] = aggout
    diagout = {}
    for arm in results["folds"][0]["arms"]:
        diagout[arm] = {
            key: float(np.nanmean([f["arms"][arm]["diag"][key] for f in results["folds"]]))
            for key in ("credit_density_novel", "frac_novel_within_3px",
                        "auc_field_vs_block_truth")
        }
    dcontrast = {}
    for base in ("A2_steered_gated", "A3_random_gated"):
        for key in ("credit_density_novel", "auc_field_vs_block_truth"):
            v = [f["arms"]["A1_hessianridge_gated"]["diag"][key] - f["arms"][base]["diag"][key]
                 for f in results["folds"]]
            dcontrast[f"A1-{base} {key}"] = {
                "mean": float(np.nanmean(v)),
                "per_fold": [float(x) for x in v],
                "folds_positive": int(sum(1 for x in v if x > 0)),
            }
    results["aggregate"]["diagnostics"] = diagout
    results["contrasts"] = {**contrasts, **dcontrast}
    promote = (
        contrasts["A1_hessianridge_gated - A3_random_gated [P]"]["mean"] > 0
        and contrasts["A1_hessianridge_gated - A0_core_shell_only [P]"]["mean"] >= 0
        and contrasts["A1_hessianridge_gated - A3_random_gated [P]"]["folds_positive"]
        >= max(3, len(results["folds"]) - 1)
    )
    results["promotion_rule"] = (
        "DECLARED BEFORE THIS RUN (2026-10-06): PROMOTE the unsteered Hessian-ridge "
        "field iff mean(A1 - A3_random)[P] > 0 AND mean(A1 - A0_core_shell_only)[P] >= 0 "
        "AND folds_positive(A1 - A3_random)[P] >= 3.  A2 (steered) and A4 (ungated) are "
        "ablations, not candidates."
    )
    results["promotion_pass"] = bool(promote)
    results["elapsed_s"] = round(time.time() - t0, 1)

    out = out_path or (ROOT / "evidence" / "holdout_run.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=float))
    print(f"\n[holdout] wrote {out} in {results['elapsed_s']} s")
    print(f"[holdout] PROMOTION PASS = {results['promotion_pass']}")
    for k, v in contrasts.items():
        print(f"  {k:52s} mean {v['mean']:+.5f}  folds +{v['folds_positive']}/{v['n_folds']}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", type=int, default=None, help="use an N x N top-left crop")
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--budget", type=int, default=NOVEL_BUDGET)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--shell", type=int, default=1, help="shell radius px (0 = off)")
    ap.add_argument("--decay", type=float, default=0.6)
    a = ap.parse_args()
    run(n_crop=a.crop, folds=a.folds, out_path=Path(a.out) if a.out else None,
        budget=a.budget, shell_radius=a.shell, shell_decay=a.decay)
