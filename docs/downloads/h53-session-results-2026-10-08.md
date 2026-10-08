# H53 session results — 2026-10-08 (R1 regeneration + X5 screen)

**Status: R1 NOT_PROMOTED under its frozen preregistered rule. X5 REJECTED by its
frozen screen rule. The session artifact is RESEARCH ONLY / DO NOT SUBMIT.**

## 1. R1 six-fold paired holdout (`evidence/r1_holdout_20261008.json`)

Instrument: six contiguous 3×3 spatial folds, 12 px training buffer, visible
known-fault proxy truth, emission + scoring restricted to the held-out block,
matched mass M/|G| = 3.47. Fields refit identically to `run_experiments.py`
(rng 1000+fold, neg 250,000, HGB 250 iterations, seed=fold).

| fold | base (=P1 anchor) | restrict | relocate | moved (relocate) |
|---|---|---|---|---|
| 0 | 0.2834321 | 0.2834321 | 0.2834321 | 0 |
| 1 | 0.2717839 | 0.2644986 | 0.2638512 | 285 (mean 28.5 px) |
| 2 | 0.2902703 | 0.2891191 | 0.2886602 | 177 (mean 8.7 px) |
| 3 | 0.2433593 | 0.2433593 | 0.2433593 | 0 |
| 4 | 0.3050492 | 0.3050492 | 0.3050492 | 0 |
| 5 | 0.3179963 | 0.3179963 | 0.3179963 | 0 |
| **mean** | **0.2853152** | **0.2839091** | **0.2837247** | — |

- Instrument check (Amendment A1): `base` reproduces
  `evidence/p1_holdout_20261007.json` `baseline_ungated` with max deviation
  **0.0 on all six folds**. The archived frozen-best 0.2853406 is 2.5e-5 above
  the rebuilt-pipeline base (stale archived fold-0 fields; documented in the
  preregistration amendment).
- restrict: mean Δ = **−0.0014061**, 0/6 folds won, 100 % inside approved tiles.
- relocate: mean Δ = **−0.0015905**, 0/6 folds won, 100 % inside.
- Uniform-tiles dominance control: confined mean 0.2839091 vs uniform fill
  0.1880090 (excess +0.0959 ≥ margin 0.002) — the fine model, not the tiles,
  does the work; Stage 1 does not dominate.
- **Verdict: NOT_PROMOTED.** Rule (2) requires mean Δ ≥ 0; the confinement cost
  is real on the proxy. The artifact is therefore RESEARCH ONLY / DO NOT SUBMIT.

### Findings

1. **Confinement is free on 4/6 folds.** The unrestricted STE emission already
   falls 100 % inside the fold-specific q10 domain on folds 0, 3, 4, 5. The cost
   concentrates on folds 1–2, where 177–285 dots (0.5–0.8 %) sit inside
   disapproved 10 km tiles.
2. **Nearest-cell relocation is credit-destructive at tile scale.** Disapproved
   regions are whole 10 km tiles, so relocated dots travel up to tens of pixels
   (fold-1 mean 28.5 px), far beyond the 3 px DTI kernel — their credit is
   destroyed. Relocate is uniformly no better than restrict; restrict is simpler
   and marginally better.
3. **The fold-specific q10 mask protocol matters.** The P1 10-07 harness (which
   removed held-out trace rows from the budget) measured only −0.00042 mean
   gating cost; this session's `fold.known` protocol measures −0.00141. Both are
   leakage-safe; the difference is mask construction. The artifact's actual
   (full-catalogue) mask is a third variant; holdout cost estimates for
   confinement carry this protocol uncertainty.
4. **The archived frozen-best is not reproducible** (fields gitignored). The
   rebuilt-pipeline base (0.2853152) is the current anchor and reproduces
   bit-exactly across sessions.

## 2. X5 off-catalogue screen (`evidence/x5_screen_20261008.json`)

H53-X5 (rank-1 new hypothesis): radiometric K/Th alteration concordance on
magnetic lineaments, off-catalogue. Screened on the S (SGMC-off-catalogue) and
L (lidar-crest-off-catalogue) instruments at matched 12,691 top-ranked pixels
plus a mass-44,090 probe and a 5-trial random control.

| layer | S (top-12,691) | L |
|---|---|---|
| x5 fusion (K/Th × tmi_s15_lin) | 0.0114 | 0.0039 |
| K/Th only | 0.0019 | 0.0012 |
| tmi_s15_lin only | 0.0141 | 0.0242 |
| random control (mean ± sd) | 0.0281 ± 0.0004 | — |

**Decision: REJECTED.** The fusion is far below the random control (let alone
the preregistered bar of random+3σ and best-single+0.005). Radiochemistry at
100 m adds no off-catalogue signal over the magnetic lineament layer in this
instrument. (Caveat recorded as IR-R1-03: top-n tie expansion makes historical
S values mass-inflated; the strict-mass comparison here is the fairer one, and
the rejection is decisive either way.)

## 3. Deliverables written this session

- `scripts/run_r1_holdout.py` (+5 unit tests for the relocate operator)
- `scripts/build_submission_r1.py` (fail-closed builder; `reverify_promotion`
  re-derives the rule from raw per-fold numbers)
- `scripts/recheck_r1_instrument.py` (Amendment A1 recompute)
- `scripts/screen_x5.py`
- `knowledge/preregistration-2026-10-08.md` (+Amendment A1)
- RESEARCH-ONLY artifact `gemsdoe51-r1-restrict-*-research-only.tif` (unique
  geometry; all-finite [0,1]; zeros outside; uniqueness gate PASS recorded in
  its checks JSON) — **DO NOT SUBMIT**
- Site: front-page status card driven by `ok_to_download_and_submit`
- Registry: hypotheses H53-X5/X6/X4; irregularities IR-R1-01..03
- README: session log + 2026-10-08 standing prompt appendix

## 4. Next-session priorities (ranked)

1. **Confinement without cost**: the fold evidence says only 0.5–0.8 % of dots
   are problematic. A *tile-level budget repair* — re-emit only the disapproved
   dots by continuing the STE greedy search on the approved domain with the
   occupied mask kept — is the natural operator and should recover nearly all of
   the −0.0014. Preregister it as R2 before running.
2. **Full-map q10 audit**: measure directly how many of the full-footprint
   STE dots sit outside the full-catalogue q10 mask (the artifact-relevant
   mask), instead of inferring from fold protocols.
3. **X2 (paired scarp-face asymmetry)** remains the top untested geological
   candidate; it needs a concrete operator definition on the max-aggregated
   lidar bands before screening.
4. **X4 is blocked**: mirror USGS Siler DOI 10.5066/P9YL58W6 via the owner
   GitHub bridge (sha256-pinned) before any stress-corridor work.
5. Portal acceptance remains unverified for every artifact; the first upload of
   a zeros-outside file should record the portal response verbatim.
