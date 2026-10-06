"""Spatially blocked holdout instrument -- scored separately for Stage A and Stage B.

The instrument is deliberately boring and explicit:

  * truth  = the visible catalogue inside the held-out fold (a PROXY; it cannot reward a genuinely
    unmapped fault -- IR-51-06);
  * every fold removes a 600 m buffer around its own catalogue from both training and scoring;
  * rules are compared at MATCHED pixel counts so no contrast can be won by emitting more mass;
  * the promotion gate, copied in spirit from the sibling repositories' preregistered rule, is
    "mean paired contrast > 0 on at least 3 of 4 folds".

Stage A and Stage B are scored in separate calls and their results are reported separately, as the
task requires.  Stage A is scored as a *tile-level* prior (does it concentrate held-out labels?);
Stage B is scored as an *emission rule* under the exact published metric.
"""

from __future__ import annotations

import numpy as np

from . import detector, emission, grid, metric


def stage_b_fold_contrast(beliefs: dict[int, np.ndarray], budget_px: int = 8_000,
                          spacing_px: float = 2.8, n_blocks: int = 2) -> dict:
    """Paired per-fold contrast of emission rules under the exact DTI."""
    cat = grid.catalogue()
    rng = np.random.default_rng(detector.RNG_SEED)
    folds = detector.fold_masks(n_blocks)

    rows = []
    for b, belief in sorted(beliefs.items()):
        test = folds.get(b)
        if test is None or not test.any():
            continue
        ours = detector.rule_credit_density(belief, test, budget_px, spacing_px)
        inc = detector.rule_incumbent(belief, test, budget_px, spacing_px)
        idx = np.flatnonzero(test.ravel())
        pick = rng.choice(idx, min(budget_px, idx.size), replace=False)
        rand = np.zeros(grid.SHAPE, bool)
        rand.ravel()[pick] = True
        r_ours = metric.evaluate_binary(ours, cat, valid=test)
        r_inc = metric.evaluate_binary(inc, cat, valid=test)
        r_rand = metric.evaluate_binary(rand, cat, valid=test)
        rows.append(dict(fold=int(b), test_px=int(test.sum()),
                         n_ours=int(ours.sum()), n_incumbent=int(inc.sum()),
                         dti_ours=r_ours["dti"], dti_incumbent=r_inc["dti"],
                         dti_random=r_rand["dti"],
                         tp_ours=r_ours["tp"], tp_incumbent=r_inc["tp"],
                         d_ours_minus_incumbent=r_ours["dti"] - r_inc["dti"],
                         d_ours_minus_random=r_ours["dti"] - r_rand["dti"]))
    if not rows:
        return dict(folds=[], error="no folds scored")
    d_inc = np.array([r["d_ours_minus_incumbent"] for r in rows])
    d_rand = np.array([r["d_ours_minus_random"] for r in rows])
    out = dict(budget_px=budget_px, spacing_px=spacing_px, folds=rows,
               mean_dti_ours=float(np.mean([r["dti_ours"] for r in rows])),
               mean_dti_incumbent=float(np.mean([r["dti_incumbent"] for r in rows])),
               mean_dti_random=float(np.mean([r["dti_random"] for r in rows])),
               mean_contrast_vs_incumbent=float(d_inc.mean()),
               folds_positive_vs_incumbent=int((d_inc > 0).sum()),
               mean_contrast_vs_random=float(d_rand.mean()),
               folds_positive_vs_random=int((d_rand > 0).sum()),
               n_folds=len(rows),
               promoted=bool((d_inc > 0).sum() >= 3))
    return out


def stage_a_fold_table(stage_a_rows: list[dict], n_blocks: int = 2) -> dict:
    """Report the Stage A tile prior separately (label density lift in approved tiles)."""
    return dict(note="Stage A is reported separately; see strain.stage_a_holdout and "
                     "strain.stage_a_independent_test for the falsification evidence.")
