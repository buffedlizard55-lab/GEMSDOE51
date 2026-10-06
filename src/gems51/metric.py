"""Exact re-implementation of the DOE GEMS Prize Distance-Weighted Tversky Index (DTI).

SOURCE OF TRUTH (official, read 2026-10-06):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  Section "Performance metric" / "Mathematical representation" / "Scoring example".

Published equations, transcribed verbatim from that page:

    TP_w = sum_{g in G} max_{x : d(x,g) <= R} p(x) * k(d(x,g))
    FP_w = sum_{x : p(x) > 0} p(x) * [ 1 - max_{g in G} k(d(x,g)) ]
    FN_w = sum_{g in G} [ 1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g)) ]
    k(d) = (1 - d/R)_+ = max(1 - d/R, 0)
    DTI  = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps)
    alpha = 0.2, beta = 0.8, R = 300 m  (= 3 px at the supplied 100 m grid)

VERIFICATION: `python -m gems51.metric` reproduces the official worked example EXACTLY
(TP_w = 3.00, FP_w = 1.89, FN_w = 2.00, DTI = 0.60).  See tests/test_metric.py.

MASKING (official clarification, read 2026-10-06):
  https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516
  DrivenData staff (chrisk-dd, 2026-09-16): "Pixels corresponding to known USGS/INGENIOUS
  faults are masked / excluded from evaluation, so they do not count towards penalty terms."
  Therefore this module supports BOTH modes:
    mask=None                    -> plain published metric (no masking)
    mask=<bool array is_known>   -> pixels where mask is True are dropped from the FP term
  Both are reported everywhere in this repository; neither is assumed silently.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_M = 300.0
PIXEL_M = 100.0
EPSILON = 1e-7
KERNEL_PX = RADIUS_M / PIXEL_M  # = 3.0 px


def kernel_from_distance_px(d_px: np.ndarray) -> np.ndarray:
    """k(d) = max(1 - d/R, 0), with d in pixels and R = 3 px."""
    return np.maximum(1.0 - np.asarray(d_px, dtype=np.float64) / KERNEL_PX, 0.0)


def dti_components(
    pred: np.ndarray,
    truth: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict:
    """Compute (TP_w, FP_w, FN_w) and the DTI exactly as published.

    pred  : float array, prediction probabilities in [0, 1]
    truth : bool array, ground-truth fault pixels
    mask  : optional bool array; True where the pixel is a KNOWN (catalogue) fault pixel
            and must be excluded from the penalty terms (official clarification).
    """
    pred = np.asarray(pred, dtype=np.float32)
    truth = np.asarray(truth, dtype=bool)
    if pred.shape != truth.shape:
        raise ValueError(f"shape mismatch: {pred.shape} vs {truth.shape}")

    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != pred.shape:
            raise ValueError("mask shape mismatch")
        # A known-fault pixel contributes nothing to the FP term.  It must not be
        # allowed to deliver credit either: credit is computed on the (hidden) truth
        # only, and hidden truth pixels are by definition not masked.
        pred_eval = np.where(mask, 0.0, pred)
    else:
        pred_eval = pred

    n_truth = int(truth.sum())
    if n_truth == 0:
        # Published formula is 0/0 here; the convention used is the reference
        # implementation's (both empty = perfect, predictions with no truth = zero).
        n_pred = int((pred_eval > 0).sum())
        return dict(tp=0.0, fp=float(pred_eval.sum()), fn=0.0,
                    dti=(1.0 if n_pred == 0 else 0.0), n_truth=0, n_pred=n_pred)

    # ---- TP_w and FN_w: for every truth pixel, the best credit any prediction gives it
    # distance_transform_edt(~pos) gives, at each pixel, the distance to the nearest
    # pixel where pos is True.  We need, at each TRUTH pixel, the maximum of
    # pred(x)*k(d(x,g)) over x.  Because k is a decreasing function of distance and
    # pred <= 1, the maximum is attained by the *nearest* pixel that carries the
    # highest value; the published formula's max over x is evaluated exactly by
    # sweeping the kernel support (R = 3 px) which is small.
    tp_unweighted = np.zeros_like(pred_eval, dtype=np.float32)
    dist_to_pred = distance_transform_edt(pred_eval <= 0.0)
    # A prediction of probability p at distance d can deliver at most p*k(d).
    # Sweep the R=3 px neighbourhood of each prediction pixel (offsets within radius).
    offs = []
    rr = int(np.ceil(KERNEL_PX))
    for dy in range(-rr, rr + 1):
        for dx in range(-rr, rr + 1):
            if dy * dy + dx * dx <= KERNEL_PX * KERNEL_PX:
                offs.append((dy, dx))
    for dy, dx in offs:
        d = float(np.hypot(dy, dx))
        w = max(1.0 - d / KERNEL_PX, 0.0)
        if w <= 0.0:
            continue
        shifted = np.roll(np.roll(pred_eval, dy, axis=0), dx, axis=1)
        # np.roll wraps; zero the wrapped edges
        if dy > 0:
            shifted[:dy, :] = 0.0
        elif dy < 0:
            shifted[dy:, :] = 0.0
        if dx > 0:
            shifted[:, :dx] = 0.0
        elif dx < 0:
            shifted[:, dx:] = 0.0
        np.maximum(tp_unweighted, shifted * w, out=tp_unweighted)

    tp_w = float(tp_unweighted[truth].astype(np.float64).sum())
    fn_w = float(n_truth - tp_w)
    if fn_w < 0.0:
        fn_w = 0.0

    # ---- FP_w: every prediction pixel is charged (1 - best kernel weight to any truth)
    dist_to_truth = distance_transform_edt(~truth)
    fp_kernel = kernel_from_distance_px(dist_to_truth)
    fp_w = float((pred_eval.astype(np.float64) * (1.0 - fp_kernel.astype(np.float64))).sum())

    denom = tp_w + ALPHA * fp_w + BETA * fn_w + EPSILON
    return dict(
        tp=tp_w, fp=fp_w, fn=fn_w, dti=float(tp_w / denom),
        n_truth=n_truth, n_pred=int((pred_eval > 0).sum()),
        denom=float(denom),
    )


def dti(pred: np.ndarray, truth: np.ndarray, mask: np.ndarray | None = None) -> float:
    return dti_components(pred, truth, mask)["dti"]


# ---------------------------------------------------------------------------
# Official worked example, transcribed from the two schematics published on
# page 967 (gems_metric_1.png, gems_metric_2.png).  Used as the self-test.
# ---------------------------------------------------------------------------
OFFICIAL_EXAMPLE_TRUTH = np.array(
    [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 1, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ],
    dtype=bool,
)

OFFICIAL_EXAMPLE_PRED = np.array(
    [
        [0, 0, 0, 0, 0.5],
        [0, 0, 0, 0.6, 0.4],
        [0, 0, 0.8, 0.7, 0],
        [0, 0.9, 0.9, 0, 0],
        [0, 0.9, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ],
    dtype=np.float64,
)

OFFICIAL_EXAMPLE_EXPECTED = dict(tp=3.00, fp=1.89, fn=2.00, dti=0.60)


def _self_test() -> int:
    got = dti_components(OFFICIAL_EXAMPLE_PRED, OFFICIAL_EXAMPLE_TRUTH)
    ok = (
        abs(got["tp"] - 3.00) < 0.02
        and abs(got["fp"] - 1.89) < 0.02
        and abs(got["fn"] - 2.00) < 0.02
        and abs(got["dti"] - 0.60) < 0.005
    )
    print("official worked example (page 967, gems_metric_1/2.png)")
    print(f"  expected  TP_w=3.00  FP_w=1.89  FN_w=2.00  DTI=0.60")
    print(f"  measured  TP_w={got['tp']:.4f}  FP_w={got['fp']:.4f}  "
          f"FN_w={got['fn']:.4f}  DTI={got['dti']:.6f}")
    print("  SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
