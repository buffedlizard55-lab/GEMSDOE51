"""H-51-L — trace-axis snap: positional refinement of emitted dots.

The measured gap to the public leader is placement precision, not structure
discovery (README §"What next session should do"): our dots sit ≈ 260 m from the
nearest truth on average versus ≈ 200 m implied for the leader, and kernel credit
decays linearly with that offset (k(d) = 1 − d/3, d in px).  Every emission in
GEMSDOE1–52 places dots at the NMS-selected cell centre and never moves them.

This module is the missing step.  After NMS has chosen *which* dots to emit, each
dot may relocate within a small neighbourhood to the strongest cell of a
scarp-specific **crest surface**:

* a fault scarp is a thin crest, so the natural locator is the most-negative
  Hessian eigenvalue of a topographic field (σ-scaled crest response);
* the 1 m-DEM scarp stack (`lidar_scarp_features_u8`, owner quantisation of the
  USGS 1 m DEM scarp detector, hash-pinned in `registry/data_manifest.json`)
  provides `ex_max` (scarp existence), `step_max` and `relief` where the GeoDAWN
  LiDAR covers the pixel (~75 % of the footprint, measured);
* outside that cover the crest of `comp_det_elev` (band 12, official description
  "Detrended elevation") supplies the same role at coarser resolution.

All components are percentile-ranked over the footprint before averaging, so no
component's units leak into another, and the fused surface is flat (NaN-free):
cells with no data anywhere take value 0 and never attract a dot.

Safety constraints, all enforced in :func:`refine_positions`:
* a dot may only move to a cell that was itself a legal emission site
  (footprint, outside the catalogue exclusion, inside the holdout block when
  validating) — snapping can never smuggle mass into a forbidden place;
* two dots may never land on the same cell (occupied cells are masked, so the
  emitted mass and dot count are exactly conserved);
* a dot moves only if the surface strictly improves, and ties keep the original
  cell, so refinement can only raise the field value under which dots sit.

This is a *position* refinement, not a belief-field blur: it never changes which
dots exist, only where within ±2 px they sit.  That is the mechanism the group's
own history has never tested (GEMSDOE32's H34 blurred the field and measured a
wash; no experiment in GEMSDOE1–52 moved points after NMS).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .grid import GRID
from .stack import _nc_deriv, lineament_bank


def _rank_percentile(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Monotone percentile map in [0, 1] over ``valid``; 0 where invalid."""
    v = a[valid]
    out = np.zeros(a.shape, np.float32)
    if v.size == 0:
        return out
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    pct = order.astype(np.float64) / max(1, v.size - 1)
    out[valid] = pct.astype(np.float32)
    return out


def build_snap_surface(stack, footprint: np.ndarray, verbose: bool = True,
                       suppress: np.ndarray | None = None,
                       suppress_radius_px: float = 4.0) -> np.ndarray:
    """Fuse crest evidence from every available topographic channel.

    Components (each percentile-ranked over its own domain, then averaged over
    the components available at that pixel):
      1. crest of comp_det_elev at sigma = 1.5 px
      2. crest of comp_det_elev at sigma = 2.5 px
      3. crest of lid_relief at sigma = 1.5 px (only where LiDAR is finite)
      4. lid_ex_max  (1 m-DEM scarp existence score)
      5. lid_step_max (1 m-DEM step height)

    ``suppress`` (a boolean mask of pixels, e.g. the known catalogue) zeroes the
    fused surface within ``suppress_radius_px`` of those pixels.  Why: the
    strongest crests ARE the mapped faults — the class we already have — and an
    unsuppressed surface drags dots toward the flanks of mapped scarps, i.e.
    into exactly the mass the group's own B=2 live experiment showed to be dead
    (0.2600 -> 0.2778 by removing it).  Suppression forces the snap to relocate
    a dot only along its OWN lineament, never toward a catalogued one.
    """
    get = lambda n: np.asarray(stack.data[stack.names.index(n)], dtype=np.float32)
    det = get("comp_det_elev")
    m_det = np.isfinite(det) & footprint
    comps: list[tuple[str, np.ndarray, np.ndarray]] = []
    for sigma in (1.5, 2.5):
        _e, crest, _l = lineament_bank(det, m_det, sigma)
        comps.append((f"det_crest_s{int(sigma * 10)}", crest, m_det & np.isfinite(crest)))
    lid_relief = get("lid_relief")
    m_lid = np.isfinite(lid_relief) & footprint
    _e, crest_r, _l = lineament_bank(lid_relief, m_lid, 1.5)
    comps.append(("lidrel_crest_s15", crest_r, m_lid & np.isfinite(crest_r)))
    for nm in ("lid_ex_max", "lid_step_max"):
        a = get(nm)
        m = np.isfinite(a) & footprint
        comps.append((nm, a, m))

    acc = np.zeros(GRID.shape, np.float32)
    nav = np.zeros(GRID.shape, np.float32)
    for name, a, m in comps:
        r = _rank_percentile(np.where(m, a, 0.0), m)
        acc += r
        nav += m.astype(np.float32)
        if verbose:
            print(f"  [snap] component {name:22s} domain={int(m.sum()):9,} px")
    with np.errstate(divide="ignore", invalid="ignore"):
        surf = np.where(nav > 0, acc / np.maximum(nav, 1e-9), 0.0)
    surf = np.where(footprint & (nav > 0), surf, 0.0).astype(np.float32)
    if suppress is not None:
        d = ndi.distance_transform_edt(~np.asarray(suppress, bool))
        dead = d <= suppress_radius_px
        surf[dead] = 0.0
        if verbose:
            print(f"  [snap] suppressed within {suppress_radius_px:g} px of the "
                  f"catalogue: {int(dead.sum()):,} px zeroed")
    if verbose:
        print(f"  [snap] fused surface domain = {int((surf > 0).sum()):,} px")
    return surf


