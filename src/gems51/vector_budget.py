"""Trace-segment Kostrov budgets and footprint-exact 100 m segment clipping.

Kreemer et al. (2000), Eq. 3:

    eps_dot_ij = 1/2 sum_k L_k*u_dot_k/(A*sin(delta_k)) *
                 (n_i*m_j + n_j*m_i)

Assuming a common seismogenic thickness, shear modulus and thickness cancel.
For a pure normal fault, horizontal strain is positive extension with factor
``cos(dip)`` for a total fault-plane rate or ``cot(dip)`` for a vertical rate.
For vertical RL/LL strike slip, the signed shear coefficient is ``L*u/(2*A)``.
Unknown senses are omitted, never silently imputed.

``budget`` is the historical 10 km rectangle-only audit API. The new
``prepare_segments_in_support`` / ``budget_prepared`` pair splits source trace
segments at raster-cell boundaries and retains only line length in the supplied
valid-data mask. Use the latter for new footprint-scale physical Stage-1 work;
legacy audit receipts remain reproducible through ``budget``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .grid import GRID


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
    """Kreemer-eq.-(3) tensor for one straight segment (returned in 1/year)."""
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
    """Source-style scalar dilation, second invariant and shear from a summed tensor."""
    half = (exx + eyy) / 2
    radius = np.hypot((exx - eyy) / 2, exy)
    p1, p2 = half + radius, half - radius
    return dict(
        dilatation=exx + eyy,
        second_invariant=np.hypot(p1, p2),
        shear=np.where(p1 * p2 < 0, np.minimum(np.abs(p1), np.abs(p2)), 0.0),
    )


def budget(rows, excluded=(), tile_m=10000.0, convention="fault_plane"):
    """Historical 10 km rectangle-only audit; kept unchanged for old receipts.

    New physical Stage-1 code must use ``prepare_segments_in_support`` and
    ``budget_prepared`` so trace length and tile area are clipped to the finite
    data footprint. This legacy function uses full 10 km rectangles.
    """
    if tile_m != 10000.0:
        raise ValueError("this legacy audited grid uses fixed 10km tiles")
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


_SENSE_CODE = {"N": 0, "RL": 1, "LL": 2}


@dataclass(frozen=True)
class PreparedSegments:
    """Footprint-clipped segment fragments cached for repeated holdout scenarios."""

    tile_px: int
    tile_shape: tuple[int, int]
    area_by_tile_m2: np.ndarray
    record_id: np.ndarray
    source_segment_index: np.ndarray
    pixel_row: np.ndarray
    pixel_col: np.ndarray
    tile_id: np.ndarray
    length_m: np.ndarray
    strike_x: np.ndarray
    strike_y: np.ndarray
    rate_mm_yr: np.ndarray
    sense_code: np.ndarray
    meta: dict

    @property
    def supported_record_ids(self) -> np.ndarray:
        return np.unique(self.record_id)

    def records_intersecting(self, pixel_mask: np.ndarray) -> np.ndarray:
        """Unique source record IDs with any retained line fragment in a mask."""
        mask = np.asarray(pixel_mask, dtype=bool)
        if mask.shape != GRID.shape:
            raise ValueError(f"pixel mask shape {mask.shape} != {GRID.shape}")
        hit = mask[self.pixel_row, self.pixel_col]
        return np.unique(self.record_id[hit])

    def rasterize_records(self, record_ids) -> np.ndarray:
        """Rasterize source line cells (including unknown-sense rows) in support."""
        wanted = np.asarray(list(record_ids))
        out = np.zeros(GRID.shape, dtype=bool)
        if wanted.size == 0 or self.record_id.size == 0:
            return out
        hit = np.isin(self.record_id, wanted)
        out[self.pixel_row[hit], self.pixel_col[hit]] = True
        return out


def _cell_candidates(x: float, y: float, area_mask: np.ndarray,
                     origin_x: float, origin_y: float, pixel_m: float):
    """Return one deterministic valid cell for a segment interval midpoint.

    A line lying exactly on a pixel edge is included once if either adjacent
    pixel belongs to the data footprint; it is never double-counted.
    """
    qx = (x - origin_x) / pixel_m
    qy = (origin_y - y) / pixel_m
    ix, iy = round(qx), round(qy)
    tol = 1e-10
    cols = ([ix - 1, ix] if abs(qx - ix) <= tol else [math.floor(qx)])
    rows = ([iy - 1, iy] if abs(qy - iy) <= tol else [math.floor(qy)])
    candidates = sorted((int(r), int(c)) for r in rows for c in cols)
    h, w = area_mask.shape
    for r, c in candidates:
        if 0 <= r < h and 0 <= c < w and area_mask[r, c]:
            return r, c
    return None


def _pixel_intervals_in_mask(x0: float, y0: float, x1: float, y1: float,
                             area_mask: np.ndarray, origin_x: float,
                             origin_y: float, pixel_m: float):
    """Yield (row, col, length) for each line portion inside a true mask pixel."""
    h, w = area_mask.shape
    dx, dy = x1 - x0, y1 - y0
    total_length = math.hypot(dx, dy)
    if total_length <= 0.0:
        return
    xmin, xmax = origin_x, origin_x + w * pixel_m
    ymax, ymin = origin_y, origin_y - h * pixel_m
    clipped = clip_segment(x0, y0, x1, y1, xmin, ymin, xmax, ymax)
    if clipped is None:
        return
    ax, ay, bx, by = clipped
    cdx, cdy = bx - ax, by - ay
    clipped_length = math.hypot(cdx, cdy)
    if clipped_length <= 0.0:
        return
    # Convert clipped endpoints to the original segment's parameter t.
    t_start = ((ax - x0) * dx + (ay - y0) * dy) / (total_length * total_length)
    t_end = ((bx - x0) * dx + (by - y0) * dy) / (total_length * total_length)
    if t_end < t_start:
        t_start, t_end = t_end, t_start
    cuts = [t_start, t_end]
    for origin, step, start, delta in ((origin_x, pixel_m, x0, dx),
                                      (origin_y, pixel_m, y0, dy)):
        if abs(delta) <= 1e-15:
            continue
        lo = min(start + t_start * delta, start + t_end * delta)
        hi = max(start + t_start * delta, start + t_end * delta)
        k0 = math.floor((lo - origin) / step) - 1
        k1 = math.ceil((hi - origin) / step) + 1
        for k in range(k0, k1 + 1):
            boundary = origin + k * step
            t = (boundary - start) / delta
            if t_start + 1e-12 < t < t_end - 1e-12:
                cuts.append(t)
    cuts = np.unique(np.asarray(cuts, dtype=np.float64))
    cuts.sort()
    for ta, tb in zip(cuts[:-1], cuts[1:]):
        if tb - ta <= 1e-14:
            continue
        tm = (ta + tb) * 0.5
        xm = x0 + tm * dx
        ym = y0 + tm * dy
        cell = _cell_candidates(xm, ym, area_mask, origin_x, origin_y, pixel_m)
        if cell is None:
            continue
        yield cell[0], cell[1], total_length * (tb - ta)


def _tile_areas(area_mask: np.ndarray, tile_px: int, pixel_m: float):
    h, w = area_mask.shape
    ny = (h + tile_px - 1) // tile_px
    nx = (w + tile_px - 1) // tile_px
    padded = np.zeros((ny * tile_px, nx * tile_px), dtype=np.float64)
    padded[:h, :w] = np.asarray(area_mask, dtype=np.float64)
    count = padded.reshape(ny, tile_px, nx, tile_px).sum(axis=(1, 3))
    return count * pixel_m**2


def prepare_segments_in_support(rows, area_mask: np.ndarray, tile_px: int = 200) -> PreparedSegments:
    """Split official source line segments at pixel/tile boundaries and mask edges.

    ``area_mask`` must be the common valid footprint on which the observed
    geodetic scalar layers are defined. This simultaneously clips numerator
    (trace length) and denominator (actual supported tile area), unlike the
    older bounding-rectangle diagnostic.
    """
    area_mask = np.asarray(area_mask, dtype=bool)
    if area_mask.shape != GRID.shape:
        raise ValueError(f"area_mask shape {area_mask.shape} != {GRID.shape}")
    if int(tile_px) != tile_px or tile_px <= 0:
        raise ValueError("tile_px must be a positive integer")
    a, b, c, d, e, f = GRID.transform
    if abs(b) > 1e-12 or abs(d) > 1e-12 or abs(a + e) > 1e-9:
        raise ValueError("source-vector clipping currently requires north-up square pixels")
    pixel_m = float(a)
    if pixel_m <= 0:
        raise ValueError("pixel size must be positive")
    tile_px = int(tile_px)
    tile_areas = _tile_areas(area_mask, tile_px, pixel_m)
    ny, nx = tile_areas.shape
    origin_x, origin_y = float(c), float(f)

    record_ids = []
    segment_ids = []
    rows_out = []
    cols_out = []
    tile_ids = []
    lengths = []
    strike_xs = []
    strike_ys = []
    rates = []
    senses = []
    supported_source_segments = set()
    unsupported_source_segments = set()
    missing_rate_source_segments = set()
    record_lengths = {}
    supported_length = 0.0
    unknown_length = 0.0
    missing_rate_length = 0.0
    source_count = 0

    for source_index, row in enumerate(rows.itertuples(index=False)):
        source_count += 1
        try:
            record_id = int(row.record_id)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"record_id must be an integer, got {row.record_id!r}") from exc
        x0, y0, x1, y1 = map(float, (row.x0, row.y0, row.x1, row.y1))
        dx, dy = x1 - x0, y1 - y0
        source_length = math.hypot(dx, dy)
        if source_length <= 0.0:
            continue
        sx, sy = dx / source_length, dy / source_length
        sense = str(row.sense).strip().upper() if row.sense is not None else ""
        if sense in ("N", "RL", "LL"):
            sense_code = _SENSE_CODE[sense]
        else:
            sense_code = -1
        try:
            rate = float(row.slip_mm_yr)
        except (TypeError, ValueError):
            rate = float("nan")

        source_has_support = False
        for r, col, part_length in _pixel_intervals_in_mask(
            x0, y0, x1, y1, area_mask, origin_x, origin_y, pixel_m
        ):
            source_has_support = True
            supported_source_segments.add(source_index)
            record_lengths[record_id] = record_lengths.get(record_id, 0.0) + part_length
            record_ids.append(record_id)
            segment_ids.append(source_index)
            rows_out.append(r)
            cols_out.append(col)
            tile_ids.append((r // tile_px) * nx + (col // tile_px))
            lengths.append(part_length)
            strike_xs.append(sx)
            strike_ys.append(sy)
            rates.append(rate)
            senses.append(sense_code)
            if sense_code < 0:
                unsupported_source_segments.add(source_index)
                unknown_length += part_length
            elif not np.isfinite(rate) or rate < 0:
                missing_rate_source_segments.add(source_index)
                missing_rate_length += part_length
            else:
                supported_length += part_length
        if not source_has_support:
            continue

    arrays = dict(
        record_id=np.asarray(record_ids, dtype=np.int32),
        source_segment_index=np.asarray(segment_ids, dtype=np.int32),
        pixel_row=np.asarray(rows_out, dtype=np.int32),
        pixel_col=np.asarray(cols_out, dtype=np.int32),
        tile_id=np.asarray(tile_ids, dtype=np.int32),
        length_m=np.asarray(lengths, dtype=np.float64),
        strike_x=np.asarray(strike_xs, dtype=np.float64),
        strike_y=np.asarray(strike_ys, dtype=np.float64),
        rate_mm_yr=np.asarray(rates, dtype=np.float64),
        sense_code=np.asarray(senses, dtype=np.int8),
    )
    meta = dict(
        source_segment_rows=int(source_count),
        source_trace_records=int(len(set(int(x) for x in rows.record_id))),
        segments_with_supported_geometry=int(len(supported_source_segments)),
        records_with_supported_geometry=int(len(record_lengths)),
        supported_source_length_m=float(sum(record_lengths.values())),
        known_sense_rate_length_m=float(supported_length),
        unknown_sense_segment_rows=int(len(unsupported_source_segments)),
        unknown_sense_unique_records=int(len({int(rows.iloc[i].record_id)
                                               for i in range(len(rows))
                                               if i in unsupported_source_segments})),
        unknown_sense_length_m=float(unknown_length),
        missing_or_negative_rate_segment_rows=int(len(missing_rate_source_segments)),
        missing_or_negative_rate_length_m=float(missing_rate_length),
        pixel_size_m=pixel_m,
        tile_px=tile_px,
        tile_m=pixel_m * tile_px,
        tile_shape=[int(ny), int(nx)],
        support_area_m2=float(area_mask.sum() * pixel_m**2),
        tile_area_m2_min=float(tile_areas[tile_areas > 0].min()) if (tile_areas > 0).any() else 0.0,
        tile_area_m2_max=float(tile_areas.max()) if tile_areas.size else 0.0,
        unknown_sense="omitted from tensor; retained as trace geometry for holdout truth",
    )
    return PreparedSegments(
        tile_px=tile_px, tile_shape=(ny, nx), area_by_tile_m2=tile_areas,
        meta=meta, **arrays,
    )


def budget_prepared(prepared: PreparedSegments, excluded=(),
                    convention: str = "fault_plane", normal_dip_deg: float = 60.0):
    """Sum a cached, footprint-clipped segment tensor into broad tiles (1/year)."""
    if convention not in ("fault_plane", "vertical"):
        raise ValueError("convention must be 'fault_plane' or 'vertical'")
    if not 0.0 < normal_dip_deg < 90.0:
        raise ValueError("normal dip must be strictly between 0 and 90 degrees")
    excluded = np.asarray(list(excluded), dtype=np.int32)
    if excluded.size:
        keep_record = ~np.isin(prepared.record_id, excluded)
    else:
        keep_record = np.ones(prepared.record_id.shape, dtype=bool)
    known_sense = prepared.sense_code >= 0
    valid_rate = np.isfinite(prepared.rate_mm_yr) & (prepared.rate_mm_yr >= 0.0)
    used = keep_record & known_sense & valid_rate
    unknown = keep_record & ~known_sense
    missing_rate = keep_record & known_sense & ~valid_rate

    out = np.zeros((3, *prepared.tile_shape), dtype=np.float64)
    if used.any():
        tile_id = prepared.tile_id[used]
        area = prepared.area_by_tile_m2.ravel()[tile_id]
        if np.any(area <= 0.0):
            raise ValueError("a supported segment falls in a zero-area tile")
        length = prepared.length_m[used]
        rate = prepared.rate_mm_yr[used] * 1e-3
        tx = prepared.strike_x[used]
        ty = prepared.strike_y[used]
        nx, ny = -ty, tx
        base = length * rate / area
        sense = prepared.sense_code[used]
        normal = sense == _SENSE_CODE["N"]
        strike = ~normal
        if convention == "fault_plane":
            dip_factor = math.cos(math.radians(normal_dip_deg))
        else:
            dip_factor = 1.0 / math.tan(math.radians(normal_dip_deg))
        exx = np.zeros(length.shape, dtype=np.float64)
        eyy = np.zeros(length.shape, dtype=np.float64)
        exy = np.zeros(length.shape, dtype=np.float64)
        exx[normal] = base[normal] * dip_factor * nx[normal] ** 2
        eyy[normal] = base[normal] * dip_factor * ny[normal] ** 2
        exy[normal] = base[normal] * dip_factor * nx[normal] * ny[normal]
        if strike.any():
            sign = np.where(sense[strike] == _SENSE_CODE["LL"], -1.0, 1.0)
            shear = base[strike] * sign / 2.0
            exx[strike] = 2.0 * shear * nx[strike] * tx[strike]
            eyy[strike] = 2.0 * shear * ny[strike] * ty[strike]
            exy[strike] = shear * (nx[strike] * ty[strike] + ny[strike] * tx[strike])
        n_tiles = int(np.prod(prepared.tile_shape))
        flat = np.stack([
            np.bincount(tile_id, weights=exx, minlength=n_tiles),
            np.bincount(tile_id, weights=eyy, minlength=n_tiles),
            np.bincount(tile_id, weights=exy, minlength=n_tiles),
        ]).reshape((3, *prepared.tile_shape))
        out += flat

    def unique_count(m):
        if not np.any(m):
            return 0
        return int(np.unique(prepared.source_segment_index[m]).size)

    if used.any():
        used_records = int(np.unique(prepared.record_id[used]).size)
        used_length = float(prepared.length_m[used].sum())
    else:
        used_records, used_length = 0, 0.0
    meta = dict(
        **prepared.meta,
        rate_convention=convention,
        normal_dip_deg=float(normal_dip_deg),
        excluded_trace_records=int(excluded.size),
        used_sense_rate_segments=unique_count(used),
        used_trace_records=used_records,
        used_length_m=used_length,
        omitted_unknown_sense_segments=unique_count(unknown),
        omitted_unknown_sense_records=(int(np.unique(prepared.record_id[unknown]).size)
                                       if unknown.any() else 0),
        omitted_unknown_sense_length_m=float(prepared.length_m[unknown].sum()),
        omitted_missing_or_negative_rate_segments=unique_count(missing_rate),
        omitted_missing_or_negative_rate_length_m=float(prepared.length_m[missing_rate].sum()),
    )
    return out, meta
