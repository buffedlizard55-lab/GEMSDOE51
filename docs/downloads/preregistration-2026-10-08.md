# Preregistration — 2026-10-08 session (R1 regeneration + new hypothesis slate)

**Written before any holdout run in this session.** This document freezes the
decision rules so no result can be tuned into a promotion after the fact. It is
the governing record for whatever artifact this session writes.

## 1. What this session must produce

1. A **unique GeoTIFF artifact** with an obvious submit / do-not-submit status
   (user brief, highest urgency). Status is set ONLY by the frozen rules below.
2. A separately reported **Stage-1** (coarse strain-budget prior) and
   **Stage-2** (fine-scale detector/emission) holdout result.
3. A ranked slate of **new** geological hypotheses not previously implemented.
4. Site + manifest updates so the download page states the status unambiguously.

## 2. Candidate: R1 — promoted-procedure regeneration with legal geometry

The promoted procedure (six-fold proxy DTI `0.285340602656319`,
`evidence/hh_blend_holdout.json`) is the best *measured* configuration in this
repository. It is not upload-legal as archived:

- only 86.71 % of its emitted dots lie inside Stage-1 q10 approved tiles
  (standing requirement: **every** Stage-2 point inside approved tiles); and
- it writes NaN outside the footprint with a NaN NoData tag, while the reported
  portal error was "Predicted values must be in range [0, 1]" — the all-finite
  `0`-outside encoding removes every non-finite cell as a hazard class.

R1 changes **geometry encoding only, no new geology**:

- Stage 1 unchanged: Kreemer et al. (2000) Eq. (3) Kostrov sum deficit over
  10 km tiles, threshold at the 10th percentile (q10 ⇒ ~90 % of the footprint
  approved). Stage-1 weight stays `0.0`; it defines the allowed domain only.
- Stage 2 unchanged: full-field H-D (seed 17) + H-H (seed 19), fixed 50/50
  probability blend, STE L9 / w_cont 0.35 / spacing 2.4 emission, catalogue
  exclusion 2.0 px, mass M/|G| = 3.47.
- Two confinement operators, both evaluated (data picks the winner, frozen):
  - **RESTRICT**: STE candidate set is intersected with the approved mask
    before greedy spacing (the operator used by P1/N2 builds).
  - **RELOCATE**: emit unrestricted first; every dot outside approved tiles is
    moved to the nearest approved, non-excluded, unoccupied cell (KDTree with
    lazy blocking, spacing 2.4 preserved, deterministic processing order =
    emission score order). Keeps ~87 % of dots bit-identical to the promoted
    support; moved dots travel the shortest possible distance (q10 covers ~90 %
    of the footprint, so nearest approved cells are typically 1–3 px away, inside
    the 3 px DTI kernel support).
- Output encoding: float32, exact template CRS/shape/affine, dots = 1.0,
  **every other cell 0.0 (no NaN anywhere, no NoData tag)**.

### Frozen promotion rule for R1 (identical in form to the H51-N2 precedent)

PROMOTE (upload-eligible) iff ALL of:

1. **Instrument check** — the `base` variant (no confinement) reproduces
   `evidence/hh_blend_holdout.json` STE per-fold values with max |Δ| ≤ 1e-5.
2. **No compliance cost** — `mean(best confined variant) − mean(base) ≥ 0`.
3. **Fold support** — best confined variant wins ≥ 4/6 folds vs `base`.
4. **Confinement** — 100 % of emitted dots inside approved q10 tiles (verified
   from the final bytes, not assumed).

If the rule fails, the artifact is written only as **RESEARCH ONLY / DO NOT
SUBMIT**, uniquely named, with receipts. No post-hoc rule edits.

Variant selection: if both RESTRICT and RELOCATE satisfy (2)–(3), the higher
mean is selected; ties go to RELOCATE (smaller perturbation).

### Stage-1 / Stage-2 reporting separation

- Stage 1 holdout is the five-trace-split rank-residual receipt
  (`data/stage1_trace_holdout.json`, corrected: deficit Spearman 0.039,
  top-20 % lift 1.196) plus the two-stage scan (`data/two_stage_results.json`,
  Stage-1-only DTI 0.1481 < uniform 0.1861). Stage 1 is coarse by design and
  never places a point; q10 confinement is a domain constraint, not a scoring
  weight.
- Stage 2 holdout is the six-fold paired harness written by this session
  (`evidence/r1_holdout_20261008.json`).

