"""Unit tests for the R1 relocate confinement operator (scripts/run_r1_holdout.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_r1_holdout import relocate_dots  # noqa: E402


def test_inside_dots_are_untouched():
    allowed = np.zeros((10, 10), bool)
    allowed[2:5, 2:5] = True
    ys = np.array([2, 3, 4])
    xs = np.array([2, 3, 4])
    oy, ox, stats = relocate_dots(ys, xs, allowed, spacing=1.0)
    assert np.array_equal(oy, ys) and np.array_equal(ox, xs)
    assert stats["moved"] == 0 and stats["failed"] == 0


def test_outside_dot_moves_to_nearest_allowed_cell():
    allowed = np.zeros((20, 20), bool)
    allowed[8:12, 8:12] = True
    ys = np.array([10, 0])
    xs = np.array([10, 0])
    oy, ox, stats = relocate_dots(ys, xs, allowed, spacing=1.0)
    assert oy[0] == 10 and ox[0] == 10            # inside: untouched
    assert allowed[oy[1], ox[1]]                  # outside: moved into allowed
    # nearest allowed corner to (0,0) is (8,8)
    assert (oy[1], ox[1]) == (8, 8)
    assert stats["moved"] == 1 and stats["failed"] == 0


def test_spacing_is_respected_after_relocation():
    allowed = np.zeros((30, 30), bool)
    allowed[10:20, 10:20] = True
    # two dots outside, both nearest to the same corner; spacing 2.4 forces
    # the second to land > 2.4 px from the first
    ys = np.array([0, 1])
    xs = np.array([0, 0])
    oy, ox, stats = relocate_dots(ys, xs, allowed, spacing=2.4)
    assert stats["moved"] == 2 and stats["failed"] == 0
    d = np.hypot(oy[0] - oy[1], ox[0] - ox[1])
    assert d > 2.4 - 1e-9


def test_deterministic():
    rng = np.random.default_rng(7)
    allowed = rng.random((40, 40)) < 0.85
    ys = rng.integers(0, 40, 12)
    xs = rng.integers(0, 40, 12)
    a = relocate_dots(ys.copy(), xs.copy(), allowed, spacing=2.4)
    b = relocate_dots(ys.copy(), xs.copy(), allowed, spacing=2.4)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert a[2] == b[2]


def test_failed_when_no_allowed_cell_exists():
    allowed = np.zeros((10, 10), bool)
    ys = np.array([5])
    xs = np.array([5])
    oy, ox, stats = relocate_dots(ys, xs, allowed, spacing=1.0)
    assert stats["failed"] == 1 and stats["moved"] == 0
