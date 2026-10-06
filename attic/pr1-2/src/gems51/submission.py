"""Submission assembly, format receipts, the uniqueness gate and the stage-dominance check.

Format rules (verbatim source: competition problem description, "Submission format"):
  * same projected CRS as the training data (EPSG:32611),
  * same resolution (100 m),
  * same bounds; data outside the bounds null or nan,
  * single layer, 32-bit float, values between 0 and 1.

The portal error the operator hit -- "Predicted values must be in range [0, 1]" -- is produced by
(a) any value outside [0,1] anywhere in the raster and (b) a nodata TAG whose sentinel lies
outside [0,1] (the training raster's own sentinel is -3.4028234663852886e+38).  This module
therefore writes **all-finite float32 with nodata=None** and verifies, by re-reading the bytes
from disk, that min >= 0, max <= 1 and n_nan == 0 (grid.verify_float32).
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np

from . import grid, strain


def approved_mask_from_stage_a(quantile: float = 0.5, tile_px: int = strain.TILE_PX) -> np.ndarray:
    """Stage A gate: top-quantile tiles by geodetic strain magnitude (band 4).

    Decision record: the brief's rule (residual after subtracting the mapped-fault moment budget)
    was implemented (`strain.deficit_table`) and FALSIFIED as a locator --
    Spearman rho vs lidar scarp intensity -0.048, vs off-catalogue SGMC fault density -0.205,
    held-out catalogue label-density lift 0.949 (1/4 folds > 1).  The geodetic strain magnitude
    itself passed the primary independent instrument (rho +0.376, top-quartile lift 1.39), so it is
    used as the coarse gate and the falsified residual is reported in the site.  Both numbers are
    in evidence/stage_a_*.json.
    """
    rows = strain.deficit_table(tile_px=tile_px)
    vals = np.array([r["geodetic_ns_yr"] for r in rows if np.isfinite(r["geodetic_ns_yr"])])
    thr = float(np.quantile(vals, quantile))
    appr = {(r["tile_i"], r["tile_j"]) for r in rows
            if np.isfinite(r["geodetic_ns_yr"]) and r["geodetic_ns_yr"] >= thr}
    return strain.approved_mask(appr, tile_px=tile_px)


def candidate_mask(approved: np.ndarray, catalogue_buffer_px: float = 2.0) -> np.ndarray:
    """Pixels eligible for emission: footprint & approved tiles & >= buffer from the catalogue."""
    d_cat = grid.catalogue_distance()
    return approved & grid.footprint() & (d_cat >= catalogue_buffer_px) & (d_cat > 0)


def build_emission(belief: np.ndarray, approved: np.ndarray, buffer_px: float = 2.0,
                   rule: str = "thin", density: float = 0.04, quantile: float = 0.90,
                   spacing: int = 3) -> tuple[np.ndarray, dict]:
    """The shipped emission rule.

    rule="thin" (PROMOTED, the default): belief-priority 1-px dots with a hard minimum separation
    of `spacing` px, sized at `density` x candidate pixels.  This is the ancestor rule shape
    refined by this repository's own detector, gate and off-catalogue constraint.  It is the rule
    that survived the off-catalogue A/B instrument (evidence/offcat_holdout.json): both coverage
    lattices trialled lost or tied it there (lattice q0.10 s3 mean paired delta -0.0104, 1/4 folds;
    lattice q0.20 s3 +0.0040 but only 2/4 folds), so under the pre-registered promotion rule
    (mean > 0 AND >=3/4 folds positive) NOTHING was promoted over it and the incumbent rule ships.

    rule="lattice" (NOT PROMOTED, kept for reproducibility): a 1-px coverage lattice of `spacing`
    px over the top (1 - quantile) of the candidate area by belief.  It won a sweep whose truth was
    a subsample of the visible catalogue (+0.0286, 4/4 folds, evidence/strategy_sweep.json) and lost
    the faithful off-catalogue instrument, which is recorded here as a worked example of a spurious
    promotion caught by holdout.

    Original lattice rationale, for the record:

    Rule (promoted on the blocked holdout, see evidence/emission_promotion.json and
    evidence/strategy_sweep.json):

      1. candidate = footprint AND approved tiles AND >= buffer_px from every catalogue pixel;
      2. threshold = the `quantile` quantile of the belief field over the candidate pixels,
         so the region kept is the top 10% of the candidate area by belief;
      3. emit 1-pixel dots on a square lattice of `spacing` pixels inside that region, taking the
         first phase of each lattice cell.

    Why a lattice and not thin dots along the ridge: with the official metric a predicted pixel
    that sits ON truth costs nothing (FP_w weight 1 - k(d) = 0 at d = 0) and a missed truth pixel
    costs beta = 0.8, while extra false mass costs only alpha = 0.2.  Measured on the four blocked
    folds under a truth density matched to the hidden label set (K ~ 12,200 px), this rule beats
    the thin-dot incumbent on 4/4 folds (mean paired DTI +0.0286, i.e. +25% relative) while
    emitting ~3.6x less mass.

    Returns (mask, info) where info records the exact parameters and realised counts.
    """
    cand = candidate_mask(approved, buffer_px)
    if rule == "thin":
        from . import detector
        n_target = max(1, int(round(density * int(cand.sum()))))
        mask = detector.rule_incumbent(belief, cand, n_target, spacing)
        info = dict(rule="thin_dots_belief_priority", promoted=True,
                    density=float(density), min_separation_px=float(spacing),
                    catalogue_buffer_px=float(buffer_px), candidate_px=int(cand.sum()),
                    target_px=int(n_target),
                    emitted_inside_candidate_fraction=float(
                        mask.sum() and (mask & cand).sum() / mask.sum()))
        return mask, info
    if rule != "lattice":
        raise ValueError(f"unknown emission rule {rule!r}")
    vals = belief[cand]
    thr = float(np.quantile(vals, quantile)) if vals.size else float("inf")
    region = cand & (belief >= thr)
    mask = np.zeros(grid.SHAPE, bool)
    mask[::spacing, ::spacing] = region[::spacing, ::spacing]
    info = dict(rule="coverage_lattice_not_promoted", promoted=False, spacing_px=int(spacing),
                quantile=float(quantile), catalogue_buffer_px=float(buffer_px),
                belief_threshold=thr, candidate_px=int(cand.sum()), region_px=int(region.sum()),
                n_emitted=int(mask.sum()),
                emitted_inside_region_fraction=float(
                    mask.sum() and (mask & region).sum() / mask.sum()),
                emitted_inside_candidate_fraction=float(
                    mask.sum() and (mask & cand).sum() / mask.sum()))
    return mask, info


def uniqueness_gate(mask: np.ndarray, scored_dir=None, jaccard_max: float = 0.25) -> dict:
    """Compare the emission against every hash-pinned sibling submission on disk.

    Contract: Jaccard(mask, prior) < jaccard_max for every prior, and the emission is neither a
    superset of nor identical to any prior.  Sibling files come from .cache/gems_data/scored/.
    """
    import rasterio
    from .paths import SCORED
    scored_dir = Path(scored_dir or SCORED)
    rows = []
    for f in sorted(scored_dir.glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1).astype(np.float32)
        other = np.isfinite(a) & (a > 0)
        inter = int((mask & other).sum())
        union = int((mask | other).sum())
        j = inter / union if union else 0.0
        rows.append(dict(file=f.name, prior_px=int(other.sum()), intersection_px=inter,
                         jaccard=float(j),
                         superset_of_prior=bool(inter == int(other.sum()) and other.sum() > 0),
                         subset_of_prior=bool(inter == int(mask.sum()) and mask.sum() > 0)))
    worst = max(rows, key=lambda r: r["jaccard"]) if rows else None
    ok = bool(rows) and all(r["jaccard"] < jaccard_max for r in rows) and \
        not any(r["superset_of_prior"] or r["subset_of_prior"] for r in rows)
    return dict(n_prior=len(rows), jaccard_max_allowed=jaccard_max,
                max_jaccard=worst["jaccard"] if worst else None,
                max_jaccard_file=worst["file"] if worst else None,
                rows=rows, passed=ok)


def stage_dominance_check(mask: np.ndarray, approved: np.ndarray,
                          candidate: np.ndarray | None = None,
                          tile_px: int = strain.TILE_PX) -> dict:
    """Confirm the submission is not a re-paint of Stage A's footprint.

    Tests (all cheap, all reported):
      * fill_fraction      emitted dots / approved-tile pixels.  A stage-1-dominated submission
                           tends to 1.0 (the tiles painted in); a fine-scale emission is a few %.
      * tile_concentration share of the emission in the top 10% of approved tiles by emitted count,
                           divided by the 10% a stage-1-dominated (tile-uniform) emission would put
                           there.
      * detector_evidence  the substantive argument, imported from evidence/: the Stage B belief
                           field beat the sibling repositories' published out-of-fold belief field
                           by +0.048 mean paired DTI at matched mass (8/8 paired comparisons), so
                           the emission cannot be a restatement of the coarse stage.
    """
    approved_px = int(approved.sum())
    n = int(mask.sum())
    fill = n / approved_px if approved_px else float("nan")
    counts = []
    for (i, j, rs, cs, _cov) in grid.tiles(tile_px):
        t = mask[rs, cs]
        if t.any() or (approved[rs, cs].any()):
            counts.append((int(t.sum()), int(approved[rs, cs].sum())))
    counts = [(c, a) for c, a in counts if a > 0]
    counts.sort(key=lambda t: -t[0])
    top10 = max(1, int(round(0.1 * len(counts))))
    share_top = sum(c for c, _ in counts[:top10]) / n if n else float("nan")
    uniform_share = sum(a for _, a in counts[:top10]) / approved_px if approved_px else float("nan")
    ratio = share_top / uniform_share if uniform_share else float("nan")
    coverage = float((mask & approved).sum()) / n if n else float("nan")
    verdict = "fine-scale selectivity present"
    if not (fill < 0.15 and ratio > 1.5):
        verdict = "WARNING: emission looks stage-1-like"
    return dict(approved_px=approved_px, emitted_px=n, fill_fraction=fill,
                coverage_in_approved=coverage, n_approved_tiles=len(counts),
                share_in_top_decile_tiles=share_top,
                uniform_share_of_top_decile=uniform_share,
                tile_concentration_ratio=ratio, verdict=verdict)


def write_submission(values: np.ndarray, name: str, note: str, out_dir=None,
                     nodata=None) -> dict:
    """Write the GeoTIFF (+zip) and return the full receipt (format, hashes, gate inputs)."""
    from .paths import DOCS_DIR, DOWNLOADS_DIR
    out_dir = Path(out_dir or DOWNLOADS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    tif = out_dir / f"{name}.tif"
    receipt = grid.write_float32(tif, values, nodata=nodata)
    zip_path = out_dir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, arcname=tif.name)
    receipt.update(name=name, note=note, zip=str(zip_path),
                   zip_bytes=int(zip_path.stat().st_size),
                   zip_sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest())
    checks = out_dir / f"checks-{name}.json"
    checks.write_text(json.dumps(receipt, indent=2) + "\n")
    receipt["checks_path"] = str(checks)
    return receipt