### Exact Stage-1 formula and sources (user asked for the verified formula)

Kostrov moment-tensor summation, in the horizontal form of Kreemer, Haines,
Holt & Blewitt (2000), Eq. (3):

    eps_dot_ij = (1/2) * sum_k [ L_k * u_dot_k / (A * sin(delta_k)) ] * m_ij^k
    m_ij^k = n_i^k s_j^k + n_j^k s_i^k     (unit moment-tensor orientation)

- Kostrov (1974), Izv. Acad. Sci. USSR Phys. Solid Earth (original sum:
  eps_dot_ij = (1/(2 mu V)) * sum_k Mdot_ij^k).
- Kreemer et al. (2000), JGR 105(B12), Eq. 3 — public PDF:
  https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf
  (fetched by the 2026-10-07 session; see `evidence/stage1_formula_audit.json`).
- Ward (1998) GJI 134:172–186 and Stevens & Avouac (2015) JGR 120:5828–5848
  eq. (1) use the identical budget.
- Field et al. (2014) UCERF3, BSSA 104(3):1122–1180, doi:10.1785/0120130164 —
  precedent for balancing geodetic/geologic deformation and explicit off-fault
  strain (cited by the user hypothesis; three UCERF3 deformation models invert
  geodetic + geologic data jointly).

Slip-rate provenance: INGENIOUS/NBMG Qfaults v2 `SLIPRT2023` verified as
mm/yr (`SLIPRTNUM` numeric part) against the official DBF and field
definitions (`registry/official/`, `evidence/official_attribute_audit_20261007.json`,
all 1,126 mirrored rows match by index/name/rate/sense). Slip **component**
(vertical vs fault-plane) and per-trace dip remain documented assumptions
(`rate_convention="vertical"`, 60° normal dip fallback, vertical strike-slip);
rank-space subtraction keeps the prior robust to that convention uncertainty.
Deficit used: `rank(geodetic II) − rank(fault tensor II)` per 10 km tile —
NOT an absolute dilation/shear subtraction (source conventions unresolved;
documented in `src/gems51/strain_budget.py`).

## 3. New candidate hypothesis slate (ranked; not implemented before this text)

Ranking = qualitative expected DTI improvement per implementation cost, based
on repository evidence (`evidence/layer_screen_offcatalogue.json`,
`evidence/hh_blend_holdout.json`, archived sibling score inventory). No DTI
values are promised.

| Rank / ID | Layers | Physical signature | Why it could catch off-catalogue faults | Difference from implemented work | Expected benefit / cost |
|---|---|---|---|---|---|
| 1 / H53-X2 | `lidar_scarp_features_u8.tif` directional up-face/down-face, cross-face, step, relief (+ detrended elevation) | **Paired scarp-face asymmetry ratio**: along a local cross-profile, the ratio of the two facing responses; asymmetric step kept, symmetric crest/valley suppressed | A degraded fault scarp keeps one-sided polarity after amplitude drops below mapping thresholds; fluvial ridges are symmetric. Targets the strongest measured off-catalogue layer family (lid_relief_s15_lin S=0.0746) | H-D sums same-facing coherence; no paired opposite-face ratio exists in `extras.py` | Moderate / LOW — reuses mirrored layers, ~3 new static features |
| 2 / H53-X5 | `geodawn_rad_u8.tif` (K, Th, U, TC) + TMI ridge crests + catalogue distance | **Alteration-crossing concordance**: K/Th ratio enrichment colocal with a magnetic lineament crest, conditioned on ≥ 200 m from catalogued faults | Hydrothermal fluid pathways alter surface radioelement concentrations along structures; the conditioning targets structures NOT already mapped | P3's conditional-negative-control was never implemented; sibling r11f/r12 fused scarp ∧ radiometric, not K/Th × magnetic-crest × off-catalogue | Moderate / MEDIUM — radiometric mirror already hash-verified |
| 3 / H53-X3 | `gdr_wellspring_in_footprint.csv` (temperature, chemistry) + independent lineament crests | **Warm-spring alignment statistic**: warm-spring points aligned with detected crests more than random rotation controls | Spring clusters on unmapped lineaments indicate permeable fault pathways; orthogonal to morphology-based detection | No feature in this repo uses point geochemistry at all | Low-moderate / MEDIUM — requires mirror provenance + unit/duplicate audit first |
| 4 / H53-X6 | Detrended elevation + DEM step/relief | **Along-strike displacement taper**: second along-strike derivative of step amplitude with finite taper bracketed by coherent shoulders | Dying displacement profiles expose unmapped segment ends away from catalogue tips | H_C uses catalogue-tip distance; H-H counts potential-field endpoints; neither measures topographic displacement taper | Low-moderate / HIGH |
| 5 / H53-X4 | Slip/dilation tendency polygons × detected lineament orientations | Stress-compatible structural corridors (coarse prior only) | Critically stressed orientations are more permeable | Nothing in-repo | **NOT VIABLE FROM THIS SANDBOX**: requires USGS Siler release DOI 10.5066/P9YL58W6 from sciencebase.gov, which is outside the egress allowlist and not mirrored. Viability condition: mirror it via the owner's GitHub bridge with sha256 pin before any further work. |

