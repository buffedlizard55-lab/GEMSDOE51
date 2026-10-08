# H53 session results — 2026-10-08

Top-candidate validation of the preregistered H53 slate, the H53-F operating-point
sweep, and the unique two-stage submission TIFF. Everything below is measured;
receipts are JSON under `evidence/`, provenance under `registry/`.

## 1. What was asked

The standing brief (README, 2026-10-08 intake) requires, highest urgency first: a
**unique TIF submission** for DrivenData #306 that is never a copy/relabel of a
previous submission, with the site making it obvious whether the file is OK to
download and submit, an easy one-click download, a unique submission name and a
short portal comment; the two-stage method exactly as briefed (Stage 1 = geodetic
strain-budget deficit as a coarse first stage via Kreemer et al. 2000 Eq. 3;
Stage 2 = separately holdout-scored fine-scale model placing points ONLY inside
approved tiles); both stages' holdouts reported separately; the GeoTIFF
normalized and written; the uniqueness gate run; the submission confirmed not
dominated by Stage 1's footprint; 3–5 new candidate geological hypotheses ranked
and the top one validated on the spatially-blocked holdout BEFORE spending a
weekly slot; the prior portal error "Predicted values must be in range [0, 1]"
fixed by all-finite [0,1] encoding; a clean executive-summary subpage explaining
exactly how to submit; multi-pass verification; a PR merged onto main.

## 2. Harness fidelity (prerequisite for trusting any number)

- Environment rebuilt from scratch (restore → prepare → stack → extras → gate refs).
- `run_experiments.py --arm H_D --ratios 3.47 --save-fields` and `--arm H_H ...`
  regenerated all 12 fold fields; the archived arm holdouts regenerate
  **bit-for-bit** (`data/holdout_H_D.json`, `data/holdout_H_H.json`).
- The H53 holdout's fresh ungated H-H/H-D 50/50 blend + STE baseline reproduces
  the frozen receipt `evidence/hh_blend_holdout.json` **exactly**: fresh vs
  frozen mean deviation **0.0**, max per-fold deviation **0.0**
  (`evidence/h53_holdout_20261008.json`, `baseline` block).
- The H53 holdout was run twice end-to-end; the two COMPLETE receipts are
  **identical** in rows, gates, baseline, candidate_result and h53f blocks
  (determinism check; the second run adds the uniform-control block).

## 3. H53-A top-candidate validation (preregistered, frozen rule)

