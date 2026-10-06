"""Stage-2 fine-scale fault detector and the fold machinery around it.

Leakage control
---------------
Two of the sixty features are *context* features: distance to the nearest
catalogued fault pixel and local catalogued-fault density.  They are computed
from the catalogue **that the fold is allowed to see**.  If they were computed
from the full catalogue they would hand the held-out truth straight to the
model, and the holdout would report a number that means nothing.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from .grid import GRID

STACK_PATH_KEY = "stack.dat"


class Stack:
    """Memory-mapped feature stack with fold-dependent context columns."""

    def __init__(self, prepared_dir):
        import json
        from pathlib import Path
        self.dir = Path(prepared_dir)
        self.names = json.loads((self.dir / "stack_names.json").read_text())
        self.n = len(self.names)
        self.data = np.memmap(self.dir / STACK_PATH_KEY, dtype=np.float32, mode="r",
                              shape=(self.n, *GRID.shape))
        self.i_dcat = self.names.index("d_cat")
        self.i_cden = self.names.index("cat_dens")
        # ---------------------------------------------------------------------
        # IR-51-LEAK-01: d_cat and cat_dens are derived from the catalogue, and
        # in this holdout design the training positives ARE catalogue pixels.
        # Every positive therefore has d_cat == 0 and every negative d_cat > 0,
        # so a model given these two columns learns "d_cat == 0" and nothing
        # else -- measured in-block AUC collapsed to exactly 0.500 while the
        # physical features alone reach 0.63.  They are excluded from the model
        # and used only at emission time (as the exclusion radius around known
        # faults, which is physically the same information).
        # ---------------------------------------------------------------------
        self.static = [i for i in range(self.n) if i not in (self.i_dcat, self.i_cden)]

    # ---------------------------------------------------------------- context
    @staticmethod
    def context(catalogue: np.ndarray, density_size: int = 21):
        """(log1p distance to nearest fault px, count of fault px in a density_size window)."""
        d = ndi.distance_transform_edt(~catalogue).astype(np.float32)
        dens = ndi.uniform_filter(catalogue.astype(np.float32), size=density_size,
                                  mode="constant") * float(density_size ** 2)
        return np.log1p(d).astype(np.float32), dens.astype(np.float32)

    # ---------------------------------------------------------------- sampling
    def block_matrix(self, rows: slice, footprint_blk: np.ndarray,
                     extra: list[np.ndarray] | None = None) -> np.ndarray:
        """Feature matrix for every footprint pixel of a row block.

        Rows are read one feature at a time; fancy-indexing the whole
        (58, 3730, 3292) stack at once would materialise a 2.8 GB copy.
        """
        extra = extra or []
        f = len(self.static)
        n = int(footprint_blk.sum())
        X = np.empty((f + len(extra), n), dtype=np.float32)
        for j, i in enumerate(self.static):
            X[j] = np.asarray(self.data[i], dtype=np.float32)[rows][footprint_blk]
        for j, a in enumerate(extra):
            X[f + j] = np.asarray(a, dtype=np.float32)[rows][footprint_blk]
        return X.T

    def sample(self, pos_mask: np.ndarray, neg_pool: np.ndarray, n_neg: int,
               rng: np.random.Generator, extra: list | None = None):
        """Sample a training matrix: all positives + ``n_neg`` background pixels.

        ``extra`` is a list of (name, full-grid array) context columns appended to
        the physical features.  Catalogue-derived columns must NOT be passed here
        (see IR-51-LEAK-01).
        """
        py, px = np.nonzero(pos_mask)
        ny_all, nx_all = np.nonzero(neg_pool)
        k = min(n_neg, ny_all.size)
        sel = rng.choice(ny_all.size, size=k, replace=False)
        ny, nx = ny_all[sel], nx_all[sel]

        feats = self.static
        extra = extra or []
        n_static = len(feats)
        X = np.empty((py.size + k, n_static + len(extra)), dtype=np.float32)
        y = np.zeros(py.size + k, dtype=np.int8)
        y[:py.size] = 1
        all_y = np.concatenate([py, ny])
        all_x = np.concatenate([px, nx])
        del py, px, ny, nx
        for j, i in enumerate(feats):
            col = np.asarray(self.data[i], dtype=np.float32)
            X[:, j] = col[all_y, all_x]
        for j, a in enumerate(extra):
            X[:, n_static + j] = np.asarray(a, dtype=np.float32)[all_y, all_x]
        return X, y


def fit_detector(X: np.ndarray, y: np.ndarray, seed: int = 0, **kw):
    params = dict(loss="log_loss", learning_rate=0.08, max_iter=320,
                  max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0,
                  max_bins=255, early_stopping=False, random_state=seed)
    params.update(kw)
    m = HistGradientBoostingClassifier(**params)
    m.fit(X, y)
    return m


def predict_grid(model, stack: Stack, footprint: np.ndarray,
                 extra: list | None = None, chunk: int = 186) -> np.ndarray:
    """Score every footprint pixel; NaN elsewhere."""
    H, W = GRID.shape
    out = np.full((H, W), np.nan, dtype=np.float32)
    for r0 in range(0, H, chunk):
        r1 = min(r0 + chunk, H)
        rows = slice(r0, r1)
        fb = footprint[rows]
        if not fb.any():
            continue
        X = stack.block_matrix(rows, fb, extra)
        p = model.predict_proba(X)[:, 1].astype(np.float32)
        tmp = out[rows]
        tmp[fb] = p
        out[rows] = tmp
    return out
