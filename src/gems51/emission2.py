"""Emission geometry for the metric, v2 — three documented placement rules.

Why emission geometry is not a detail
-------------------------------------
The official scorer credits each truth pixel with ``max over nearby predictions
of p(x)*k(d)``, so a *line* of dots along a trace is worth far more than the
same number of scattered dots: measured on the six-fold blocked proxy in this
repository, an oracle that places 3.47 dots per truth pixel at random inside the
300 m neighbourhood of the truth scores 0.553, while the same budget placed
uniformly inside the block scores 0.193.  The gap is not model quality — it is
where the mass is spent.

The three rules here
--------------------
1. ``nms_topn``      plain greedy non-maximum suppression of a belief field
                     (the repository's incumbent geometry; kept as the control).
2. ``sale_lines``    **S**trike-**A**ligned **L**ine **E**mission: seeds are
                     taken from the belief field, and each seed emits a short
                     line of dots *along the locally mapped fault fabric*
                     instead of a single dot.  Physical basis: a newly recognised
                     fault in this setting is overwhelmingly new geometry of an
                     existing fault system — a continuation, a splay or a
                     parallel strand (DrivenData staff clarification, 2026-09-23,
                     https://community.drivendata.org/t/where-do-you-draw-the-line/11536)
                     — so the local strike of the *mapped* fabric is the best
                     available predictor of the strike of the missing one, and
                     the metric rewards mass laid along that strike.
3. ``near_catalogue_only`` / ``far_from_catalogue`` — the catalogue-flank rules.
   Under the "zero credit, still counted" reading of the scoring FAQ (see
   :mod:`gems51.live_metric`) mass placed on, or immediately beside, a published
   fault earns nothing and costs ``alpha`` per unit.  The sibling GEMSDOE32
   experiment (40,199-dot file live 0.2708 versus its 44,090-dot superset
   live 0.2600 — the only difference being the 3,891 dots inside 100 m of the
   catalogue) is the design evidence used here; the flank radius is therefore a
   swept parameter, never assumed.

All placement functions take an explicit ``allow`` mask (the Stage-1 approved
tiles) and ``forbid`` mask (a dilated published-catalogue exclusion).  Nothing
is ever emitted outside ``allow`` or inside ``forbid``; that is the confinement
requirement the task imposes on Stage 2, and it is enforced here rather than
checked afterwards.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .grid import GRID


def _as_bool(a, shape) -> np.ndarray:
    if a is None:
        return np.zeros(shape, bool)
    b = np.asarray(a, bool)
    if b.shape != shape:
        raise ValueError(f"mask shape {b.shape} != {shape}")
    return b


# --------------------------------------------------------------------- rule 1
def nms_topn(field: np.ndarray, n_dots: int, radius: float = 2.4,
             forbid: np.ndarray | None = None, allow: np.ndarray | None = None,
             valid: np.ndarray | None = None) -> np.ndarray:
    """Greedy NMS of ``field`` restricted to ``allow & ~forbid``; returns (ys, xs)."""
    from .emission import nms_dots

    f = np.array(field, dtype=np.float32, copy=True)
    shape = f.shape
    excl = _as_bool(forbid, shape)
    if allow is not None:
        excl = excl | ~_as_bool(allow, shape)
    ys, xs = nms_dots(f, int(n_dots), radius=radius, exclude=excl, valid=valid)
    return ys, xs


# --------------------------------------------------------------------- rule 2
def axis_from_catalogue(catalogue: np.ndarray, sigma_grad: float = 2.0,
                        sigma_int: float = 3.0):
    """Local along-strike unit axis of the mapped fabric.

    Steerable structure tensor of a smoothed trace indicator: the dominant
    gradient direction is perpendicular to the trace, so the strike is that
    direction rotated by 90 degrees.  Returns ``(cos, sin, support)`` where
    ``support`` marks pixels with a locally coherent map fabric.
    """
    I = ndi.gaussian_filter(np.asarray(catalogue, np.float32), sigma_grad, mode="nearest")
    gy, gx = np.gradient(I)
    Jxx = ndi.gaussian_filter(gx * gx, sigma_int, mode="nearest")
    Jyy = ndi.gaussian_filter(gy * gy, sigma_int, mode="nearest")
    Jxy = ndi.gaussian_filter(gx * gy, sigma_int, mode="nearest")
    theta = 0.5 * np.arctan2(2.0 * Jxy, (Jxx - Jyy))
    strike = theta + np.pi / 2.0
    # raster +row = south, so the image y component of a north positive axis is negated
    cos_t = np.cos(strike).astype(np.float32)
    sin_t = (-np.sin(strike)).astype(np.float32)
    # coherency of the tensor: 1 for a perfectly linear local fabric
    tr = Jxx + Jyy
    diff = np.sqrt((Jxx - Jyy) ** 2 + 4.0 * Jxy ** 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        coh = np.where(tr > 0, diff / np.maximum(tr, 1e-12), 0.0)
    return cos_t, sin_t, (tr > 0) & (coh > 0.25)


def axis_from_field(field: np.ndarray, sigma_grad: float = 1.0, sigma_int: float = 5.0):
    """Fallback axis: local *ridge* orientation of the belief field itself.

    A fault trace in a belief field is a ridge (locally 1-D bright structure);
    the tensor's maximum-gradient direction is across the ridge, so the ridge
    axis is again that direction rotated by 90 degrees.
    """
    f = np.nan_to_num(np.asarray(field, np.float32), nan=0.0)
    return axis_from_catalogue(f, sigma_grad=sigma_grad, sigma_int=sigma_int)


def sale_lines(field: np.ndarray, n_target: int, cos_axis: np.ndarray, sin_axis: np.ndarray,
               forbid: np.ndarray, allow: np.ndarray, line_half: int = 5,
               spacing: float = 2.4, seed_sep: float = 6.0,
               axis_min_strength: np.ndarray | None = None) -> np.ndarray:
    """Strike-aligned line emission: seeds from ``field``, dots along the local axis.

    Parameters
    ----------
    field        belief field; higher = more likely a fault.
    n_target     maximum number of emitted dots (unit mass each).
    cos_axis/sin_axis  local unit axis (image row/col components) at every pixel.
    forbid       pixels that must not receive mass (published-catalogue flank).
    allow        Stage-1 approved tiles; nothing is emitted outside them.
    line_half    half-length of each emitted line, in pixels (steps of ``spacing``).
    spacing      distance between consecutive dots along a line (>= kernel radius/1.25
                 keeps consecutive dots from double-crediting one truth pixel).
    seed_sep     minimum distance between two seed centres.
    axis_min_strength  optional coherence mask; seeds outside it emit a single dot
                 (degenerates gracefully to plain NMS) instead of a line.

    Returns ``(ys, xs)`` of int32 arrays.
    """
    H, W = GRID.shape
    f = np.asarray(field, np.float32)
    if f.shape != (H, W):
        raise ValueError(f"field shape {f.shape} != {(H, W)}")
    forbid = _as_bool(forbid, (H, W))
    allow = _as_bool(allow, (H, W))
    ok = allow & ~forbid & np.isfinite(f)
    if axis_min_strength is not None:
        ok_axis = ok & _as_bool(axis_min_strength, (H, W))
    else:
        ok_axis = ok

    # candidate order: descending field over the admissible domain
    flat = np.where(ok, f, -np.inf).ravel()
    n_cand = min(int(ok.sum()), max(4 * n_target, n_target + 2048))
    cand = np.argpartition(flat, -n_cand)[-n_cand:]
    cand = cand[np.argsort(flat[cand])[::-1]]

    taken: set[int] = set()
    seed_block: set[int] = set()
    out_y: list[int] = []
    out_x: list[int] = []
    r_take = max(int(np.ceil(spacing * 0.75)), 1)
    r_seed = max(int(np.ceil(seed_sep)), 1)
    take_off = [(dy, dx) for dy in range(-r_take, r_take + 1)
                for dx in range(-r_take, r_take + 1) if dy * dy + dx * dx <= r_take * r_take]
    seed_off = [(dy, dx) for dy in range(-r_seed, r_seed + 1)
                for dx in range(-r_seed, r_seed + 1) if dy * dy + dx * dx <= r_seed * r_seed]

    def free(y: int, x: int) -> bool:
        if not (0 <= y < H and 0 <= x < W) or not ok[y, x]:
            return False
        for dy, dx in take_off:
            if (y + dy) * W + (x + dx) in taken:
                return False
        return True

    for c in cand:
        if len(out_y) >= n_target:
            break
        y, x = int(c // W), int(c % W)
        if not ok[y, x] or (y * W + x) in seed_block:
            continue
        # seed suppression: do not start another line within seed_sep of this seed
        for dy, dx in seed_off:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                seed_block.add(ny * W + nx)

        if ok_axis[y, x]:
            cy, cx = float(cos_axis[y, x]), float(sin_axis[y, x])
            if not np.isfinite(cy) or not np.isfinite(cx):
                cy, cx = 0.0, 1.0
            steps = [(0, 0)]
            for s in range(1, line_half + 1):
                steps += [(s * spacing, 1), (-s * spacing, -1)]
            for dist, sgn in steps:
                if len(out_y) >= n_target:
                    break
                yy = int(round(y + sgn * dist * cx))   # axis row component
                xx = int(round(x + sgn * dist * cy))   # axis col component
                if not free(yy, xx):
                    continue
                out_y.append(yy)
                out_x.append(xx)
                taken.add(yy * W + xx)
        else:
            if free(y, x):
                out_y.append(y)
                out_x.append(x)
                taken.add(y * W + x)

    return (np.asarray(out_y, np.int32), np.asarray(out_x, np.int32))


# ----------------------------------------------------------------- rule 2b
def ste_topn(field: np.ndarray, n_dots: int, forbid: np.ndarray, allow: np.ndarray,
             line_length: int = 9, w_cont: float = 0.35, spacing: float = 2.4,
             sigmas=(1.0, 2.0, 3.5)) -> np.ndarray:
    """Strike-coherent trace emission (STE), the repository's validated best geometry.

    Exact recipe of ``scripts/evaluate_hh_blend.py::ste_emit`` (the configuration
    that produced the historical six-fold proxy mean 0.2853406 for the H-H/H-D
    blend): multi-scale ridge/vesselness response of the belief field
    (Frangi et al. 1998), along-strike line accumulation (Radon/Vanderbrug 1976),
    then greedy spacing at 2.4 px.  Here the legal domain is additionally trimmed
    by the Stage-1 approved mask and the published-catalogue flank, so the same
    recipe can be used under the H52 confinement rules.
    """
    from . import trace_emission as te

    dom = _as_bool(allow, field.shape) & ~_as_bool(forbid, field.shape) \
        & np.isfinite(field) & np.isfinite(field)
    f0 = np.nan_to_num(np.asarray(field, np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    response = np.zeros(f0.shape, np.float32)
    for sigma in sigmas:
        ridge, _ = te.ridge_response(f0, dom, sigma)
        np.copyto(response, ridge, where=ridge > response)
    raw_rank = te._rank01(f0, dom)
    acc, _ = te.line_accumulate(response, length=line_length, n_orient=12)
    acc_rank = te._rank01(acc, dom)
    score = ((raw_rank ** (1.0 - w_cont)) * (acc_rank ** w_cont)).astype(np.float32)
    return te.spaced_dots(score, dom, int(n_dots), spacing=spacing)


# --------------------------------------------------------------------- rule 3
def catalogue_flank_zone(catalogue: np.ndarray, radius_px: float) -> np.ndarray:
    """Pixels within ``radius_px`` of a published catalogue pixel (bool).

    ``radius_px`` is in 100 m pixels: 1.0 = 100 m, 2.0 = 200 m, 3.0 = 300 m — the
    kernel radius, so a dot just outside this zone is at least one kernel radius
    from any published fault pixel and is fully penalised if its own structure is
    not a real new fault.
    """
    if radius_px <= 0:
        return np.zeros(np.asarray(catalogue).shape, bool)
    d = ndi.distance_transform_edt(~np.asarray(catalogue, bool))
    return d <= radius_px


def rasterise(ys: np.ndarray, xs: np.ndarray, shape=GRID.shape) -> np.ndarray:
    out = np.zeros(shape, np.float32)
    if len(ys):
        out[ys, xs] = np.float32(1.0)
    return out
