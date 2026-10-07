"""Turning a continuous detector field into an emitted point set.

Theory (from the metric identity DTI = TP / (a*(TP+FP) + b*|G|))
---------------------------------------------------------------
The score depends on the metric's weighted TP/FP terms, not just raw dot count.
Two consequences guide emission:

1. **Redundancy is costly.** For each truth pixel the scorer takes the maximum
   over nearby predictions. A second dot can add little or no TP credit while
   still adding weighted false-positive cost.

2. **The marginal break-even condition depends on both terms.** If a proposed
   increment changes weighted TP by c and weighted FP by f, it improves DTI iff
   c*(1 - a*DTI) > a*DTI*f. The often-quoted c > a*DTI applies only when
   c+f=1; it is not a universal raw-pixel rule.

The algebra and tests are in ``src/gems51/metric.py`` and ``tests/test_metric.py``.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .grid import GRID


def suppress_within(field: np.ndarray, exclude: np.ndarray) -> np.ndarray:
    """Set the field to -inf where emission is forbidden (e.g. near known faults)."""
    f = np.array(field, dtype=np.float32, copy=True)
    f[exclude | ~np.isfinite(f)] = -np.inf
    return f


def nms_dots(field: np.ndarray, n_dots: int, radius: float = 2.4,
             exclude: np.ndarray | None = None, valid: np.ndarray | None = None):
    """Greedy non-maximum suppression: take the best pixel, blank its neighbourhood, repeat.

    ``radius`` is in pixels (1 px = 100 m).  At radius 2.4 two emitted dots are
    never closer than sqrt(2) px yet rarely within 2.4 px, which is the scale at
    which two dots start competing for the same truth pixel (kernel support is
    3 px).
    """
    f = suppress_within(field, exclude) if exclude is not None else np.array(field, dtype=np.float32)
    if valid is not None:
        f = np.where(valid, f, -np.inf)
    work = f.copy()
    H, W = work.shape
    yy, xx = np.mgrid[0:H, 0:W]
    # circular suppression footprint
    r = int(np.ceil(radius))
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    nb = (dy * dy + dx * dx) <= radius * radius
    offs = [(int(a), int(b)) for a, b in zip(dy[nb], dx[nb])]

    chosen = []
    # work in flat argmax order via a heap-free approach: repeated max is O(n) per
    # step which is too slow for 5 M pixels x 40 k dots, so we pre-select a
    # candidate pool that is comfortably larger than n_dots and thin within it.
    pool_size = min(int((work > -np.inf).sum()), max(n_dots * 12, n_dots + 4096))
    flat = work.ravel()
    cand = np.argpartition(flat, -pool_size)[-pool_size:]
    cand = cand[np.argsort(flat[cand])[::-1]]
    cand = [(int(c // W), int(c % W)) for c in cand]

    taken = np.zeros((H, W), bool)
    for y, x in cand:
        if len(chosen) >= n_dots:
            break
        if not np.isfinite(work[y, x]):
            continue
        v = work[y, x]
        if v <= -np.inf:
            continue
        chosen.append((y, x))
        for oy, ox in offs:
            ny, nx = y + oy, x + ox
            if 0 <= ny < H and 0 <= nx < W:
                work[ny, nx] = -np.inf
    ys = np.array([c[0] for c in chosen], dtype=np.int32)
    xs = np.array([c[1] for c in chosen], dtype=np.int32)
    return ys, xs


def rasterise(ys: np.ndarray, xs: np.ndarray, values=None, shape=GRID.shape) -> np.ndarray:
    out = np.zeros(shape, dtype=np.float32)
    v = np.ones(len(ys), dtype=np.float32) if values is None else np.asarray(values, np.float32)
    out[ys, xs] = v
    return out


def thin_to_mask(ys, xs) -> np.ndarray:
    m = np.zeros(GRID.shape, bool)
    m[ys, xs] = True
    return m
