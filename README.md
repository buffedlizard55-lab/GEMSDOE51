# GEMSDOE51 — DOE GEMS fault-discovery research

**Current decision (2026-10-08): NO artifact is cleared for a competition slot. No slot has been used; no organizer score or portal acceptance is claimed.** The fresh K2 candidate failed both the paired spatial promotion rule and the strict family uniqueness gate. Local format checks do not override either failure.

The previous H-H/H-D blend remains the best *measured local visible-catalogue proxy* (frozen mean DTI 0.2853406), but it predates the all-points-inside-Stage-1-q10 requirement (86.71% inside) and its NaN-outside encoding has not been portal-validated. Do not upload it. The fresh reconstruction was 0.2853152, 0.00002545 below the frozen value and outside the 1e-5 reproduction tolerance; this discrepancy is retained as a harness irregularity.

**Latest H53-family experiment: finite-lag H53-A.** Its Stage-1 audit is complete; Stage 2 was blocked before candidate scoring by the baseline-reproduction gate, so this operationalization has no score or TIFF. The componentwise budget-q10 H53-A TIFF is a separate research-only variant with its own failed Stage-2 and uniqueness results; H53-K2x is another distinct, earlier H53-family screen. None is the later overall K2-08 experiment below, and K2-08 must not be attributed to any H53 result.

## Latest overall experiment — K2-08: download for research only; do not submit

A new feature-based K2 experiment was trained from the prepared data, not copied or re-encoded from an older TIFF. Its unique byte hash and no exact byte match establish a distinct artifact, **not global/support uniqueness**. The pinned 54-repository family audit is `NOT_CLEARED` (containment 1.0; one invalid-grid reference), and the blocked holdout failed promotion. No competition slot was used.

- **[Download the research-only GeoTIFF](docs/downloads/gemsdoe51-k2-08-research-only-20261008.tif)**
- Candidate: `GEMSDOE51-K2-08-conductive-ribbon`; **44,069** unit-valued points; SHA-256 `3543d0c430ca1ef145204b81ef44fa736794f1240d63745f9f31f1d0e1edee0e`.
- Local format: one-band float32, EPSG:32611, 3730×3292, 100 m template transform; finite `[0,1]` values inside the footprint; NaN/NoData outside. Serialized-byte range and q10-confinement guards pass. **Portal validation was not performed**; the prior “Predicted values must be in range [0, 1]” error's triggering file is unknown.
- Spatial holdout: frozen best **0.2853406**; fresh H-H/H-D gated mean **0.2755433**; K2 gated mean **0.2748879**; paired Δ **−0.0006554**, **2/6** folds positive. Ungated K2 mean 0.2845355 also misses the frozen best. `NOT_PROMOTED_NO_SUBMISSION`.
- Stage 1: physical tensor summation and dilation/shear subtraction were tested only as a broad 20 km q10 tile prior. Whole-trace holdout approved 90.33% of area, recalled 91.00% of held traces (lift 1.007), and had uniform DTI 0.063356 in approved area vs 0.063645 over support (Δ −0.000289). All emitted points are inside q10, but the mask is weak/broad and did not dominate Stage 2.
- Family uniqueness: 365/365 pinned payloads fetched; no exact byte duplicate; max support Jaccard 0.15347; max containment 1.0; one format-test raster has a different grid; **`NOT_CLEARED`**.
- [Full K2 results](docs/downloads/k2-08-results-2026-10-08.md) · [three-pass review](knowledge/k2-08-review-three-passes-2026-10-08.md) · [hypothesis slate](knowledge/k2-08-candidate-hypotheses-2026-10-08.md) · [artifact receipt](docs/downloads/k2_research_artifact_20261008.json) · [Stage-1 receipt](docs/downloads/physical_stage1_holdout_20261008.json) · [Stage-2 holdout](docs/downloads/k2_spatial_holdout_20261008.json) · [uniqueness audit](docs/downloads/k2_family_uniqueness_20261008.json).

**Download only to inspect or reproduce this research artifact. Do not paste its name into the competition portal.** Older TIFFs remain preserved as prior art; no prior file was replaced or reissued.

## Historical experiments and source context

## Latest H53-family experiment — H53-A baseline gate (2026-10-08; K2-08 is a later separate experiment)

- **Identifier:** `GEMSDOE51-H53-A-20261008` (research/preregistration identifier only; not a portal submission name). **Submission filename and short portal note:** not issued for the finite-lag H53-A operationalization because it produced no TIFF and its baseline gate blocked Stage 2.
- **Hypothesis:** a bounded 1–8 pixel non-zero lag between detrended-elevation and isostatic-gravity edges, with a zero-lag control, at σ=2 and 5 px. The ranked 3-candidate slate and frozen rules are in [`knowledge/hypothesis-slate-20261008.md`](knowledge/hypothesis-slate-20261008.md) and [`registry/preregistration_h53.json`](registry/preregistration_h53.json).
- **Stage 1, separately measured:** five fixed whole-record splits; nominal q10 approved area `90.19%`, held-out visible-catalogue trace-pixel recall `92.91%`, recall/area lift `1.0301`. Matched-mass uniform-dot DTI was `0.048390` inside approved tiles vs `0.049025` over the full footprint; these are noisy local proxy draws, not an organizer metric or evidence that the residual is a fault.
- **Baseline provenance gate:** frozen H-H/H-D receipt mean `0.285340603`; fresh canonical 1000+fold reconstruction `0.285315155`; delta `−0.000025448` vs allowed `±0.000010000`. Folds 1–5 reproduce their cached receipt metrics; fold 0 differs by `−0.000152687`. The legacy field arrays and their generating metadata are missing. `run_h52_holdout.py`'s 2000+fold cache family was not substituted. No cause is assigned to the fold-0 mismatch.
- **Stage 2:** finite-lag H53-A `NOT RUN — BLOCKED`; the preregistered fail-closed baseline gate did not pass. There is no candidate score, TIFF, uniqueness result, or format result for that operationalization.
- **Decision:** finite-lag H53-A download for research: **NO TIFF exists**; the separate budget-q10 H53-A and earlier H53-K2x TIFFs: **research only**; submit any of them: **NO**. No competition slot was used. Do not attribute a H53 score to GEMSDOE32's owner-reported `0.2778` or the user-supplied `0.3195`; a one-time official leaderboard check on 2026-10-08 found `0.3195` was not the page high.
- Receipts: [`evidence/h53a_stage1_holdout_20261008.json`](evidence/h53a_stage1_holdout_20261008.json), [`evidence/h53a_baseline_provenance_20261008.json`](evidence/h53a_baseline_provenance_20261008.json). Next: preserve the failed reproduction gate; recover a documented baseline field lineage or preregister a new baseline before scoring a future candidate. Do not weaken the frozen rule post hoc.

### Separate componentwise budget-q10 H53-A variant — RESEARCH ONLY / DO NOT SUBMIT

This is a **different operationalization** from finite-lag H53-A above and from the earlier H53-K2x screen below. It has its own artifact and measured receipts; it does not create a score or TIFF for finite-lag H53-A. K2-08 remains the latest overall experiment.

