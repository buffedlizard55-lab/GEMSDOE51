"""H53-A: fine-scale geodetic strain-residual ridge features.

Preregistered in ``evidence/candidate_hypotheses_prereg_h53sr_20261008.json`` and
``registry/preregistration_h53sr_20261008.json`` BEFORE any validation run.

Physical hypothesis (the user brief's central Stage-1 hypothesis, taken to
fine scale): where the geodetic strain rate exceeds what the mapped faults'
slip rates can accommodate, the catalogue is likelier to be missing structures.
Stage 1 keeps that residual only as a coarse prior over 10 km tiles with zero
soft score weight; H53-A turns the same residual into fine-scale ridge
features (2.5 km tiles, smoothed, crest response) inside the Stage-2 detector.

Conventions inherited from the Stage-1 audit (``registry/irregularities.json``
IR-51-12 and ``knowledge/gemsdoe32-case-study-2026-10-07.md`` section 3): the
residual is computed in RANK space, because the competition geodetic layers'
units and invariant conventions are not organizer-authenticated, and an
absolute dilatation/shear subtraction from a fault tensor invariant is not
claimed.  The fault tensor uses the Kreemer et al. (2000) Eq. (3)
moment-tensor summation implemented in ``gems51.strain_budget``:

    eps_ij = 1/2 * sum_k [ L_k * u_dot_k / (A * sin(delta_k)) ] * m_ij^k,
    m_ij^k = n_i^k * s_j^k + n_j^k * s_i^k

Leakage control: the caller must pass the FOLD-VISIBLE catalogue (``fold.known``)
and a slip-rate table with the held-out trace rows already removed, exactly as
``scripts/evaluate_hk1_holdout._stage1_q10_approved`` does.  The observed
geodetic bands are competition inputs available everywhere and carry no
holdout-truth information.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import strain_budget as sb
from .grid import GRID
from .stack import lineament_bank

H, W = GRID.shape

# Fine tile edge in pixels: 25 px = 2.5 km (Stage 1 uses 100 px = 10 km).
FINE_TILE_PX = 25
# Gaussian smoothing applied to the upsampled residual before ridge detection,
# so the crest operator sees a continuous field rather than 25-px blocks.
SMOOTH_SIGMA_PX = 4.0
# Ridge-response scales (px), matching the repo's lineament-bank scales.
RIDGE_SCALES = (1.5, 4.0)

BANDS = ("geod_2ndinv", "geod_shearrate", "geod_dilaterate")


def upsample_tiles(tiles: np.ndarray, tile_px: int) -> np.ndarray:
    """Nearest upsample of a tile map onto the full pixel grid (as Stage 1)."""
    big = np.repeat(np.repeat(tiles, tile_px, axis=0), tile_px, axis=1)
    return big[:H, :W]


def residual_tile_maps(catalogue_known: np.ndarray, footprint: np.ndarray,
                       df, observations: dict, tile_px: int = FINE_TILE_PX,
                       cfg: sb.BudgetConfig | None = None) -> dict:
    """Rank-space residual q(observed tile mean) - q(fault tensor II), per band.

    Returns a dict with one tile map per geodetic band plus the shared support
    mask.  Tiles with < 5% footprint support are excluded from the ranking, as
    in the Stage-1 implementation.
    """
    if cfg is None:
        cfg = sb.BudgetConfig(tile_px=tile_px, rate_convention="vertical",
                              assume_unknown_normal=True)
    exx, eyy, exy, *_ = sb.kostrov_tiles(catalogue_known, df, cfg,
                                         area_mask=footprint)
    fault_ii = sb.invariant(exx, eyy, exy, "II")
    support = sb.observed_tiles(np.ones(footprint.shape, dtype=np.float32),
                                footprint, tile_px)
    valid_tiles = np.isfinite(support) & (support > 0.05)
    q_fault = sb.quantile_map(np.where(valid_tiles, fault_ii, np.nan))
    out = {}
    for name in BANDS:
        if name not in observations:
            raise KeyError(f"observed geodetic band {name!r} missing")
        obs_t = sb.observed_tiles(observations[name], footprint, tile_px)
        q_obs = sb.quantile_map(np.where(valid_tiles, obs_t, np.nan))
        out[name] = q_obs - q_fault
    out["valid_tiles"] = valid_tiles
    out["fault_ii"] = fault_ii
    return out


def h53a_features(catalogue_known: np.ndarray, footprint: np.ndarray,
                  df, observations: dict, tile_px: int = FINE_TILE_PX,
                  smooth_sigma: float = SMOOTH_SIGMA_PX,
                  scales: tuple = RIDGE_SCALES) -> dict[str, np.ndarray]:
    """Build the six H53-A crest features on the full pixel grid.

    For each geodetic band: upsample the rank residual to 100 m, Gaussian
    smooth, then take the crest (ridge) response of the existing lineament
    bank at each scale.  Returns ``{h53a_<band>_s<scale>_crest: (H, W) f32}``
    with NaN outside the footprint.
    """
    resid = residual_tile_maps(catalogue_known, footprint, df, observations,
                               tile_px=tile_px)
    g = {}
    for name in BANDS:
        big = upsample_tiles(resid[name], tile_px)
        finite = footprint & np.isfinite(big)
        smooth = ndi.gaussian_filter(
            np.where(finite, big, 0.0).astype(np.float32),
            smooth_sigma, mode="nearest")
        smooth[~finite] = np.nan
        smooth = smooth.astype(np.float32)
        for sigma in scales:
            _edge, crest, _lin = lineament_bank(smooth, finite, sigma)
            crest = np.asarray(crest, dtype=np.float32)
            crest[~finite] = np.nan
            g[f"h53a_{name}_s{int(sigma * 10):02d}_crest"] = crest
        del big, smooth
    return g


def feature_names(scales: tuple = RIDGE_SCALES) -> list[str]:
    return [f"h53a_{name}_s{int(s * 10):02d}_crest"
            for name in BANDS for s in scales]
