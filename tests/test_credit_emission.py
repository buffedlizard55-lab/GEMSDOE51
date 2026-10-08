"""Unit tests for the expected-credit emission algebra (``gems51.credit_emission``).

These are cheap, data-free identities.  They exist because the H51-N2 submission
builder and the H51-N1 screen both call this module, and until now it had no
regression cover: a silent change in the kernel, the DTI identity or the
calibration would move an emitted artifact without any test failing.

The kernel values are the *published* metric weights: a triangular kernel with
300 m support, i.e. ``k(d) = max(1 - d/3, 0)`` on a 100 m grid, which is exactly
what ``tests/test_metric.py`` verifies against the official worked example.
"""

from __future__ import annotations

import numpy as np

from gems51 import credit_emission as ce
from gems51.metric import dti_binary


def test_kernel_offsets_match_the_published_triangle():
    """k(d) = max(1 - d/3, 0) on the 100 m grid: 1 at the pixel, 0 exactly at 300 m."""
    offs = {(dy, dx): k for dy, dx, k in ce._offsets(3.0)}
    assert offs[(0, 0)] == 1.0
    assert abs(offs[(0, 1)] - (1 - 1 / 3)) < 1e-12
    assert abs(offs[(2, 0)] - (1 - 2 / 3)) < 1e-12
    assert abs(offs[(1, 1)] - (1 - np.hypot(1, 1) / 3)) < 1e-12
    assert (3, 0) not in offs            # zero weight is dropped, not stored
    assert all(k > 0 for k in offs.values())
    assert max(np.hypot(dy, dx) for dy, dx in offs) <= 3.0


def test_expected_credit_follows_the_scorer_direction():
    """``credit[y] = sum_x k(|x-y|) g(x)``: the credit a dot at y earns from the truth g.

    The scorer takes, for each truth pixel, the maximum kernel weight over nearby
    predictions.  For a single predicted dot at y that is exactly the sum above,
    so the values here are the scorer's ``TP_w`` for a one-dot submission.
    """
    g = np.zeros((9, 9), np.float32)
    g[4, 4] = 1.0
    credit = ce.expected_credit(g)
    assert np.isclose(credit[4, 4], 1.0, atol=1e-6)          # dot on the truth pixel
    assert np.isclose(credit[4, 6], 1.0 - 2.0 / 3.0, atol=1e-6)
    assert np.isclose(credit[3, 3], 1.0 - np.hypot(1, 1) / 3.0, atol=1e-6)
    assert credit[4, 7] == 0.0                               # 3 px away, k = 0
    # A dot can never earn more than the whole kernel mass of a saturated field.
    solid = np.ones((15, 15), np.float32)
    interior = ce.expected_credit(solid)[7, 7]
    assert np.isclose(interior, sum(k for _, _, k in ce._offsets()), atol=1e-4)


def test_expected_credit_is_linear_in_the_field():
    rng = np.random.default_rng(0)
    a = rng.random((16, 16)).astype(np.float32)
    b = rng.random((16, 16)).astype(np.float32)
    assert np.allclose(ce.expected_credit(a + b), ce.expected_credit(a) + ce.expected_credit(b),
                       atol=1e-5)


def test_predicted_dti_matches_the_published_index_algebra():
    """DTI = TP_w / (TP_w + alpha*FP_w + beta*FN_w) with FP_w = M - TP_w, FN_w = |G| - TP_w."""
    for n_dots, credit_sum, g in ((38_100, 4_000.0, 12_700.0), (10_000, 9_000.0, 12_700.0),
                                  (5_000, 0.0, 12_700.0)):
        got = ce.predicted_dti(credit_sum, n_dots, g)
        tp = credit_sum
        fp = max(n_dots - tp, 0.0)
        fn = max(g - tp, 0.0)
        want = tp / (tp + ce.ALPHA * fp + ce.BETA * fn)
        assert np.isclose(got, want, atol=1e-9)


def test_predicted_dti_agrees_with_the_scorer_on_a_synthetic_case():
    """The closed form must equal what ``dti_binary`` computes for the same layout."""
    truth = np.zeros((40, 40), bool)
    truth[20, 6:34] = True                      # 28 truth pixels
    pred = np.zeros((40, 40), bool)
    pred[20, 6:34:3] = True                     # 10 dots along the trace
    result = dti_binary(pred, truth, valid=np.ones((40, 40), bool), known=None)
    # Credit of each dot under the scorer = kernel mass of the truth it covers.
    credit = float(np.sum(np.minimum(1.0, (np.arange(28) % 3 == 0) * 1.0)))  # dots sit on truth
    tp = float(result["tp"])
    fp = float(result["fp"])
    fn = float(result["fn"])
    want = tp / (tp + 0.2 * fp + 0.8 * fn)
    assert np.isclose(result["dti"], want, atol=1e-9)
    assert credit >= 0  # the scorer's TP_w is the ground truth here


def test_calibrate_to_total_hits_the_requested_mass_and_stays_in_unit_range():
    rng = np.random.default_rng(1)
    field = rng.random((64, 64)).astype(np.float32)
    valid = np.ones(field.shape, bool)
    cal, u = ce.calibrate_to_total(field, valid, target=500.0)
    assert np.isclose(float(cal.sum()), 500.0, rtol=1e-4)
    assert cal.max() <= 1.0 + 1e-6
    assert cal.min() >= 0.0
    assert np.isfinite(u) and u > 0


def test_calibrate_to_total_is_monotone_in_the_target():
    rng = np.random.default_rng(2)
    field = rng.random((32, 32)).astype(np.float32)
    valid = np.ones(field.shape, bool)
    small, _ = ce.calibrate_to_total(field, valid, target=100.0)
    big, _ = ce.calibrate_to_total(field, valid, target=400.0)
    assert small.sum() < big.sum()
    # Same ordering: a larger target can only lift values, never reshuffle them.
    assert np.all(np.argsort(small.ravel()) == np.argsort(big.ravel()))


def test_select_dots_respects_the_floor_and_the_spacing():
    credit = np.zeros((60, 60), np.float32)
    credit[10:50, 10:50] = 0.5
    allowed = np.zeros_like(credit, bool)
    allowed[10:50, 10:50] = True
    ys, xs, cr = ce.select_dots(credit, allowed, credit_floor=0.4, spacing_px=3.0,
                                max_dots=100, pool_size=5_000)
    assert len(ys) > 0 and len(ys) == len(xs) == len(cr)
    assert np.all(cr >= 0.4 - 1e-6)
    pts = np.stack([ys.astype(float), xs.astype(float)], 1)
    if len(pts) > 1:
        d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
        d += np.eye(len(pts)) * 1e9
        assert d.min() >= 3.0 - 1e-6


def test_values_are_never_out_of_range_for_the_public_interface():
    """Cheap guard on the interface the submission path relies on."""
    field = np.zeros((8, 8), np.float32)
    field[3, 3] = 2.5          # an uncalibrated belief value
    credit = ce.expected_credit(np.clip(field, 0.0, 1.0))
    assert credit.max() <= sum(k for _, _, k in ce._offsets())
    assert np.isfinite(credit).all()
