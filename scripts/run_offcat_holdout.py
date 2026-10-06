#!/usr/bin/env python3
"""Faithful OFF-CATALOGUE holdout: split the visible catalogue into fault systems A and B, train the
detector on A alone, and score emission rules against B.

Why this instrument matters
---------------------------
The ancestor repositories validated emission rules against the *visible* catalogue, then emitted
dots 200 m away from it.  That instrument cannot see the real failure mode: a belief field trained
on the catalogue is most confident exactly where the catalogue already is, so a rule can win on the
instrument while shipping emission that is a halo around known faults -- worthless on a hidden set
defined as "faults the catalogue does not contain".

This script builds the closest legitimate instrument available offline:

  * fault SYSTEMS (8-connected components of the catalogue raster) are split into A (training) and
    B (truth), balanced by pixel count, seeded;
  * the detector is trained on A only.  Every non-A pixel is a negative -- including B pixels,
    exactly as in the real task where unmapped faults sit inside the "negative" class;
  * folds are the same 2x2 spatial blocks with a 600 m boundary band removed; belief is predicted
    inside the held-out block only;
  * every emission rule must respect the production constraints: inside the held-out block, at
    least 2 px from any A pixel (the "off-catalogue" rule), and inside the Stage-A approved tiles;
  * DTI is computed against B with the official metric and weights.

Two truth variants are reported:
  B_all    -- all B pixels
  B_far    -- only B components whose minimum distance to A is >= 5 px (>= 500 m), i.e. structures
              that are not merely an interleaved strand of a mapped fault zone.

Known bias, stated up front: B faults are drawn from the same compilation as A and are therefore
interleaved with it; B_far reduces but does not remove that bias.  A halo-style rule will look
better here than it deserves.  evidence/offcat_holdout.json records the halo control explicitly so
the reader can see the size of that effect.

    python3 scripts/run_offcat_holdout.py [--folds 0,1] [--quick]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label as ndlabel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import detector, features, grid, metric, paths, submission  # noqa: E402

RNG_SEED = 51
NEG_PER_POS = 3
MAX_TRAIN_PX = 220_000
CAT_BUFFER_PX = 2.0
APPROVED_Q = 0.5
THIN_DENSITY = 0.04          # the ancestor rule: dots at 4% of the candidate area
THIN_SPACING = 3.0
LATTICES = [(0.90, 3), (0.95, 3), (0.80, 3), (0.90, 2), (0.90, 4), (0.90, 5), (0.70, 3)]
HALO_RING = (2.0, 5.0)       # px from A; control for "just emit around the catalogue"


def split_components(cat: np.ndarray, fp: np.ndarray, rng: np.random.Generator,
                     min_px: int = 30) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split catalogue fault systems into A (train) and B (truth), balanced by pixel count."""
    lab, n = ndlabel(cat & fp, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    comps = [i for i in range(1, n + 1) if sizes[i] >= min_px]
    rng.shuffle(comps)
    total = sum(sizes[i] for i in comps)
    a_mask = np.zeros(grid.SHAPE, bool)
    b_ids, acc = [], 0
    for i in comps:
        if acc < total / 2:
            acc += sizes[i]
            b_ids.append(i)
    b_mask = np.isin(lab, b_ids) if b_ids else np.zeros(grid.SHAPE, bool)
    a_mask = np.isin(lab, [i for i in comps if i not in set(b_ids)])
    return a_mask, b_mask, lab


def belief_for_fold(stack, a_mask: np.ndarray, train_mask: np.ndarray, rng,
                    rows0: int, rows1: int) -> np.ndarray:
    """Train HistGBM on A pixels inside train_mask, return the belief field over rows [rows0, rows1)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    pos = np.flatnonzero((a_mask & train_mask).ravel())
    if pos.size == 0:
        raise RuntimeError("no training positives in this fold -- check the A/B split")
    if pos.size > MAX_TRAIN_PX // (1 + NEG_PER_POS):
        pos = rng.choice(pos, MAX_TRAIN_PX // (1 + NEG_PER_POS), replace=False)
    neg_pool = np.flatnonzero((~a_mask & train_mask).ravel())
    n_neg = min(neg_pool.size, max(pos.size * NEG_PER_POS, 20_000))
    neg = rng.choice(neg_pool, n_neg, replace=False)
    idx = np.concatenate([pos, neg])
    rows, cols = np.unravel_index(idx, grid.SHAPE)
    X = np.empty((idx.size, stack.shape[0]), dtype=np.float32)
    for k in range(stack.shape[0]):
        X[:, k] = stack[k][rows, cols]
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)]).astype(np.int8)
    model = HistGradientBoostingClassifier(max_iter=220, learning_rate=0.08, max_leaf_nodes=31,
                                          min_samples_leaf=40, l2_regularization=1.0,
                                          random_state=RNG_SEED, early_stopping=False)
    model.fit(X, y)
    cols_n = grid.SHAPE[1]
    block = 200
    out = np.zeros((rows1 - rows0, cols_n), dtype=np.float32)
    for s0 in range(rows0, rows1, block):
        s1 = min(s0 + block, rows1)
        Xb = np.empty((stack.shape[0], (s1 - s0) * cols_n), dtype=np.float32)
        for k in range(stack.shape[0]):
            Xb[k] = stack[k, s0:s1, :].ravel()
        Xb = np.nan_to_num(Xb, nan=0.0, posinf=0.0, neginf=0.0).T
        out[s0 - rows0:s1 - rows0, :] = model.predict_proba(Xb)[:, 1].reshape(s1 - s0, cols_n)
    return out


def lattice(mask: np.ndarray, spacing: int, phase: int = 0) -> np.ndarray:
    out = np.zeros(grid.SHAPE, bool)
    out[phase::spacing, phase::spacing] = mask[phase::spacing, phase::spacing]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", default="0,1,2,3")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    folds_wanted = [int(x) for x in args.folds.split(",") if x != ""]
    t0 = time.time()

    paths.ensure_dirs()
    stack = features.load_or_build(verbose=True)
    cat = grid.catalogue()
    fp = grid.footprint()
    rng = np.random.default_rng(RNG_SEED)
    a_mask, b_mask, lab = split_components(cat, fp, rng)
    d_a = distance_transform_edt(~(a_mask & fp))
    # B_far: components of B whose minimum distance to A exceeds 5 px
    lab_b = np.where(b_mask, lab, 0)
    far_ids = []
    for i in np.unique(lab_b):
        if i == 0:
            continue
        m = lab_b == i
        if d_a[m].min() >= 5.0:
            far_ids.append(int(i))
    b_far = np.isin(lab_b, far_ids) if far_ids else np.zeros(grid.SHAPE, bool)
    print(f"A={int(a_mask.sum())} px  B={int(b_mask.sum())} px  B_far={int(b_far.sum())} px "
          f"({len(far_ids)} components)  [{time.time() - t0:.0f}s]", flush=True)

    approved = submission.approved_mask_from_stage_a(APPROVED_Q)
    block = grid.spatial_blocks(2)
    rows_n = grid.SHAPE[0]
    per_r = int(np.ceil(rows_n / 2))

    results = []
    for b in folds_wanted:
        rows0, rows1 = divmod(b, 2)
        r0, r1 = rows0 * per_r, min((rows0 + 1) * per_r, rows_n)
        m = block == b
        d_in = distance_transform_edt(m)
        test_block = m & (d_in > detector.BUFFER_PX) & fp
        train_ok = np.zeros(grid.SHAPE, bool)
        for k in range(4):
            if k == b:
                continue
            mk = block == k
            train_ok |= mk & (distance_transform_edt(mk) > detector.BUFFER_PX)
        belief = np.zeros(grid.SHAPE, np.float32)
        bloc = belief_for_fold(stack, a_mask, train_ok, rng, r0, r1)
        belief[r0:r1, :] = bloc
        cand = test_block & approved & (d_a >= CAT_BUFFER_PX)
        n_cand = int(cand.sum())
        print(f"fold {b}: candidate {n_cand} px, belief max {bloc.max():.3f} "
              f"[{time.time() - t0:.0f}s]", flush=True)

        rules: dict[str, np.ndarray] = {}
        n_thin = max(1, int(round(THIN_DENSITY * n_cand)))
        rules["thin_d0.04_s3.0"] = detector.rule_incumbent(belief, cand, n_thin, THIN_SPACING)
        # Mass is a DECISION VARIABLE, not a constant: the hidden label set is believed to be
        # ~5x sparser than the visible catalogue, and under DTI = T/(0.2T + 0.2F + 0.8K) every
        # dot that misses costs 0.2 while every truth pixel pays at most 1.  These arms are
        # deliberately NOT mass-matched to the incumbent -- that is the point of the test -- and
        # they are paired per fold against thin_d0.04_s3.0 below.
        for d in (0.01, 0.02, 0.03, 0.06, 0.08):
            rules[f"thin_d{d:.2f}_s3.0"] = detector.rule_incumbent(
                belief, cand, int(d * cand.sum()), THIN_SPACING)
        tb = belief[cand]
        for q, s in LATTICES:
            thr = float(np.quantile(tb, q)) if tb.size else 1.0
            region = cand & (belief >= thr)
            rules[f"lattice_q{1 - q:.2f}_s{s}"] = lattice(region, s, 0)
        ring = cand & (d_a >= HALO_RING[0]) & (d_a < HALO_RING[1])
        rules["halo_ring_2_5px_s3"] = lattice(ring, 3, 0)
        rules["uniform_s3"] = lattice(cand, 3, 0)
        if args.quick:
            rules = {k: v for k, v in rules.items() if k in
                     ("thin_d0.04_s3.0", "lattice_q0.10_s3")}

        for rule, mask in rules.items():
            rec = dict(fold=b, rule=rule, n_px=int(mask.sum()))
            for tname, truth in (("B_all", b_mask & test_block), ("B_far", b_far & test_block)):
                if truth.sum() == 0:
                    continue
                r = metric.evaluate_binary(mask, truth, valid=test_block)
                rec[f"dti_{tname}"] = r["dti"]
                rec[f"T_{tname}"] = r["tp"]
                rec[f"F_{tname}"] = r["fp"]
                rec[f"K_{tname}"] = r["tp"] + r["fn"]
            results.append(rec)

    # paired contrasts vs the ancestor thin-dot rule, per fold and truth variant
    paired = {}
    for tname in ("B_all", "B_far"):
        for rule in sorted({r["rule"] for r in results} - {"thin_d0.04_s3.0"}):
            deltas = []
            for b in folds_wanted:
                base = next((r for r in results if r["fold"] == b and
                             r["rule"] == "thin_d0.04_s3.0"), None)
                alt = next((r for r in results if r["fold"] == b and r["rule"] == rule), None)
                if base and alt and f"dti_{tname}" in base and f"dti_{tname}" in alt:
                    deltas.append(alt[f"dti_{tname}"] - base[f"dti_{tname}"])
            if deltas:
                paired[f"{rule}|{tname}"] = dict(
                    mean_delta=float(np.mean(deltas)), folds_positive=int(sum(d > 0 for d in deltas)),
                    n_folds=len(deltas), per_fold=[float(d) for d in deltas])

    out = dict(
        instrument="off-catalogue A/B fault-system split, spatially blocked folds, official DTI",
        fold_buffer_px=detector.BUFFER_PX, catalogue_buffer_px=CAT_BUFFER_PX,
        approved_quantile=APPROVED_Q, a_px=int(a_mask.sum()), b_px=int(b_mask.sum()),
        b_far_px=int(b_far.sum()), n_b_far_components=len(far_ids),
        known_bias="B faults come from the same compilation as A and are interleaved with it, so a "
                   "rule that emits a halo around A scores better here than it would on genuinely "
                   "unmapped structures. The halo control quantifies that effect.",
        results=results, paired=paired)
    (ROOT / "evidence" / "offcat_holdout.json").write_text(json.dumps(out, indent=1) + "\n")

    print(f"\n=== mean DTI by rule (folds {folds_wanted}) [{time.time() - t0:.0f}s]")
    for tname in ("B_all", "B_far"):
        rows = [r for r in results if f"dti_{tname}" in r]
        if not rows:
            continue
        by = {}
        for r in rows:
            by.setdefault(r["rule"], []).append(r[f"dti_{tname}"])
        print(f"-- truth {tname}")
        for rule, vals in sorted(by.items(), key=lambda kv: -np.mean(kv[1])):
            print(f"   {np.mean(vals):.4f} (n={len(vals)}) {rule}")
    print("\n=== paired vs thin_d0.04_s3.0")
    for k, v in sorted(paired.items(), key=lambda kv: -kv[1]["mean_delta"]):
        print(f"   {v['mean_delta']:+.4f}  {v['folds_positive']}/{v['n_folds']}  {k}")


if __name__ == "__main__":
    main()
