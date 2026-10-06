"""Metric tests.  No network, no data files: the published worked example and the identities.

The published worked example (competition problem description, "Scoring example"):
    TP_w = 3.00, FP_w = 1.89, FN_w = 2.00  ->  DTI = 3.00 / (3.00 + 0.2*1.89 + 0.8*2.00) = 0.60
"""

from __future__ import annotations

import numpy as np
import pytest

from gems51 import metric


def test_published_worked_example():
    dti = metric.dti_from_components(3.00, 1.89, 2.00)
    assert dti == pytest.approx(0.60, abs=5e-3)


def test_fn_identity_and_budget_form():
    """FN_w = |G| - TP_w, and DTI = T/(0.2(T+F) + 0.8K) exactly."""
    rng = np.random.default_rng(0)
    truth = rng.random((40, 40)) < 0.05
    for _ in range(5):
        pred = (rng.random((40, 40)) < 0.04).astype(float)
        r = metric.evaluate_binary(pred > 0, truth)
        assert r["fn"] == pytest.approx(r["n_truth"] - r["tp"])
        closed = r["tp"] / (0.2 * (r["tp"] + r["fp"]) + 0.8 * r["n_truth"])
        assert r["dti"] == pytest.approx(closed, rel=1e-9)


def test_exact_matches_bruteforce_small():
    rng = np.random.default_rng(1)
    truth = rng.random((25, 25)) < 0.06
    pred = np.zeros((25, 25))
    ys, xs = np.nonzero(rng.random((25, 25)) < 0.05)
    pred[ys, xs] = 1.0
    got = metric.evaluate_binary(pred > 0, truth)
    ref = metric.evaluate_bruteforce(pred, truth)
    assert got["tp"] == pytest.approx(ref["tp"], abs=1e-9)
    assert got["fp"] == pytest.approx(ref["fp"], abs=1e-9)
    assert got["dti"] == pytest.approx(ref["dti"], abs=1e-12)


def test_soft_prediction_matches_bruteforce():
    rng = np.random.default_rng(7)
    truth = rng.random((25, 25)) < 0.06
    pred = (rng.random((25, 25)) < 0.05) * rng.random((25, 25))
    got = metric.evaluate(pred, truth)
    ref = metric.evaluate_bruteforce(pred, truth)
    assert got["dti"] == pytest.approx(ref["dti"], abs=1e-9)


def test_marginal_theorem_special_case():
    """Adding ONE dot that covers a single truth pixel: improve iff k > alpha*DTI."""
    truth = np.zeros((21, 21), bool)
    truth[10, 10] = True
    pred = np.zeros((21, 21))
    base = metric.evaluate_binary(pred > 0, truth)
    assert base["dti"] == 0.0
    for dy, dx in [(0, 0), (0, 1), (1, 1), (0, 2), (2, 2), (0, 3)]:
        p = np.zeros((21, 21))
        p[10 + dy, 10 + dx] = 1.0
        r = metric.evaluate_binary(p > 0, truth)
        k = float(metric.kernel(np.hypot(dy, dx)))
        assert (r["dti"] > 0) == (k > 0.0)


def test_marginal_gain_sign_matches_general_theorem():
    """Sign of the exact DTI delta == sign of the (T1) inequality, on random states."""
    rng = np.random.default_rng(3)
    truth = rng.random((60, 60)) < 0.05
    pred = (rng.random((60, 60)) < 0.05).astype(float)
    r0 = metric.evaluate_binary(pred > 0, truth)
    ys, xs = np.nonzero((pred == 0) & (rng.random((60, 60)) < 0.02))
    for y, x in list(zip(ys, xs))[:40]:
        p2 = pred.copy()
        p2[y, x] = 1.0
        r1 = metric.evaluate_binary(p2 > 0, truth)
        d_tp = r1["tp"] - r0["tp"]
        d_fp = r1["fp"] - r0["fp"]
        lhs = d_tp * (metric.ALPHA * r0["fp"] + metric.BETA * r0["n_truth"])
        rhs = metric.ALPHA * r0["tp"] * d_fp
        assert (r1["dti"] > r0["dti"]) == (lhs > rhs)


def test_rejects_values_outside_unit_interval():
    """The portal error 'Predicted values must be in range [0, 1]' must be caught locally."""
    truth = np.zeros((8, 8), bool)
    truth[4, 4] = True
    bad = np.zeros((8, 8))
    bad[4, 4] = 1.5
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        metric.evaluate(bad, truth)
    nan = np.zeros((8, 8))
    nan[4, 4] = np.nan
    with pytest.raises(ValueError, match="finite"):
        metric.evaluate(nan, truth)


def test_kernel_support_is_three_pixels():
    assert metric.kernel(0.0) == 1.0
    assert metric.kernel(3.0) == 0.0
    assert metric.kernel(np.hypot(2, 2)) == pytest.approx(1 - np.hypot(2, 2) / 3)


def test_credit_audit_reports_redundancy():
    m = np.zeros((11, 11))
    m[5, 4:7] = 1.0
    a = metric.credit_audit(m)
    assert a.n_emitted == 3
    assert a.redundancy_fraction == pytest.approx(1.0)   # adjacent dots cover each other
    single = np.zeros((11, 11))
    single[5, 5] = 1.0
    assert metric.credit_audit(single).redundancy_fraction == 0.0
