"""Stage A -- geodetic strain-budget deficit over broad tiles (COARSE PRIOR ONLY).

Hypothesis (stated in the task brief, implemented literally here)
------------------------------------------------------------------
Where the geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the
catalogue is likelier to be missing structures.

FORMULA USED -- and its source (no unsourced formula is used anywhere in this file)
----------------------------------------------------------------------------------
Kostrov's moment-tensor summation (Kostrov 1974, Izv. Acad. Sci. USSR Phys. Solid Earth 1, 23-40):

        eps_dot_ij = (1 / (2 mu tau V)) * sum_{n=1..N} M_ij^n                          (K)

re-written for Quaternary fault slip data (length L_k, slip rate u_dot_k, dip delta_k) by
Kreemer, Haines, Holt & Blewitt (2000), "On the determination of a global strain rate model",
eq. (3) -- public PDF at https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf :

        eps_dot_ij = (1 / (2 A)) * sum_k  L_k u_dot_k m_ij^k / sin(delta_k)              (K3)

where A is the grid-cell area (the horizontal area of the deforming volume), m_ij^k the unit
moment tensor of fault k and delta_k its dip.  (K3) follows from (K) with V = A * H,
M_0^k = mu L_k (H / sin delta_k) u_dot_k because the down-dip width of the seismogenic fault
patch is W_k = H / sin(delta_k) with H the seismogenic thickness, and mu cancels.

IMPLEMENTED REDUCTION.  The available official trace table
(`gdr_qfaults_traces.csv`, GDR submission 1391 / INGENIOUS-derived compilation) carries slip
rate, clipped trace length, slip sense and a grid centroid, but NOT a per-trace rake, so the unit
moment tensor m_ij cannot be formed.  This module therefore implements the SCALAR (isotropic,
mean-moment) reduction of (K3):

        eps_geo(tile) = (1 / (2 A_tile)) * sum_k  L_k u_dot_k / sin(delta_k)             (K3s)

with L_k in metres, u_dot_k in m/yr (mm/yr * 1e-3), delta_k the dip taken from the empirical dip
distribution of the official USGS ScienceBase slip-tendency release (Siler 2022,
https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d), grouped by slip sense, and
A_tile the tile area in m^2.  Units of (K3s): 1/yr; converted to nanostrain/yr (*1e9) to compare
with the official geodetic bands.

CONSEQUENCE OF THE REDUCTION (stated openly, not hidden): dropping the tensor orientation changes
the scalar magnitude by an O(1) factor and mixes deviatoric/shear components.  This module
therefore never uses the absolute value of the deficit: the approval rule is a QUANTILE rule
(`approve_quantile`), which is invariant to any global constant factor.  Only the SPATIAL PATTERN
of the deficit -- which tiles carry more geodetic strain than their mapped faults can absorb --
is used, as a coarse prior.

What this is NOT
----------------
* NOT a claim that the residual is elastic or aseismic: the brief's own caveats apply (the deficit
  can be distributed off-fault, aseismic, or caused by wrong catalogue slip rates).
* NOT a fine-scale locator: tiles are ~25 km; the fine stage (Stage B, `detector.py`) is scored
  separately and must place points only inside the approved tiles.

Precedent for balancing geodetic and geologic deformation, and for modelling off-fault moment
release explicitly:
  * Field et al. (2014), UCERF3, BSSA 104(3) 1122-1180, doi:10.1785/0120130164 (three deformation
    models invert geodetic and geologic data jointly; off-fault strain is modelled explicitly).
  * Zeng & Shen (2016), "A fault-based model for crustal deformation, fault slip-rates and
    off-fault strain rate in California", BSSA 106(2) 766-784, doi:10.1785/0120140250,
    USGS Publications Warehouse 70160311 (https://pubs.usgs.gov/publication/70160311): off-fault
    moment rate 0.88e19 N m/yr against a 2.76e19 N m/yr total for California -- i.e. the residual
    after fault-based deformation is large and spatially structured, which is the premise of this
    stage.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field

import numpy as np

from . import grid

TILE_PX: int = 250                 # 250 px * 100 m = 25 km square tiles
NANOSTRAIN: float = 1e9            # 1/yr -> nanostrain/yr
DEFAULT_DIP_DEG: float = 60.0      # fallback when the slip-sense group has no measurement


@dataclass
class TraceTable:
    """Mapped-fault traces with slip rates (official GDR / INGENIOUS-derived compilation)."""

    slip_rate_mm_yr: np.ndarray
    length_m: np.ndarray
    slip_sense: list[str]
    row: np.ndarray
    col: np.ndarray
    in_footprint: np.ndarray
    name: list[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return int(self.slip_rate_mm_yr.size)

    def moment_area_rate(self, dips_deg: dict[str, float] | None = None) -> np.ndarray:
        """Per-trace contribution L_k * u_dot_k / sin(delta_k) in m^2/yr  (scalar (K3s) term)."""
        dips = dips_deg or {}
        out = np.zeros(self.n, dtype=np.float64)
        for i in range(self.n):
            sense = self.slip_sense[i]
            dip = dips.get(sense, DEFAULT_DIP_DEG)
            if not math.isfinite(dip) or dip <= 0.0:
                dip = DEFAULT_DIP_DEG
            out[i] = (self.length_m[i] * (self.slip_rate_mm_yr[i] * 1e-3)
                      / math.sin(math.radians(dip)))
        return out


def load_traces(path=None) -> TraceTable:
    from .paths import QFAULT_TRACES
    path = path or QFAULT_TRACES
    rows: list[dict] = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)

    def fnum(v, default=float("nan")):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    slip, length, sense, rr, cc, infp, names = [], [], [], [], [], [], []
    for r in rows:
        s = fnum(r.get("slip_rate"))
        L = fnum(r.get("clipped_length_m"))
        if not math.isfinite(s) or not math.isfinite(L) or L <= 0:
            continue
        slip.append(s)
        length.append(L)
        sense.append((r.get("slip_sense") or "").strip())
        rr.append(int(float(r["centroid_row"])))
        cc.append(int(float(r["centroid_col"])))
        infp.append(str(r.get("centroid_in_footprint", "0")).strip() == "1")
        names.append(r.get("name", ""))
    return TraceTable(np.array(slip), np.array(length), sense, np.array(rr), np.array(cc),
                      np.array(infp), names)


def dip_by_sense(slip_tendency_csv=None, verbose: bool = False) -> dict[str, float]:
    """Empirical median dip per slip-sense class from the official USGS ScienceBase release.

    Siler (2022), USGS ScienceBase item 6296974dd34ec53d276bb33d (slip/dilation tendency for
    Quaternary faults in the Great Basin).  Returns {} if the table is unavailable, in which case
    the documented fallback dip of 60 deg is used.
    """
    from .paths import WORK_DIR
    path = slip_tendency_csv or (WORK_DIR / "sb_slip_tendency_in_footprint.csv")
    if not path.exists():
        return {}
    by: dict[str, list[float]] = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            sense = (r.get("slip_sense") or "").strip()
            try:
                dip = float(r.get("Dip"))
            except (TypeError, ValueError):
                continue
            if 0.0 < dip <= 90.0:
                by.setdefault(sense, []).append(dip)
    out = {}
    for sense, vals in by.items():
        if len(vals) >= 30:
            out[sense] = float(np.median(vals))
            if verbose:
                print(f"  dip[{sense}] median={out[sense]:.1f} deg from n={len(vals)} segments")
    return out


def _tile_area_m2(sl_rows: slice, sl_cols: slice) -> float:
    return float((sl_rows.stop - sl_rows.start) * (sl_cols.stop - sl_cols.start)) * grid.PIXEL_M ** 2


def geologic_strain_by_tile(traces: TraceTable, dips: dict[str, float], tile_px: int = TILE_PX,
                            exclude_block: np.ndarray | None = None, block_id: int | None = None):
    """Tile dict: (i, j) -> scalar geologic strain rate (nanostrain/yr) from (K3s).

    `exclude_block`/`block_id` implement the leave-one-block-out construction used by the Stage A
    holdout test: traces whose centroid falls in the held-out block are removed before summing, so
    the prior for a block never sees that block's own mapped faults.
    """
    contrib = traces.moment_area_rate(dips)
    if exclude_block is not None and block_id is not None:
        mask = exclude_block[traces.row, traces.col] == block_id
        contrib = np.where(mask, 0.0, contrib)
    acc: dict[tuple[int, int], float] = {}
    for k in range(traces.n):
        r, c = traces.row[k], traces.col[k]
        key = (r // tile_px, c // tile_px)
        acc[key] = acc.get(key, 0.0) + float(contrib[k])
    out = {}
    for (i, j, rs, cs, cov) in grid.tiles(tile_px):
        area = _tile_area_m2(rs, cs)
        out[(i, j)] = acc.get((i, j), 0.0) / (2.0 * area) * NANOSTRAIN
    return out


def geodetic_strain_by_tile(band: str = "geod_2ndinv", tile_px: int = TILE_PX):
    """Tile mean of an official geodetic strain-rate band (nanostrain/yr, band units)."""
    a = grid.read_band(band)
    out = {}
    for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
        v = a[rs, cs]
        v = v[np.isfinite(v)]
        out[(i, j)] = float(v.mean()) if v.size else float("nan")
    return out


def deficit_table(tile_px: int = TILE_PX, band: str = "geod_2ndinv") -> list[dict]:
    """Per-tile Stage A table: geodetic, geologic, residual and ratio."""
    from .paths import WORK_DIR
    traces = load_traces()
    dips = dip_by_sense()
    if not dips:
        print("[stage A] WARNING: ScienceBase slip-tendency table absent -> fallback dip "
              f"{DEFAULT_DIP_DEG} deg (documented assumption)")
    geo = geologic_strain_by_tile(traces, dips, tile_px)
    geod = geodetic_strain_by_tile(band, tile_px)
    rows = []
    for key in sorted(geod):
        i, j = key
        g = geod[key]
        k = geo.get(key, 0.0)
        if not math.isfinite(g):
            continue
        rows.append(dict(tile_i=i, tile_j=j, geodetic_ns_yr=g, geologic_ns_yr=k,
                         residual_ns_yr=g - k, ratio=(k / g) if g > 0 else float("nan"),
                         deficit=1.0 - (k / g) if g > 0 else float("nan")))
    return rows


def approve_quantile(rows: list[dict], q: float = 0.5) -> set[tuple[int, int]]:
    """Approved tiles = tiles whose deficit is at or above the q-quantile.

    A quantile rule is used deliberately: it is invariant to any global constant factor, which is
    the honest way to handle the O(1) ambiguity introduced by the scalar reduction (K3s) and by
    the unknown convention/units of the published geodetic bands.
    """
    vals = np.array([r["deficit"] for r in rows if math.isfinite(r["deficit"])])
    if vals.size == 0:
        return set()
    thr = float(np.quantile(vals, q))
    return {(r["tile_i"], r["tile_j"]) for r in rows
            if math.isfinite(r["deficit"]) and r["deficit"] >= thr}


def approved_mask(approved: set[tuple[int, int]], tile_px: int = TILE_PX) -> np.ndarray:
    m = np.zeros(grid.SHAPE, dtype=bool)
    for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
        if (i, j) in approved:
            m[rs, cs] = True
    return m & grid.footprint()


def stage_a_holdout(tile_px: int = TILE_PX, n_blocks: int = 2, band: str = "geod_2ndinv",
                    q: float = 0.5) -> dict:
    """Falsifiable Stage A test on spatially blocked folds.

    For each block b: rebuild the deficit with the block's own traces removed (leave-one-block-out)
    and ask whether the approved tiles still concentrate the *held-out* catalogue labels.
    Reported per block (label density lift in approved tiles) and pooled (Spearman rho).
    """
    from scipy.stats import spearmanr

    traces = load_traces()
    dips = dip_by_sense()
    block = grid.spatial_blocks(n_blocks)
    cat = grid.catalogue()
    fp = grid.footprint()
    geod_field = grid.read_band(band)

    per_block = []
    ridge_x, ridge_y = [], []
    for b in range(n_blocks * n_blocks):
        geo_b = geologic_strain_by_tile(traces, dips, tile_px, exclude_block=block, block_id=b)
        rows = []
        for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
            v = geod_field[rs, cs]
            v = v[np.isfinite(v)]
            if not v.size:
                continue
            g = float(v.mean())
            k = geo_b.get((i, j), 0.0)
            rows.append(dict(tile_i=i, tile_j=j, geodetic_ns_yr=g, geologic_ns_yr=k,
                             deficit=(1.0 - k / g) if g > 0 else float("nan")))
        appr = approve_quantile(rows, q)
        # held-out labels: catalogue pixels inside block b
        sel = np.zeros(grid.SHAPE, bool)
        sel[block == b] = True
        denom_px = int((sel & fp).sum())
        lab_px = int((sel & cat & fp).sum())
        approved_px = 0
        approved_lab = 0
        for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
            if (i, j) not in appr:
                continue
            s = np.zeros(grid.SHAPE, bool)
            s[rs, cs] = True
            s &= sel
            approved_px += int((s & fp).sum())
            approved_lab += int((s & cat & fp).sum())
        lift = ((approved_lab / approved_px) / (lab_px / denom_px)) if approved_px and denom_px \
            and lab_px else float("nan")
        per_block.append(dict(block=b, approved_tiles=len(appr), approved_px=approved_px,
                              held_out_label_px=lab_px, label_density_lift=lift))
        for r in rows:
            if math.isfinite(r["deficit"]):
                ridge_x.append(r["deficit"])
                ii, jj = r["tile_i"], r["tile_j"]
                rs2 = slice(ii * tile_px, (ii + 1) * tile_px)
                cs2 = slice(jj * tile_px, (jj + 1) * tile_px)
                sub_lab = cat[rs2, cs2] & fp[rs2, cs2]
                sub_fp = fp[rs2, cs2]
                ridge_y.append(float(sub_lab.sum()) / max(1, int(sub_fp.sum())))
    rho = float(spearmanr(ridge_x, ridge_y).statistic) if len(ridge_x) > 10 else float("nan")
    lifts = [b["label_density_lift"] for b in per_block if math.isfinite(b["label_density_lift"])]
    return dict(tile_px=tile_px, quantile=q, band=band, per_block=per_block,
                spearman_deficit_vs_label_density=rho,
                mean_lift=float(np.mean(lifts)) if lifts else float("nan"),
                folds_with_lift_gt_1=int(sum(1 for v in lifts if v > 1.0)),
                n_folds=len(lifts))


# ---------------------------------------------------------------------------------------------
# Stage A validation.  Two instruments, one of which is biased by construction.
# ---------------------------------------------------------------------------------------------
# INSTRUMENT 1 (biased -- reported as a negative control): catalogue-label density in held-out
# blocks.  The deficit is defined as what the *catalogue* cannot accommodate, so it is
# mechanically anti-correlated with catalogue density wherever the trace table is complete.
# A failure on instrument 1 is therefore expected and is NOT evidence against the hypothesis.
#
# INSTRUMENT 2 (the real test): independent off-catalogue fault evidence.  If a high deficit
# marks ground where the catalogue is missing structures, then it must also carry a higher
# density of fault evidence that comes from a *different* compilation and is *not* in the
# catalogue:
#   * SGMC faults rasterised on this grid (derived_sgmc_faults_100m_u8.tif) restricted to pixels
#     >= 2 px from the catalogue;
#   * lidar scarp-feature intensity (lidar_scarp_features_u8.tif, 12 bands of scarp proxies).
# Both are hash-pinned external layers (see registry/data_manifest.json) derived from official
# USGS/GeoDAWN products.  This is a falsifiable test: rho <= 0 refutes the prior.

def _independent_layers():
    import rasterio
    from .paths import SGMC_FAULTS, LIDAR_SCARP
    layers = {}
    if SGMC_FAULTS.exists():
        with rasterio.open(SGMC_FAULTS) as ds:
            layers["sgmc"] = (ds.read(1) > 0)
    if LIDAR_SCARP.exists():
        with rasterio.open(LIDAR_SCARP) as ds:
            arr = ds.read().astype(np.float32)
            layers["lidar_scarp"] = arr.mean(axis=0)
    return layers


def stage_a_independent_test(tile_px: int = TILE_PX, band: str = "geod_2ndinv",
                             exclude_radius_px: float = 2.0) -> dict:
    """Falsifiable test: does the deficit concentrate INDEPENDENT off-catalogue fault evidence?"""
    import math as _m

    from scipy.stats import spearmanr

    from .paths import WORK_DIR

    traces = load_traces()
    dips = dip_by_sense()
    geo = geologic_strain_by_tile(traces, dips, tile_px)
    geod_field = grid.read_band(band)
    cat = grid.catalogue()
    fp = grid.footprint()
    layers = _independent_layers()
    d_cat = grid.catalogue_distance()

    rows = []
    for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
        v = geod_field[rs, cs]
        v = v[np.isfinite(v)]
        if not v.size:
            continue
        g = float(v.mean())
        kk = geo.get((i, j), 0.0)
        if g <= 0:
            continue
        sel = fp[rs, cs]
        row = dict(tile_i=i, tile_j=j, geodetic_ns_yr=g, geologic_ns_yr=kk,
                   deficit=1.0 - kk / g, cat_density=float(cat[rs, cs][sel].mean()))
        if "sgmc" in layers:
            offcat = layers["sgmc"][rs, cs] & (d_cat[rs, cs] >= exclude_radius_px.px if False
                                               else d_cat[rs, cs] >= exclude_radius_px)
            row["sgmc_offcat_density"] = float(offcat[sel].mean())
        if "lidar_scarp" in layers:
            row["lidar_scarp_mean"] = float(layers["lidar_scarp"][rs, cs][sel].mean())
        rows.append(row)

    out = dict(tile_px=tile_px, band=band, n_tiles=len(rows))
    for key in ("sgmc_offcat_density", "lidar_scarp_mean"):
        xs = [r["deficit"] for r in rows if key in r and _m.isfinite(r[key])]
        ys = [r[key] for r in rows if key in r and _m.isfinite(r[key])]
        if len(xs) > 10:
            rho = float(spearmanr(xs, ys).statistic)
            # partial correlation controlling for catalogue density (rank-based residualisation)
            z = [r["cat_density"] for r in rows if key in r and _m.isfinite(r[key])]
            import numpy as _np
            rx = _np.argsort(_np.argsort(xs)).astype(float)
            ry = _np.argsort(_np.argsort(ys)).astype(float)
            rz = _np.argsort(_np.argsort(z)).astype(float)
            rx = rx - rx.mean(); ry = ry - ry.mean(); rz = rz - rz.mean()
            bx = (_np.dot(rx, rz) / _np.dot(rz, rz)) if _np.dot(rz, rz) else 0.0
            by = (_np.dot(ry, rz) / _np.dot(rz, rz)) if _np.dot(rz, rz) else 0.0
            ex, ey = rx - bx * rz, ry - by * rz
            partial = float(_np.corrcoef(ex, ey)[0, 1])
            q = float(np.quantile(xs, 0.75))
            top = [y for x, y in zip(xs, ys) if x >= q]
            rest = [y for x, y in zip(xs, ys) if x < q]
            lift = (float(np.mean(top)) / float(np.mean(rest))) if rest and np.mean(rest) else \
                float("nan")
            out[key] = dict(spearman_rho=rho, partial_rho_given_cat_density=partial,
                            top_quartile_lift=lift, n=len(xs))
    (WORK_DIR / "stage_a_independent_test.json").write_text(__import__("json").dumps(out, indent=2))
    return out


def gate_comparison(tile_px: int = TILE_PX, exclude_radius_px: float = 2.0) -> dict:
    """Compare candidate Stage A gating rules against independent off-catalogue fault evidence.

    Rules compared (each is a tile-level predicate; the approved set is the top 50% of tiles under
    the rule, matching the quantile convention used elsewhere in this module):
      strain_2ndinv        geodetic second invariant alone                       (band 4)
      strain_shear         geodetic shear rate alone                             (band 7)
      strain_dilatation    |geodetic dilatation rate| alone                      (band 8)
      deficit              residual 1 - geologic/geodetic (the brief's rule)     (band 4)
      deficit_and_strain   deficit >= median AND strain_2ndinv >= median
      strain_per_moment    strain_2ndinv divided by (1 + geologic strain)  -- strain intensity
                           where the mapped faults do NOT already explain it

    Instrument: Spearman rho between the rule's tile score and (i) SGMC fault density at
    >= 2 px from the catalogue, (ii) lidar scarp-feature intensity; plus the top-quartile lift.
    """
    from scipy.stats import spearmanr

    traces = load_traces()
    dips = dip_by_sense()
    geo = geologic_strain_by_tile(traces, dips, tile_px)
    fp = grid.footprint()
    cat = grid.catalogue()
    d_cat = grid.catalogue_distance()
    layers = _independent_layers()
    b4 = grid.read_band("geod_2ndinv")
    b7 = grid.read_band("geod_shearrate")
    b8 = grid.read_band("geod_dilaterate")

    tiles = []
    for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
        sel = fp[rs, cs]
        if sel.sum() < 100:
            continue
        def tmean(a):
            v = a[rs, cs][sel]
            v = v[np.isfinite(v)]
            return float(v.mean()) if v.size else float("nan")
        strain = tmean(b4)
        kk = geo.get((i, j), 0.0)
        if not np.isfinite(strain) or strain <= 0:
            continue
        t = dict(tile_i=i, tile_j=j, strain=strain, shear=tmean(b7),
                 dilat=abs(tmean(b8)), geologic=kk, deficit=1.0 - kk / strain,
                 strain_per_moment=strain / (1.0 + kk),
                 cat_density=float(cat[rs, cs][sel].mean()))
        if "sgmc" in layers:
            t["sgmc"] = float((layers["sgmc"][rs, cs] & (d_cat[rs, cs] >= exclude_radius_px))[sel].mean())
        if "lidar_scarp" in layers:
            t["scarp"] = float(layers["lidar_scarp"][rs, cs][sel].mean())
        tiles.append(t)

    def q(med):
        return med

    def med(key):
        return float(np.median([t[key] for t in tiles if np.isfinite(t[key])]))

    m_strain, m_deficit = med("strain"), med("deficit")
    rules = {
        "strain_2ndinv": lambda t: t["strain"],
        "strain_shear": lambda t: t["shear"],
        "strain_dilatation": lambda t: t["dilat"],
        "deficit": lambda t: t["deficit"],
        "deficit_and_strain": lambda t: ((t["strain"] >= m_strain and t["deficit"] >= m_deficit)
                                         * 1.0 * (t["strain"] + t["deficit"])),
        "strain_per_moment": lambda t: t["strain_per_moment"],
    }
    out = dict(tile_px=tile_px, n_tiles=len(tiles), median_strain=m_strain,
               median_deficit=m_deficit, rules={})
    for name, fn in rules.items():
        xs = [fn(t) for t in tiles]
        rec = {}
        for key, label in (("sgmc", "sgmc_offcat_density"), ("scarp", "lidar_scarp_mean")):
            if key not in tiles[0]:
                continue
            ys = [t[key] for t in tiles]
            rho = float(spearmanr(xs, ys).statistic)
            q75 = float(np.quantile(xs, 0.75))
            top = [y for x, y in zip(xs, ys) if x >= q75]
            rest = [y for x, y in zip(xs, ys) if x < q75]
            rec[label] = dict(spearman_rho=rho,
                              top_quartile_lift=(float(np.mean(top)) / float(np.mean(rest)))
                              if rest and np.mean(rest) else float("nan"))
        # approved-tile share and catalogue density of the approved half (context only)
        thr = float(np.median(xs))
        appr = [t for t, x in zip(tiles, xs) if x >= thr]
        rec["approved_tiles"] = len(appr)
        out["rules"][name] = rec
    return out
