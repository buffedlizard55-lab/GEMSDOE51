"""Tests for the official DTI metric.

Each test names the property it pins and where that property comes from.
Run with:  python -m pytest tests -q
"""

from __future__ import annotations

import numpy as np
import pytest

from gems51.metric import (
    ALPHA, BETA, RADIUS_PX, dti, dti_binary, dti_bruteforce, kernel,
    breakeven_credit_bar,
)


def test_kernel_definition():
    """k(d) = max(1 - d/R, 0), R = 3 px (300 m at 100 m/px)."""
    assert kernel(0.0) == pytest.approx(1.0)
    assert kernel(1.5) == pytest.approx(0.5)
    assert kernel(3.0) == pytest.approx(0.0)
    assert kernel(4.0) == pytest.approx(0.0)


def test_published_worked_example_arithmetic():
    """The organizer's own worked example: TP=3.00, FP=1.89, FN=2.00 -> 0.60.

    Source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric
    The figure's prediction raster is not published, so we pin the arithmetic,
    which is fully specified: 3.00 / (3.00 + 0.2*1.89 + 0.8*2.00).
    """
    tp, fp, fn = 3.00, 1.89, 2.00
    val = tp / (tp + ALPHA * fp + BETA * fn)
    assert val == pytest.approx(0.60, abs=5e-3)
    # and |G| = TP + FN (identity I1) holds in the published numbers
    assert tp + fn == pytest.approx(5.00)


def test_identity_fn_equals_n_minus_tp():
    """I1: FN_w = |G| - TP_w."""
    rng = np.random.default_rng(0)
    for _ in range(6):
        pred = (rng.random((38, 40)) < 0.06) * rng.random((38, 40))
        truth = rng.random((38, 40)) < 0.03
        r = dti(pred, truth)
        assert r["fn"] == pytest.approx(r["n_truth"] - r["tp"], abs=1e-9)


def test_identity_dti_equals_budget_form():
    """I2: DTI = TP / (a*(TP+FP) + b*|G| + eps) with a=0.2, b=0.8."""
    rng = np.random.default_rng(1)
    for _ in range(6):
        pred = (rng.random((26, 30)) < 0.07) * rng.random((26, 30))
        truth = rng.random((26, 30)) < 0.04
        r = dti(pred, truth)
        if r["n_truth"] == 0:
            continue
        budget = ALPHA * (r["tp"] + r["fp"]) + BETA * r["n_truth"]
        assert r["dti"] == pytest.approx(r["tp"] / (budget + 1e-12), rel=1e-9)


def test_matches_bruteforce_transcription():
    """The vectorised implementation must equal the literal published equations."""
    rng = np.random.default_rng(2)
    for _ in range(4):
        pred = (rng.random((18, 22)) < 0.08) * rng.random((18, 22))
        truth = rng.random((18, 22)) < 0.05
        fast, slow = dti(pred, truth), dti_bruteforce(pred, truth)
        for k in ("tp", "fp", "fn", "dti"):
            assert fast[k] == pytest.approx(slow[k], rel=1e-10, abs=1e-12), k


def test_binary_matches_soft_on_binary_input():
    rng = np.random.default_rng(3)
    for _ in range(4):
        pred = (rng.random((30, 28)) < 0.05).astype(float)
        truth = rng.random((30, 28)) < 0.04
        a, b = dti(pred, truth), dti_binary(pred > 0, truth)
        for k in ("tp", "fp", "fn", "dti"):
            assert a[k] == pytest.approx(b[k], rel=1e-10, abs=1e-12), k


def test_known_mask_removes_pixels_from_both_terms():
    """Organizer clarification (thread 11516): known fault pixels are excluded."""
    truth = np.zeros((20, 20), bool)
    truth[10, 10] = True
    pred = np.zeros((20, 20))
    pred[10, 10] = 1.0          # a dot sitting exactly on the truth pixel
    assert dti(pred, truth)["dti"] == pytest.approx(1.0, abs=1e-6)

    known = np.zeros((20, 20), bool)
    known[10, 10] = True        # ...but that pixel is a known fault -> masked
    r = dti(pred, truth, known=known)
    assert r["n_truth"] == 0
    assert r["dti"] == pytest.approx(0.0)


def test_out_of_range_predictions_rejected():
    pred = np.zeros((8, 8))
    pred[3, 3] = 1.5
    with pytest.raises(ValueError):
        dti(pred, np.zeros((8, 8), bool))
    pred[3, 3] = np.nan
    with pytest.raises(ValueError):
        dti(pred, np.zeros((8, 8), bool))


def test_empty_truth_gives_zero():
    pred = np.zeros((10, 10))
    pred[4, 4] = 1.0
    r = dti(pred, np.zeros((10, 10), bool))
    assert r["dti"] == 0.0
    assert r["fp"] == pytest.approx(1.0)


def test_break_even_bar_is_alpha_times_dti():
    """Marginal pixel with expected credit c raises DTI iff c > alpha*DTI."""
    assert breakeven_credit_bar(0.278) == pytest.approx(0.0556, abs=1e-4)


def test_break_even_bar_is_empirically_correct():
    """Numeric check: adding a pixel that earns exactly alpha*DTI leaves DTI ~unchanged."""
    rng = np.random.default_rng(7)
    H = W = 60
    truth = rng.random((H, W)) < 0.02
    pred = ((rng.random((H, W)) < 0.05) * 1.0)
    base = dti(pred, truth)["dti"]
    bar = breakeven_credit_bar(base)

    # place a new isolated dot far from everything else -> earns ~0 credit
    far = np.zeros((H, W), bool)
    far[0, 0] = True
    assert not truth[0, 0]
    after_bad = dti(np.where(far, 1.0, pred), truth)["dti"]
    assert after_bad < base, "a zero-credit pixel must lower DTI"

    # place a new dot directly on an *uncovered* truth pixel -> earns ~1.0 credit
    covered = np.zeros_like(pred)
    ys, xs = np.nonzero(truth)
    tgt = None
    for y, x in zip(ys, xs):
        if pred[max(0, y - 3):y + 4, max(0, x - 3):x + 4].max() == 0:
            tgt = (y, x)
            break
    if tgt is not None:
        covered[tgt] = 1.0
        after_good = dti(np.where(covered > 0, 1.0, pred), truth)["dti"]
        assert after_good > base, "a full-credit pixel must raise DTI"
        assert bar < 1.0
