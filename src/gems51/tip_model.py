"""Structural-inheritance prior: where the *next* trace is, given the mapped ones.

Hypothesis (H52-A, ``knowledge/candidate-hypotheses-h52-2026-10-07.md``)
----------------------------------------------------------------------
DrivenData staff state that the hidden label set contains faults that are
"continuations, splays and parallel strands" of already-mapped fault systems
(organizer post, https://community.drivendata.org/t/where-do-you-draw-the-line/11536).
That is a *geometric* claim, and it is the only statement we have about the hidden
truth's composition.  Every detector in this repository converts a pixel-wise
attribute field (DEM texture, potential-field edges, coherence) into dots; none of
them uses the mapped catalogue as a *shape generator*.  This module does exactly
that and nothing else.

What it computes
----------------
From a binary mapped-trace mask it extracts **tips** (skeleton free ends) and, for
each tip, the local along-strike direction and curvature estimated from the last
K skeleton pixels.  It then paints two kinds of inherited geometry:

  * **tip continuation** — a corridor of length ``corridor_px`` continuing the
    trace beyond its mapped end, with lateral half-width ``half_width_px``.
    Weight decays as ``exp(-t/tau_px)`` beyond ``start_px`` along the corridor and
    falls off laterally as ``1 - (|s|/(half_width_px+0.5))**2``.
  * **relay bridge** — the connection between two *facing* tips of different mapped
    components whose gap is below ``bridge_gap_px`` and whose strike directions are
    sub-parallel and mutually facing.  This is the geometry of a relay ramp /
    linkage zone (Cartwright, Trudgill & Mansfield, Journal of Structural Geology
    17(9) 1319-1326, 1995, doi:10.1016/0191-8141(95)00030-8; Fossen, *Structural
    Geology*, 2nd ed., CUP 2016, ch. 8), i.e. precisely where a mapped trace is
    expected to continue but is missing from the catalogue.

Geological grounding for the *sign* of the prior
------------------------------------------------
Fault traces grow by tip propagation and linkage, so trace length and displacement
are correlated and the continuation of a mapped segment is the most likely place
for an unmapped one (Walsh & Watterson, JSG 9(8) 1039-1046, 1988,
doi:10.1016/0191-8141(88)90110-1; Dawers, Anders & Scholz, Geology 21(9) 845-848,
1993, doi:10.1130/0091-7613(1993)021<0845:GONFDI>2.3.CO;2).  The prior is
deliberately *not* a field-anomaly detector: it needs no geophysical layer, so it
is orthogonal to every arm already in this repository, and its expected failure
mode (extrapolating a trace that genuinely stops) is measurable on the blocked
holdout.

This module is pure NumPy/SciPy/scikit-image, has no global state, and never
touches pixels the caller excludes.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

try:  # scikit-image 0.26 in this environment; keep the import guarded
    from skimage.morphology import skeletonize
except Exception:  # pragma: no cover
    skeletonize = None


def skeleton(mask: np.ndarray) -> np.ndarray:
    if skeletonize is None:  # pragma: no cover
        raise RuntimeError("scikit-image is required for tip detection")
    return skeletonize(np.asarray(mask, bool))


def _neighbour_count(sk: np.ndarray) -> np.ndarray:
    ker = np.ones((3, 3), np.uint8)
    ker[1, 1] = 0
    return ndi.convolve(sk.astype(np.uint8), ker, mode="constant", cval=0)


def _walk(sk: np.ndarray, y0: int, x0: int, steps: int) -> list[tuple[int, int]]:
    """Greedy 8-connected walk along the skeleton starting at an endpoint."""
    H, W = sk.shape
    path = [(y0, x0)]
    visited = {(y0, x0)}
    cy, cx = y0, x0
    for _ in range(int(steps)):
        best, best_d = None, -1.0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = cy + dy, cx + dx
                if not (0 <= ny < H and 0 <= nx < W) or not sk[ny, nx]:
                    continue
                if (ny, nx) in visited:
                    continue
                # prefer the neighbour farthest from the start: at a junction this
                # continues along the trace instead of turning back
                d = (ny - y0) ** 2 + (nx - x0) ** 2
                if d > best_d:
                    best_d, best = d, (ny, nx)
        if best is None:
            break
        path.append(best)
        visited.add(best)
        cy, cx = best
    return path


def tips(mask: np.ndarray, min_component_px: int = 12, walk_px: int = 14) -> dict:
    """Skeleton free ends of ``mask`` with local strike and curvature.

    Returns equal-length arrays ``y``, ``x`` (tip pixel), ``dy``, ``dx`` (outward
    unit direction, points *beyond* the mapped end), ``curv`` (signed 1/px),
    ``arc`` (arclength fitted), plus ``n_tips`` and ``n_components_used``.  Only
    components of at least ``min_component_px`` are used: a one-pixel speckle has
    no strike to inherit.
    """
    m = np.asarray(mask, bool)
    lab, n_lab = ndi.label(m, structure=np.ones((3, 3), int))
    empty = np.zeros(0)
    if n_lab == 0:
        return dict(y=empty.astype(int), x=empty.astype(int), dy=empty, dx=empty,
                    curv=empty, arc=empty, n_tips=0, n_components_used=0)
    sizes = np.bincount(lab.ravel())
    keep = np.zeros(n_lab + 1, bool)
    keep[1:] = sizes[1:] >= int(min_component_px)
    sk = skeleton(keep[lab])
    nbr = _neighbour_count(sk)
    end_y, end_x = np.nonzero(sk & (nbr == 1))
    ys, xs, dys, dxs, curvs, arcs = [], [], [], [], [], []
    for y0, x0 in zip(end_y.tolist(), end_x.tolist()):
        path = _walk(sk, y0, x0, walk_px)
        if len(path) < 4:
            continue
        p = np.asarray(path, float)
        seg = np.r_[0.0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
        if seg[-1] < 3.0:
            continue
        t = -seg                            # 0 at the tip, decreasing back along the trace,
                                            # so d/dt at t=0 points *outward* (beyond the tip)
        A = np.vstack([np.ones_like(t), t, t ** 2]).T
        cy = np.linalg.lstsq(A, p[:, 0], rcond=None)[0]
        cxc = np.linalg.lstsq(A, p[:, 1], rcond=None)[0]
        v = np.array([cy[1], cxc[1]], float)          # dy, dx (t increases outward)
        nv = float(np.hypot(*v))
        if nv <= 1e-9:
            continue
        v /= nv
        # signed curvature in the outward parametrisation: kappa = (v x a)/|v|^3
        # with a = 2*c2 the second-order coefficient (a is perpendicular to v
        # on a circle; projecting a onto v, as a first version did, returns 0).
        speed = float(np.hypot(cy[1], cxc[1]))
        curv = 2.0 * float(cy[1] * cxc[2] - cxc[1] * cy[2]) / max(speed ** 3, 1e-9)
        ys.append(y0), xs.append(x0), dys.append(v[0]), dxs.append(v[1])
        curvs.append(curv), arcs.append(float(abs(t[0])))
    return dict(
        y=np.asarray(ys, int), x=np.asarray(xs, int),
        dy=np.asarray(dys, float), dx=np.asarray(dxs, float),
        curv=np.asarray(curvs, float), arc=np.asarray(arcs, float),
        n_tips=int(len(ys)), n_components_used=int(keep.sum()),
    )


def _facing_bridges(t: dict, gap_max: float) -> np.ndarray:
    """Pairs (i, j, gap) of tips that face each other with sub-parallel strikes."""
    ys, xs = t["y"], t["x"]
    if len(ys) < 2 or gap_max <= 0:
        return np.zeros((0, 3), float)
    from scipy.spatial import cKDTree
    tree = cKDTree(np.c_[ys, xs])
    out = []
    for i, j in tree.query_pairs(float(gap_max)):
        v = np.array([ys[j] - ys[i], xs[j] - xs[i]], float)
        d = float(np.hypot(*v))
        if d < 2.0:
            continue
        v /= d
        di = np.array([t["dy"][i], t["dx"][i]])
        dj = np.array([t["dy"][j], t["dx"][j]])
        # each outward direction must point at the other tip, and the two strikes
        # must be sub-parallel (opposite outward senses)
        if (di @ v) < 0.7 or (dj @ -v) < 0.7:
            continue
        if (di @ dj) > -0.5:
            continue
        out.append((i, j, d))
    return np.asarray(out, float).reshape(-1, 3)


def tip_prior(mask: np.ndarray, shape: tuple[int, int] | None = None,
              corridor_px: int = 40, half_width_px: float = 2.0, tau_px: float = 12.0,
              max_curvature: float = 0.125, bridge_gap_px: float = 40.0,
              tau_bridge_px: float = 15.0, min_component_px: int = 12,
              walk_px: int = 14, start_px: float = 3.0,
              exclude: np.ndarray | None = None) -> dict:
    """Structural-inheritance prior as a float32 field in [0, 1].

    ``mask``          mapped traces the caller is allowed to see for this fold
    ``corridor_px``   how far (px; 1 px = 100 m) each trace is continued past its tip
    ``tau_px``        exponential decay length of the continuation weight
    ``bridge_gap_px`` maximum tip-to-tip distance for a relay bridge (0 disables)
    ``start_px``      corridor starts this far beyond the tip
    ``exclude``       cells that must never receive prior weight (e.g. the published
                      catalogue flank, where emission is forbidden anyway)

    Returns ``dict(prior, tips, n_bridges, bridges, corridor_px, tau_px, ...)``.
    """
    m = np.asarray(mask, bool)
    H, W = (m.shape if shape is None else shape)
    t = tips(m, min_component_px=min_component_px, walk_px=walk_px)
    pr = np.zeros((H, W), np.float32)
    if t["n_tips"] == 0:
        return dict(prior=pr, tips=t, n_bridges=0, bridges=np.zeros((0, 3)), n_points=0)

    ys, xs = t["y"], t["x"]
    T = np.arange(1, int(corridor_px) + 1, dtype=float)          # distance past the tip
    kap = np.clip(t["curv"], -max_curvature, max_curvature)
    ang = kap[:, None] * T[None, :] / 2.0                        # half-angle form
    ca, sa = np.cos(ang), np.sin(ang)
    vy, vx = t["dy"][:, None], t["dx"][:, None]
    ry = vy * ca - vx * sa
    rx = vy * sa + vx * ca
    step = 1.0
    cyy = ys[:, None] + np.cumsum(ry * step, axis=1)             # (n_tips, corridor)
    cxx = xs[:, None] + np.cumsum(rx * step, axis=1)
    offs = np.arange(-int(np.ceil(half_width_px)), int(np.ceil(half_width_px)) + 1, dtype=float)
    lat = 1.0 - np.minimum(np.abs(offs) / (half_width_px + 0.5), 1.0) ** 2
    w_along = np.where(T >= float(start_px), np.exp(-T / max(tau_px, 1e-6)), 0.0)
    acc = np.zeros((H, W), np.float32)
    n_points = 0
    for i in range(int(t["n_tips"])):
        py = cyy[i][:, None] - rx[i][:, None] * offs[None, :]
        px = cxx[i][:, None] + ry[i][:, None] * offs[None, :]
        w = w_along[:, None] * lat[None, :]
        iy = np.rint(py).astype(np.int64)
        ix = np.rint(px).astype(np.int64)
        ok = (w > 1e-3) & (iy >= 0) & (iy < H) & (ix >= 0) & (ix < W)
        if not ok.any():
            continue
        np.add.at(acc, (iy[ok], ix[ok]), w[ok].astype(np.float32))
        n_points += int(ok.sum())
    bridges = _facing_bridges(t, bridge_gap_px)
    for i_f, j_f, d in bridges:
        i, j = int(i_f), int(j_f)
        n = int(max(3, np.ceil(d)))
        yy = np.rint(np.linspace(ys[i], ys[j], n)).astype(np.int64)[1:-1]
        xx = np.rint(np.linspace(xs[i], xs[j], n)).astype(np.int64)[1:-1]
        if yy.size == 0:
            continue
        w = float(np.exp(-d / max(tau_bridge_px, 1e-6)))
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        np.add.at(acc, (yy[ok], xx[ok]), np.float32(w))
        n_points += int(ok.sum())
    np.clip(acc, 0.0, 1.0, out=acc)
    if exclude is not None:
        acc[np.asarray(exclude, bool)] = 0.0
    return dict(prior=acc, tips=t, n_bridges=int(bridges.shape[0]), bridges=bridges,
                n_points=int(n_points), corridor_px=int(corridor_px),
                tau_px=float(tau_px), half_width_px=float(half_width_px),
                bridge_gap_px=float(bridge_gap_px))


def boosted_score(field: np.ndarray, prior: np.ndarray, kappa: float) -> np.ndarray:
    """Belief field multiplied by an inheritance boost ``1 + kappa * prior``.

    ``kappa = 0`` reproduces the field exactly (the incumbent arm), so the sweep is
    monotone in the strength of the structural prior.  ``field`` is not ranked here
    because every consumer in this repository already compares *scores* through a
    monotone transform, and the boost must stay comparable across folds.
    """
    f = np.asarray(field, np.float32)
    return (f * (1.0 + float(kappa) * np.asarray(prior, np.float32))).astype(np.float32)
