# H53 candidate slate — preregistered 2026-10-08, before any validation run

**Status: FROZEN. No result-driven tuning is permitted after this file is written.**

Scope: five geological hypotheses not previously implemented in this repository,
plus one engineering calibration sweep. Every hypothesis uses only data already
restored and hash-pinned in this checkout (competition `training_features.tif`
bands, owner-mirrored lidar/radiometric/SGMC rasters, INGENIOUS slip-rate table,
GDR 1391 well/spring and vent CSVs). **No new external data is required for any
candidate in this slate**; where a candidate touches the GDR well/spring table, the
file is already restored and SHA-256-pinned (`data/restore_receipt.json`, entry
`ext_gdr_wellspring_in_footprint`, 2,146,771 bytes), so availability is verified,
not assumed.

Novelty is bounded to inspection of `src/gems51`, `scripts/`, `knowledge/`, and the
archived hypothesis records (`registry/hypotheses.json`,
`evidence/candidate_hypotheses_prereg_20261007.json`,
`evidence/hypothesis_slate_20261007.json`, `knowledge/next-candidates-20261007.md`).
It is not a claim of global novelty in the published literature.

Ranking criterion: expected DTI improvement on the frozen six-fold spatially
blocked holdout (visible-catalogue proxy), divided by implementation cost, with
mechanism specificity as the tie-breaker. Expected benefits below are qualitative
research judgments, **not predicted DTI values**.

## The frozen instrument (unchanged, so numbers stay comparable)

- Six contiguous 3×3 spatial blocks of the visible USGS+INGENIOUS catalogue;
  12 px training buffer; the block is the fold's truth, the rest of the
  catalogue is "known" and masked by the scorer; 250,000 sampled negatives per
  fold, seed `1000 + fold.index`; HGB `max_iter=250`, model seed `fold.index`.
- Emission: STE L9, continuity exponent 0.35, greedy spacing 2.4 px, catalogue
  flank 2.0 px, mass `M = 3.47 × n_truth`.
- Stage 1 reported separately: fold-specific rank-space strain-budget deficit
  over 10 km tiles with held-out trace rows removed; approved domain = tiles at
  or above the q10 percentile; all Stage-2 points confined to approved tiles;
  non-dominance limit lift ≤ 1.5 and approved area ≥ 2/3 of the footprint.
- Frozen best to beat: `0.285340602656319` (H-H/H-D 50/50 blend + STE, ungated,
  `evidence/hh_blend_holdout.json`). The frozen best is itself **not uploadable**:
  it predates the q10 all-points-inside requirement (86.71% inside) and encodes
  NaN outside the footprint, the unresolved portal range hazard (IR-51-21).

## Ranked hypotheses

| Rank / ID | Layers | Physical signature / operator | Why it may find catalogue-missing faults | Difference from implemented work | Expected DTI benefit / cost |
|---|---|---|---|---|---|
| **1 / H53-A (TOP — validated this session)** | `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate` + fault-predicted strain tensor from `strain_budget.kostrov_tiles` (Kreemer et al. 2000, Eq. 3) at 2.5 km tiles | Thin positive **off-fault strain-residual ridge**: rank-space residual q(observed tile mean) − q(fault tensor II) per geodetic band at 2.5 km tiles, upsampled, Gaussian-smoothed σ=4 px, then crest/ridge response max(0,−λ_min)·σ² at σ=1.5 and 4.0 px (existing lineament-bank Hessian). 6 features. | Blind or distributed deformation produces no surface scarp, so a scarp-built catalogue misses it, but it does produce geodetic strain the mapped faults cannot accommodate. Precedent: UCERF3 models off-fault strain explicitly (Field et al. 2014, doi:10.1785/0120130164). | Stage 1 uses the same residual at **10 km** tiles as raw rank values and only as a q10 hard gate with zero soft score weight; H53-A uses **2.5 km** tiles, a smoothed ridge response, and feeds the Stage-2 HGB as features. No implemented arm turns the strain residual into a fine-scale ridge feature. | Uncertain: the tile-level deficit measured weak (Spearman 0.039) while raw geodetic fields measured stronger (0.099–0.24), so the subtraction is a genuine test, not a formality. Medium cost (new module + one extra six-fold arm). |
| 2 / H53-B | `depth_to_base_surf` (competition band: depth to basement = cover thickness) | **Curvature hinge of the detrended basement surface**: detrend with Gaussian σ=50 px, then ridge response max(0,−λ_min)·σ² at σ=2 and 4 px of the detrended surface. | A blind range-front fault under alluvium bends the basement surface (a hinge) without leaving a scarp; the catalogue is scarp-based, so this class is systematically missed. | H-E's `base_s15/s40_edge` are **first-derivative** (|grad|) edge banks on the same layer, which peak on the basinward dip, away from the trace; H53-B uses the **second derivative** of the **detrended** surface, which peaks at the hinge (the trace). | Low-to-moderate, uncertain. Low-medium cost. |
| 3 / H53-C | `cond_surf` (competition band: subsurface conductivity) | **Along-strike persistence of the conductivity edge**: normalized-convolution edge response at σ=2 and 5 px, then along-strike line accumulation (`trace_emission.line_accumulate`, length 9, 12 orientations), rank-normalized. | A basin-bounding fault juxtaposes resistive bedrock against conductive basin fill; the contact is a long, continuous conductivity lineament that persists for kilometres even where the scarp is eroded or buried. | H-D is scarp-facing coherence on lidar/det_elev; H-H is potential-field endpoint/bridge **topology**; H-E has `cond_s*` edge banks but no along-strike **continuity** operator. H53-C measures continuity of the conductivity edge itself. | Low-to-moderate, uncertain. Low cost (reuses the lineament bank and line accumulator). |
| 4 / H53-D | `rad_K`, `rad_Th` (K/Th ratio) + independent edge banks from `tmi` / `iso_grav_anom` | **Across-strike alteration asymmetry**: mean K/Th contrast between the two sides within a ±5 px window centred on independent geophysical edges, plus along-edge elongation of the ratio anomaly. | Hydrothermal alteration along a fault zone produces a narrow, elongate K/Th (or K-depletion) anomaly that follows the fault trace, not the scarp; surface mapping misses it. | H51-K3 (preregistered, untested) proposed ratio lineaments *conditional* on structural edges; H53-D measures the **side-to-side contrast** across the edge, which a lineament detector cannot express. Radiometric bands sit in the base stack only as raw values; no ratio or asymmetry transform exists in the repo. | Low-to-moderate, speculative for fault pixels. Medium cost. |
| 5 / H53-E | GDR 1391 well/spring CSV (`ext_gdr_wellspring_in_footprint.csv`, 27,092 rows, restored + hash-pinned), volcanic-vent CSV (21 rows), independent lineament bank (`tmi`/`iso_grav_anom` edges) | **Manifestation-aligned thin corridor**: for each thermal manifestation, locate the nearest independent lineament pixel; rasterize a thin corridor (Gaussian σ=2 px) around those pixels; rank-normalize. | The hidden labels are newly identified faults in a geothermal field; faults hosting warm springs/vents are likelier to be the ones experts identify. Alignment with an **independent** geophysical lineament is more fault-specific than generic geothermal favorability. | H51-X3 (preregistered, untested) proposed point-to-lineament distance/orientation features; H53-E rasterizes a **thin corridor** around the lineaments nearest manifestations — deliberately not a broad habitat surface (the 0.0041 / 0.1223 / 0.1352 failure mode). No current feature uses well/spring temperature or chemistry. | Low for the fault-pixel metric; moderate for the long-term geothermal-vent goal. Medium cost (point joins + provenance audit). External data already restored and pinned (GDR 1391, CC-BY 4.0). |

