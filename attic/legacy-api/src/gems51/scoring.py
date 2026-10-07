"""Spatially-blocked holdout scoring on the official metric.

The holdout design, and why it is the right one for THIS competition:

  * The organisers confirmed the hidden test set is "any fault pixel not already captured
    by USGS/INGENIOUS" and that mapped-fault pixels are masked out of the penalty terms.
  * So a *leave-one-block-out* protocol is the honest analogue: hold one spatial block of
    the mapped catalogue out entirely, do not let the model see it, call it "the hidden
    faults", and score the whole-map emission against it under the official metric with
    the REMAINDER of the catalogue used as the mask.

  * Protocol O (oracle location): emit only inside the held-out block.  Generous.
  * Protocol P (unknown location): emit over the whole footprint.  This is the shape of
    the real competition, and it is the one reported as the headline.

A 30 px buffer around the held-out block is excluded from the model's catalogue input so
that the shell/core cannot leak across the boundary.
"""
from __future__ import annotations

import numpy as np

from . import metric


def crop_bbox(*arrays: np.ndarray, pad: int = 8):
    """Crop every array to a common bounding box of the union of their non-trivial cells."""
    mask = np.zeros(arrays[0].shape, dtype=bool)
    for a in arrays:
        if a.dtype == bool:
            mask |= a
        else:
            mask |= np.isfinite(a) & (a != 0)
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return tuple(a.copy() for a in arrays)
    y0, y1 = max(0, ys.min() - pad), min(mask.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(mask.shape[1], xs.max() + pad + 1)
    return tuple(a[y0:y1, x0:x1] for a in arrays)


def score(
    pred: np.ndarray,
    truth: np.ndarray,
    known_mask: np.ndarray | None = None,
    *,
    restrict_to_footprint: np.ndarray | None = None,
    crop: bool = True,
) -> dict:
    """Official DTI with the official masking rule, on a cropped working window.

    pred           : float raster (probabilities in [0, 1])
    truth          : bool array of HIDDEN faults (must NOT be masked)
    known_mask     : bool array of known/catalogue faults -> excluded from penalty terms
    restrict_to_footprint : if given, prediction is zeroed outside it (and truth clipped)
    """
    p = np.asarray(pred, dtype=np.float32)
    t = np.asarray(truth, dtype=bool)
    k = None if known_mask is None else np.asarray(known_mask, dtype=bool)
    f = None if restrict_to_footprint is None else np.asarray(restrict_to_footprint, dtype=bool)

    if crop:
        stack = [p.astype(np.float32), t.astype(np.float32)]
        if k is not None:
            stack.append(k.astype(np.float32))
        if f is not None:
            stack.append(f.astype(np.float32))
        cropped = crop_bbox(*stack)
        p = cropped[0]
        t = cropped[1] > 0.5
        i = 2
        if k is not None:
            k = cropped[i] > 0.5
            i += 1
        if f is not None:
            f = cropped[i] > 0.5

    if f is not None:
        p = np.where(f, p, 0.0)
        t = t & f
    # The hidden truth must never be masked.
    if k is not None:
        k = k & (~t)

    res = metric.dti_components(p, t, mask=k)
    res_plain = metric.dti_components(p, t, mask=None) if k is not None else res
    return {
        "dti_masked": res["dti"],
        "dti_unmasked": res_plain["dti"],
        "tp": res["tp"], "fp": res["fp"], "fn": res["fn"],
        "n_truth": res["n_truth"], "n_pred": res["n_pred"],
        "sum_pred": float(p.sum()),
        "mean_credit_per_pred_px": (res["tp"] / res["n_pred"]) if res["n_pred"] else 0.0,
    }


def quadrant_blocks(shape: tuple[int, int], n: int = 2, buffer_px: int = 30):
    """Yield (name, block_slice, model_exclusion_mask) for an n x n spatial blocking."""
    h, w = shape
    ys = np.linspace(0, h, n + 1).astype(int)
    xs = np.linspace(0, w, n + 1).astype(int)
    for i in range(n):
        for j in range(n):
            sl = (slice(ys[i], ys[i + 1]), slice(xs[j], xs[j + 1]))
            ex = np.zeros(shape, dtype=bool)
            y0 = max(0, ys[i] - buffer_px)
            y1 = min(h, ys[i + 1] + buffer_px)
            x0 = max(0, xs[j] - buffer_px)
            x1 = min(w, xs[j + 1] + buffer_px)
            ex[y0:y1, x0:x1] = True
            yield f"b{i}{j}", sl, ex
