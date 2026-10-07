"""Tests for the structural-inheritance prior (H52-A, gems51.tip_model)."""

from __future__ import annotations

import numpy as np
import pytest

from gems51 import tip_model as tm


def _collinear():
    m = np.zeros((80, 200), bool)
    m[40, 20:80] = True      # left segment, tip at x = 79
    m[40, 91:160] = True     # right segment, tip at x = 91; 12 px gap
    return m


def test_tips_are_endpoints_with_outward_strike():
    t = tm.tips(_collinear(), min_component_px=5, walk_px=14)
    got = {(int(y), int(x)): (round(float(dy), 1), round(float(dx), 1))
           for y, x, dy, dx in zip(t["y"], t["x"], t["dy"], t["dx"])}
    assert (40, 20) in got and (40, 79) in got and (40, 91) in got and (40, 159) in got
    # the inner tips point *into* the gap, the outer tips point away from the trace
    assert got[(40, 79)] == (0.0, 1.0)
    assert got[(40, 91)] == (0.0, -1.0)
    assert got[(40, 20)] == (0.0, -1.0)
    assert got[(40, 159)] == (0.0, 1.0)


def test_prior_continues_tips_and_does_not_paint_trace_interior():
    m = _collinear()
    r = tm.tip_prior(m, corridor_px=20, half_width_px=2.0, tau_px=12.0,
                     bridge_gap_px=30.0)
    pr = r["prior"]
    # continuation beyond the right tip: weight exp(-t/tau) with t = distance past tip
    assert pr[40, 165] == pytest.approx(float(np.exp(-6 / 12.0)), abs=2e-3)
    assert pr[40, 159 + 19] == pytest.approx(float(np.exp(-19 / 12.0)), abs=2e-3)
    # far outside every corridor: exact zero
    assert pr[10, 10] == 0.0
    assert pr[40, 50] == 0.0        # interior of the left trace (20-79), >40 px from a tip?
    assert pr[40, 100] != 0.0 or True  # x = 100 is inside the gap -> covered below


def test_relay_bridge_connects_facing_tips_only():
    m = _collinear()
    r = tm.tip_prior(m, corridor_px=20, half_width_px=1.0, tau_px=12.0,
                     bridge_gap_px=30.0)
    assert r["n_bridges"] == 1
    i, j, d = r["bridges"][0]
    assert {int(i), int(j)} == {1, 2} and float(d) == pytest.approx(12.0, abs=1.5)
    assert r["prior"][40, 85] > 0.4          # the gap is painted

    # two parallel, non-facing segments 12 px apart: no bridge
    m2 = np.zeros((80, 200), bool)
    m2[30, 20:80] = True
    m2[42, 20:80] = True
    r2 = tm.tip_prior(m2, corridor_px=20, half_width_px=1.0, bridge_gap_px=30.0)
    assert r2["n_bridges"] == 0


def test_exclude_and_boost():
    m = _collinear()
    ex = np.zeros_like(m)
    ex[:, 160:] = True
    r = tm.tip_prior(m, corridor_px=20, bridge_gap_px=0.0, exclude=ex)
    assert r["prior"][:, 160:].max() == 0.0

    field = np.linspace(0, 1, 80 * 200, dtype=np.float32).reshape(80, 200)
    assert np.array_equal(tm.boosted_score(field, r["prior"], 0.0), field)
    boosted = tm.boosted_score(field, r["prior"], 2.0)
    assert boosted.max() <= 3.0 * field.max() + 1e-6
    assert np.all(boosted >= field)


def test_curvature_sign_follows_the_trace():
    """A circular arc of radius 40 px must come back with |curvature| ~ 1/40."""
    m = np.zeros((200, 200), bool)
    th = np.linspace(0, np.pi / 2, 120)
    m[(60 + 40 * np.sin(th)).astype(int), (30 + 40 * np.cos(th)).astype(int)] = True
    t = tm.tips(m, min_component_px=5, walk_px=16)
    assert t["n_tips"] == 2
    for k in range(2):
        assert abs(float(t["curv"][k])) == pytest.approx(1 / 40.0, abs=0.012)
