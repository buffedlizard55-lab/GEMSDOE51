"""Candidate-hypothesis feature groups (the things we have *not* tried before).

Each builder returns a dict  name -> (H, W) float32 grid, NaN outside the
footprint.  Groups are added to the baseline physical stack one at a time so the
holdout can attribute any change in DTI to that specific hypothesis.

Static groups do not depend on the catalogue and are computed once.
Catalogue-dependent groups must be recomputed per fold from ``fold.known`` only,
otherwise the held-out truth leaks into the model (IR-51-LEAK-01).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .grid import GRID
from .stack import lineament_bank

H, W = GRID.shape


def _edge_bank(field: np.ndarray, mask: np.ndarray, label: str, scales=(1.5, 4.0)):
    out = {}
    for s in scales:
        edge, crest, lin = lineament_bank(field, mask, s)
        t = int(s * 10)
        out[f"{label}_s{t:02d}_edge"] = edge
        out[f"{label}_s{t:02d}_crest"] = crest
        out[f"{label}_s{t:02d}_lin"] = lin
    return out


def cross_physics_edge_features(magnetic: np.ndarray, gravity: np.ndarray,
                                mask: np.ndarray, sigma: float = 2.0) -> dict[str, np.ndarray]:
    """Return edge-normal agreement and joint edge strength for two scalar fields.

    The normals are unoriented, so reversing the sign of one anomaly does not
    change its geological edge direction.  ``coedge`` is the geometric mean of
    robustly scaled gradient magnitudes multiplied by |cos(theta)|.  The scale
    denominators are the 95th percentiles of deterministic, evenly subsampled
    valid pixels; no labels or holdout truths enter the transform.
    """
    mask = np.asarray(mask, dtype=bool)
    mag = np.asarray(magnetic, dtype=np.float32)
    grav = np.asarray(gravity, dtype=np.float32)
    valid = mask & np.isfinite(mag) & np.isfinite(grav)
    gx_m = _ncd(mag, valid, sigma, [0, 1])
    gy_m = _ncd(mag, valid, sigma, [1, 0])
    gx_g = _ncd(grav, valid, sigma, [0, 1])
    gy_g = _ncd(grav, valid, sigma, [1, 0])
    norm_m = np.hypot(gx_m, gy_m)
    norm_g = np.hypot(gx_g, gy_g)
    denom = np.maximum(norm_m * norm_g, 1e-12)
    alignment = np.clip(np.abs(gx_m * gx_g + gy_m * gy_g) / denom, 0.0, 1.0)
    alignment[(norm_m <= 1e-8) | (norm_g <= 1e-8)] = 0.0

    def robust_p95(v):
        ok = valid & np.isfinite(v)
        vals = v[ok]
        if vals.size == 0:
            return 0.0
        stride = max(1, int(np.ceil(vals.size / 200_000)))
        return float(np.quantile(vals[::stride], 0.95))

    scale_m = robust_p95(norm_m)
    scale_g = robust_p95(norm_g)
    if scale_m <= 1e-12 or scale_g <= 1e-12:
        coedge = np.zeros(mag.shape, dtype=np.float32)
    else:
        em = np.clip(norm_m / scale_m, 0.0, 1.0)
        eg = np.clip(norm_g / scale_g, 0.0, 1.0)
        coedge = np.sqrt(em * eg) * alignment
    alignment = alignment.astype(np.float32)
    coedge = coedge.astype(np.float32)
    alignment[~valid] = np.nan
    coedge[~valid] = np.nan
    return {"alignment": alignment, "coedge": coedge}


def _masked_gaussian(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Mask-normalized Gaussian smoothing of a source derivative field."""
    valid = np.asarray(valid, dtype=bool) & np.isfinite(field)
    numerator = ndi.gaussian_filter(
        np.where(valid, field, 0.0).astype(np.float32), sigma=float(sigma), mode="nearest"
    )
    denominator = ndi.gaussian_filter(
        valid.astype(np.float32), sigma=float(sigma), mode="nearest"
    )
    out = np.full(field.shape, np.nan, dtype=np.float32)
    good = valid & (denominator >= 0.2)
    np.divide(numerator, denominator, out=out, where=good)
    return out


