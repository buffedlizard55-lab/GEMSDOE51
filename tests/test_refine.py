"""Unit tests for H-51-L positional refinement (src/gems51/refine.py).

These tests pin down the two failure modes the first validation discovered, so
they can never silently return:

* spacing collapse  -- v1 let 75% of dots end with a neighbour inside 2.4 px
  (0% at baseline), costing -0.013 proxy DTI at equal dot set;
* silent mass loss  -- v2 dropped ~7% of dots whose cells were contested,
  silently changing the emission budget the comparison was supposed to hold.

The module docstring carries the history; these tests are the enforcement.
"""
from __future__ import annotations

import numpy as np
import pytest

from gems51.refine import refine_positions


def _spaced_dots(rng, H, W, n_try, min_gap=3):
    pts, occ = [], np.zeros((H, W), bool)
    for _ in range(n_try):
        y, x = rng.integers(4, H - 4), rng.integers(4, W - 4)
        if occ[max(0, y - min_gap):y + min_gap + 1,
               max(0, x - min_gap):x + min_gap + 1].any():
            continue
        pts.append((y, x))
        occ[y, x] = True
    ys = np.array([p[0] for p in pts])
    xs = np.array([p[1] for p in pts])
    return ys, xs


def _spacing_violations(ry, rx, min_spacing=2.4):
    v = 0
    for i in range(len(ry)):
        for j in range(i + 1, len(ry)):
            if (abs(ry[i] - ry[j]) <= 3 and abs(rx[i] - rx[j]) <= 3
                    and np.hypot(ry[i] - ry[j], rx[i] - rx[j]) <= min_spacing):
                v += 1
    return v


def test_mass_conserved_and_no_duplicates():
    rng = np.random.default_rng(1)
    surf = rng.random((96, 96)).astype(np.float32)
    ys, xs = _spaced_dots(rng, 96, 96, 800)
    ry, rx, st = refine_positions(ys, xs, surf, np.ones((96, 96), bool),
                                  window=2, min_spacing=2.4)
    assert len(ry) == len(ys)                       # nothing dropped
    assert st["n_dropped"] == 0
    assert len({(int(y), int(x)) for y, x in zip(ry, rx)}) == len(ry)


def test_spacing_never_collapses():
    rng = np.random.default_rng(2)
    surf = rng.random((96, 96)).astype(np.float32)
    ys, xs = _spaced_dots(rng, 96, 96, 800)
    ry, rx, _ = refine_positions(ys, xs, surf, np.ones((96, 96), bool),
                                 window=2, min_spacing=2.4)
    assert _spacing_violations(ry, rx) == 0


def test_moves_respect_allowed_mask():
    rng = np.random.default_rng(3)
    H = W = 64
    surf = rng.random((H, W)).astype(np.float32)
    surf[: H // 2] += 10.0                          # bait: forbidden half is "best"
    allowed = np.ones((H, W), bool)
    allowed[: H // 2] = False
    ys, xs = _spaced_dots(rng, H, W, 300)
    keep = ys >= H // 2
    ys, xs = ys[keep], xs[keep]
    ry, rx, _ = refine_positions(ys, xs, surf, allowed, window=3)
    assert (ry >= H // 2).all()                     # never smuggled into forbidden


def test_dots_only_move_to_strictly_better_surface():
    rng = np.random.default_rng(4)
    surf = rng.random((48, 48)).astype(np.float32)
    ys, xs = _spaced_dots(rng, 48, 48, 200)
    ry, rx, _ = refine_positions(ys, xs, surf, np.ones((48, 48), bool),
                                 window=2, margin=0.0)
    # every moved dot must sit on a strictly better surface cell than before
    for (y0, x0), (y1, x1) in zip(zip(ys, xs), zip(ry, rx)):
        if (y0, x0) != (y1, x1):
            assert surf[y1, x1] > surf[y0, x0]


def test_input_outside_allowed_raises():
    surf = np.zeros((16, 16), np.float32)
    allowed = np.ones((16, 16), bool)
    allowed[0, 0] = False
    with pytest.raises(ValueError):
        refine_positions(np.array([0]), np.array([0]), surf, allowed)
