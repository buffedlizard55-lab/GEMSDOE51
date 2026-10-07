"""Auto-context stacking: give a pixel-wise classifier the spatial context a CNN has.

Method and citation
-------------------
Tu & Bai, "Auto-Context and Its Application to High-Level Vision Tasks and 3D
Brain Image Segmentation", IEEE Transactions on Pattern Analysis and Machine
Intelligence 32(10), 1744-1757 (2010), doi:10.1109/TPAMI.2009.186.

A level-1 classifier is trained on the raw features and produces a belief map.
Multi-scale summaries of that belief map are then appended to the raw features
and a level-2 classifier is trained on the union.  The level-2 model can
therefore condition on "is there a long, coherent, high-belief lineament running
through this pixel?" — a statement no per-pixel model can make, and the exact
statement that separates a fault trace from a noisy blob.

Why it matters here
-------------------
The scored object is a *trace*, not a pixel.  The reference solution
(https://github.com/drivendataorg/gems-prize-reference-solution) buys that
context with a U-Net over 128x128 patches.  Auto-context buys the same thing for
a gradient-boosted tree at a few minutes of CPU rather than GPU-hours, which is
what this environment has.

Leakage control (the thing that makes or breaks stacking)
---------------------------------------------------------
If the level-1 belief used to build the level-2 *training* rows came from a
model that had already seen those rows' labels, the belief is optimistically
biased exactly on the training positives and level-2 learns to trust it far more
than it should.  The standard remedy, and the one used here, is **cross-fitting**
(Breiman, "Stacked regressions", Machine Learning 24(1), 49-64, 1996,
doi:10.1007/BF00117832): the training region is split into K spatially
contiguous parts, and each part's belief is produced by a level-1 model fitted
on the other K-1 parts.  The belief over the held-out evaluation block is
produced by a level-1 model fitted on the whole training region.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import trace_emission as te

CONTEXT_NAMES = [
    "ac_rank",        # empirical-CDF of the level-1 belief
    "ac_mean05",      # local mean, 500 m window
    "ac_mean11",      # local mean, 1.1 km window
    "ac_mean21",      # local mean, 2.1 km window
    "ac_max05",       # local max, 500 m window
    "ac_ridge",       # multi-scale Frangi ridge response of the belief
    "ac_line09",      # along-strike line accumulator, 900 m
    "ac_line17",      # along-strike line accumulator, 1.7 km
]


def context_features(field: np.ndarray, domain: np.ndarray,
                     sigmas=(1.0, 2.0, 3.5)) -> list[np.ndarray]:
    """Build the eight auto-context layers from a level-1 belief field.

    ``field``  float32 grid, NaN outside the footprint
    ``domain`` bool grid on which ranks and filters are defined
    Returns a list of float32 grids in the order of ``CONTEXT_NAMES``.
    """
    f = np.nan_to_num(np.asarray(field, np.float32), nan=0.0,
                      posinf=0.0, neginf=0.0).astype(np.float32)
    dom = np.asarray(domain, bool)

    out: list[np.ndarray] = []
    out.append(te._rank01(f, dom))
    for size in (5, 11, 21):
        out.append(ndi.uniform_filter(f, size=size, mode="nearest").astype(np.float32))
    out.append(ndi.maximum_filter(f, size=5, mode="nearest").astype(np.float32))

    v = np.zeros(f.shape, np.float32)
    for s in sigmas:
        vi, _ = te.ridge_response(f, dom, s)
        np.copyto(v, vi, where=vi > v)
    out.append(v)
    for ll in (9, 17):
        acc, _ = te.line_accumulate(v, length=ll, n_orient=12)
        out.append(te._rank01(acc, dom))

    for a in out:
        a[~dom] = np.nan
    assert len(out) == len(CONTEXT_NAMES)
    return out


def contiguous_parts(mask: np.ndarray, k: int = 2, axis: int = 0) -> list[np.ndarray]:
    """Split ``mask`` into ``k`` contiguous slabs of roughly equal True-count.

    Contiguity (rather than a random split) is what makes the cross-fitted
    belief honest: a randomly interleaved split would let a level-1 model
    memorise a trace in one part and be asked about the same trace, 100 m away,
    in another.
    """
    counts = mask.sum(axis=1 - axis if axis == 0 else 0)
    cum = np.cumsum(counts)
    total = cum[-1]
    edges = [0]
    for j in range(1, k):
        edges.append(int(np.searchsorted(cum, total * j / k)))
    edges.append(mask.shape[axis])
    parts = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = np.zeros(mask.shape, bool)
        if axis == 0:
            m[a:b, :] = True
        else:
            m[:, a:b] = True
        parts.append(m & mask)
    return parts
