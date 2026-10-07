#!/usr/bin/env python3
"""End-to-end pipeline: data -> Stage A -> Stage B -> emission -> submission -> gates -> evidence.

    python3 scripts/run_all.py [--skip-data] [--quick]

Every artefact it writes is listed in registry/claims.json with its evidence file.  It is
deliberately re-runnable: intermediate feature stacks and belief fields are cached under work/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SUBMISSION_NAME = "gemsdoe51-strainbudget-s1-v1"
EMISSION_RULE = "thin"           # promoted rule; "lattice" is the refuted alternative
EMISSION_DENSITY = 0.04          # of the candidate area; peak of the mass sweep
EMISSION_SPACING_PX = 3.0        # minimum separation in px between dots
CATALOGUE_BUFFER_PX = 2.0
STAGE_A_QUANTILE = 0.5
BUILD_BUDGETS = (8_000, 32_000)


def _dump(name: str, obj) -> None:
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / name).write_text(json.dumps(obj, indent=1, default=str) + "\n")
    print(f"  evidence/{name}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--quick", action="store_true", help="fewer folds/prefix steps (debug only)")
    args = ap.parse_args()

    t0 = time.time()
    from gems51 import detector, emission, grid, holdout, metric, paths, strain, submission

    paths.ensure_dirs()
    if not args.skip_data:
        print("[1/8] restoring hash-pinned data ...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_data.py"), "--group", "all"],
                       check=True)

    print("[2/8] grid facts ...", flush=True)
    fp, cat = grid.footprint(), grid.catalogue()
    facts = dict(epsg=grid.EPSG, shape=list(grid.SHAPE), pixel_m=grid.PIXEL_M,
                 transform=[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
                 footprint_px=int(fp.sum()),
                 submission_domain_px=int(grid.submission_domain().sum()),
                 catalogue_positive_px=int(cat.sum()),
                 catalogue_positive_in_footprint_px=int((cat & fp).sum()),
                 n_bands=len(grid.BAND_NAMES), band_names=list(grid.BAND_NAMES))
    _dump("grid_facts.json", facts)

    print("[3/8] Stage A: budget table, holdout, independent test, gate comparison ...", flush=True)
    rows = strain.deficit_table()
    dips = strain.dip_by_sense()
    geod = np.array([r["geodetic_ns_yr"] for r in rows])
    geo = np.array([r["geologic_ns_yr"] for r in rows])
    deficit = np.array([r["deficit"] for r in rows if np.isfinite(r["deficit"])])
    traces = strain.load_traces()
    _dump("stage_a_budget.json", dict(
        n_tiles=len(rows), tile_px=strain.TILE_PX, dip_by_sense_deg=dips,
        n_traces=traces.n, n_traces_in_footprint=int(traces.in_footprint.sum()),
        clipped_length_km_in_footprint=float(traces.length_m[traces.in_footprint].sum() / 1000.0),
        slip_rate_mm_yr=dict(median=float(np.median(traces.slip_rate_mm_yr)),
                             max=float(traces.slip_rate_mm_yr.max())),
        moment_area_rate_mm_m_yr=float((traces.slip_rate_mm_yr * traces.length_m).sum()),
        geodetic_ns_yr=dict(median=float(np.median(geod)), p95=float(np.percentile(geod, 95)),
                            max=float(geod.max())),
        geologic_ns_yr=dict(median=float(np.median(geo)), p95=float(np.percentile(geo, 95)),
                            max=float(geo.max())),
        ratio_geologic_over_geodetic=dict(median=float(np.median(geo / geod)),
                                          p25=float(np.percentile(geo / geod, 25)),
                                          p75=float(np.percentile(geo / geod, 75)),
                                          mean=float(np.mean(geo / geod))),
        deficit=dict(median=float(np.median(deficit)), p25=float(np.percentile(deficit, 25)),
                     p75=float(np.percentile(deficit, 75))),
        formula="eps_geo = (1/(2 A_tile)) * sum_k L_k u_dot_k / sin(dip_k)   [Kostrov 1974; "
                "Kreemer et al. 2000 eq. 3, scalar reduction]"))
    _dump("stage_a_holdout.json", strain.stage_a_holdout())
    _dump("stage_a_independent_test.json", strain.stage_a_independent_test())
    gate = strain.gate_comparison()
    _dump("stage_a_gate_comparison.json", gate)

    print("[4/8] Stage B: spatially blocked folds ...", flush=True)
    res, beliefs = detector.run_folds()
    _dump("stage_b_folds.json", [dict(fold=r.fold, auc=r.auc, n_train_pos=r.n_train_pos,
                                      n_train_neg=r.n_train_neg, test_px=r.test_px) for r in res])
    np.savez_compressed(ROOT / "work" / "beliefs.npz",
                        **{f"f{k}": v.astype(np.float16) for k, v in beliefs.items()})

    print("[5/8] detector comparison against the sibling published OOF fields ...", flush=True)
    from sklearn.metrics import roc_auc_score
    folds = detector.fold_masks(2)
    oof_files = {"oof_B": paths.EXTERNAL / "oof_B_19_plus_lidar_u16.npz",
                 "oof_D": paths.EXTERNAL / "oof_D_19_plus_lidar_radiometric_u16.npz"}
    auc_rows, contrasts, sweep, packer_rows = [], [], {}, []
    for b, belief in sorted(beliefs.items()):
        test = folds[b]
        lab = cat[test]
        rec = dict(fold=b, test_px=int(test.sum()),
                   auc_ours=float(roc_auc_score(lab, belief[test])))
        for nm, f in oof_files.items():
            if f.exists():
                rec[f"auc_{nm}"] = float(roc_auc_score(
                    lab, np.load(f)["probability_u16"].astype(np.float32)[test] / 65535.0))
        auc_rows.append(rec)
        for budget in BUILD_BUDGETS:
            m_ours = detector.rule_incumbent(belief, test, budget, EMISSION_SPACING_PX)
            d_ours = metric.evaluate_binary(m_ours, cat, valid=test)["dti"]
            row = dict(fold=b, budget=budget, dti_ours=d_ours)
            for nm, f in oof_files.items():
                if f.exists():
                    other = np.load(f)["probability_u16"].astype(np.float32) / 65535.0
                    m_th = detector.rule_incumbent(other, test, budget, EMISSION_SPACING_PX)
                    row[f"dti_{nm}"] = metric.evaluate_binary(m_th, cat, valid=test)["dti"]
                    row[f"delta_vs_{nm}"] = row["dti_ours"] - row[f"dti_{nm}"]
            contrasts.append(row)
        avail = int(test.sum())
        for dens in (0.005, 0.01, 0.02, 0.04, 0.08):
            n = max(1, int(dens * avail))
            m = detector.rule_incumbent(belief, test, n, EMISSION_SPACING_PX)
            sweep.setdefault(f"{dens}", []).append(
                metric.evaluate_binary(m, cat, valid=test)["dti"])
        # Alternative emitter: redundancy-aware expected-budget packing, at a matched budget.
        for budget in BUILD_BUDGETS:
            packer = emission.ExpectedBudgetPacker(spacing_px=EMISSION_SPACING_PX, n_prefix=36,
                                                   max_dots=budget)
            p = packer.pack(belief, test)
            n_best = max(1, int(p.best_count))
            m_pack = np.zeros(grid.SHAPE, bool)
            if p.rows.size:
                m_pack[p.rows[:n_best], p.cols[:n_best]] = True
            m_inc = detector.rule_incumbent(belief, test, n_best, EMISSION_SPACING_PX)
            packer_rows.append(dict(
                fold=b, budget=budget, n_chosen=n_best,
                dti_packer=metric.evaluate_binary(m_pack, cat, valid=test)["dti"],
                dti_incumbent_matched=metric.evaluate_binary(m_inc, cat, valid=test)["dti"],
                dti_pred=float(p.dti_pred[min(int(np.argmax(p.dti_pred)), p.dti_pred.size - 1)]),
                contrast=None))
    _dump("auc_comparison.json", auc_rows)
    _dump("detector_contrast.json", dict(contrasts=contrasts, mass_sweep_mean={
        k: float(np.mean(v)) for k, v in sweep.items()},
        note="same emitter (belief-priority dot-thin), different belief field, matched mass"))
    spacing = {}
    for sp in (2.0, 2.8, 3.5):
        per = []
        for b, belief in sorted(beliefs.items()):
            test = folds[b]
            m = detector.rule_incumbent(belief, test, 8_000, sp)
            per.append(metric.evaluate_binary(m, cat, valid=test)["dti"])
        spacing[f"{sp}"] = per
    _dump("emission_sweep.json", dict(spacing_at_budget_8000=spacing,
                                      mean={k: float(np.mean(v)) for k, v in spacing.items()},
                                      chosen_spacing_px=EMISSION_SPACING_PX))
    for r in packer_rows:
        r["contrast"] = r["dti_packer"] - r["dti_incumbent_matched"]
    _dump("holdout_packer.json", dict(
        rows=packer_rows,
        mean_contrast=float(np.mean([r["contrast"] for r in packer_rows])) if packer_rows else None,
        folds_positive=int(sum(r["contrast"] > 0 for r in packer_rows)),
        n_folds=len(packer_rows),
        promoted=bool(packer_rows and np.mean([r["contrast"] for r in packer_rows]) > 0
                      and sum(r["contrast"] > 0 for r in packer_rows) >= 0.75 * len(packer_rows)),
        criterion="mean paired contrast > 0 AND positive on >= 75% of the paired rows (3/4 folds, "
                  "6/8 fold-budget rows); a raw count of 3 was NOT a valid threshold for an "
                  "eight-row design and was corrected here.", 
        note="ExpectedBudgetPacker vs the incumbent dot-thin rule at a matched dot count. "
             "dti_pred is the packer's own self-prediction and was found badly calibrated "
             "(predicts ~0.49 where ~0.27 is realized); it is recorded for audit, never used "
             "to size the emission."))
    _dump("holdout_stage_b.json", holdout.stage_b_fold_contrast(beliefs, budget_px=8_000,
                                                                spacing_px=EMISSION_SPACING_PX))

    print("[6/8] production model + emission ...", flush=True)
    stack = detector.load_or_build(verbose=False)
    from sklearn.ensemble import HistGradientBoostingClassifier
    rng = np.random.default_rng(detector.RNG_SEED)
    X, y = detector._sample_training(stack, cat, fp, rng)
    model = HistGradientBoostingClassifier(max_iter=220, learning_rate=0.08, max_leaf_nodes=31,
                                           min_samples_leaf=40, l2_regularization=1.0,
                                           random_state=detector.RNG_SEED, early_stopping=False)
    model.fit(X, y)
    belief_full = detector.predict_full_grid(model, stack)
    approved = submission.approved_mask_from_stage_a(STAGE_A_QUANTILE)
    cand = submission.candidate_mask(approved, CATALOGUE_BUFFER_PX)
    mask, emit_info = submission.build_emission(belief_full, approved, CATALOGUE_BUFFER_PX,
                                                rule=EMISSION_RULE, density=EMISSION_DENSITY,
                                                spacing=EMISSION_SPACING_PX)
    np.save(ROOT / "work" / "approved_mask.npy", approved)
    np.save(ROOT / "work" / "candidate_mask.npy", cand)
    np.save(ROOT / "work" / "emission_mask.npy", mask)
    audit = metric.credit_audit(mask)
    _dump("emission_audit.json", dict(
        **{k: v for k, v in emit_info.items() if k != "n_emitted"},
        n_emitted=audit.n_emitted, total_mass=audit.total_mass,
        redundancy_fraction=audit.redundancy_fraction,
        mean_self_kernel=audit.mean_self_kernel,
        approved_px=int(approved.sum())))
    # Promotion record: it is the FAITHFUL off-catalogue A/B instrument that decides, not the
    # catalogue-subsample sweep.  See the module docstring of scripts/run_offcat_holdout.py.
    sw_path = ROOT / "evidence" / "strategy_sweep.json"
    of_path = ROOT / "evidence" / "offcat_holdout.json"
    if sw_path.exists() and of_path.exists():
        sw = json.loads(sw_path.read_text())
        of = json.loads(of_path.read_text())
        inc = {r["fold"]: r for r in sw["rows"]
               if r["truth"] == "thin20" and r["strategy"].startswith("incumbent")}
        lat = {r["fold"]: r for r in sw["rows"]
               if r["truth"] == "thin20" and r["strategy"] == "lattice_q0.1_s3_p0"}
        pairs = [dict(fold=f, dti_lattice=lat[f]["dti"], dti_incumbent=inc[f]["dti"],
                      delta=lat[f]["dti"] - inc[f]["dti"],
                      n_lattice=lat[f]["n_px"], n_incumbent=inc[f]["n_px"])
                 for f in sorted(set(inc) & set(lat))]
        deltas = [p["delta"] for p in pairs]
        lat20 = of["paired"].get("lattice_q0.20_s3|B_far", {})
        lat10 = of["paired"].get("lattice_q0.10_s3|B_far", {})
        thin = of["paired"]
        # the shipped rule's own numbers on the faithful instrument: mean DTI, not a delta
        rows = [r for r in of["results"] if r["rule"] == "thin_d0.04_s3.0"]
        shipped_mean = float(np.mean([r.get("dti_B_far", np.nan) for r in rows]))
        _dump("emission_promotion.json", dict(
            shipped_rule="thin dots, belief priority, 4% of the candidate area, min separation 3 px",
            shipped_rule_mean_dti_B_far=shipped_mean,
            catalogue_subsample_sweep=dict(
                instrument="PROXY: truth = seeded 20% subsample of the visible catalogue",
                lattice_vs_thin_pairs=pairs,
                mean_delta=float(np.mean(deltas)) if deltas else None,
                folds_positive=int(sum(d > 0 for d in deltas)), n_folds=len(pairs),
                apparent_promotion=bool(deltas and np.mean(deltas) > 0
                                        and sum(d > 0 for d in deltas) >= 3)),
            offcat_instrument=dict(
                instrument="FAITHFUL: fault systems split A/B, trained on A, truth = B, official DTI",
                note="this is the instrument that decides; its per-fold rows are in "
                     "evidence/offcat_holdout.json",
                **{"lattice_q0.10_s3_B_far": lat10, "lattice_q0.20_s3_B_far": lat20,
                   "lattice_q0.10_s3_B_all": of["paired"].get("lattice_q0.10_s3|B_all", {}),
                   "lattice_q0.20_s3_B_all": of["paired"].get("lattice_q0.20_s3|B_all", {})}),
            decision="The coverage-lattice promotion was REFUTED by the faithful instrument "
                     "(-0.0104 mean paired DTI, 1/4 folds at q0.10; +0.0040 but only 2/4 folds at "
                     "q0.20). Under the pre-registered rule (mean > 0 AND >=3/4 folds positive) "
                     "no lattice is promoted, so the incumbent thin-dot rule ships.",
            lesson="A promotion validated only against a subsample of the visible catalogue did not "
                   "survive a holdout that withholds whole fault systems. This is exactly what the "
                   "standing instruction to validate before spending a slot is for."))

    print("[7/8] submission + gates ...", flush=True)
    note = ("GEMSDOE51 | S1 strain-gate + S2 blocked-CV 44-ch detector, sparse off-catalogue dots, "
            "stage-A deficit reported as falsified; UNSCORED")
    receipt = submission.write_submission(emission.to_values(mask), SUBMISSION_NAME, note)
    _dump("submission_receipt.json", receipt)
    _dump("uniqueness_gate.json", submission.uniqueness_gate(mask))
    _dump("stage_dominance.json", submission.stage_dominance_check(mask, approved, cand))

    print("[8/8] done in %.1f s" % (time.time() - t0), flush=True)
    print(json.dumps({k: receipt[k] for k in ("name", "n_positive", "min", "max", "n_nan",
                                              "sha256", "all_finite", "in_0_1")}, indent=1))


if __name__ == "__main__":
    main()