def _tie_aware_rank01(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Average-tie empirical rank; a constant field has zero edge strength."""
    from scipy.stats import rankdata

    out = np.full(values.shape, np.nan, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(values)
    if not valid.any():
        return out
    selected = values[valid]
    if selected.size == 1 or float(selected.max()) <= float(selected.min()):
        out[valid] = 0.0
        return out
    ranks = rankdata(selected, method="average")
    out[valid] = ((ranks - 1.0) / (selected.size - 1.0)).astype(np.float32)
    return out


def tilt_angle_edge_feature(vertical_gradient: np.ndarray,
                            horizontal_gradient: np.ndarray,
                            mask: np.ndarray, sigma: float,
                            tilt_tolerance_rad: float = 0.20) -> np.ndarray:
    """Scale-normalized potential-field tilt-edge confidence.

    ``theta = atan2(VG, abs(HG))`` is a tilt-like phase proxy between the
    supplied vertical-gradient band and the absolute value of the supplied
    horizontal-gradient band for the *same source field*. The local gravity HG
    band contains signed values; taking its absolute value avoids sign
    cancellation. Because the available band metadata does not establish whether
    HG is a full 2-D magnitude or one signed horizontal component, this is not
    claimed to be the conventional total-horizontal-derivative tilt angle. The
    empirical-rank HG strength downweights near-zero gradients, while
    ``exp(-abs(theta)/tau)`` emphasizes near-zero phase. Raw supplied bands are
    used rather than independently rank-transformed scalar fields. All values
    outside ``mask`` remain NaN.
    """
    vertical = np.asarray(vertical_gradient, dtype=np.float32)
    horizontal = np.asarray(horizontal_gradient, dtype=np.float32)
    mask = np.asarray(mask, dtype=bool)
    if vertical.shape != horizontal.shape or mask.shape != vertical.shape:
        raise ValueError("vertical gradient, horizontal gradient, and mask must match")
    if sigma <= 0 or tilt_tolerance_rad <= 0:
        raise ValueError("sigma and tilt_tolerance_rad must be positive")

    valid = mask & np.isfinite(vertical) & np.isfinite(horizontal)
    # The supplied gravity HG band is signed in the local mirror; abs(HG) is a
    # magnitude proxy, not a claim that this band is the full 2-D THDR.
    horizontal_magnitude = np.abs(horizontal)
    vg = _masked_gaussian(vertical, valid, sigma)
    hg = _masked_gaussian(horizontal_magnitude, valid, sigma)
    valid &= np.isfinite(vg) & np.isfinite(hg)
    hg = np.maximum(hg, 0.0)
    strength = _tie_aware_rank01(hg, valid)
    theta = np.arctan2(vg, hg)
    score = strength * np.exp(-np.abs(theta) / float(tilt_tolerance_rad))
    score[~valid] = np.nan
    return score.astype(np.float32)


def _build_hk1_tilt_features(stack, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Read raw like-unit gradient pairs and build preregistered H51-K1 features."""
    import rasterio
    from pathlib import Path

    raw_path = Path(stack.dir).parent / "raw" / "training_features.tif"
    if not raw_path.is_file():
        raise FileNotFoundError(f"raw competition feature raster is required: {raw_path}")

    required = ("tmi_hg", "tmi_vg", "iso_grav_anom_hg", "iso_grav_anom_vg")
    with rasterio.open(raw_path) as src:
        GRID.assert_matches(dict(transform=src.transform, height=src.height,
                                 width=src.width, crs=src.crs))
        descriptions = [d.split(" - ")[0].strip() if d else "" for d in src.descriptions]
        if len(set(descriptions)) != len(descriptions):
            raise ValueError("competition raster has missing or duplicate band descriptions")
        absent = [name for name in required if name not in descriptions]
        if absent:
            raise ValueError(f"competition raster is missing required H51-K1 bands: {absent}")
        raw = {}
        for name in required:
            values = src.read(descriptions.index(name) + 1).astype(np.float32)
            values[~np.isfinite(values) | (values <= -1e38)] = np.nan
            raw[name] = values

    mag_mask = footprint & np.isfinite(raw["tmi_hg"]) & np.isfinite(raw["tmi_vg"])
    grav_mask = footprint & np.isfinite(raw["iso_grav_anom_hg"]) & np.isfinite(raw["iso_grav_anom_vg"])
    mag_by_scale = [tilt_angle_edge_feature(raw["tmi_vg"], raw["tmi_hg"],
                                             mag_mask, sigma=s)
                    for s in (2.0, 5.0)]
    grav_by_scale = [tilt_angle_edge_feature(raw["iso_grav_anom_vg"],
                                              raw["iso_grav_anom_hg"],
                                              grav_mask, sigma=s)
                     for s in (2.0, 5.0)]
    mag_persist = np.minimum(mag_by_scale[0], mag_by_scale[1])
    grav_persist = np.minimum(grav_by_scale[0], grav_by_scale[1])
    joint_valid = np.isfinite(mag_persist) & np.isfinite(grav_persist)
    joint = np.full(footprint.shape, np.nan, dtype=np.float32)
    joint[joint_valid] = np.sqrt(np.maximum(
        mag_persist[joint_valid] * grav_persist[joint_valid], 0.0
    )).astype(np.float32)
    return {
        "hk1_mag_persist": mag_persist.astype(np.float32),
        "hk1_grav_persist": grav_persist.astype(np.float32),
        "hk1_joint_persist": joint,
    }


def build_static(stack, footprint: np.ndarray) -> dict:
    """Hypothesis groups that use no catalogue information."""
    g = {}
    get = lambda n: np.asarray(stack.data[stack.names.index(n)], dtype=np.float32)

    # ---------------------------------------------------------------- H-E
    # Basin-bounding (range-front) faults.  A Great Basin range front is a step
    # in the depth-to-basement surface, a gravity gradient, and a resistivity
    # contrast between bedrock and basin fill -- three *independent* expressions
    # of the same buried structure.  A buried or blind range-front fault can be
    # almost invisible in topography while being obvious here, which is exactly
    # the class of structure a scarp-based catalogue misses.
    for src, lab in [("comp_depth_to_base_surf", "base"),
                     ("comp_cond_surf", "cond")]:
        f = get(src)
        m = np.isfinite(f) & footprint
        g.update(_edge_bank(f, m, lab, scales=(1.5, 4.0)))
    grav = get("comp_iso_grav_anom")
    m = np.isfinite(grav) & footprint
    g.update(_edge_bank(grav, m, "grav2", scales=(4.0,)))

    # depth-to-basement step *asymmetry*: a range front is a monotone step, so
    # the along-profile first derivative keeps one sign over kilometres.
    base = get("comp_depth_to_base_surf")
    m = np.isfinite(base) & footprint
    gx = _ncd(base, m, 3.0, [0, 1])
    gy = _ncd(base, m, 3.0, [1, 0])
    mag = np.hypot(gx, gy)
    # coherence of the step direction in a 9x9 window (|mean vector| / mean |vector|)
    ux = np.where(mag > 0, gx / np.maximum(mag, 1e-9), 0.0)
    uy = np.where(mag > 0, gy / np.maximum(mag, 1e-9), 0.0)
    ux = np.where(m, ux, 0.0); uy = np.where(m, uy, 0.0)
    wgt = np.where(m, mag, 0.0)
    k = np.ones((9, 9), np.float32)
    sx = ndi.convolve(ux * wgt, k, mode="nearest")
    sy = ndi.convolve(uy * wgt, k, mode="nearest")
    sw = ndi.convolve(wgt, k, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        coh = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
    coh[~(m.astype(bool))] = np.nan
    g["base_step_coh09"] = coh.astype(np.float32)

    # ---------------------------------------------------------------- H-X1
    # Cross-physics edge-normal concordance.  A buried fault/contact can produce
    # a magnetic edge and a density/gravity edge even where relief is weak.  The
    # *new* signal is not either edge magnitude by itself (both are already in
    # the base stack), but the local agreement of their unoriented edge normals.
    # Derivatives are computed from the rank-normalised competition bands so
    # feature scale is comparable and robust to the source units.  Two scales
    # (200 m and 500 m) are preregistered in knowledge/preregistration-2026-10-07.md.
    mag = get("comp_tmi")
    grav = get("comp_iso_grav_anom")
    common = footprint & np.isfinite(mag) & np.isfinite(grav)
    for sigma in (2.0, 5.0):
        feats = cross_physics_edge_features(mag, grav, common, sigma=sigma)
        suffix = f"s{int(sigma * 10):02d}"
        g[f"mg_alignment_{suffix}"] = feats["alignment"]
        g[f"mg_coedge_{suffix}"] = feats["coedge"]

    # ---------------------------------------------------------------- H-D
    # Scarp-facing coherence.  A through-going range-front fault has one facing
    # direction for kilometres; noise, drainages and dune fields do not.  We
    # measure |mean unit gradient| / mean |gradient| of the 1 m-DEM relief and of
    # detrended elevation over a 9x9 window -> high where a single scarp
    # dominates the window, regardless of how small that scarp is.
    for src, lab in [("lid_relief", "lidrel"), ("comp_det_elev", "detelev")]:
        f = get(src)
        m = np.isfinite(f) & footprint
        gx = _ncd(f, m, 2.0, [0, 1])
        gy = _ncd(f, m, 2.0, [1, 0])
        mag = np.hypot(gx, gy)
        ok = m & np.isfinite(mag) & (mag > 0)
        ux = np.where(ok, gx / np.maximum(mag, 1e-9), 0.0)
        uy = np.where(ok, gy / np.maximum(mag, 1e-9), 0.0)
        wgt = np.where(ok, mag, 0.0)
        sx = ndi.convolve(ux * wgt, k, mode="nearest")
        sy = ndi.convolve(uy * wgt, k, mode="nearest")
        sw = ndi.convolve(wgt, k, mode="nearest")
        with np.errstate(divide="ignore", invalid="ignore"):
            coh = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
        coh[~m] = np.nan
        g[f"{lab}_facecoh09"] = coh.astype(np.float32)
        # and the same at a longer 21x21 window -> tests *persistence*
        k21 = np.ones((21, 21), np.float32)
        sx = ndi.convolve(ux * wgt, k21, mode="nearest")
        sy = ndi.convolve(uy * wgt, k21, mode="nearest")
        sw = ndi.convolve(wgt, k21, mode="nearest")
        with np.errstate(divide="ignore", invalid="ignore"):
            coh21 = np.hypot(sx, sy) / np.maximum(sw, 1e-9)
        coh21[~m] = np.nan
        g[f"{lab}_facecoh21"] = coh21.astype(np.float32)

    # ---------------------------------------------------------------- H-51-M
    # Cross-scale crest coincidence (session 2026-10-07, knowledge/02 §3 rank 2)
    _build_xscale(g, get, footprint)

    # ---------------------------------------------------------------- H-H
    # Potential-field/basement edge terminations joined by a conductive relay
    # bridge.  This is deliberately a topology operator: it is not a generic
    # high-gradient or local co-location score.  See _build_endpoint_bridge for
    # the exact finite, label-independent construction.
    g.update(_build_endpoint_bridge(get, footprint))

    # ---------------------------------------------------------------- H51-K1
    # Cross-scale tilt-edge persistence from the raw, like-unit TMI and gravity
    # derivative pairs. This candidate was preregistered before implementation
    # in knowledge/candidate-hypotheses-2026-10-07.md. The two scale-specific
    # scores are collapsed with a pixelwise minimum; the model receives only the
    # magnetic, gravity, and joint persistent responses, not six tunable scales.
    g.update(_build_hk1_tilt_features(stack, footprint))

    return g


def _rank_over(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1] over ``valid`` (monotone, 0 where invalid)."""
    v = a[valid]
    out = np.zeros(a.shape, np.float32)
    if v.size == 0:
        return out
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[valid] = (order.astype(np.float64) / max(1, v.size - 1)).astype(np.float32)
    return out


def _build_xscale(g: dict, get, footprint: np.ndarray) -> None:
    """H-51-M — cross-scale crest coincidence (session 2026-10-07).

    A fine crest (sigma 1.5 px) that sits exactly on the axis of the coarse
    crest (sigma 4 px) marks the trace of a through-going structure; an
    asymmetric scarp displaces the single-scale response off-axis, so the
    positional agreement of the two scales is a localisation signal no shipped
    feature carries.  Implemented as Q(fine crest) * exp(-d/1.5) where d is the
    distance to the top-2% coarse-crest set, plus the symmetric rank-min
    agreement min(Q_fine, Q_coarse).
    """
    det = get("comp_det_elev")
    m = np.isfinite(det) & footprint
    _e, crest15, _l = lineament_bank(det, m, 1.5)
    _e, crest40, _l2 = lineament_bank(det, m, 4.0)
    m15 = m & np.isfinite(crest15)
    m40 = m & np.isfinite(crest40)
    thr = np.nanpercentile(crest40[m40], 98.0)
    d40 = ndi.distance_transform_edt(~(m40 & (crest40 >= thr))).astype(np.float32)
    q15 = _rank_over(crest15, m15)
    q40 = _rank_over(crest40, m40)
    near = np.exp(-d40 / 1.5).astype(np.float32)
    g["xscale_coincide_det"] = (q15 * near).astype(np.float32)
    g["xscale_minrank_det"] = np.minimum(q15, q40).astype(np.float32)

    lid = get("lid_relief")
    ml = np.isfinite(lid) & footprint
    _e, lcrest15, _l3 = lineament_bank(lid, ml, 1.5)
    ml15 = ml & np.isfinite(lcrest15)
    ql15 = _rank_over(lcrest15, ml15)
    g["xscale_coincide_lid"] = (ql15 * near).astype(np.float32)


def _ncd(a, mask, sigma, order):
    from .stack import _nc_deriv
    return _nc_deriv(a, mask, sigma, order)


def _rank_unit(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Rank a finite array to [0, 1], preserving NaN outside ``mask``."""
    out = np.full(a.shape, np.nan, dtype=np.float32)
    valid = np.asarray(mask, dtype=bool) & np.isfinite(a)
    if not valid.any():
        return out
    vals = a[valid]
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, vals.size, dtype=np.float32)
    out[valid] = ranks
    return out


def _endpointness(field: np.ndarray, mask: np.ndarray, sigma: float = 2.0,
                  threshold_q: float = 0.88) -> np.ndarray:
    """Find finite potential-field edge terminations without labels.

    A scalar-field gradient supplies the local edge normal.  The tangent is
    sampled one and two pixels in both directions.  A high edge with weak
    continuation on at least one side is an endpoint candidate.  Keeping only
    local maxima above a fixed global quantile makes the result a sparse point
    field rather than a broad habitat mask.  ``map_coordinates`` samples a
    zero-filled edge array at invalid cells; invalid output cells are reset to
    NaN before return.
    """
    valid = np.asarray(mask, dtype=bool) & np.isfinite(field)
    gx = _ncd(field, valid, sigma, [0, 1])
    gy = _ncd(field, valid, sigma, [1, 0])
    edge = np.hypot(gx, gy).astype(np.float32)
    edge[~valid] = np.nan
    finite = valid & np.isfinite(edge)
    out = np.full(field.shape, np.nan, dtype=np.float32)
    if finite.sum() < 32:
        return out
    scale = float(np.nanpercentile(edge[finite], 95.0))
    if not np.isfinite(scale) or scale <= 1e-8:
        return out

    # Tangent is perpendicular to the gradient normal.  The edge array is
    # zero-filled only for interpolation; there is no label or catalogue input.
    safe_edge = np.where(finite, edge, 0.0).astype(np.float32)
    yy, xx = np.indices(field.shape, dtype=np.float32)
    norm = np.maximum(edge, 1e-8)
    tx = -gy / norm
    ty = gx / norm
    coords = []
    for direction in (-1.0, 1.0):
        coords.append(np.array([yy + direction * ty * 1.5,
                                xx + direction * tx * 1.5], dtype=np.float32))
        coords.append(np.array([yy + direction * ty * 3.0,
                                xx + direction * tx * 3.0], dtype=np.float32))
    samples = [ndi.map_coordinates(safe_edge, c, order=1, mode="constant",
                                    cval=0.0) for c in coords]
    forward = np.minimum(samples[2], samples[3])
    backward = np.minimum(samples[0], samples[1])
    continuation = np.minimum(forward, backward) / scale
    # One-sided continuation is retained implicitly by the minimum: a segment
    # endpoint has one weak side, while a through-going edge has two strong sides.
    term = np.clip(edge / scale, 0.0, 2.0) * (1.0 - np.clip(continuation, 0.0, 1.0))
    term[~finite] = -np.inf
    q = float(np.nanpercentile(term[finite], threshold_q * 100.0))
    maxima = term >= ndi.maximum_filter(np.where(np.isfinite(term), term, -np.inf),
                                         size=5, mode="nearest")
    # A slightly higher endpoint threshold than the edge threshold avoids
    # turning every short texture fragment into an endpoint.
    q_endpoint = max(q, float(np.nanpercentile(term[finite], 97.5)))
    keep = finite & maxima & (term >= q_endpoint)
    out[keep] = np.clip(term[keep] / max(q_endpoint, 1e-8), 0.0, 1.0)
    return out


def _paired_bridge(a: np.ndarray, b: np.ndarray, min_px: float = 3.0,
                   max_px: float = 20.0) -> np.ndarray:
    """Create a bridge zone between offset endpoint sets from two layers.

    ``a`` and ``b`` are sparse endpoint maps.  A source endpoint is accepted
    only when the nearest endpoint in the other layer lies in [3, 20] pixels
    (0.3–2.0 km).  Distance transforms of those accepted endpoints define the
    ellipse-like relay zone; a point is scored only when it is near both paired
    sets and the two distances sum to no more than 1.25 times the maximum
    endpoint separation.  Thus an isolated high-gradient pixel or co-located
    edge cannot produce a bridge.
    """
    ma = np.isfinite(a) & (a > 0)
    mb = np.isfinite(b) & (b > 0)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    if not ma.any() or not mb.any():
        return out
    d_b = ndi.distance_transform_edt(~mb).astype(np.float32)
    d_a = ndi.distance_transform_edt(~ma).astype(np.float32)
    pair_a = ma & (d_b >= min_px) & (d_b <= max_px)
    pair_b = mb & (d_a >= min_px) & (d_a <= max_px)
    if not pair_a.any() or not pair_b.any():
        return out
    da = ndi.distance_transform_edt(~pair_a).astype(np.float32)
    db = ndi.distance_transform_edt(~pair_b).astype(np.float32)
    zone = (da <= max_px) & (db <= max_px) & ((da + db) <= max_px * 1.25)
    # High at paired ends and along the shortest relay corridor, lower at its
    # perimeter.  It is intentionally not a probability or a score.
    value = np.exp(-(da + db) / max_px).astype(np.float32)
    value[~zone] = np.nan
    out[zone] = value[zone]
    return out


def _build_endpoint_bridge(get, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """H-H endpoint/bridge features, exact preregistered operator.

    Inputs are rank-transformed competition layers.  Endpoint maps come from
    TMI, gravity and basement-depth scalar fields at sigma=2 px.  Their pairwise
    relay zones are intersected with a local positive conductivity residual.
    ``lid_step_max`` and ``lid_coh100`` are an independent surface check, not a
    hard mask, so blind structures remain possible.
    """
    fields = {
        "mag": get("comp_tmi"),
        "grav": get("comp_iso_grav_anom"),
        "base": get("comp_depth_to_base_surf"),
    }
    endpoints = {}
    for name, field in fields.items():
        valid = footprint & np.isfinite(field)
        endpoints[name] = _endpointness(field, valid, sigma=2.0, threshold_q=0.88)

    bridge_mg = _paired_bridge(endpoints["mag"], endpoints["grav"])
    bridge_mb = _paired_bridge(endpoints["mag"], endpoints["base"])
    bridge_gb = _paired_bridge(endpoints["grav"], endpoints["base"])
    bridges = [bridge_mg, bridge_mb, bridge_gb]
    finite_bridges = [np.isfinite(x) for x in bridges]
    any_bridge = np.logical_or.reduce(finite_bridges) if finite_bridges else np.zeros_like(footprint)
    bridge = np.zeros(footprint.shape, dtype=np.float32)
    for x in bridges:
        bridge = np.maximum(bridge, np.nan_to_num(x, nan=0.0))
    bridge[~any_bridge] = np.nan

    cond = get("comp_cond_surf")
    valid_cond = footprint & np.isfinite(cond)
    # A local positive residual rejects a region-wide conductive basin while
    # retaining a high-conductivity bridge relative to its nearby background.
    cond_fill = np.where(valid_cond, cond, 0.0).astype(np.float32)
    local = ndi.gaussian_filter(cond_fill, sigma=8.0, mode="nearest")
    local_resid = cond - local
    cond_q = _rank_unit(local_resid, valid_cond)
    cond_gate = np.clip((cond_q - 0.65) / 0.35, 0.0, 1.0)
    cond_gate[~valid_cond] = np.nan

    step = get("lid_step_max")
    coh = get("lid_coh100")
    surface = np.nan_to_num(_rank_unit(step, footprint & np.isfinite(step)), nan=0.0)
    surface_coh = np.nan_to_num(_rank_unit(coh, footprint & np.isfinite(coh)), nan=0.0)
    surface_check = (0.5 * surface + 0.5 * surface_coh).astype(np.float32)
    surface_check[~footprint] = np.nan

    out: dict[str, np.ndarray] = {}
    endpoint = np.zeros(footprint.shape, dtype=np.float32)
    for x in endpoints.values():
        endpoint = np.maximum(endpoint, np.nan_to_num(x, nan=0.0))
    endpoint[~footprint] = np.nan
    out["hh_endpoint"] = endpoint
    out["hh_bridge"] = bridge
    out["hh_bridge_cond"] = (bridge * np.nan_to_num(cond_gate, nan=0.0)).astype(np.float32)
    out["hh_bridge_surface"] = (bridge * surface_check).astype(np.float32)
    out["hh_endpoint_concordance"] = (
        endpoint * np.nan_to_num(cond_gate, nan=0.0)
    ).astype(np.float32)
    for x in out.values():
        x[~footprint] = np.nan
    return out


def build_catalogue_dependent(stack, footprint: np.ndarray, known: np.ndarray) -> dict:
    """Hypothesis groups that use only the *known* catalogue of this fold.

    H-C: continuation beyond a mapped trace tip.  The organizer confirmed that
    "new fault" includes newly mapped geometry of an existing fault system
    (https://community.drivendata.org/t/where-do-you-draw-the-line/11536), so the
    corridor just beyond the endpoint of a mapped trace is a priori the single
    cheapest place to look for an unmapped one.
    """
    g = {}
    # trace tips = catalogue pixels with exactly one 8-neighbour catalogue pixel
    nb = ndi.convolve(known.astype(np.float32), np.ones((3, 3), np.float32),
                      mode="constant") - 1.0
    tips = known & (nb <= 1.0)
    d_tip = ndi.distance_transform_edt(~tips).astype(np.float32)
    g["d_tip"] = np.log1p(d_tip).astype(np.float32)
    return g


def tips_of(known: np.ndarray) -> np.ndarray:
    nb = ndi.convolve(known.astype(np.float32), np.ones((3, 3), np.float32),
                      mode="constant") - 1.0
    return known & (nb <= 1.0)
