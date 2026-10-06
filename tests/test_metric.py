"""Brute-force verification of the published metric against this implementation.

Two independent checks:
  1. the official worked example from page 967 (TP_w=3.00, FP_w=1.89, FN_w=2.00, DTI=0.60);
  2. a randomised brute-force O(N^2) transcription of the published equations on small
     arrays, compared to the implementation at 1e-6.
Run:  PYTHONPATH=src python3 tests/test_metric.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems51 import metric  # noqa: E402


def brute_force(pred, truth, mask=None):
    """Direct transcription of the published equations, no distance transforms."""
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)
    gt = np.argwhere(truth)
    pd = np.argwhere(pred > 0)
    R = 3.0
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        pd = pd[~mask[tuple(pd.T)]]
    tp = 0.0
    for gy, gx in gt:
        if pd.size == 0:
            break
        d = np.hypot(pd[:, 0] - gy, pd[:, 1] - gx)
        k = np.maximum(1.0 - d / R, 0.0)
        tp += float(np.max(pred[pd[:, 0], pd[:, 1]] * k))
    fn = float(truth.sum()) - tp
    fp = 0.0
    for py, px in pd:
        if gt.size == 0:
            continue
        d = np.hypot(gt[:, 0] - py, gt[:, 1] - px)
        k = np.maximum(1.0 - d / R, 0.0)
        fp += float(pred[py, px] * (1.0 - k.max()))
    denom = tp + 0.2 * fp + 0.8 * fn + 1e-7
    return dict(tp=tp, fp=fp, fn=fn, dti=tp / denom)


def test_official_worked_example():
    got = metric.dti_components(metric.OFFICIAL_EXAMPLE_PRED, metric.OFFICIAL_EXAMPLE_TRUTH)
    assert abs(got["tp"] - 3.00) < 0.02, got
    assert abs(got["fp"] - 1.89) < 0.02, got
    assert abs(got["fn"] - 2.00) < 0.02, got
    assert abs(got["dti"] - 0.60) < 0.005, got
    print(f"  official worked example: TP={got['tp']:.4f} FP={got['fp']:.4f} "
          f"FN={got['fn']:.4f} DTI={got['dti']:.6f}  (published 3.00/1.89/2.00/0.60)")


def test_brute_force_agreement():
    rng = np.random.default_rng(11)
    worst = 0.0
    for trial in range(12):
        n = int(rng.integers(9, 16))
        pred = ((rng.random((n, n)) < 0.25) * rng.random((n, n))).astype(np.float32)
        truth = rng.random((n, n)) < 0.12
        mask = (rng.random((n, n)) < 0.15) & (~truth)
        bf = brute_force(pred, truth, mask=None)
        got = metric.dti_components(pred, truth, mask=None)
        for key in ("tp", "fp", "fn"):
            worst = max(worst, abs(bf[key] - got[key]))
            assert abs(bf[key] - got[key]) < 1e-6, (trial, key, bf[key], got[key])
        bfm = brute_force(pred, truth, mask=mask)
        gotm = metric.dti_components(pred, truth, mask=mask)
        worst = max(worst, abs(bfm["dti"] - gotm["dti"]))
        assert abs(bfm["dti"] - gotm["dti"]) < 1e-6, (trial, bfm, gotm)
    print(f"  brute-force agreement over 12 random trials: worst |diff| = {worst:.2e}")


def test_empty_cases():
    z = np.zeros((6, 6), dtype=np.float32)
    assert metric.dti(z, z) == 1.0
    t = np.zeros((6, 6), dtype=bool)
    t[2, 2] = True
    assert metric.dti(z, t) == 0.0
    print("  empty/edge cases: PASS")


if __name__ == "__main__":
    print("gems51 metric self-test")
    test_official_worked_example()
    test_brute_force_agreement()
    test_empty_cases()
    print("ALL PASS")