H53-A: six fine-scale geodetic strain-residual ridge features — rank-space
residual q(observed 2.5 km tile mean) − q(fault tensor II, Kreemer Eq. 3) for
`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, upsampled from 10 km tiles,
smoothed σ=4 px, crest response at σ=1.5/4.0 px (`src/gems51/strain_residual.py`).
Added to the H-H arm, blended 50/50 with freshly fitted H-D.

Instrument: frozen six-fold 3×3 spatial holdout, 12 px buffer, 250,000 negatives
(seed 1000+fold), HGB 250 iterations (seed=fold.index), STE L9 / w=0.35 /
spacing 2.4, ratio 3.47, flank 2.0 px, predictions confined to the fold-specific
q10 strain prior; held-out trace rows removed from the Stage-1 budget inputs.

| fold | fresh baseline ungated | fresh baseline q10 | H53-A ungated | H53-A q10 | Δ (gated) |
|---|---|---|---|---|---|
| 0 | 0.283585 | 0.283585 | 0.288365 | 0.288365 | +0.004781 |
| 1 | 0.271784 | 0.270436 | 0.270824 | 0.270015 | −0.000422 |
| 2 | 0.290270 | 0.289119 | 0.291052 | 0.289477 | +0.000358 |
| 3 | 0.243359 | 0.243359 | 0.248813 | 0.248813 | +0.005453 |
| 4 | 0.305049 | 0.305049 | 0.303585 | 0.303585 | −0.001464 |
| 5 | 0.317996 | 0.317996 | 0.303752 | 0.303752 | −0.014244 |
| **mean** | **0.285341** | **0.284924** | **0.284399** | **0.284001** | **−0.000923** |

Frozen best (ungated, not uploadable): **0.285340602656319**.

**Verdict: NOT PROMOTED.** The preregistered rule required the q10-gated mean to
beat the frozen best, a positive paired delta, and ≥4/6 folds; H53-A met none of
the three (0.284001 < 0.285341; Δ −0.000923; 3/6 folds). No H53-feature TIFF was
built. The hypothesis is falsified on this instrument — the fine-scale
strain-residual ridge does not add placement skill over the H-H/H-D blend once
confined to the q10 domain. (H53-B..E remain untested proposals; the slate
document ranks them for a future session.)

## 4. H53-F emission operating-point sweep (cached fields, no retraining)

| arm (ratio × flank) | mean q10-gated proxy DTI |
|---|---|
| 3.47 × 2.00 (default) | **0.284924** |
| 3.47 × 2.24 | 0.284655 |
| 2.96 × 2.00 | 0.283175 |
| 2.96 × 2.24 | 0.282942 |

Adoption rule (frozen): a non-default point is adopted only if it beats the
default by ≥ +0.0020 with ≥4/6 folds. No arm met the bar → **build at ratio 3.47,
flank 2.0 px = 44,069 dots** (the same operating point as the frozen best).

## 5. Stage-2 dominance control (is Stage 1 doing the work?)

Uniform random fills of the same approved tiles at the same mass, per fold:

| control | mean proxy DTI |
|---|---|
| uniform fill inside q10 approved tiles (U_q10) | 0.186956 |
| uniform fill over the whole held-out block (U_block) | 0.186150 |
| built geometry (fresh q10-gated baseline) | **0.284924** |

Excess over the uniform fill of the same tiles: **+0.097968** (margin 0.0020 →
PASS). The fine-scale model places dots by its own criteria; the Stage-1 tiles
are an allowed domain, not the placement signal. Stage-1 lift over the approved
area share is 1.110 (100% inside; area share 90.13%), well under the 1.5 limit.

## 6. The submission artifact

`scripts/build_submission_h53.py` (fail-closed: `require_h53_gate()` refuses to
build without a COMPLETE H53 receipt, exact baseline reproduction, Stage-1
non-dominance, the uniform-fill dominance control, and a recorded H53-F
decision).

- **Stage 1 (coarse, allowed domain only, score weight 0.0):** rank-space
  geodetic second-invariant deficit over 10 km tiles. Fault tensor II from the
  INGENIOUS Qfaults traces via the documented Kostrov/Kreemer et al. (2000) Eq. 3
  moment-tensor summation (slip rate × trace length → equivalent tile strain
  rate; `rate_convention="vertical"`, `assume_unknown_normal=True`);
  UCERF3 Field et al. 2014 (doi:10.1785/0120130164) is the precedent for
  subtracting a fault-model tensor from an observed geodetic field. q10 →
  approved domain = **90.09%** of the footprint (4,650,772 px).
- **Stage 2 (fine-scale, separately holdout-scored):** fresh full-data H-D
  (seed 53) + H-H (seed 54) belief fields, 50/50 blend, STE L9 / w=0.35 /
  spacing 2.4 emission, catalogue flank 2.0 px (200 m), **44,069 unit dots,
  100% inside the approved tiles**.
- **Encoding (portal range fix):** one float32 band, EPSG:32611, 3730×3292,
  exact template transform, **all 12,279,160 cells finite in [0,1]** (binary
  {0,1}), zeros in all 7,111,787 outside-footprint cells, **no NoData tag**.
- **Uniqueness:** pre-write support gate PASS (max Jaccard **0.2140** ≤ 0.50,
  max containment **0.3526** ≤ 0.60, 42 local priors incl. 21 pinned family
  references); staged post-write gate PASS on the final bytes; no byte
  duplicate of any held prior. New seeds → new support; not a copy/relabel.
- **Geometry audit:** 44,069 dots; nn spacing median 7.81 px (p10 3.16, p90
  19.12); distance-to-catalogue median 4.47 px (p10 2.24, p90 14.42); 0 px on
  the published catalogue; Stage-2 top-decile share 0.9973.
- **Files:** `docs/downloads/gemsdoe51-h53-twostage-20261008T040951Z-9a0b32c871.tif`
  (+ single-TIFF ZIP + checks JSON). SHA256
  `5823def4fab491ac6bd667cedb467c0540fd1bbce1351992289f4a609e7b775e`.
  Submission name `GEMSDOE51-H53-TWOSTAGE-20261008T040951Z`.
- **Manifest:** `recommended_upload_candidate` = the new record;
  `submission_readiness` = LOCAL_GATES_PASSED_NOT_PORTAL_TESTED, upload_ok=true;
  the archived H-H/H-D blend stays as the demoted, audit-only primary
  (NOT CLEARED FOR UPLOAD).

### Honest accounting vs the frozen best

The artifact regenerates the holdout-promoted procedure under the brief's
constraints. Its fresh q10-gated holdout mean is **0.284924** vs the frozen
UNGATED best **0.285341** — a measured compliance cost of **−0.000416** mean
proxy DTI for 100% q10 confinement. The frozen best is itself not uploadable
(86.71% of its dots inside q10; NaN-outside encoding). The H53-A hypothesis
numbers (0.284001, Δ −0.000923, 3/6) are reported separately and were not used
to build the file.

## 7. Site and verification

- `scripts/build_site.py` regenerated; `scripts/check_site.py` **PASS** (13
  pages, links resolve, download state matches the manifest).
- `scripts/latest_report.py` renders the H53 experiment (P1 research card
  retained); `docs/hypotheses.html` carries the H53 slate table with outcomes;
  `docs/how-to-submit.html` gives the exact five-step submission procedure and
  the generative-AI narrative draft.
- Independent byte-level verification: `scripts/check_submission.py` PASS;
  explicit full-grid scan: 0 non-finite cells, 0 cells outside [0,1], binary
  values, 7,111,787 outside-footprint zeros, no NoData; ZIP member byte-identical
  to the disk TIFF; disk/zip/manifest SHA-256 all equal.
- `tests/test_strain_residual.py` 5/5; full `pytest -q` green (see CI).

## 8. Irregularities flagged this session

- **IR-H53-01** — H53-A not promoted; no H53-feature TIFF built (falsified on
  the frozen instrument; slate outcome recorded).
- **IR-H53-02** — transcription error caught in `scripts/run_h53_holdout.py`
  before the run: the Stage-1 trace-holdout uniform DTI constant had two digits
  transposed (…2682… vs the correct …2658…, from
  `evidence/stage1_q10_trace_holdout_20261007.json`). Fixed; the receipt carries
  the verified value.
- **IR-H53-03** — build-script assembly crashed three times on missing names
  (`folds_won`, `FROZEN_BEST`, renamed `paired_holdout` keys) after the TIFF was
  already staged; each crash left an orphaned artifact pair that was removed
  before the clean final build. The final build is a single clean cycle; the
  TIFF bytes are identical across cycles (deterministic; same SHA-256).
- **IR-H53-04** — the frozen local best remains non-uploadable (86.71% q10
  inside; NaN-outside) and is now demoted to audit-only; the site says so
  explicitly. The portal range error is addressed by encoding in the new
  candidate, but **no GEMSDOE51 artifact has been portal-validated** — the
  triggering file of the original error remains unidentified.

## 9. Remaining work and limitations

- The proxy truth is the visible catalogue, not the hidden expert labels; all
  holdout numbers are local proxies, not organizer scores.
- H53-B..E are untested proposals; the slate document ranks them.
- The planning |G| = 12,700 hidden-truth estimate and the 3.47 mass ratio are
  estimates; H53-F showed the neighborhood is flat (±0.0018 over the swept
  points), so the operating point is not a sensitive lever.
- Beating the user-reported leaderboard high 0.3195 needs ~+35% placement
  quality at the same mass (see `knowledge/03_why_the_dotted_family_wins_2026-10-07.md`);
  the levers ranked there (mass/thinness, catalogue-band deletion, independent
  physical detector placement, |G| calibration) remain the research agenda.
- The entrant must still upload manually; the portal's weekly slot is the
  entrant's decision. Record the organizer's response either way.
