# Pre-registered hypothesis screen — 2026-10-07

**Frozen before implementation or scoring of any candidate below.** This is a
screening plan, not a claim that any candidate works. All local labels are a
known-fault proxy: `data/raw/labels.tif` and `existing_faults.tif` are byte-for-byte
identical, so a blocked holdout can reward rediscovery of the mapped catalog but
cannot validate truly unmapped faults (IR-51-08).

## Baseline and promotion rule

- Incumbent: H-D scarp-facing-coherence detector, six retained spatial blocks;
  held-out truth is the known-catalog raster, and predictions are scored only in
  the held-out block after excluding known catalogue pixels. The recorded mean
  proxy DTI at mass ratio `M/|G| = 3.47` is **0.2817** (`data/holdout_H_D.json` /
  `data/two_stage_results.json`; these are proxy numbers, not competition scores).
- Exact pairing: same fold definitions, training sample, detector settings,
  NMS spacing, and per-fold mass; only the candidate feature family changes.
- Promote a candidate to a submission build only if its paired mean DTI exceeds
  H-D, it is positive on at least 4 of the 6 folds, and the six-fold candidate
  mean itself exceeds 0.2817. The candidate evaluation is a **research holdout**;
  it does not authorize a DrivenData entry or imply a hidden-test score.
- The holdout implementation used here is 3 × 3 contiguous blocks, retains blocks
  with at least 500 catalogue pixels, and removes a 12-pixel (1.2 km) boundary
  band from training. Do not cite the separate four-fold/600 m protocol in
  `registry/preregistration.json` as the protocol for this experiment.

## Candidates — ranked by expected DTI, then by build cost

| Rank | ID / geological hypothesis | Layers and signature | Why it may expose an uncatalogued fault | Difference from this repo | Expected DTI / implementation cost |
|---|---|---|---|---|---|
| 1 | **H51-X1 — cross-physics edge-normal concordance.** A buried fault or lithologic contact may create coincident, similarly oriented magnetic- and gravity-field edges even where relief is weak. | Competition bands `rtp`, `tmi_hg` / `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg` / `iso_grav_anom_vg`; at 200 m and 500 m scales, compare normalized gradient strength and the absolute cosine of magnetic/gravity edge-normal angle. | Independent magnetic susceptibility and density contrasts can persist across sediment cover; requiring both edge evidence and matching orientation is more fault-specific than a broad magnetic/gravity anomaly or a topographic habitat mask. | Existing base features include the original bands and single-field lineament transforms; H-E tests basement/conductivity/gravity coincidence. No current feature combines magnetic and gravity edge *orientation agreement* at matched scale. | **Rank 1 / moderate, uncertain uplift** (no numeric forecast; labels are proxy). **Cost: medium**, internal layers only. This is the top candidate to validate first. |
| 2 | **H51-X2 — scarp-profile asymmetry, not amplitude.** A fault-generated surface step can have unequal down-facing and up-facing slopes. | 1 m DEM-derived `lid_downface_max`, `lid_upface_max`, `lid_cross_max`, `lid_step_max`, `lid_relief`; test robust polarity ratio and asymmetry relative to local relief. | A low-relief, asymmetric fault scarp can be missed by amplitude rankings; the ratio should reduce sensitivity to absolute relief and distinguish a coherent fault step from symmetric roughness. | H-D measures directional-gradient coherence/persistence over windows; the base has the component layers as raw values, but no derived paired-face asymmetry feature. | **Rank 2 / low-to-moderate, uncertain uplift. Cost: low**, internal owner-mirrored layer. |
| 3 | **H51-X3 — geothermal manifestation alignment, not habitat emission.** Hot springs/wells may reveal permeable fault corridors only when their spatial arrangement is aligned with an independently detected linear edge. | `gdr_wellspring_in_footprint.csv` fields `row`, `col`, `temp_c`, geothermometer estimates, plus the X1 magnetic/gravity edge-normal field. Use point-to-lineament orientation/coincidence; do not emit a broad thermal-favorability polygon. | A connected, structurally aligned set of high-temperature manifestations is evidence for a fluid pathway; requiring lineament geometry aims at fault location rather than generic geothermal favorability. | No current model feature uses spring/well point chemistry/temperature and its directional relation to lineaments. Prior sibling submissions containing thermal/habitat-style fields scored below the best dotted submissions; that is adverse prior evidence, not a reason to assume this constrained form helps. | **Rank 3 / low, high uncertainty. Cost: medium**, the owner-mirrored point table is present; validate provenance and duplicate observations first. |
| 4 | **H51-X4 — stress-compatible structural corridors.** Faults favorably oriented for slip/dilation under the regional stress field may remain permeable and geothermal. | USGS Siler (2022) Great Basin slip-/dilation-tendency shapefile (DOI `10.5066/P9YL58W6`), joined to mapped fault orientation and used only as a coarse stress/orientation prior on X1 lineaments. | Targets a physical fault property (stress compatibility) rather than regional geothermal habitat; a corridor parallel to an independently detected edge could indicate an unmapped continuation/splay. | The repo tests a scalar geodetic moment-budget prior, not the Siler mapped stress/tendency surfaces. | **Rank 4 / potentially moderate, not locally testable yet. Cost: high / blocked** until the official shapefile and its field definitions are downloaded, hashed, spatially matched, and passed into the same blocked holdout. The official USGS ScienceBase record lists the downloadable “Shapefile_INGENIOUS area.zip”; the current shell's network policy must still be tested before calling it obtainable here. Not promoted as viable on inspection alone. |

