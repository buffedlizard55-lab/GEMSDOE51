"""The H52 STE emitter must be the *same* geometry as the validated historical one.

``scripts/evaluate_hh_blend.py::ste_emit`` produced the historical six-fold proxy
mean 0.2853406 (``evidence/hh_blend_holdout.json``).  ``gems51.emission2.ste_topn``
is a re-implementation parameterised so it can also honour a confinement mask.  If
the two ever diverge, every number in the H52 receipts stops being comparable with
the historical instrument, so the equivalence is pinned by a test rather than by
inspection.
"""

from __future__ import annotations

import numpy as np

from gems51 import emission2 as em2
from gems51 import trace_emission as te


def historical_ste_emit(field, candidate, n_dots):
    """Verbatim copy of scripts/evaluate_hh_blend.py::ste_emit."""
    dom = np.isfinite(field) & candidate
    f0 = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    response = np.zeros(f0.shape, np.float32)
    for sigma in (1.0, 2.0, 3.5):
        ridge, _ = te.ridge_response(f0, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = te._rank01(f0, dom)
    acc, _ = te.line_accumulate(response, length=9, n_orient=12)
    acc_rank = te._rank01(acc, dom)
    score = (raw_rank ** 0.65) * (acc_rank ** 0.35)
    return te.spaced_dots(score.astype(np.float32), dom, n_dots, spacing=2.4)


def _synthetic_field(seed: int = 3, shape=(260, 260)):
    rng = np.random.default_rng(seed)
    H, W = shape
    y, x = np.mgrid[0:H, 0:W]
    f = np.zeros((H, W), np.float32)
    for _ in range(8):
        cy, cx = rng.integers(40, H - 40), rng.integers(40, W - 40)
        ang = rng.uniform(0, np.pi)
        dy, dx = np.sin(ang), np.cos(ang)
        s = -(y - cy) * dx + (x - cx) * dy
        t = (y - cy) * dy + (x - cx) * dx
        amp = rng.uniform(0.3, 1.0)
        f = np.maximum(f, (amp * np.exp(-s ** 2 / 6.0) * (np.abs(t) < 90)).astype(np.float32))
    f += rng.normal(0, 0.05, f.shape).astype(np.float32)
    return np.where(f > 0.15, f, np.nan).astype(np.float32)


def test_ste_topn_matches_historical_recipe():
    field = _synthetic_field()
    allow = np.isfinite(field)
    forbid = np.zeros_like(allow)
    ys0, xs0 = historical_ste_emit(field, allow, 400)
    ys1, xs1 = em2.ste_topn(field, 400, forbid=forbid, allow=allow)
    assert len(ys0) == len(ys1) == 400
    assert np.array_equal(ys0, ys1) and np.array_equal(xs0, xs1)


def test_ste_topn_never_emits_inside_forbidden_domain():
    field = _synthetic_field(seed=11)
    allow = np.isfinite(field)
    forbid = np.zeros_like(allow)
    forbid[120:140, :] = True          # an excluded corridor
    allow = allow & ~forbid
    ys, xs = em2.ste_topn(field, 300, forbid=forbid, allow=allow)
    assert len(ys) > 0
    assert not forbid[ys, xs].any()
    assert allow[ys, xs].all()


def test_ste_topn_n_tips_spacing():
    field = _synthetic_field(seed=5)
    allow = np.isfinite(field)
    ys, xs = em2.ste_topn(field, 200, forbid=np.zeros_like(allow), allow=allow)
    from scipy.spatial import cKDTree
    d, _ = cKDTree(np.c_[ys, xs]).query(np.c_[ys, xs], k=2)
    assert d[:, 1].min() >= 2.0        # spacing = 2.4 px in the emitter