**Validation order (frozen):** X2 is screened FIRST on the cheap off-catalogue
layer-screen instrument (no model fitting). Only if X2's screen beats the
matched-mass random control AND shows positive six-fold signal does it earn a
full paired six-fold run. R1 (Section 2) is this session's submission-track
work; the slate items are research-track and spend no submission slot.

## 4. Data and provenance status (checked this session)

- 10/10 hash-pinned inputs restored and sha256-verified via
  `scripts/restore_data.py` (GitHub-blob mirrors; provenance owner-supplied,
  NOT organizer-authenticated; `data/restore_receipt.json`).
- `training_features.tif` 418,912,844 B, sha256
  4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5.
- No DrivenData credential used; no leaderboard scraping (Terms of Use).
- Official metric source of record: DrivenData problem page 967 (alpha=0.2,
  beta=0.8, R=300 m triangular kernel), transcribed in `src/gems51/metric.py`.

## 5. Irregularities carried forward (unchanged)

- GEMSDOE32's `0.2778` is user-reported; the GEMSDOE32 owner pages label the
  artifact UNSCORED with a projected 0.2747. Both numbers are treated as
  owner/user claims, never organizer facts (`knowledge/gemsdoe32-case-study-2026-10-07.md`).
- The `0.3195` leaderboard high is user-stated and cannot be verified from this
  sandbox (no DrivenData access; no standings copying permitted).
- The local six-fold proxy truth is the visible catalogue; it cannot measure
  discovery of genuinely new fault styles. All local numbers are PROXY.

## 6. Amendment A1 — instrument anchor (written mid-run, after folds 0–1 only)

**Trigger (facts observed so far):** the pre-registered instrument check
("base reproduces evidence/hh_blend_holdout.json per fold within 1e-5") cannot
hold because the archived field files that produced those numbers were kept in
`data/prepared/`, which is gitignored and was never committed; fields must be
refit. Fold 0 of this run's `base` variant reproduces
`evidence/p1_holdout_20261007.json` `baseline_ungated` fold 0 to all 15 printed
digits (0.283432055411166), and the 2026-10-07 two-stage refit's fold-0 H-D
value matches today's refit to the last digit as well. The P1 session itself
recorded `baseline_reproduced: false` and `baseline_drift: -2.5447786610344192e-05`
against the archived blend mean — the archived blend fold-0 value
(0.28358474213082796) is stale relative to every later measurement, while
archived folds 1–5 already agree with the rebuilt pipeline exactly.

**Amendment:** rule (1) is replaced by:

  1'. **Instrument check** — the `base` variant reproduces
      `evidence/p1_holdout_20261007.json` `rows[*].scores.baseline_ungated.dti`
      per fold within 1e-5. (Same procedure: 0.5 H-D + 0.5 H-H blend, STE L9 /
      w_cont 0.35 / spacing 2.4, exclusion 2.0 px, ratio 3.47, rebuilt
      pipeline state.) The archived frozen-best values are reported alongside as
      continuity information only.

Rules (2)–(4) are unchanged. This amendment was written after folds 0–1 were
observed (fold 0: all variants tied, moved=0; fold 1: restrict −0.0073,
relocate −0.0079, moved=285) and before folds 2–5 exist, so it cannot be an
adaptation to the final result.

## Post-freeze source clarification — leaderboard claim

The statement in Section 5 records the source-access understanding at preregistration time. A
subsequent one-time read of the official leaderboard contradicted the user-supplied claim that
`0.3195` was then the current high. Treat `0.3195` as stale, not current. No leaderboard rows or
replacement values were copied into this repository, and the project's link-only/no-automatic-
monitoring policy remains in force. This source clarification does not change the R1 protocol,
holdout, or any score attribution.