## Source checks and interpretation limits

- DrivenData's problem description identifies GeoDAWN features as 100 m projected
  EPSG:32611 magnetic, gravity, geodetic, elevation, conductivity, and earthquake
  layers; it describes newly mapped expert faults as the hidden test target.
- USGS describes GeoDAWN magnetic data as supporting subsurface structure/geology
  and radiometric data as supporting surface geology/soil-composition mapping.
  This supports the *mechanism* behind X1, not a performance claim.
- INGENIOUS GDR 1391 describes quaternary faults, geodetic models, springs/wells,
  paleogeothermal features, magnetics, gravity, and conductance. Its metadata warns
  that the data are “as is”; a repository mirror is not organizer-authenticated.
- Siler's official USGS record says the slip-/dilation-tendency layer was developed
  to identify faults appropriately oriented for slip or dilation under ambient
  stress, which may relate to undiscovered hydrothermal processes. That is a
  geological rationale, not evidence of incremental DTI.
- This screen cannot establish any public or private competition score. The
  hidden expert labels and the final expert-expanded set are unavailable to this
  local holdout. Leaderboard standings are not mirrored or monitored in this
  repository; see the official [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/).

## Official/reviewable sources

1. [DrivenData problem description, data, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
2. [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
3. [INGENIOUS GDR 1391, DOI 10.15121/1881483 (license and downloadable resources)](https://gdr.openei.org/submissions/1391)
4. [USGS Siler (2022) slip-/dilation-tendency shapefile, DOI 10.5066/P9YL58W6](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d)
5. [Kreemer et al. (2000), equation (3), public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf)
6. [NBMG QFaults INGENIOUS layer schema](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson) — lists `SLIPRTNUM` but does not state its units.
7. [Official GEMS Prize rules (September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Outcome — appended 2026-10-07 after the frozen screen

This section records results without changing the candidate ranking or promotion
criterion above.

- **A narrowed H51-X1 implementation was tested** as the preregistered lead.
  Although the frozen plan listed RTP, TMI horizontal/vertical derivatives, and
  gravity horizontal/vertical derivatives, the measured feature builder used
  only rank-normalized `comp_tmi` and `comp_iso_grav_anom` as its two inputs;
  the derivative products were not separately used as inputs to the new transform (they remained in the common baseline stack). At matched 200 m and
  500 m scales, six-fold mean proxy DTI is 0.2796713, versus H-D's 0.2816627
  (paired mean difference -0.0019913); it wins 3/6 folds and mean AUC is
  0.6666622. This partial test fails the frozen promotion rule and is not
  eligible for a submission build; it does not falsify every version of the
  broader preregistered layer-family hypothesis.
- **Historical Stage-1 results are not current-formula validation.** The mainline
  five-split trace holdout recorded deficit Spearman 0.03916 and top-50% lift
  1.08290, weaker than geodetic-only (0.09930; 1.23864); its runner excluded
  held-out trace rows, but it predates the explicit signed-shear and rate-
  convention audit. The separate four-scenario formula audit used a runner that
  failed to exclude held-out trace attributes from the catalogue-derived budget,
  so it is not a valid holdout. Six-fold Stage-1-only DTI (0.14810 vs 0.18615
  uniform) and the q50 hard-gate harm (Stage 2 0.18153 vs 0.28164 ungated) are
  archived measurements tied to the prior Stage-1 field. No current-formula,
  leakage-controlled Stage-1 rerun is available; see
  [`evidence/stage1_reconciliation_20261007.json`](../evidence/stage1_reconciliation_20261007.json).
- A separate historical soft-weight sweep gives `w=0.10` mean proxy DTI 0.28213
  (3/6 positive) and `w=0.20` 0.28212 (+0.000483 paired mean; 4/6 positive)
  versus ungated H-D. These runs used the archived Stage-1 field, not the current
  formula implementation. The `w=0.20` proposal failed uniqueness against the
  archived soft-`w=0.10` artifact (Jaccard 0.86130; candidate containment
  0.92548, above limits 0.50 and 0.60); the build stopped before writing it.
- **No new model prediction was generated and no competition slot was used.** A
  prior H-G+H-D output has only been re-encoded with NaN outside the footprint
  for research inspection; it loses its matched holdout and is not a submission
  recommendation. The guarded H-D `w=0.20` preflight did not write a TIFF. Old
  zero-outside files remain archived and fail the official null/NaN-outside
  requirement.

Measured results: [`data/holdout_H_X1.json`](../data/holdout_H_X1.json),
[`data/stage1_trace_holdout.json`](../data/stage1_trace_holdout.json) (historical formula),
[`evidence/stage1_reconciliation_20261007.json`](../evidence/stage1_reconciliation_20261007.json),
[`data/two_stage_results.json`](../data/two_stage_results.json) (historical prior field), and
[`data/gate_sweep.json`](../data/gate_sweep.json) (historical prior field). Official format and AI
narrative requirements are at the [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
and in §3.2 of the [GEMS Prize rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
