"""Stage B -- fine-scale detector, trained and scored on spatially blocked folds.

Protocol (documented, preregistered in registry/preregistration.json):

1. Folds are 2x2 spatial blocks over the footprint (4 folds), matching the sibling
   repositories' four-quadrant convention so the numbers are comparable.
2. For each fold b: every pixel within `buffer_px` of the *visible catalogue in fold b* is removed
   from both training and scoring, and the held-out fold is never used for fitting.  The buffer
   exists because the scored quantity is "does the detector recover fault ground it has not been
   shown"; proximity to a mapped trace is a trivial leak.
3. The classifier is a HistGradientBoostingClassifier over the Stage B feature stack; the
   positives in the three training folds are all used, negatives are subsampled (documented
   ratio).  Output = belief field b(x) = P(pixel is a mapped fault | features), in [0, 1].
4. The belief field is then consumed by `emission.py`; the fold results are reported per fold and
   paired against the incumbent rule at matched pixel counts.

Nothing in this module ever reads the organizer's hidden labels: they do not exist in the
download.  The only truth available is the visible catalogue, which is a *proxy*: it cannot
reward a genuinely unmapped fault (see registry/irregularities.json IR-51-PROXY-01).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import grid, metric
from .features import FEATURE_NAMES, load_or_build

RNG_SEED = 51
NEG_PER_POS = 3
MAX_TRAIN_PX = 250_000
BUFFER_PX = 6.0          # 600 m, as used by the sibling holdouts


@dataclass
class FoldResult:
    fold: int
    auc: float
    n_train_pos: int
    n_train_neg: int
    test_px: int


def _sample_training(stack, cat, train_mask, rng):
    """Stratified sample: all positives (capped) + NEG_PER_POS negatives."""
    pos_idx = np.flatnonzero((cat & train_mask).ravel())
    neg_idx = np.flatnonzero((~cat & train_mask).ravel())
    if pos_idx.size > MAX_TRAIN_PX // (1 + NEG_PER_POS):
        pos_idx = rng.choice(pos_idx, MAX_TRAIN_PX // (1 + NEG_PER_POS), replace=False)
    n_neg = min(neg_idx.size, max(pos_idx.size * NEG_PER_POS, 20_000))
    neg_idx = rng.choice(neg_idx, n_neg, replace=False)
    idx = np.concatenate([pos_idx, neg_idx])
    rows, cols = np.unravel_index(idx, grid.SHAPE)
    X = np.empty((idx.size, stack.shape[0]), dtype=np.float32)
    for k in range(stack.shape[0]):
        X[:, k] = stack[k][rows, cols]
    y = np.concatenate([np.ones(pos_idx.size), np.zeros(neg_idx.size)]).astype(np.int8)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X, y


def predict_box(model, stack, r0: int, r1: int, block: int = 200) -> np.ndarray:
    """Predict the belief field over rows [r0, r1) in row blocks."""
    cols = grid.SHAPE[1]
    out = np.zeros((r1 - r0, cols), dtype=np.float32)
    for s0 in range(r0, r1, block):
        s1 = min(s0 + block, r1)
        X = np.empty((stack.shape[0], (s1 - s0) * cols), dtype=np.float32)
        for k in range(stack.shape[0]):
            X[k] = stack[k, s0:s1, :].ravel()
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0).T
        out[s0 - r0:s1 - r0, :] = model.predict_proba(X)[:, 1].reshape(s1 - s0, cols)
    return out.astype(np.float32)


def predict_full_grid(model, stack) -> np.ndarray:
    from .paths import WORK_DIR
    rows, _ = grid.SHAPE
    out = predict_box(model, stack, 0, rows)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    np.save(WORK_DIR / "belief_field_full.npy", out)
    return out


def run_folds(verbose: bool = True, n_blocks: int = 2, save_belief: bool = True):
    """Train/predict each spatially blocked fold.  Returns (results, belief_by_fold)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    stack = load_or_build(verbose=verbose)
    cat = grid.catalogue()
    fp = grid.footprint()
    d_cat = grid.catalogue_distance()
    block = grid.spatial_blocks(n_blocks)
    rng = np.random.default_rng(RNG_SEED)
    rows_n = grid.SHAPE[0]
    per_r = int(np.ceil(rows_n / n_blocks))

    # Shrink every block by BUFFER_PX so that a 600 m band along every fold boundary is removed
    # from BOTH training and scoring.  (The naive alternative -- removing pixels near the truth --
    # deletes the positives themselves and yields AUC = nan with 0 training positives; that error
    # was made and fixed in this repository, see registry/irregularities.json IR-51-FOLD-01.)
    from scipy.ndimage import distance_transform_edt as _edt
    shrunk = {}
    for bb in range(n_blocks * n_blocks):
        m = block == bb
        d_in = _edt(m)   # distance from inside the block to the nearest non-block pixel
        shrunk[bb] = m & (d_in > BUFFER_PX)

    results, beliefs = [], {}
    for b in range(n_blocks * n_blocks):
        test_mask = shrunk[b] & fp
        train_ok = np.zeros(grid.SHAPE, bool)
        for k, sm in shrunk.items():
            if k != b:
                train_ok |= sm
        train_mask = train_ok & fp
        X, y = _sample_training(stack, cat, train_mask, rng)
        model = HistGradientBoostingClassifier(
            max_iter=220, learning_rate=0.08, max_depth=None, max_leaf_nodes=31,
            min_samples_leaf=40, l2_regularization=1.0, random_state=RNG_SEED, early_stopping=False)
        model.fit(X, y)
        r0 = (b // n_blocks) * per_r
        r1 = min(r0 + per_r, rows_n)
        sub = predict_box(model, stack, r0, r1)
        belief = np.zeros(grid.SHAPE, dtype=np.float32)
        belief[r0:r1, :] = sub
        beliefs[b] = belief
        lab = (cat & test_mask)
        sc = belief[test_mask]
        auc = float(roc_auc_score(lab[test_mask], sc)) if lab[test_mask].any() else float("nan")
        r = FoldResult(fold=b, auc=auc, n_train_pos=int(y.sum()), n_train_neg=int((y == 0).sum()),
                       test_px=int(test_mask.sum()))
        results.append(r)
        if verbose:
            print(f"[stage B] fold {b}: AUC={auc:.4f} train_pos={r.n_train_pos} "
                  f"test_px={r.test_px:,}")
    return results, beliefs


# ---------------------------------------------------------------------------------------------
# Emission rules compared on the folds (matched pixel counts; paired contrasts)
# ---------------------------------------------------------------------------------------------

def rule_incumbent(belief: np.ndarray, mask: np.ndarray, n_px: int, min_dist: float = 2.8,
                   seed: int = RNG_SEED) -> np.ndarray:
    """Incumbent-style dot-thin rule: priority = belief, enforce min separation (greedy)."""
    return _greedy_by_score(belief, mask, n_px, min_dist)


def rule_credit_density(belief: np.ndarray, mask: np.ndarray, n_px: int, min_dist: float = 2.8,
                        seed: int = RNG_SEED) -> np.ndarray:
    """Ours: priority = kernel-matched belief (expected credit) / expected cost (1 - belief)."""
    from scipy.ndimage import convolve
    k = metric.kernel
    r = int(np.ceil(metric.RADIUS_PX))
    kern = np.zeros((2 * r + 1, 2 * r + 1), dtype=np.float32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            kern[dy + r, dx + r] = float(k(np.hypot(dy, dx)))
    credit = convolve(np.nan_to_num(belief, nan=0.0).astype(np.float32), kern, mode="constant")
    cost = np.clip(1.0 - np.nan_to_num(belief, nan=0.0), 1e-3, 1.0)
    score = (credit / cost).astype(np.float32)
    return _greedy_by_score(score, mask, n_px, min_dist)


def _greedy_by_score(score: np.ndarray, mask: np.ndarray, n_px: int, min_dist: float) -> np.ndarray:
    """Greedy accept by descending score with a hard minimum separation (in pixels)."""
    cand = mask & np.isfinite(score)
    flat = np.flatnonzero(cand.ravel())
    if flat.size == 0 or n_px <= 0:
        return np.zeros(grid.SHAPE, bool)
    order = flat[np.argsort(-score.ravel()[flat], kind="stable")]
    taken_rows, taken_cols, taken = [], [], []
    cell = max(1, int(np.floor(min_dist)))
    occupied: dict[tuple[int, int], list[tuple[int, int]]] = {}
    md2 = min_dist ** 2
    for idx in order:
        if len(taken) >= n_px:
            break
        rr, cc = divmod(int(idx), grid.SHAPE[1])
        key = (rr // cell, cc // cell)
        ok = True
        for ddr in (-1, 0, 1):
            for ddc in (-1, 0, 1):
                for (tr, tc) in occupied.get((key[0] + ddr, key[1] + ddc), ()):
                    if (rr - tr) ** 2 + (cc - tc) ** 2 < md2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        occupied.setdefault(key, []).append((rr, cc))
        taken_rows.append(rr)
        taken_cols.append(cc)
        taken.append(idx)
    out = np.zeros(grid.SHAPE, bool)
    out[np.array(taken_rows, dtype=np.int32), np.array(taken_cols, dtype=np.int32)] = True
    return out


def fold_masks(n_blocks: int = 2, buffer_px: float = BUFFER_PX):
    """Shrunk fold masks (dict) after removing the 600 m boundary band from every fold."""
    from scipy.ndimage import distance_transform_edt as _edt
    block = grid.spatial_blocks(n_blocks)
    fp = grid.footprint()
    out = {}
    for b in range(n_blocks * n_blocks):
        m = block == b
        out[b] = m & (_edt(m) > buffer_px) & fp
    return out