def _offsets(window: int):
    """Candidate move offsets, nearest first (tie-break stays close)."""
    offs = [(dy, dx) for dy in range(-window, window + 1)
            for dx in range(-window, window + 1)]
    offs.sort(key=lambda o: (o[0] * o[0] + o[1] * o[1], abs(o[0]) + abs(o[1])))
    return offs


def refine_positions(ys: np.ndarray, xs: np.ndarray, surf: np.ndarray,
                     allowed: np.ndarray, window: int = 2,
                     margin: float = 0.0, min_spacing: float = 2.4,
                     priority: np.ndarray | None = None,
                     ) -> tuple[np.ndarray, np.ndarray, dict]:
    """Move dots to better crest cells, conserving mass and NMS spacing.

    Why the constraints are the way they are
    ----------------------------------------
    * Spacing is a metric invariant: two final dots closer than the 3 px kernel
      radius compete for the same truth pixels, so the FIRST validation failure
      of this module (75% of dots ended with a neighbour inside 2.4 px against
      0% at baseline; -0.013 proxy DTI at equal dot set) was a spacing
      collapse.  ``min_spacing`` is enforced between ALL final placements.
    * Mass is the controlled variable: the first rewrite dropped ~7% of dots
      whose cells were contested, which silently changed the emission budget.
      This version never drops: a mover may not approach within ``min_spacing``
      of any other dot's ORIGINAL cell unless that dot has already moved, so
      every dot can always keep its own cell.

    Mechanics: dots are processed in descending ``priority`` (default: ``surf``
    at the current cell).  ``blocked`` marks cells within ``min_spacing`` of (a)
    every final placement and (b) every not-yet-decided dot's original cell.
    The dot being processed unblocks its own original disk, chooses between
    staying and the best in-window cell (a move requires beating the current
    surface value by ``margin``), then blocks the disk of its final cell.

    Returns (new_ys, new_xs, stats) with stats: n_moved, n_kept, n_dropped
    (always 0 here, kept for schema stability), mean_move_px, max_move_px,
    moved_fraction.
    """
    ys = np.asarray(ys, dtype=np.int64)
    xs = np.asarray(xs, dtype=np.int64)
    H, W = surf.shape
    assert ys.size == xs.size
    if ys.size == 0:
        return ys.copy(), xs.copy(), dict(n_moved=0, n_kept=0, n_dropped=0,
                                          mean_move_px=0.0, max_move_px=0.0,
                                          moved_fraction=0.0)
    bad = ~allowed[ys, xs]
    if bad.any():
        raise ValueError(f"{int(bad.sum())} input dots outside `allowed`")

    r = int(np.ceil(min_spacing))
    dyg, dxg = np.mgrid[-r:r + 1, -r:r + 1]
    msk = dyg * dyg + dxg * dxg <= min_spacing * min_spacing

    def mark(grid, y, x, val):
        ya = np.atleast_1d(np.asarray(y, dtype=np.int64))
        xa = np.atleast_1d(np.asarray(x, dtype=np.int64))
        dy = dyg[msk][None, :]
        dx = dxg[msk][None, :]
        yc = (ya[:, None] + dy).ravel()
        xc = (xa[:, None] + dx).ravel()
        ok = (yc >= 0) & (yc < H) & (xc >= 0) & (xc < W)
        np.add.at(grid, (yc[ok], xc[ok]), 1 if val else -1)

    blocked = np.zeros((H, W), np.int32)
    mark(blocked, ys, xs, 1)                    # disks around all original cells

    prio = surf[ys, xs] if priority is None else np.asarray(priority, np.float64)
    order = np.argsort(-prio, kind="stable")
    offs = _offsets(window)
    new_y = ys.copy()
    new_x = xs.copy()
    n_moved = 0
    move_sum = 0.0
    move_max = 0.0
    for i in order:
        y0, x0 = int(ys[i]), int(xs[i])
        mark(blocked, y0, x0, 0)                # unblock my own original disk
        cur = surf[y0, x0]
        best_v = cur + margin
        best_d = 0.0
        by, bx = y0, x0
        for dy, dx in offs:
            if dy == 0 and dx == 0:
                continue
            ny, nx = y0 + dy, x0 + dx
            if ny < 0 or ny >= H or nx < 0 or nx >= W:
                continue
            if blocked[ny, nx] > 0 or not allowed[ny, nx]:
                continue
            v = surf[ny, nx]
            d = float(np.hypot(dy, dx))
            # strictly better (by margin) wins; equal keeps the nearer cell
            if v > best_v or (v == best_v and 0 < d < best_d):
                best_v, best_d, by, bx = v, d, ny, nx
        new_y[i], new_x[i] = by, bx
        mark(blocked, by, bx, 1)                # block around my final cell
        if (by, bx) != (y0, x0):
            n_moved += 1
            move_sum += best_d
            move_max = max(move_max, best_d)
    stats = dict(n_moved=n_moved, n_kept=ys.size, n_dropped=0,
                 mean_move_px=move_sum / max(1, n_moved),
                 max_move_px=move_max,
                 moved_fraction=n_moved / max(1, ys.size))
    return new_y, new_x, stats
