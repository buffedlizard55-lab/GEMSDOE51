"""Spatially blocked holdout: a proxy instrument for *hidden* faults.

Why this instrument
-------------------
The scored truth (newly identified faults) is not public, so no local number can
be a score.  What we can do is the standard substitution: hold out a contiguous
spatial block of the *visible* catalogue, forbid the detector from ever seeing
that block, and score it as if those pixels were new discoveries.  Everything
outside the block is treated as "known" and therefore **masked**, exactly as the
organizer says the real scorer does
(https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516).

The instrument is biased and we say so:
  * its truth is the visible catalogue, so it can only reward rediscovering the
    *kind* of fault that is already mapped -- never a genuinely new style;
  * the held-out block is not masked against its own neighbours, so a prediction
    within 300 m of the block edge is credited more easily than in the real
    scoring, where the neighbouring known fault pixels are masked too.
A pass on this instrument licenses packaging a candidate.  It is never a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import numpy as np
from scipy import ndimage as ndi


def blocked_folds(shape: tuple[int, int], footprint: np.ndarray,
                  n_rows: int = 3, n_cols: int = 3, min_truth: int = 500):
    """Split the raster into n_rows x n_cols contiguous blocks; each block is a fold.

    Blocks containing fewer than ``min_truth`` catalogue pixels are dropped --
    a fold with a handful of truth pixels has a hopelessly noisy DTI.
    """
    H, W = shape
    folds = []
    rs = np.array_split(np.arange(H), n_rows)
    cs = np.array_split(np.arange(W), n_cols)
    for br in rs:
        for bc in cs:
            blk = np.zeros(shape, bool)
            blk[br[0]:br[-1] + 1, bc[0]:bc[-1] + 1] = True
            blk &= footprint
            folds.append(blk)
    return [b for b in folds]


@dataclass
class FoldSpec:
    index: int
    truth: np.ndarray        # catalogue pixels held out (pretend-new faults)
    known: np.ndarray        # catalogue pixels treated as already known (masked by the scorer)
    train_pos: np.ndarray    # catalogue pixels the detector may learn from
    train_neg_pool: np.ndarray  # candidate background pixels the detector may learn from
    scored: np.ndarray       # valid & ~known: the domain the scorer actually sees
    block: np.ndarray        # the held-out block itself (for in-block diagnostics)
    buffer_px: int = 0

    @property
    def n_truth(self) -> int:
        return int(self.truth.sum())


def make_folds(footprint: np.ndarray, catalogue: np.ndarray, buffer_px: int = 12,
               n_rows: int = 3, n_cols: int = 3, min_truth: int = 500):
    """Build fold specs with an exclusion buffer around the held-out block.

    ``buffer_px`` pixels on either side of the block boundary are removed from
    the training pool so that a detector cannot win by memorising the faults
    that run straight through the boundary.
    """
    blocks = blocked_folds(footprint.shape, footprint, n_rows, n_cols)
    kept = [b for b in blocks if int((b & catalogue).sum()) >= min_truth]
    out = []
    for i, blk in enumerate(kept):
        # the held-out block, dilated by buffer_px, is off-limits for training
        grow = ndi.binary_dilation(blk, structure=np.ones((3, 3)), iterations=max(buffer_px, 0))
        forbidden = grow & footprint
        train_pos = catalogue & ~forbidden
        train_neg_pool = footprint & ~catalogue & ~forbidden
        out.append(FoldSpec(index=i, truth=catalogue & blk,
                            known=catalogue & ~blk,
                            train_pos=train_pos, train_neg_pool=train_neg_pool,
                            scored=footprint & ~(catalogue & ~blk),
                            block=blk, buffer_px=buffer_px))
    return out


def distance_to(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (px) to the nearest True cell."""
    return ndi.distance_transform_edt(~mask)
