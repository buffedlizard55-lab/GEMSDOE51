"""Credit emitters: turn a belief field into dots using the metric's own algebra.

The official metric (DrivenData page 967, transcribed in ``gems51.metric``) is

    DTI = TP_w / ( alpha * (TP_w + FP_w) + beta * |G| ),   alpha = 0.2, beta = 0.8

with ``TP_w = sum over truth pixels of max over predictions of p * k(d)`` and the
triangular kernel ``k(d) = max(1 - d/R, 0)``, R = 300 m = 3 px.  Two facts follow
and both are used here:

1.  **The marginal rule.**  Appending one unit-valued prediction changes the
    weighted terms by ``c`` (credit) and ``f = 1 - c`` (cost, ignoring the
    max-sharing between neighbours).  It raises DTI exactly when

        c * (1 - alpha * DTI) > alpha * DTI * f        <=>   c > alpha * DTI

    i.e. *a dot is worth emitting if and only if the credit it will earn exceeds
    ``alpha * DTI``*.  At DTI = 0.28 that bar is 0.056 credit, i.e. a dot within
    ``3 - 0.6*0.28 = 2.83`` px of a truth pixel.  No mass calibration is needed
    once credit can be estimated; the threshold *is* the mass rule.

2.  **Expected credit is a kernel convolution.**  If ``p(x)`` estimates the
    probability that x is a scored truth pixel, then the credit a unit dot at x
    earns *in expectation* is

        C(x) = sum_d k(|d|) * p(x + d)

    because each truth pixel contributes ``k(distance)`` and contributes nothing
    from beyond R.  ``expected_credit`` below computes exactly this sum (the same
    offset set used by ``gems51.metric``), so ``C`` is in the same units as
    ``TP_w`` and can be compared directly to ``alpha * DTI``.

This replaces "emit ``m * |G|`` dots because a local sweep said m = 3.47" with a
per-pixel decision.  The remaining free parameter is the *calibration* of ``p``:
``calibrate_to_total`` rescales the field so that its clipped sum equals a
declared hidden-truth-pixel budget, which is the only quantity the local proxy
cannot measure (the proxy's truth is the visible catalogue, ~4-5x larger than the
new-fault population).

Nothing in this module reads the truth; it is a pure function of the field, the
allowed domain and declared constants.
"""

from __future__ import annotations

import numpy as np

ALPHA = 0.2
BETA = 0.8


def _offsets(radius: float = 3.0) -> list[tuple[int, int, float]]:
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dy, dx))
            k = max(1.0 - d / radius, 0.0)
            if k > 0.0:
                out.append((dy, dx, k))
    return out


_OFFSETS = _offsets()


def expected_credit(field: np.ndarray, valid: np.ndarray | None = None,
                    radius: float = 3.0) -> np.ndarray:
    """``C(x) = sum_d k(|d|) p(x+d)`` — the credit a unit dot at x should earn.

    Pixels whose neighbourhood leaves the valid domain contribute only the part
    that is valid, which is the same convention the scorer uses (predictions are
    only read inside the active domain).
    """
    p = np.asarray(field, dtype=np.float32)
    if valid is None:
        valid = np.ones(p.shape, bool)
    p = np.where(valid & np.isfinite(p), p, 0.0).astype(np.float32)
    out = np.zeros(p.shape, np.float32)
    offs = _offsets(radius) if radius != 3.0 else _OFFSETS
    for dy, dx, k in offs:
        src = np.roll(np.roll(p, -dy, axis=0), -dx, axis=1)
        out += (k * src).astype(np.float32)
    return out


def calibrate_to_total(field: np.ndarray, valid: np.ndarray, target: float,
                       max_value: float = 1.0) -> tuple[np.ndarray, float]:
    """Rescale ``field`` so that ``sum(min(max_value, field/u)) == target``.

    Returns ``(calibrated_field, u)``.  The clip at ``max_value`` keeps the output
    a legal probability; ``u`` is reported so the transform is auditable.  The
    solve is exact (bisection on the sorted field), not a linear rescale that the
    clip would then break.
    """
    f = np.asarray(field, dtype=np.float64)
    m = np.asarray(valid, bool) & np.isfinite(f) & (f > 0)
    vals = np.sort(f[m].ravel())
    n = vals.size
    out = np.zeros(f.shape, np.float32)
    if n == 0 or target <= 0:
        return out, float("nan")
    cs = np.concatenate([[0.0], np.cumsum(vals)])

    def total(u: float) -> float:
        # min(1, v/u): v < u contributes v/u, v >= u contributes 1
        k = int(np.searchsorted(vals, u, side="left"))
        return float(cs[k] / u + (n - k) * max_value)

    lo, hi = 1e-12, float(vals.max()) / max(target / n, 1e-12) + 1e-9
    while total(hi) > target and hi < 1e12:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if total(mid) > target:
            lo = mid
        else:
            hi = mid
    u = hi
    out[m] = np.minimum(max_value, f[m] / u).astype(np.float32)
    return out, float(u)