- **[Research-only GeoTIFF](docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.tif)** · [one-TIFF ZIP](docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.zip) · SHA-256 `2f6e74e4d48ad47d07671cee4e73f08d012178e337a9045a9b57e51012b3613a`.
- **Stage 1, separate coarse holdout:** q10 area `91.6386%`, held-out trace recall `91.6491%`, lift `0.999618`, tile Spearman `0.060803`; geodetic-only control lift `0.996075`. This shows no meaningful residual enrichment; the full-map approved area is `90.1118%`.
- **Stage 2, separate six-fold holdout:** q10-constrained mean `0.2665098` vs frozen local best `0.2853406` (Δ `−0.0188308`; `0/6` paired folds positive). Fresh baseline `0.2853152` drifted `−0.000025448`, outside the unchanged `1e-5` tolerance. Same-domain uniform mean `0.2150664` does not pass the frozen-best rule.
- **Uniqueness / format:** local 21-reference check passed, but the pinned 54-repository family gate failed support containment (`1.000` > `0.60`; max Jaccard `0.184778`; no exact byte duplicate). Local format checks pass; portal validation was not performed. **No slot is authorized.**
- Separate slate and preregistration: [budget-q10 four-hypothesis slate](knowledge/candidate-hypotheses-budget-q10-2026-10-08.md) · [machine-readable preregistration](evidence/candidate_hypotheses_budget_q10_prereg_20261008.json). Detailed [PR #20 H53/R1 review](knowledge/pr20-h53-r1-review-three-passes-2026-10-08.md).
- Receipts: [`evidence/h53_stage1_holdout_20261008.json`](evidence/h53_stage1_holdout_20261008.json), [`evidence/h53_stage2_holdout_20261008.json`](evidence/h53_stage2_holdout_20261008.json), [`evidence/h53_public_uniqueness_20261008.json`](evidence/h53_public_uniqueness_20261008.json), [`evidence/h53_artifact_20261008T030347Z.json`](evidence/h53_artifact_20261008T030347Z.json).

**Research inspection only. Do not upload or paste its research label into the competition portal.**

### Earlier H53-K2x completed screen — research download YES; submit NO

H53-K2x is a separate, earlier four-hypothesis slate and six-fold screen, not H53-A or the later overall K2-08 experiment. It was tested once and was **NOT PROMOTED**; its freshly generated TIFF is a research-only diagnostic, not a submission candidate.

- **[Download the H53-K2x research TIFF](docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif)** · [one-TIFF ZIP](docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.zip) · [final-byte checks](docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros-checks.json)
- Research label, not a portal name: `GEMSDOE51-H53-K2X-Q10-20261008-B9C0ADEE61EA`. Comment: `RESEARCH ONLY / NOT FOR SUBMISSION: H53-K2x rank-space conductive anisotropy + H-D/H-H blend; q10 official-vector tile gate; STE L9, 44,069 points. Holdout failed; do not upload.`
- Stage 2: q10-gated mean `0.2850361457` vs same-fold gated H-D/H-H `0.2848986571` (paired Δ `+0.0001374886`, 4/6 folds), but `0.0003044570` below frozen best `0.2853406027`. Fresh baseline drifted `−0.0000254478`, outside the unchanged `1e-5` tolerance. **NOT PROMOTED; no slot.** Receipt: [`evidence/h53_k2x_holdout_20261008.json`](evidence/h53_k2x_holdout_20261008.json).
- Stage 1, separate from Stage 2: five whole-trace splits approved mean area `90.15%`, held-out trace recall `96.01%`, lift `1.0650`. In Stage 2, fold-specific q10 masks excluded held-out trace rows; all scored points were confined and Stage-1 score weight was zero.
- Local checks: one-band float32, EPSG:32611, 3730×3292, exact template transform, 44,069 binary points, all finite in `[0,1]`, zeros outside, no NoData tag. These are local checks, not portal validation; outside-footprint portal semantics remain unresolved.
- Current-inventory uniqueness passes (8 comparisons; max support Jaccard `0.216804`, containment `0.356350`). Broader family uniqueness is **NOT CLEARED** (365/365 payloads fetched; no exact same-grid duplicate; max Jaccard `0.149561`, max containment `1.0`, one different-grid toy artifact incomparable). Do not claim global novelty.
- Four-candidate slate/input audit: [`knowledge/candidate-hypotheses-2026-10-08.md`](knowledge/candidate-hypotheses-2026-10-08.md), [`evidence/h53_k2x_input_audit_20261008.json`](evidence/h53_k2x_input_audit_20261008.json). The integrated [three-pass H53 review](knowledge/review-three-passes-20261008.md) keeps K2x distinct from H53-A.

**Download: YES for H53-K2x research only. Submit: NO.** Do not upload this TIFF or use it as an H53-A or K2-08 substitute.

Two additional earlier all-finite, `[0,1]` GeoTIFFs remain downloadable **for research/audit only — DO NOT SUBMIT**:

- **H51-N2 physical / credit-thin:** [`gemsdoe51-h51n2-creditthin-20261007T210820Z.tif`](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z.tif) · [single-TIFF ZIP](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z.zip) · [checks](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z-checks.json). It passes local format, uniqueness, and Stage-1 q10 confinement checks, but **failed its preregistered six-fold paired holdout**: 0.280116 vs 0.281663 for the H-D comparator (Δ −0.001547; 0/6 folds won). No submission slot.
- **H52 V4 strain-confined:** [`gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278.tif`](docs/downloads/gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278.tif) · [single-TIFF ZIP](docs/downloads/gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278.zip) · [checks](docs/downloads/gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278-checks.json). It passes local format and the current-inventory uniqueness audit (worst Jaccard 0.2049, containment 0.3401 over 16 comparisons, including the H51-N2 and P1 TIFFs) and places all points inside q10-approved tiles. **Its actual V4 NMS raster has no direct six-fold holdout receipt.** The available 0.280821 figure belongs to V7 STE q10, a different geometry, and must not be attributed to this file. The parent +0.0020 rule was not met. No submission slot.

**Action: download only to inspect or reproduce these research artifacts. Do not paste either name into the competition portal.** The site’s executive summary and submission guide are generated from `data/submission_manifest.json` and intentionally show “no upload-eligible artifact.”

## Historical session log — R1 regeneration and new hypothesis slate (pre-K2-08)

**Goal of this session (from the standing 2026-10-08 prompt, appendix below):** generate a
*unique* GeoTIFF artifact with an obvious submit / do-not-submit status, continuing the previous
session's declared next step — regenerating the promoted H-H/H-D blend procedure with
upload-legal geometry — and rank new geological hypotheses.

**What R1 is (no new geology; geometry-encoding only).** The promoted procedure (six-fold proxy
DTI 0.285340602656319) was not upload-legal as archived: only 86.71 % of its dots lay inside
Stage-1 q10 approved tiles and its NaN-outside encoding was never portal-validated. R1 keeps the
identical two-stage design — Stage 1: Kreemer et al. (2000) Eq. (3) Kostrov strain-budget deficit
over 10 km tiles (rank-space residual against the geodetic second invariant; q10 ⇒ ~90 % of the
footprint approved; weight 0.0, domain only), Stage 2: H-D + H-H 50/50 blend, STE L9 / w0.35 /
spacing 2.4 emission, mass 44,069 dots — and adds: (a) 100 % confinement of emitted points inside
approved tiles via a preregistered `restrict` or `relocate` operator selected by the holdout; and
(b) all-finite `[0,1]` encoding with zeros outside the footprint and no NoData tag (direct fix for
the reported portal "Predicted values must be in range [0, 1]" hazard).

**Preregistered rule (frozen before any run, `knowledge/preregistration-2026-10-08.md`):**
PROMOTE iff (1) the unconstrained `base` variant reproduces the archived frozen-best per fold
within 1e-5 — amended before folds 2–5 ran (§6 Amendment A1: the anchor is the 2026-10-07 P1
receipt's `baseline_ungated`, because the archived frozen-best fold fields were never committed;
the archived values are reported for continuity only); (2) mean(best confined) − mean(base) ≥ 0;
(3) best confined wins ≥ 4/6 folds; (4) 100 % of dots inside approved tiles. Failure ⇒ artifact
is RESEARCH ONLY / DO NOT SUBMIT.
The manifest key `ok_to_download_and_submit` and the site's first line are generated from that
verdict — there is no manual override.

**Stage-1 / Stage-2 holdouts are reported separately.** Stage 1 (coarse prior):
`data/stage1_trace_holdout.json` (deficit Spearman 0.039; top-20 % lift 1.196) and
`data/two_stage_results.json` (Stage-1-only DTI 0.1481 < uniform 0.1861 — Stage 1 is weak by
design and never places points). Stage 2: `evidence/r1_holdout_20261008.json` (six-fold paired).

**New hypothesis slate (ranked; full table in the preregistration and `registry/hypotheses.json`):**
1. H51-X2 paired scarp-face asymmetry (carried, untested); 2. **H53-X5 radiometric K/Th × magnetic
lineament, off-catalogue** (new; screened this session by `scripts/screen_x5.py`,
receipt `evidence/x5_screen_20261008.json`); 3. H51-X3 warm-spring alignment (needs mirror audit);
4. H53-X6 along-strike displacement taper (new, high cost); 5. H53-X4 stress corridors —
**NOT VIABLE from this sandbox**: needs the USGS Siler release DOI 10.5066/P9YL58W6 from
sciencebase.gov, outside the egress allowlist and not mirrored.

**Answer to the standing question about GEMSDOE32 / 0.2778 / 0.3195.** The `0.2778` attached to
`h33-h33-2-b2` is a user-reported number; the GEMSDOE32 owner pages label that artifact UNSCORED
with a projected 0.2747 and describe a 200 m catalogue-prune plus dotted emission — a design case,
not a verified score. The plausible mechanism is metric-driven (DTI rewards sparse, well-placed
mass; known faults are masked, so mass near the catalogue pays false-positive cost without guaranteed
credit). A one-time official leaderboard check on 2026-10-08 found the user-reported `0.3195`
was not the page high; treat it as stale, not current. No standings snapshot is stored and no
automatic monitoring is used. The best *measured local* configuration remains the blend at
0.2853406 on the visible-catalogue proxy; the historical R1 test asked whether upload-legal
geometry could match it and failed its paired rule.

**Result (final, 2026-10-08).** R1 is **NOT_PROMOTED** under the frozen rule: on the paired
six-fold proxy the `restrict` confinement operator costs −0.0014061 mean DTI (0/6 folds won;
`relocate` −0.0015905), so the session GeoTIFF is marked **RESEARCH ONLY / DO NOT SUBMIT**
(`ok_to_download_and_submit=false` in `data/submission_manifest.json`, red card on the front
page). The instrument check passed with deviation 0.0 on all six folds against the 2026-10-07 P1
baseline (Amendment A1 anchor; the archived 0.2853406 fields were never committed — IR-R1-01).
Confinement is free on four folds; the cost concentrates on folds 1–2 where 0.5–0.8 % of dots sit
inside disapproved 10 km tiles (IR-R1-02). The uniform-tiles dominance control passes decisively
(0.2839091 vs 0.1880090), so Stage 1 does not dominate placement. The all-finite zeros-outside
encoding is implemented and gate-verified. New hypothesis H53-X5 (radiometric K/Th × magnetic
lineament) was **REJECTED** by its preregistered screen (fusion S=0.0114 vs random control
0.0281). Full numbers and next-session priorities:
[`knowledge/h53-session-results-2026-10-08.md`](knowledge/h53-session-results-2026-10-08.md).

- Historical R1 research-only TIFF: [download](docs/downloads/gemsdoe51-r1-restrict-20261008T031052Z-research-only.tif) · [single-file ZIP](docs/downloads/gemsdoe51-r1-restrict-20261008T031052Z-research-only.zip) · [final-byte checks](docs/downloads/gemsdoe51-r1-restrict-20261008T031052Z-research-only-checks.json) · [paired holdout](docs/downloads/r1_holdout_20261008.json). SHA-256 `2a0707537962757e9aa8f856fd6d3fdfdc8d0e387b0eef6639eacf18fe2ba7b2`; it failed the paired rule (−0.0014061; 0/6 folds) and is retained as prior art, not an upload candidate.
- Historical finite-lag H53-A audit (no finite-lag candidate TIFF): [Stage-1 receipt](docs/downloads/h53a_stage1_holdout_20261008.json) · [baseline-provenance gate](docs/downloads/h53a_baseline_provenance_20261008.json). Stage 2 was blocked before scoring.

## Parallel-session research TIFF (P1): download yes; submit NO

[Live site](https://buffedlizard55-lab.github.io/GEMSDOE51/) · [Pull request12](https://github.com/buffedlizard55-lab/GEMSDOE51/pull/12) · [Three-pass review and handoff](knowledge/review-three-passes-20261007.md)

**A genuinely new P1 prediction TIFF has been generated. It is research-only, NOT recommended for competition submission. No slot was used.** The spatial holdout did not beat the current benchmark; we will not mislabel a failed experiment as a high-scoring submission.

- **[Download new TIFF](docs/downloads/gemsdoe51-p1-odd-even-q10-2a687636c85e-zeros.tif)** · [single-TIFF ZIP](docs/downloads/gemsdoe51-p1-odd-even-q10-2a687636c85e-zeros.zip)
- [Executive summary / latest results](docs/latest.html) · [How to submit — currently blocked](docs/how-to-submit.html)
- Identifier: `GEMSDOE51-P1-Q10-2a687636c85e`
- Note: `RESEARCH ONLY: odd/even scarp-profile HGB + HD blend; q10 broad strain gate; STE L9; 44069 dots; blocked holdout not cleared. Do not upload.`
- SHA256: `73a8dcb305609def44f4c2cc421f6c4a3c4d5c45a9fe8ef64078a58706908fb4`
- Final-byte checks: one float32 band, EPSG32611, 3730×3292, exact template transform, **all12,279,160 cells finite in[0,1]**, zero NaNs, zero out-of-range values, no NoData tag. This addresses numeric range hazards, not proven portal acceptance.
- New P1 holdout mean: **0.2839869**, paired gated baseline **0.2848987**, Δ **−0.0009117**, only **2/6** folds improved. Frozen-best reproduction also remains outside tolerance. **NOT PROMOTED.**
- All44,069 emitted points are in approved Stage1 tiles, covering90.09% of footprint. Lift1.110; within-tile occupancy0.947%. **84.64%** of gated dots also occur in the same detector's ungated output (support Jaccard0.7337). This passes operational broadness/confinement checks, not proof of causal independence.
- Initial available-reference uniqueness gate: **PASS**, max support Jaccard0.183076 / containment0.309492. **Broader family gate: NOT CLEARED.** All365 pinned payloads were restored;364 matching-shape maps compared with no byte/support duplicate (max Jaccard0.152086), but dense probability maps fully contain sparse supports (containment1.0), and one toy format-test TIFF has a different grid. [Full receipt](evidence/p1_family_audit_20261007.json). Do not infer global novelty or upload eligibility from the initial narrower PASS.

### Session update 2026-10-07 (evening) — validation instruments and three rejected candidates

This session did **not** build a submission TIFF. It settled *which instrument can arbitrate a submission decision*, and rejected every new candidate against it. All receipts are JSON under `evidence/`.

- **The frozen local best is the best artifact on every instrument measured so far.** `docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif` (44,069 dots) scores SGMC-off-catalogue **S = 0.2191** (covers 20.9 % of 66,277 off-catalogue SGMC pixels), 1-m lidar scarp **L = 0.0704**, and 0.064890 on the paired fixed-support six-fold visible-catalogue proxy. Sibling live-calibrated instruments rank the 12 live-scored artifacts at ρ ≈ +0.53–0.54; the visible-catalogue proxy is the outlier (ρ ≈ +0.14) and is *structurally unable to arbitrate catalogue-distance questions*: any support with no dot within 300 m of the catalogue scores exactly **0.000000** on it.
- **Rejected candidate 1 — catalogue-omission residual (H51-OMIT).** 20-channel rank-fusion of stack features, reduced by lineament-bank ridge/crest/anisotropy responses, then residualised against its own distance-to-catalogue expectation (22 bins), emitted as 2-px-spaced dots inside q10 Stage-1 tiles. At matched 16,000 dots: S = 0.0224 / L = 0.0389 — *below* the matched-mass random control (S = 0.0270 ± 0.0010) and below the sibling d2.8 reference (S = 0.1028). Receipt: `evidence/omit_candidate_build.json`.
- **Rejected candidate 2 — morphology-only emission.** The best genuinely new layers on S are `lid_relief_s15_lin` (S-AUC 0.778; top-12,691 DTI 0.0746) and `tmi_s15_lin` (0.0648); every `comp_*` competition band is at chance on S (0.001–0.016). A fusion of `lid_relief_s15_lin` + `lid_lapneg_max` + `lid_step_max` reaches S = 0.1420 at 44k dots (random 0.0854), but only 0.2218 on the exact six-fold proxy protocol (random 0.2171; frozen best 0.2853). Receipts: `evidence/layer_screen_offcatalogue.json`, `evidence/layer_screen_controls.json`, `evidence/lidar_field_holdout.json`.
- **Rejected candidate 3 — halo pruning and a mass-constant halo→morphology swap.** The promoted support's near-catalogue rim (24 % of dots at 2.24–2.5 px) earns 0.148 SGMC-credit per dot vs 0.314 for the support average; but removing it costs coverage on both arbitrating instruments (S 0.2191 → 0.2006 at ≤2.5 px; → 0.1834 at ≤3.0 px) and refilling the budget with morphology dots still loses (0.2065). Receipts: `evidence/support_variants_20261007.json`, `evidence/prune_halo_variants_20261007.json`, `evidence/swap_halo_variants_20261007.json`.
- **Consequence:** no new support beats the incumbent, so a new artifact can only be a *regeneration of the promoted procedure* — new seeds, all points inside q10 approved tiles with the 44,069-dot budget refilled inside that domain, and all-finite `[0,1]` output with zeros outside the footprint (the direct fix for the portal's "Predicted values must be in [0,1]" hazard). That regeneration is the next build; the fail-closed guard in `scripts/build_submission_hh_blend.py` requires an explicit manifest decision before any file is written. **No slot was used and no organizer score is claimed.**
- **Unblocks the next build:** `data/prepared/extras_static.dat` (35 layers) and `extras_static_names.json` were rebuilt successfully this session by `scripts/build_extras.py`; the six-fold fold specification was re-verified to reproduce the frozen receipt's per-fold truth sizes exactly; and `pytest -q` passes 73/73.

### What changed this session

1. **Data placement is resolved:** ten pinned inputs downloaded and SHA-verified; six-fold training and full-grid inference ran on CPU. No GPU was needed for this HGB pipeline. Data/raw and prepared rasters remain out of Git.
2. **Official source verification is stronger:** obtained original INGENIOUS DBF, field definitions, geodetic metadata and regional trace geometry through GitHub Actions. All1,126 mirrored trace rows match official name/rate/sense. `SLIPRTNUM` units are now verified as mm/year; rate component and individual dips remain assumptions.
3. **Source-corrected physical budget:** implemented Kreemer Eq3 using84,331 actual vector segments clipped to10km tiles, source-matched principal-strain shear, and explicit unit/component scenarios. Separate five-trace-split holdout:90.15% area,96.01% recall, lift1.0650. This audit is not silently substituted into P1's preregistered legacy gate.
4. **Four new hypotheses ranked; P1 tested without result-driven tuning.** The failed result is retained with a new downloadable diagnostic map, not spent on a weekly slot.
5. **Format checks strengthened:** invalid outside sentinels/NoData tags fail closed; full-grid finite/range checks accompany every new TIFF. Source definitions corrected several earlier physical explanations.

Read [the new hypothesis slate](knowledge/next-candidates-20261007.md), [official-source/equation review](knowledge/official-source-review-20261007.md), and [P1 measured receipt](evidence/p1_holdout_20261007.json) before future work. The task is **fault discovery**, not direct prediction of geothermal vents. These local catalogue-proxy measurements do not authenticate GEMSDOE32 file attribution or establish an organizer score; the reported `0.3195` was not the official page high on the one-time 2026-10-08 check.

**Historical material below is retained for audit.** Earlier claims that no new TIFF exists or slip-rate units are unknown are superseded by this update; the earlier K1 failure and benchmark measurements are unchanged. The standing brief is included below and expanded in the2026-10-07 intake appendix. Read it each session (`AGENTS.md`).

## Full user task brief and standing acceptance criteria

This full working brief is retained so a future session can continue without asking for manual design input. It consolidates the original request and subsequent corrections; it is not a claim that every result below succeeded.

> Review the repository and complete the end-to-end DOE GEMS project. Critically assess the claimed GEMSDOE32 `0.2778` result attributed to `H33-2-B2` and the stated `0.3195` leaderboard high; do not hallucinate a score-to-file or geological explanation. Use trusted, checked sources, link them, and distinguish owner reports, local measurements, user-supplied claims, and organizer facts.
>
> Before implementation, propose and rank 3–5 distinct geological hypotheses. For each, identify its layers, target physical signature/operator, why it could expose fault geometry missing from the existing USGS/INGENIOUS catalogue rather than merely recover known-fault habitat, how it differs from implemented repository/prior-art work, expected benefit, and implementation cost. If outside data is needed, name the free official source and verify availability before treating it as viable.
>
> Validate the leading candidate on the same spatially blocked holdout before using any competition submission slot. Do not spend a slot on an idea that has not beaten the current spatially blocked best under a preregistered rule. Report Stage 1 and Stage 2 holdouts separately. Stage 1 must remain coarse and non-dominant. Reconcile that with the requirement that every Stage-2 prediction point lie inside an approved Stage-1 tile; implement and validate the actual allowed-domain mask rather than assuming `stage1_weight=0.0` provides confinement.
>
> Only recommend submission if a candidate passes promotion, Stage-1 confinement/non-dominance, scoped uniqueness, and format gates. A substantively new, uniquely named diagnostic GeoTIFF may be generated after a failed completed holdout only when prominently marked RESEARCH ONLY / NOT FOR SUBMISSION. Do not copy, relabel, or merely re-encode a previous submission to satisfy the requirement. Make file/download/submission status obvious. Check exact grid, CRS, affine transform, dtype, `[0,1]` values (including the outside-footprint encoding against the live portal issue), and the official submission format. Never claim upload, organizer score, or acceptance without evidence.
>
> Review and update the site, preserve auditable research and source links, include this full prompt in README, and autonomously attempt a pull request and merge to `main`. State blockers and irregularities. No manual user input is expected.

This session is fixed to branch `arena/922033c2-gemsdoe51`; work remains on that branch. The repository's leaderboard policy is link-only: DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) restrict automated monitoring/copying and require prior written permission for manual monitoring/copying. No standings feed, snapshot, or copied leaderboard rows are maintained here.

## Historical status and local benchmark (before K2-08)

| Item | Status / result |
|---|---|
| **Upload eligibility** | **None. No slot authorized.** H53-A Stage 2 is blocked by failed baseline reproduction; H53-K2x failed promotion; H51-N2 loses its paired holdout; H52 V4 has no direct holdout for the written geometry. |
| H53-A Stage 1 (separate, source-segment budget) | 5 whole-record splits; nominal q10 approved area `0.901904`, recall `0.929089`, lift `1.030146`; uniform-dot proxy DTI `0.048390` in mask vs `0.049025` full footprint. No Stage-2 score. |
| H53-A baseline lineage | Canonical fresh H-D/H-H mean `0.2853151549`; frozen cached-field receipt `0.2853406027`; Δ `−2.54478e-5` vs tolerance `1e-5`; Stage 2 blocked before candidate scoring. Exact legacy field provenance unavailable. |
| Earlier H53-K2x six-fold screen | q10-gated mean `0.2850361`; same-fold gated baseline `0.2848987`; Δ `+0.0001375` in `4/6`, but `0.0003045` below frozen best. **NOT PROMOTED; research TIFF only.** |
| Compliance cost of the brief's constraints | `-0.0015469` mean proxy DTI (0/6 folds) versus the archived H-D configuration; the harness reproduces the archived receipt with max deviation `0.0` |
| Off-catalogue A/B physical-arm AUC (4 folds) | `0.6936` all / `0.6486` catalogue-independent (≥5 px from any A pixel) |
| Far-field ring-weight experiment | `+0.017314` on the off-catalogue A/B instrument, `-0.113310` on the blocked instrument → **instrument disagreement; no ring weight used** |
| Existing local H-H/H-D blend + STE L9 | Historical local best only; not portal-validated, not uploaded, no organizer score |
| Six-fold H-H/H-D proxy DTI | `0.2853406027`, visible known-fault catalogue; `4/6` folds beat H-D |
| Existing H-D proxy comparator | `0.2816626603` |
| P1 odd/even profile screen | 0.2839869; NOT PROMOTED; new research TIFF generated, no slot |
| H51-K1 new-operator screen | **NOT PROMOTED**; no new TIFF; no slot |
| Portal `[0,1]` validation error | **OPEN BLOCKER**; triggering file identity unknown |
| Organizer score / acceptance | None verified for GEMSDOE51 |

The existing local benchmark artifacts are linked for audit only:

- [GeoTIFF](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif)
- [One-file ZIP](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.zip)
- [Local checks receipt](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z-checks.json)
- [Submission manifest](data/submission_manifest.json)
- SHA-256: `9bd1e50d86114daa7c944d0c6d4f9f7cba6ba5070ae98ba5e45a965d78650777`
- Earlier identifier (do **not** paste until the portal issue is resolved): `GEMSDOE51-HH-HD-BLEND-STE-R347-20261007`
- Earlier note: `H-H potential-field edge-termination/conductive-relay features plus H-D, fixed 50/50 probability blend, STE L9 w0.35 spacing 2.4; holdout-promoted but no organizer score claimed.`

This old raster is locally verified as one-band `float32`, EPSG:32611, shape `3730 × 3292`, correct template transform, finite in-footprint values in `[0,1]`, and NaN outside with a NaN NoData tag. **The portal's reported range error remains unresolved**: local validity is not evidence that the portal accepts NaN outside. The exact file used in the reported portal attempt was not recorded. Do not infer that the old H-H/H-D TIFF either caused or fixes the error.

## Preregistered candidate slate and result

The full four-item slate, exact operators, source checks, prior-art boundaries, costs, and outcome are in [`knowledge/candidate-hypotheses-2026-10-07.md`](knowledge/candidate-hypotheses-2026-10-07.md) and [`evidence/candidate_hypotheses_prereg_20261007.json`](evidence/candidate_hypotheses_prereg_20261007.json). They are also linked from the [hypotheses page](docs/hypotheses.html).

1. **H51-K1 (top):** cross-scale potential-field tilt-like partial-gradient edge persistence using `tmi_hg/tmi_vg` and `iso_grav_anom_hg/iso_grav_anom_vg`.
2. **H51-K2:** directional conductivity contrast across an independent basement/potential-field edge.
3. **H51-K3:** radiometric-ratio lineaments conditional on independent structural edges.
4. **H51-K4:** earthquake-density ridge conditioned on independent structural edges; blocked until source semantics are verified.

The slate is operator-level and inspection-bounded, not a claim of global novelty. The local gravity HG band is signed; its available metadata does not establish whether it is a full 2-D magnitude or a directional component. K1 therefore tests a precisely coded **tilt-like partial-gradient proxy**, not a conventional total-horizontal-derivative tilt angle.

### H51-K1 Stage-2 holdout (separate from Stage 1)

Receipt: [`evidence/hk1_spatial_holdout_20261007.json`](evidence/hk1_spatial_holdout_20261007.json). This is a six-fold 3×3 contiguous spatial holdout, 12-pixel/1.2-km training buffer, 250,000 sampled negatives per fold, fixed seeds, `M/|G|=3.47`, and the same STE L9 / continuity `0.35` / spacing `2.4` rule. The proxy truth is the visible known-fault catalogue, not the hidden expert labels.

| Fold | Fresh H-D/H-H, ungated | H51-K1 blend, ungated | H-D/H-H, q10-gated | H51-K1, q10-gated | Paired gated Δ |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.283432 | 0.283529 | 0.283432 | 0.283529 | +0.000097 |
| 1 | 0.271784 | 0.275603 | 0.270436 | 0.274444 | +0.004008 |
| 2 | 0.290270 | 0.292220 | 0.289119 | 0.290417 | +0.001298 |
| 3 | 0.243359 | 0.242234 | 0.243359 | 0.242234 | −0.001126 |
| 4 | 0.305049 | 0.304764 | 0.305049 | 0.304764 | −0.000286 |
| 5 | 0.317996 | 0.315072 | 0.317996 | 0.315072 | −0.002924 |
| **Mean** | **0.285315** | **0.285570** | **0.284899** | **0.285077** | **+0.000178** |

The fresh ungated H-D/H-H reconstruction missed the frozen `0.2853406027` receipt by `−0.00002545`, outside the preregistered `1e-5` reproduction tolerance. The final K1 q10-gated mean (`0.2850766`) did not exceed the frozen ungated best (`0.2853406`), and the paired q10-gated gain over the same-fold q10-gated baseline was positive in only `3/6` folds. It is therefore **not promoted**, despite the ungated K1 point estimate of `0.2855703`. The separate receipts preserve every fold and metric. No K1 TIFF was built.

### Stage 1 q10 trace holdout (reported separately)

The q10 Stage-1 prior was evaluated before K1's six-fold comparison by holding out complete trace-table rows and removing held-out rows from the fault-budget tensor. Receipt: [`evidence/stage1_q10_trace_holdout_20261007.json`](evidence/stage1_q10_trace_holdout_20261007.json).

- q10 deficit mask mean approved area: `0.90063` of footprint.
- Held-out trace recall inside mask: `0.95390`; mean lift `1.05915`.
- Uniform-random-dot proxy DTI inside mask: `0.0506274`, versus `0.0485643` over the full footprint.
- During the six spatial Stage-2 folds, the separately rebuilt fold-specific q10 masks approved `0.90135` of footprint on average. Confining every K1 point to them gave Stage-1 lift `1.10945`, below the preregistered non-dominance limit `1.5`; all evaluated candidate points were inside the approved mask.

This is weak coarse enrichment, not a strong predictor. Slip-rate units/component remain provisional (see IR-51-12 and the [irregularities page](docs/irregularities.html)); Stage-1 has zero soft score weight. The q10 mask is only a broad allowed-domain constraint for the tested K1 comparison. The old local H-H/H-D TIFF was created before this q10 allowed-domain requirement and fails it: on the current full-data q10 deficit mask, 38,211 of 44,069 predicted points (86.71%) are inside the 90.09% approved area (lift 0.9624). It was not rebuilt under the q10 constraint.

## GEMSDOE32 `0.2778` and the stated `0.3195` high

The file-to-score story for `H33-2-B2 = 0.2778` is **unsupported**. The sibling GEMSDOE32 owner README/site labels `H33-2-B2` as **UNSCORED** and describes `0.2747` as a modeled projection. No organizer-authenticated mapping from the named TIFF to an observed score, exact prediction field, or hidden labels has been verified. A public DTI value alone cannot reveal a method's causal contribution or geological mechanism. See [`evidence/score_attribution_audit.json`](evidence/score_attribution_audit.json) and the [case-study page](docs/analysis.html).

The user-reported `0.3195` “current leaderboard high” was **not the page high** in the one-time official leaderboard check recorded on 2026-10-08; treat it as stale, not current. No leaderboard snapshot is stored and no automated monitoring is used. Use the [official leaderboard link](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) directly; no GEMSDOE51 score is claimed.

The official metric is the published distance-weighted Tversky index, `DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|)`, with a triangular distance-credit kernel that reaches zero at 300 m. Explaining a score requires the exact scored raster, hidden truth geometry and size, and weighted TP/FP; none can be inferred from the number alone.

## Site review and submission-status pages

The static site is generated from current records by `scripts/build_site.py` and checked by `scripts/check_site.py`. The key pages are:

- [Executive summary](docs/index.html)
- [Submission instructions and current block](docs/how-to-submit.html)
- [Hypotheses and K1 result](docs/hypotheses.html)
- [Separate Stage-1 / Stage-2 holdouts](docs/holdout.html)
- [GEMSDOE32 score-attribution review](docs/analysis.html)
- [Irregularity register](docs/irregularities.html)
- [Leaderboard policy / official link only](docs/leaderboard.html)

At that earlier point, the site said no file was upload-eligible, H53-A Stage 2 was blocked before candidate scoring, and portal validation was unresolved. The separate earlier H53-K2x TIFF is research-only and failed promotion. K2-08, above, is the later overall experiment and also remains research-only. The old local benchmark link is for audit only; the P1 TIFF and other historic maps are research-only. Before any future upload, identify the exact file from the user-reported error and resolve whether outside-footprint NaNs are accepted; do not assume the local verifier is the portal.

## Sources and provenance

- [DrivenData problem description, metric, data layers and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS / GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [NBMG QFaults INGENIOUS REST schema](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson); its schema does not establish the local slip-rate units
- [Kreemer et al. (2000), public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf), Eq. 3
- [Miller & Singh (1994), potential-field tilt paper](https://doi.org/10.1016/0926-9851(94)90022-1); K1 is explicitly not claimed to be the conventional total-horizontal-derivative tilt angle
- [USGS blind geothermal systems / Great Basin report](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)
- [USGS GeoDAWN ScienceBase record, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)

All large rasters and owner-mirrored datasets are out of Git. Hash pins establish local mirror consistency, not organizer authentication.

## Historical H53-A execution record (2026-10-08)

The H53 slate and Stage-1/Stage-2 protocol were frozen before H53 measurements. At that historical point, the test suite, repository API/import/collection checks, and generated-site link/download checks passed; no aggregate count is carried forward here as a result for the current tree. Six label-blind H53-A features were built to ignored `data/prepared/arm_h53a.dat`; no finite-lag H53-A TIFF was written. The separate budget-q10 H53-A variant and earlier H53-K2x research TIFF are documented above.

The source-corrected Stage-1 holdout used 84,331 official clipped source segments from 1,126 records, 10 km tiles, and five deterministic whole-record splits (seed 5308). Nominal assumption: verified source rate unit mm/year; fault-plane rate; 60° normal dip; unknown sense omitted; literal geodetic scale `1e-8/year`. The top 90% residual-rank mask approved `90.19%` of footprint area and recalled `92.91%` of held-out trace pixels (lift `1.0301`). Uniform matched-mass random-dot DTI was `0.048390` inside the approved mask vs `0.049025` over the footprint; one seeded draw per split is descriptive only. The `1e-9/year` and vertical-rate sensitivities are reported in the receipt. **Preregistration wording irregularity:** its `sensitivity_not_used_for_selection` list also redundantly says “fault-plane rate convention,” although fault-plane rate is the nominal convention in the same frozen preregistration. The executable receipt resolves what was actually evaluated: nominal `1e-8/year` fault-plane, `1e-9/year` fault-plane sensitivity, and `1e-8/year` vertical-rate sensitivity. The frozen preregistration is preserved unchanged; no fourth case is claimed.

Baseline audit: `evaluate_hh_blend.py` consumes old `field_H_D_fold*` / `field_H_H_fold*` caches whose exact generating metadata and arrays are no longer present. The canonical `run_experiments.py` path uses negative seed `1000 + fold.index`; the distinct H52 cache uses `2000 + fold.index` and was not reused. A fresh 1000+fold H-D/H-H fit reproduces folds 1–5 exactly but differs on fold 0 by `−0.000152687`, for a mean delta `−0.000025448` from frozen `0.285340603`, exceeding the locked `1e-5` tolerance. No cause is asserted. The frozen baseline is not reproducible from preserved evidence, so the H53 Stage-2 runner correctly refuses to train/score the candidate. This is a provenance gate failure, **not a measured H53-A failure**. The separate earlier H53-K2x screen was measured and not promoted. A post-audit code-review hardening also made any future passing path verify the frozen-receipt, input-arm and per-fold field hashes before candidate scoring. This is an implementation-integrity check, not a changed score threshold; it does not alter the already-failed frozen result.

Receipts: [`evidence/h53a_stage1_holdout_20261008.json`](evidence/h53a_stage1_holdout_20261008.json), [`evidence/h53a_baseline_provenance_20261008.json`](evidence/h53a_baseline_provenance_20261008.json). The finite-lag H53-A candidate has no score, TIFF, scoped uniqueness audit, or portal-format result. The separate budget-q10 H53-A TIFF and H53-K2x screen are documented above. No competition slot was used. See the [integrated H53-A/H53-K2x review](knowledge/review-three-passes-20261008.md) and [PR #20 R1/budget-q10 review](knowledge/pr20-h53-r1-review-three-passes-2026-10-08.md).

## What was measured in this session (2026-10-07, evening block)

| Question | Script | Receipt | Result |
|---|---|---|---|
| Does the *visible inventory* carry placement signal beyond the physical layers? | `scripts/run_h51_n1.py` | `evidence/h51_n1_ab_fold0_timing.json`, `evidence/h51_n1_ab_static_fields.json` | **No** — the static physical arm beats the inventory-context arm in every regime on the A/B instrument; AUC_all `0.6936`, AUC_far `0.6486` |
| Where in the distance-to-catalogue coordinate does the credit sit? | `scripts/run_ring_profile_ab.py` | `evidence/ring_profile_ab.json` | Far-field ring (`15 px`) beats unweighted (`0.205821` vs `0.188507`, `+0.017314`) on the A/B instrument; the near-field ring is the worst profile |
| Do the brief's hard constraints cost score? | `scripts/run_h51_n2_holdout.py` | `evidence/h51_n2_paired_holdout.json` | `-0.0015469` mean, 0/6 folds; the baseline reproduces the archived receipt exactly (max deviation `0.0`); the ring weight is **rejected** here (`-0.113310`) |
| Does the H51-N2 research artifact pass local geometry/format checks? | `scripts/build_submission_n1.py` | `evidence/submission_h51n2.json`; `evidence/h51_n2_paired_holdout.json` | Format, `[0,1]` range, q10 confinement, lift and scoped uniqueness pass; **holdout fails** (Δ −0.0015469; 0/6 wins), so the artifact is research-only and no slot is authorized |
| Why did the thin-dot artifacts score highly, and what was proposed against the stale user-reported `0.3195`? | analysis | `knowledge/03_why_the_dotted_family_wins_2026-10-07.md` | Historical analysis only; it does not validate the `0.3195` claim or attribute any score to a file |

### H52 reconciliation note (2026-10-07, after cross-session merge review)

The H52 V4 GeoTIFF is retained as a research artifact, **not** as an upload recommendation.
`docs/downloads/gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278-checks.json` has
`holdout: null`. It was built as V4 (NMS r=2.4), but the only 0.280821 value in the available
pass-2 ledger is `V7_ste_q10` (STE), so that number is not evidence for the V4 raster. The
pass-2 ledger records `harness_ok: false` under the older clause; the arithmetic recheck
`evidence/h52_harness_recheck_20261007T235024Z.json` supports the respecified tolerance but is
not a fresh six-fold pass-2 run. See **IR-H52-09**. The candidate’s format and scoped
uniqueness gates do not waive the required holdout promotion rule.

The branch also includes the parallel H51-N2 session and its source-audit work. Its TIFF is
retained as research-only: its own paired six-fold holdout is 0.2801158 versus 0.2816627 for
H-D (Δ −0.0015469; 0/6 wins), with the receipt explicitly `NOT_PROMOTED`. Its current-inventory
support audit also passes, but that is not a submission candidate despite format/uniqueness checks.

## Reproduce, test, and review

With the hash-pinned data restored (`python scripts/restore_data.py --group all`), run:

```bash
PYTHONPATH=src .venv/bin/python scripts/prepare_data.py
PYTHONPATH=src .venv/bin/python src/gems51/stack.py
PYTHONPATH=src .venv/bin/python scripts/build_arm_extras.py --group hd   # build_extras.py OOMs in this sandbox
PYTHONPATH=src .venv/bin/python scripts/run_h51_n1.py --instrument ab --folds 0,1,2,3 \
  --arms static --skip-emission --save-fields work/fields \
  --out evidence/h51_n1_ab_static_fields.json
PYTHONPATH=src .venv/bin/python scripts/run_ring_profile_ab.py --out evidence/ring_profile_ab.json
PYTHONPATH=src .venv/bin/python scripts/run_h51_n2_holdout.py --folds 0,1,2,3,4,5
PYTHONPATH=src .venv/bin/python scripts/build_submission_n1.py --ratio 3.0 --spacing 2.8 \
  --excl-radius 2.24 --stage1-q 10 --tag h51n2-creditthin --dry-run   # drop --dry-run to write the artifact
PYTHONPATH=src .venv/bin/python scripts/run_stage1_trace_holdout.py \
  --thresholds 10 --output evidence/stage1_q10_trace_holdout_20261007.json
# H53-A: build label-blind features and baseline-only provenance audit once.
PYTHONPATH=src .venv/bin/python scripts/build_h53_features.py
PYTHONPATH=src .venv/bin/python scripts/build_arm_extras.py --group hd
PYTHONPATH=src .venv/bin/python scripts/build_arm_extras.py --group hh
PYTHONPATH=src .venv/bin/python scripts/audit_h53a_baseline_provenance.py
# The frozen receipt already exists in this checkout; never overwrite it to shop for a result.
PYTHONPATH=src .venv/bin/python scripts/run_h53a_stage1_holdout.py
# Fail-closed: exits without fitting H53 if the baseline audit did not reproduce.
PYTHONPATH=src .venv/bin/python scripts/run_h53a_stage2_holdout.py
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/build_site.py
PYTHONPATH=src .venv/bin/python scripts/check_site.py
```

`scripts/build_extras.py` cannot complete in a ~4 GB sandbox (it was OOM-killed); `scripts/build_arm_extras.py --group hd` builds the four H-D layers that every number above depends on. Memory-hungry runs are best executed one fold at a time.

## Remaining work and limitations (for the next session)

1. **H53-A Stage 2 is blocked before candidate scoring.** The fresh canonical H-D/H-H baseline failed the preregistered `1e-5` reproduction tolerance because the frozen evaluator's cached fields were never committed (same root cause as IR-R1-01). Do not run the candidate through the failed guard, relabel this as a candidate failure, change seeds after seeing results, or weaken the frozen gate. The R1 session demonstrated one recovery path — Amendment A1 re-anchored the instrument on the committed P1 receipt and reproduced it with deviation 0.0 — so a future H53-A Stage-2 attempt can preregister the same anchor before collecting candidate scores.
2. **No prediction TIFF exists for the finite-lag H53-A operationalization.** It has only a Stage-1 result because the baseline gate blocked candidate scoring. Do not create or expose a submission candidate from those edge features alone. A future uniquely generated TIFF requires a completed, valid paired Stage-2 holdout and all promotion, confinement/non-dominance, scoped uniqueness, and format checks. The separate budget-q10 H53-A variant has its own research-only TIFF and failed Stage-2/uniqueness gates; it does not change the finite-lag result. Until a candidate passes every gate, no H53 file is cleared for a competition slot.
3. **Portal validation is untested.** The user-reported “Predicted values must be in range [0, 1]” error has no verified triggering filename. The R1 artifact removes the NaN outside-footprint failure mode entirely (all-finite [0,1], zeros outside), but no upload has been performed; local range checks do not prove portal acceptance. If a future upload is rejected, record the exact error text and file name before changing anything.
4. **No organizer score exists for GEMSDOE51.** All local DTI values use visible known-fault proxy truth, not hidden expert labels. GEMSDOE32 `0.2778` attribution remains unverified; the one-time official page check found the user-reported `0.3195` was not the page high. Neither claim proves file attribution or causation.
5. **The known-fault holdout is reused.** Five H53 Stage-1 whole-record splits and the existing six spatial blocks provide proxy comparisons, not an untouched lockbox or evidence of hidden-fault generalization. The two local instruments also disagree about distance-to-catalogue; resolving it needs a third instrument or revealed labels. Until then the conservative reading (no ring weight, keep points clear of the immediate halo) is what the artifacts use.
6. **Commit field digests alongside any future frozen number.** `extras_static.dat` was rebuilt on 2026-10-08 (35 layers; used by the R1 holdout and the H-H arm), and the H-D/H-H groups rebuild via `scripts/build_arm_extras.py`, but the archived frozen-best fold *fields* remain uncommitted (IR-R1-01). Keep generated arrays out of Git; commit digests so frozen numbers stay auditable.
7. **Untested preregistered candidates remain:** H51-X2 (paired scarp-face asymmetry; top priority, needs an operator definition on the max-aggregated lidar bands), H51-X3 (warm-spring alignment; needs mirror audit), H53-X6 (along-strike taper; high cost), H53-X4 (stress corridors; BLOCKED on USGS Siler DOI 10.5066/P9YL58W6 mirror), and the R2 confinement repair (re-emit disapproved dots by continuing the STE greedy search on the approved domain) — each needs its own preregistration. H53-X5 was screened and REJECTED on 2026-10-08 (`evidence/x5_screen_20261008.json`).
8. **`inventory_context` has a known degeneracy:** because the training positives *are* the known catalogue, any catalogue-distance feature lets the model learn the halo (the IR-51-LEAK-01 pattern). Any future inventory-conditioned arm must be trained on held-out systems (the A/B design), not on the full catalogue.
9. **The H51-N2 artifact should be re-emitted** if a better arm (for example a rebuilt H-H blend) becomes available: the emitter, gates and receipts are parameterised and take ~90 seconds to rerun.
10. **Known limitations:** geodetic residuals can reflect off-fault/aseismic strain, rate/component uncertainty, dip/rake assumptions, unit interpretation, or interpolation. The q10 mask is a coarse permitted domain, not a fine-scale fault locator. Random-dot DTI controls are one realization per split.

`evidence/h53a_baseline_provenance_20261008.json` and `evidence/h53a_stage1_holdout_20261008.json` are the current H53 receipts. The earlier `evidence/hk1_spatial_holdout_20261007.json` remains the authoritative K1 outcome; do not rerun it to shop for a passing result. The standing user prompt below is retained and must be read on every future session.

---

## Standing user prompt — 2026-10-07 intake supplement

Read this brief **every session before implementation**, along with the full working brief above and the latest evidence. Repeated verification boilerplate is consolidated here; this is an operational transcription, not an organizer statement or a verbatim chat export.

> **THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!**
>
> **MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.
>
> Geodetic strain-budget deficit, used strictly as a coarse first stage. Hypothesis: where the geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the catalogue is likelier to be missing structures. Precedent for balancing geodetic and geologic deformation exists in the UCERF3 deformation models (Field et al., Bulletin of the Seismological Society of America 104(3), 1122–1180, 2014, doi:10.1785/0120130164). Three of those models invert geodetic and geologic data together, and UCERF3 also models off-fault strain explicitly. A related USGS-listed paper ("A fault-based model for crustal deformation, fault slip-rates and off-fault strain rate in California") estimates off-fault moment rates separately. Convert each mapped fault's slip rate (the INGENIOUS compilation is reported to hold slip rates; confirm in the shapefile attributes) and trace length into an equivalent tile strain rate using a documented moment-tensor summation. State the exact formula and cite its source, because I haven't verified one. Subtract that from the dilatation and shear strain-rate layers, and keep the residual only as a prior over broad tiles. Strain rates are coarse, and the deficit can be distributed off-fault, aseismic or caused by wrong catalogue slip rates. Habitat-style statements scored worst in this project (0.0041, 0.1223, 0.1352), so a second, separately holdout-scored fine-scale model must place points only inside approved tiles. Report both stages' holdout results separately. Normalize, write the GeoTIFF, run the uniqueness gate, and confirm the submission isn't dominated by stage one's footprint.
>
> Study GEMSDOE32 H33-2-B2, reported score0.2778, and whether a unique submission can exceed it and the stated leaderboard high0.3195. Use PhD-level scientific judgment, official checked sources and links. Do not infer causation from a score alone. Before implementing, generate3–5 previously untried geological hypotheses, each naming layers, physical signature/operator, missing-catalogue rationale, differences from existing code, expected DTI benefit and implementation cost. Rank and validate the top candidate on spatially blocked holdouts. **Do not spend a submission slot on an idea that hasn't beaten the current holdout best.** If new data are needed, identify free official sources and verify availability before calling the idea viable.
>
> Work autonomously without requesting manual data placement; review the repo and next steps from previous sessions first. Research official scientific literature and data, organize an auditable knowledge base with manual-review links, propose distinct grounded approaches, and keep the project useful and current. Do not hallucinate or claim unperformed verification. Flag irregularities and explain limitations/access blockers. The long-term geothermal-discovery goal must not be confused with the actual fault-pixel competition target.
>
> Build a clean, simple, user-friendly GitHub Pages site. The first screen/executive summary must make the new TIFF download and submission-readiness decision obvious. Include a uniquely identifiable filename and short comment for the optional submission note. Add an executive-summary/instructions subpage. Address the reported portal error **“Predicted values must be in range [0, 1]”**. Portal accepts a single-band GeoTIFF or ZIP containing one GeoTIFF matching required CRS, shape and geotransform; values must be[0,1]. Local checks and actual portal acceptance are separate evidence.
>
> Understand official competition overview, problem description, rules, datasets, reference solution and metric; obtain data, train, infer, normalize and validate. Use free public third-party sources with appropriate rights. The previous “single blocker is data placement / GPU needed” assertion must be tested rather than repeated. No DrivenData authentication is supplied; do not invent access. Use available authorized mirrors and official downloads autonomously where possible.
>
> **Core Values — Maximize P(Win):** weigh tradeoffs and risks, choose the path maximizing the probability of success, set aside attachment to a favored idea. **Own the Outcome:** own results end to end, fix problems without waiting for permission, treat failure and success as signals, and remain accountable for the final outcome.
>
> **Three passes required.** Pass1 implement and verify; Pass2 review bugs, missing requirements, incorrect assumptions and edge cases, fixing findings; Pass3 recheck against the original request and improve accuracy, reliability, completeness and quality. Do not stop at pass1. Create a pull request, merge onto main, and leave explicit next-session work and limitations. Never claim a leaderboard improvement or fully satisfied scientific requirement without evidence.

### User-supplied score/site inventory (unverified claims, not a leaderboard feed)

Sites below are starting points for studying prior methods, not permissible sources of a copied “new” submission. Blank scores mean no result supplied. The existing sibling audit inventories54 repositories; it does not establish organizer score-to-file attribution.

| Repository/site | User-supplied identifiers and scores |
|---|---|
| [GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html) | gems-submission-20260925T001403Z-7f00890a:0.1563 |
| [6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/) | gems6_hgb88-topk03_33cec71ff0:0.0286 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | pindrop-v4-nodes:0.1193; discovery:0.0830; ridge:0.1152 |
| [GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html) | dual-family-union-f68e590f:0.1560 |
| [GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/) | gems-submission-20260926T163915Z-237f0063:0.0343 |
| [5GEMSDOE](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html) | gems-submission-20260926T175114Z-7f00890a:0.1563 |
| [7GEMSDOE](https://buffedlizard55-lab.github.io/7GEMSDOE/) | lidarscarp-ridge-top2pct-36c3a3f341c8:0.1461 |
| [8GEMSDOE](https://buffedlizard55-lab.github.io/8GEMSDOE/) | Hedge-v2_submission:0.1563 |
| [GEMSDOE9](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html) | 2314b599:0.0107 |
| [11GEMSDOE](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html) | gems-structural-area06-v1:0.0202 |
| [12GEMSDOE](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html) | r7-nms3-dem10-scarp_0c9199f14e62 and allfinite twin:0.1294 |
| [15GEMSDOE](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html) | gems-tso1-conj_alteration_mag:0.0782 |
| [14GEMSDOE](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html) | GEMS_r5-geom-horse-ensemble:0.0020 |
| [17GEMSDOE](https://buffedlizard55-lab.github.io/17GEMSDOE/) | F-ensemble-2pct:0.0187 |
| [18GEMSDOE](https://buffedlizard55-lab.github.io/18GEMSDOE/) | H19-C_c11e495e:0.0297 |
| [19GEMSDOE](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html) | h19-4-691e4dfa:0.1894; h19-5-e27054cf:0.1922 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | h16-continuation:0.0461; h20-dem10-scarp-thin:0.0921; H25-ctx-ridge:0.1280; h28-dotted-ridge:0.1839 |
| [13GEMSDOE](https://buffedlizard55-lab.github.io/13GEMSDOE/) | r13-lattice-s5_v2_nan-outside:0.0904 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | h16-1-df20f65e:0.1855; h18-3a-c502dfab:0.0976; h18-4-aef8f42c:0.0360 |
| [GEMSDOE21](https://buffedlizard55-lab.github.io/GEMSDOE21/) | h19-4-reference:0.1894 |
| [20GEMSDOE](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html) | h20-1-be0e8f6b:0.1890; h20-5-824ce73a:0.1859 |
| [GEMSDOE22](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html) | h23-a-e2ec4b49:0.1002; h23-b-86176698:0.0748 |
| [GEMSDOE23](https://buffedlizard55-lab.github.io/GEMSDOE23/) | h30-arrangement-matched-habitat:0.1352 |
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | h25-1-dotted-h19-5-d1-5-989f59505db1:0.2477 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | dotted-h19-5-d2-8-e56ea318af89:0.2600 |
| [GEMSDOE26](https://buffedlizard55-lab.github.io/GEMSDOE26/) | dilcond-oof-v1-47629f496133:0.1223 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | topo-gap-closure-t-v2-on-d1-5:0.2449 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | h27-4-r1-solo-d2-8:0.2708; h32-1-prethin-tip-euler:0.2649; h36-1-rung30-blind-r1:0.2710; h38-1-hf-euler-r30-r1:unreported |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | efd28-repro:0.2600; repo-c0-habitat-emission:0.0041; sgmc-off-catalogue-44k:0.0512; wormrank-d28, wormsurv-filter, xfit-c0-habitat, xfit-h41-union-qfaults:unreported |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | d28-poisson300m-offcat-44090:0.2600 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | h27-4-solo-d28:0.2708 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros:0.2778 (user report; owner site UNSCORED) |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | h33d-analog-tip-stepover-r30:0.2632 |
| [GEMSDOE34](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html) | h34-scatter-q50-arr-matched:0.0778 |
| [GEMSDOE35](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html) | h35-06-aaa86efb25-candidate:0.0418 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | anderson-geothermal-pinn-38854:0.2750 |
| [GEMSDOE37](https://buffedlizard55-lab.github.io/GEMSDOE37/) | h6-physics-dotted-80k:0.1193 |
| [GEMSDOE38](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html) | D-step-3p0-07pct-tipProt:0.0763 |
| [GEMSDOE39](https://buffedlizard55-lab.github.io/GEMSDOE39/) | h40-e-disc-h40e-30k-zeros:unreported |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | h8-euler-lineament-depthcluster (soft/hard), h45-eulerdepthreadcluster:unreported |
| [GEMSDOE41](https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html) | h42-submission-primary:unreported |
| [GEMSDOE42](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html) | xscale-worm-persistence:0.0581 |
| [GEMSDOE43](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html) | sup01-hgb21-sep40-n40000:0.0424 |
| [GEMSDOE44](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/) | h46-twostageAB:unreported |
| [GEMSDOE45](https://buffedlizard55-lab.github.io/GEMSDOE45/) | h51-km-faultzone:0.0106 |
| [GEMSDOE46](https://buffedlizard55-lab.github.io/GEMSDOE46/) | r11f-scarp-radiometric-fusion:0.1589; r12-scarp-rad-concordance:unreported |
| [GEMSDOE47](https://buffedlizard55-lab.github.io/GEMSDOE47/) | unreported |
| [GEMSDOE48](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html) | unreported |
| [GEMSDOE49](https://buffedlizard55-lab.github.io/GEMSDOE49/) | gate_ortho_w0.25-40k:0.2376 |
| [GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/) | unreported |
| [GEMSDOE51](https://buffedlizard55-lab.github.io/GEMSDOE51/) | unreported |
| [GEMSDOE52](https://buffedlizard55-lab.github.io/GEMSDOE52/) | unreported |
| 53GEMSDOE,54GEMSDOE | unreported; no explicit site URLs supplied |

### Competition/data links supplied with the task

- [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/format/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard — link only](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [EPSG32611](https://epsg.io/32611), [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS project](https://gbcge.org/current-projects/ingenious/), [GDR1391](https://gdr.openei.org/submissions/1391)
- User mirrors, not independently authenticated official downloads: [GEMS PDF](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0), [example submission](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0), [existing faults](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0), [numerical features](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0), [DEM links PDF](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

## Standing user prompt — 2026-10-08 intake supplement

Read this section at the start of every session, together with `AGENTS.md`. The operative
requirements from the 2026-10-08 task brief (verbatim where quoted):

> "MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
> UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST
> BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION."
>
> "Geodetic strain-budget deficit, used strictly as a coarse first stage. Hypothesis: where the
> geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the catalogue
> is likelier to be missing structures. … Convert each mapped fault's slip rate … and trace
> length into an equivalent tile strain rate using a documented moment-tensor summation. State the
> exact formula and cite its source, because I haven't verified one. Subtract that from the
> dilatation and shear strain-rate layers, and keep the residual only as a prior over broad tiles.
> … Habitat-style statements scored worst in this project (0.0041, 0.1223, 0.1352), so a second,
> separately holdout-scored fine-scale model must place points only inside approved tiles. Report
> both stages' holdout results separately. Normalize, write the GeoTIFF, run the uniqueness gate,
> and confirm the submission isn't dominated by stage one's footprint."
>
> "WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE …
> GEMSDOE32 … h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778. Why and how did this get the
> highest score and are we able to generate a submission that scores higher than 0.2778? …
> 0.3195 is the highest score right now …"
>
> "Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each
> naming: the specific layer(s) involved, the physical signature being targeted …, why it should
> catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how
> it differs from anything already implemented in this repo. Rank them by expected DTI improvement
> and implementation cost. Validate the top candidate on our spatially-blocked holdout set before
> touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten
> the current holdout best. If a candidate can't be validated without new external data, name the
> specific free, official source needed and check it's obtainable before proposing the idea as
> viable."
>
> "Work line by line verifying from official verified trusted sources, provide links for manual
> review. There should be no manual input, work on your own to complete tasks. Flag any
> irregularities for review. No hallucinations. … Go ahead and create a pull request and then
> merge the pull request onto the main. Make suggestions for what work still needs to be done and
> any limitations that is in the way of a successful project."

Operational constraints carried by this session:

1. The submission artifact must be a single-band float32 GeoTIFF, EPSG:32611, 3730×3292, exact
   template transform, every value finite in `[0, 1]` (zeros outside the footprint, no NoData
   tag), downloadable from the GitHub Pages site with its status obvious on first view.
2. The status is decided ONLY by the preregistered six-fold paired rule (no manual overrides);
   `data/submission_manifest.json` key `ok_to_download_and_submit` is the source of truth.
3. Stage-1 holdout and Stage-2 holdout are reported separately; Stage 1 stays coarse and
   non-dominant (uniform-fill dominance control required under hard confinement).
4. Uniqueness gate against every locally held prior plus the 21 commit-pinned family references
   (`scripts/fetch_gate_refs.sh`); byte, support-Jaccard (≤ 0.50) and containment (≤ 0.60) checks.
5. No leaderboard scraping or standings copying (DrivenData Terms of Use); all external numbers
   are labeled user-reported/owner-reported unless they are organizer records.
6. Core values: Maximize P(Win) and Own the Outcome — fail closed on evidence, fix problems
   without waiting to be asked, and treat failures as signals.

The session's detailed design record is `knowledge/preregistration-2026-10-08.md`; receipts are
`evidence/r1_holdout_20261008.json`, `evidence/x5_screen_20261008.json`, and the final-byte
checks JSON next to the artifact in `docs/downloads/`.