## Engineering calibration (not a geological hypothesis): H53-F emission operating point

On the **cached fresh fold blend fields** (no retraining): ratio ∈ {2.96, 3.47}
× flank ∈ {2.0, 2.24} px, STE L9 w=0.35 spacing 2.4, q10-gated, paired against the
(3.47, 2.0) gated baseline at identical folds.

Rationale: the official metric's marginal rule (emit a unit dot iff its kernel
credit exceeds `0.2 × DTI`, i.e. ≈ 0.056 at DTI 0.28) and the owner-reported
family ladder (0.2600 at 44,090 dots → 0.2778 at 37,654 dots, the latter also
deleting the ≤200 m catalogue band) suggest the current 44,069-dot mass
(3.47 × 12,700 planning |G|) may over-emit. The blocked proxy arbitrates.

**Adoption rule (frozen):** a non-default operating point is adopted for the
submission build only if it beats the (3.47, 2.0) gated mean by ≥ +0.0020 with
≥ 4/6 folds positive. Otherwise the build keeps ratio 3.47, flank 2.0 px
(44,069 dots), exactly the validated frozen geometry.

## Frozen promotion rule for H53-A (the top candidate)

Candidate field = `0.5 × H-D + 0.5 × (H-H + H53-A features)`, fitted per fold on
the fold's training pool with the same seeds as the baseline arms. Baseline field
= `0.5 × H-D + 0.5 × H-H` (fresh, same folds).

Promotion requires **all** of:

1. the fresh ungated baseline reproduces the frozen mean `0.285340602656319`
   within `1e-5` (harness fidelity);
2. the candidate **q10-gated** mean > the frozen best `0.285340602656319`;
3. the paired q10-gated candidate-vs-baseline mean delta > 0 with ≥ 4/6 folds
   positive;
4. every candidate point lies inside the fold-specific q10 approved tiles
   (100% confinement);
5. approved area ≥ 2/3 of the footprint in every fold and Stage-1 lift ≤ 1.5
   (non-dominance).

If H53-A fails, it is recorded as NOT PROMOTED and **no H53-A TIFF is built**; the
submission artifact is then the regeneration of the promoted H-H/H-D procedure
under the brief's constraints (new seeds, q10 confinement, all-finite `[0,1]`
encoding), validated by its own paired six-fold receipt for the exact built
geometry. A failed candidate never consumes a competition slot and never
produces an upload recommendation.

## Scientific sources checked for this slate

- Official task, metric, format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (fetched 2026-10-07).
- UCERF3 deformation models, off-fault strain: Field et al. (2014), BSSA 104(3), 1122–1180, doi:10.1785/0120130164 (cited in the user brief; abstract-level knowledge, not re-fetched this session).
- Kreemer et al. (2000) Eq. 3 moment-tensor summation: https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf (fetched 2026-10-07).
- GDR submission 1391 (INGENIOUS Qfaults v2 + geothermal observations, CC-BY 4.0): https://gdr.openei.org/submissions/1391 (fetched 2026-10-07; CSVs restored and hash-pinned this session).
- USGS GeoDAWN airborne magnetic/radiometric surveys (data provenance of the radiometric bands): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (linked in the user brief).
- Ridge/vesselness operator: Frangi et al. (1998), MICCAI, doi:10.1007/BFb0056195 (already cited in `src/gems51/trace_emission.py`).

All five hypotheses are proposed physical discriminants, not literature-validated
discoveries or numerical performance claims. The six folds have been reused across
many hypotheses; a new independent lockbox is required before any strong
generalization claim.