def select_dots(credit: np.ndarray, allowed: np.ndarray, credit_floor: float,
                spacing_px: float = 2.8, max_dots: int = 400_000,
                pool_size: int = 900_000) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Greedy credit-ordered Poisson-disk selection with a credit floor.

    Parameters
    ----------
    credit : float32 (H, W)
        Expected credit per unit dot (``expected_credit``).
    allowed : bool (H, W)
        Emission domain (footprint, minus the known-fault mask, minus any coarse
        Stage-1 veto).
    credit_floor : float
        Stop as soon as the next best dot's expected credit falls below this
        (the marginal rule: ``alpha * DTI``).
    spacing_px : float
        Minimum separation between dots.  Two dots closer than ~R share the same
        truth pixels, so the second one adds credit already counted.
    max_dots, pool_size : int
        Safety caps for a 3730 x 3292 grid.

    Returns
    -------
    (ys, xs, credits) as int32/int32/float32 arrays, in selection order.
    """
    H, W = credit.shape
    cand = np.asarray(allowed, bool) & np.isfinite(credit) & (credit >= credit_floor)
    n_cand = int(cand.sum())
    if n_cand == 0:
        return (np.zeros(0, np.int32), np.zeros(0, np.int32), np.zeros(0, np.float32))
    flat_idx = np.flatnonzero(cand.ravel())
    vals = credit.ravel()[flat_idx]
    take = min(pool_size, n_cand)
    if take < n_cand:
        sel = np.argpartition(vals, -take)[-take:]
        flat_idx, vals = flat_idx[sel], vals[sel]
    order = np.argsort(vals)[::-1]
    flat_idx, vals = flat_idx[order], vals[order]

    r = float(spacing_px)
    sup = int(np.ceil(r))
    dy, dx = np.mgrid[-sup:sup + 1, -sup:sup + 1]
    nb = (dy * dy + dx * dx) <= r * r
    offs = [(int(a), int(b)) for a, b in zip(dy[nb], dx[nb])]
    blocked = np.zeros((H, W), bool)
    ys_out: list[int] = []
    xs_out: list[int] = []
    cr_out: list[float] = []
    for f, v in zip(flat_idx, vals):
        if len(ys_out) >= max_dots or v < credit_floor:
            break
        y, x = divmod(int(f), W)
        if blocked[y, x]:
            continue
        ys_out.append(y)
        xs_out.append(x)
        cr_out.append(float(v))
        for oy, ox in offs:
            ny, nx = y + oy, x + ox
            if 0 <= ny < H and 0 <= nx < W:
                blocked[ny, nx] = True
    return (np.asarray(ys_out, np.int32), np.asarray(xs_out, np.int32),
            np.asarray(cr_out, np.float32))


def predicted_dti(credit_sum: float, n_dots: int, g_hat: float,
                  alpha: float = ALPHA, beta: float = BETA) -> float:
    """DTI implied by a selection, using expected credit and a declared |G|.

    ``TP_w ~ sum of selected credits``, ``FP_w ~ n_dots - TP_w`` (each dot costs
    one unit of mass and earns back its credit), ``FN_w = |G| - TP_w``.
    """
    tp = float(credit_sum)
    fp = max(float(n_dots) - tp, 0.0)
    fn = max(float(g_hat) - tp, 0.0)
    return tp / (tp + alpha * fp + beta * fn + 1e-12)


def selfconsistent_threshold(credit: np.ndarray, allowed: np.ndarray, g_hat: float,
                             spacing_px: float = 2.8, alpha: float = ALPHA,
                             beta: float = BETA, dti0: float = 0.28,
                             iterations: int = 6, max_dots: int = 400_000,
                             pool_size: int = 900_000) -> dict:
    """Solve the fixed point ``floor = alpha * DTI(selection(floor))``.

    Starts from ``dti0`` (the level the reported sibling artifacts are near),
    selects, recomputes the implied DTI with the declared ``g_hat``, and repeats.
    The iteration is monotone in practice and cheap (6 selections).
    """
    floor = alpha * dti0
    hist = []
    for _ in range(iterations):
        ys, xs, cr = select_dots(credit, allowed, floor, spacing_px=spacing_px,
                                 max_dots=max_dots, pool_size=pool_size)
        dti_hat = predicted_dti(float(cr.sum()), int(ys.size), g_hat, alpha, beta)
        hist.append(dict(floor=float(floor), n_dots=int(ys.size),
                         credit_sum=float(cr.sum()), dti_hat=float(dti_hat)))
        new_floor = alpha * max(dti_hat, 1e-6)
        if abs(new_floor - floor) <= 1e-4:
            break
        floor = new_floor
    return dict(ys=ys, xs=xs, credits=cr, floor=float(floor),
                dti_hat=float(dti_hat), history=hist)
