"""Unit tests for the H52 emission geometry and the live-consistent metric reading.

These tests are deliberately small but they pin the two properties the submission
builder relies on: (1) nothing is ever emitted outside the allowed domain or inside
the forbidden catalogue flank, and (2) the two scoring readings differ by exactly
the submitted mass sitting on published-catalogue pixels.
"""

from __future__ import annotations

import numpy as np

from gems51 import emission2 as em2
from gems51.grid import GRID
from gems51.live_metric import dti_binary_live, on_catalogue_mass
from gems51.metric import dti_binary

H, W = GRID.shape


def _synthetic_field():
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    field = -np.abs(((yy * 0.7 + xx * 0.7) % 300.0) - 150.0) / 150.0
    field = np.where(field > 0.6, field, 0.0).astype(np.float32)
    allow = np.zeros((H, W), bool)
    allow[1000:1200, 1000:1300] = True
    forbid = np.zeros((H, W), bool)
    forbid[1100:1105, :] = True
    return field, allow, forbid


def test_sale_lines_respects_confinement_and_spacing():
    field, allow, forbid = _synthetic_field()
    cos_a = np.full((H, W), 0.8, np.float32)
    sin_a = np.full((H, W), -0.6, np.float32)
    ys, xs = em2.sale_lines(field, 500, cos_a, sin_a, forbid, allow,
                            line_half=5, spacing=2.4, seed_sep=6.0)
    assert 0 < len(ys) <= 500
    assert allow[ys, xs].all(), "emitted outside the allowed domain"
    assert not forbid[ys, xs].any(), "emitted inside the forbidden flank"
    p = np.zeros((H, W), bool)
    p[ys, xs] = True
    from scipy.spatial import cKDTree
    d, _ = cKDTree(np.c_[ys, xs]).query(np.c_[ys, xs], k=2)
    assert d[:, 1].min() >= 2.0, "two dots closer than the kernel's credit peak spacing"


def test_nms_topn_respects_confinement():
    field, allow, forbid = _synthetic_field()
    ys, xs = em2.nms_topn(field, 500, radius=2.8, forbid=forbid, allow=allow)
    assert len(ys) > 0
    assert allow[ys, xs].all() and not forbid[ys, xs].any()


def test_flank_zone_geometry():
    cat = np.zeros((H, W), bool)
    cat[2000, 2000] = True
    z = em2.catalogue_flank_zone(cat, 3.0)
    assert z[2000, 2003] and z[2000, 2000]
    assert z[1999, 1999], "the flank zone is Euclidean: a diagonal neighbour is 1.41 px away"
    assert not z[2000, 2004] and not z[1996, 2000], "beyond the radius must be outside the zone"


def test_live_metric_penalises_on_catalogue_mass_only():
    truth = np.zeros((H, W), bool)
    truth[500:520, 500:520] = True
    known = np.zeros((H, W), bool)
    known[700:720, 700:720] = True
    pred = np.zeros((H, W), bool)
    pred[500, 500] = True          # on the truth
    pred[705, 705] = True          # on the published catalogue
    pred[900, 900] = True          # on nothing
    valid = np.ones((H, W), bool)
    a = dti_binary(pred, truth, valid=valid, known=known)
    b = dti_binary_live(pred, truth, valid=valid, known=known)
    # reading A deletes the on-catalogue dot; reading B keeps and penalises it
    assert b["mass"] == a["mass"] + 1
    assert b["fp"] > a["fp"]
    assert b["dti"] < a["dti"]
    leak = on_catalogue_mass(pred, known, valid=valid)
    assert leak == dict(predicted_px=3, on_catalogue_px=1, on_catalogue_fraction=1 / 3)
