"""Trace-segment Kostrov budget, using official vector lengths rather than pixels.

Kreemer et al. (2000), Eq.3: E_ij = 1/2 sum L*u/(A*sin(dip)) * (n_i m_j+n_j m_i).
Assume faults span a common seismogenic thickness, so mu and thickness cancel.
N: dip60°, plane-slip u -> positive normal extension L*u*cos(dip)/A.
RL/LL: dip90°, signed shear L*u/(2*A). Unknown senses omitted, not imputed.
E is a horizontal tensor in east/north coordinates, in yr^-1. Actual trace
vertices are clipped to each 10km tile, including fractional segments.
Dips/rakes and slip component remain assumptions. This is NOT a geodetic inversion.
"""

from __future__ import annotations
import numpy as np


def clip_segment(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """Liang–Barsky closed-rectangle clipping; zero-length returns None."""
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return None
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
        if lo >= hi:
            return None
    return x0 + lo * dx, y0 + lo * dy, x0 + hi * dx, y0 + hi * dy


def segment_tensor(
    x0,
    y0,
    x1,
    y1,
    rate_mm_yr,
    sense,
    area_m2=1e8,
    dip_deg=60.0,
    convention="fault_plane",
):
    if not np.isfinite(rate_mm_yr) or rate_mm_yr < 0 or area_m2 <= 0:
        raise ValueError("finite nonnegative rate and positive area required")
    if convention not in ("fault_plane", "vertical"):
        raise ValueError("unknown slip component convention")
    dx, dy = x1 - x0, y1 - y0
    length = np.hypot(dx, dy)
    if length == 0:
        return np.zeros(3)
    tx, ty = dx / length, dy / length
    nx, ny = -ty, tx
    scale = length * rate_mm_yr * 1e-3 / area_m2
    if sense == "N":
        if not 0 < dip_deg < 90:
            raise ValueError("normal fault dip must be between 0 and 90")
        delta = np.deg2rad(dip_deg)
        scale *= np.cos(delta)
        if convention == "vertical":
            scale /= np.sin(delta)
        return scale * np.array([nx * nx, ny * ny, nx * ny])
    if sense in ("RL", "LL"):
        scale *= 1 if sense == "RL" else -1
        return scale * np.array([tx * nx, ty * ny, (tx * ny + ty * nx) / 2])
    raise ValueError("unsupported sense: no silent normal-fault fallback")


def summaries(exx, eyy, exy):
    half = (exx + eyy) / 2
    radius = np.hypot((exx - eyy) / 2, exy)
    p1, p2 = half + radius, half - radius
    return dict(
        dilatation=exx + eyy,
        second_invariant=np.hypot(p1, p2),
        shear=np.where(p1 * p2 < 0, np.minimum(np.abs(p1), np.abs(p2)), 0.0),
    )


def budget(rows, excluded=(), tile_m=10000.0, convention="fault_plane"):
    # Complete enclosing cells, not footprint-area-rescaled cells. This is a
    # physical 10km tile tensor; observations are sampled only on footprint.
    if tile_m != 10000.0:
        raise ValueError("this audited grid uses fixed 10km tiles")
    h, w = 38, 33
    origin_x, origin_y = 243350.0, 4508550.0
    out = np.zeros((3, h, w))
    excluded = set(excluded)
    omitted = 0
    length = 0.0
    for row in rows.itertuples(index=False):
        if row.record_id in excluded:
            continue
        if (
            row.sense not in ("N", "RL", "LL")
            or not np.isfinite(row.slip_mm_yr)
            or row.slip_mm_yr < 0
        ):
            omitted += 1
            continue
        xs = [row.x0, row.x1]
        ys = [row.y0, row.y1]
        c0 = max(0, int(np.floor((min(xs) - origin_x) / tile_m)))
        c1 = min(w - 1, int(np.floor((max(xs) - origin_x) / tile_m)))
        r0 = max(0, int(np.floor((origin_y - max(ys)) / tile_m)))
        r1 = min(h - 1, int(np.floor((origin_y - min(ys)) / tile_m)))
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                left = origin_x + c * tile_m
                top = origin_y - r * tile_m
                seg = clip_segment(
                    xs[0], ys[0], xs[1], ys[1], left, top - tile_m, left + tile_m, top
                )
                if seg is None:
                    continue
                # Boundary-parallel segments belong to exactly one cell.
                mx = (seg[0] + seg[2]) / 2
                my = (seg[1] + seg[3]) / 2
                if (
                    int(np.floor((mx - origin_x) / tile_m)) != c
                    or int(np.floor((origin_y - my) / tile_m)) != r
                ):
                    continue
                out[:, r, c] += segment_tensor(
                    *seg,
                    row.slip_mm_yr,
                    row.sense,
                    area_m2=tile_m**2,
                    convention=convention,
                )
                length += np.hypot(seg[2] - seg[0], seg[3] - seg[1])
    return out, dict(
        used_length_m=length,
        omitted_segments=omitted,
        convention=convention,
        tile_m=tile_m,
        unknown_sense="omitted",
    )
