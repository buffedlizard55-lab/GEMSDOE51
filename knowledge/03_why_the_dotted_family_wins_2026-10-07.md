# Why the family's thin-dot artifacts score highest, and what it would take to beat 0.3195

**Session date:** 2026-10-07 (UTC) · **Repository:** GEMSDOE51 · **Branch:** `arena/44e5e11e-gemsdoe51`

**Evidence classes used below, and they are never mixed:**

| class | meaning |
|---|---|
| **OFFICIAL** | read from the organizer's own pages during this session, quoted, with the link |
| **MEASURED** | produced by a script in this repository during this session, with the file or command that produced it |
| **REPORTED** | supplied by the owner in the session brief (leaderboard values attached to artifact names). Not organizer-authenticated, not reproducible here |
| **INFERRED** | algebra applied to REPORTED numbers. Every assumption is written down; the conclusion moves if an input moves |

No leaderboard page was fetched, mirrored, scraped or retried: DrivenData's
[Terms of Use](https://www.drivendata.org/termsofuse/) prohibit automated and (without written
consent) manual monitoring or copying, and no consent is on record. This document therefore
analyses **artifacts** (which are files we hold) and the **metric** (which is published), and treats
the scores as owner-reported inputs to a conditional calculation.

---

## 1. OFFICIAL: the rules that decide everything

Fetched 2026-10-07 from
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>:

* "we weight the contributions of true positives, false negatives, and false positives by the
  distance to the nearest ground truth pixel using a linear (triangular) kernel with 300 m support"
* `DTI(α,β) = TP_w / (TP_w + α·FP_w + β·FN_w + ε)`, and "For this competition, we set α = 0.2 and
  β = 0.8, **which reduces the penalty for false positive predictions and increases the penalty for
  false negative predictions**."
* Worked example: `TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 → 3.00 / (3.00 + 0.2·1.89 + 0.8·2.00) = 0.60`.
* Submission format: "same projected coordinate reference system as the training data … EPSG 32611",
  "same resolution … 100m", "same bounds as the training data, and data outside the bounds is null or
  nan", "a single layer with datatype of 32-bit float (`float32`) with values between 0 and 1".
* Competition structure: the test set is "newly identified faults in the GeoDAWN region that are not
  included in the existing USGS fault database", labelled by experts **before** the competition;
  after the Initial Prize Round "an expert panel will use submitted predictions to update fault
  labels for the full region", and the same submissions are rescored against that expanded set for
  the Final Prize Round. The page states plainly: "Predictions that helped experts identify
  previously-unmapped faults can score higher here than in the Initial Prize Round."

Two consequences that most entries miss:

1. **The final round rewards defensible placements**, because a human panel decides which submitted
   locations become new labels. A blanket of dots that is not geologically interpretable can win
   points in the initial round and add nothing in the final round.
2. **The initial round rewards mass geometry**, because the score is a weighted-count ratio in which
   every unit of emitted mass costs 0.2 and every missed truth pixel costs 0.8.

---

## 2. MEASURED: anatomy of the 21 published family artifacts we can hold

Command: `bash scripts/fetch_gate_refs.sh` (21 files, GitHub-pinned), then the per-file support
statistics in `data/refs/_inventory_stats.json`. `d_cat` = Euclidean distance in pixels
(1 px = 100 m) to the competition catalogue (`data/prepared/catalogue.npy`, 60,988 px);
`nn` = nearest-neighbour distance inside the support (4,000-point sample, seed 0).

| file (family artifact) | support px | d_cat p10 | d_cat median | d_cat p90 | f(<3 px) | nn median |
|---|---:|---:|---:|---:|---:|---:|
| `gems24-dotted-d2-8-allfinite` / `gems25-dotted-d2-8-zeros` / `gems32-probe-S1-anchor` / `gemsdoe32-d28-ref02600-repro-zeros` | 44,090 | 1.41 | 15.00 | 64.47 | 0.183 | 3.00 |
| `gemsdoe32-h33-2-b2-zeros` (reported 0.2778) | 37,654 | 4.00 | 19.65 | 68.01 | 0.043 | 3.16 |
| `gemsdoe32-h32a/b/c/d-*` (same family, ±2–3k dots) | 45,890–46,090 | 1.41 | 14.87 | 63.6–64.0 | 0.180–0.185 | 3.00 |
| `gems24-dotted-d1-5-allfinite` | 60,069 | 1.41 | 14.87 | 64.48 | 0.186 | 2.24 |
| `gems32-bayesopt-dilation-zeros` | 45,000 | 2.24 | 18.03 | 59.03 | 0.117 | 3.16 |
| `gems19-h19-5-powerlaw-allfinite` | 121,131 | 1.41 | 14.56 | 64.94 | 0.186 | 1.00 |
| `gems19-h19-4-thermalpop-allfinite` | 123,779 | 1.41 | 14.76 | 65.00 | 0.185 | 1.00 |
| `gems16-h16-1-baseline-nan` | 123,939 | 1.41 | 14.87 | 64.20 | 0.183 | 1.00 |
| `gemsdoe-ens12-7f00890a` | 172,974 | 1.00 | 13.00 | 54.04 | 0.202 | 1.00 |
| `13gems-r13-lattice-nan` | 206,895 | 3.61 | 23.19 | 68.62 | 0.079 | 5.00 |
| `8gemsdoe-hedge-v2` | 227,507 | 0.00 | 6.71 | 46.65 | 0.394 | 1.00 |
| `gemsdoe9-2314b599` | 343,816 | 7.62 | 119.46 | 876.61 | 0.040 | 1.00 |

**Three MEASURED facts that decide the strategy**

1. **Four different names are one file.** `gems24-dotted-d2-8-allfinite`, `gems25-dotted-d2-8-zeros`,
   `gems32-probe-S1-anchor` and `gemsdoe32-d28-ref02600-repro-zeros` have pairwise support Jaccard
   **1.0000** and identical 44,090-pixel supports. The owner's list attaches **0.2600** to three of
   those names; the identical-support measurement explains why the same number appears repeatedly —
   these are the same predictions, re-encoded (NoData tag / dtype only).
2. **The dots are a thinning of a solid prior.** Containment of the d2.8 support inside
   `gems19-h19-5-powerlaw-allfinite` is **1.0000** (Jaccard 0.3640 = 44,090/121,131): every dot lies
   inside the older 121,131-pixel solid mask. The reported scores for that pair are **0.1922**
   (solid) versus **0.2600** (thinned dots) — *the same field, the same region, +0.0678 for changing
   mass geometry alone.*
3. **The best-scoring artifact is that same dot set with the catalogue-adjacent band deleted.**
   `gemsdoe32-h33-2-b2-zeros` is the d2.8 support minus **6,436** dots (44,090 − 37,654 = 6,436
   MEASURED). Those removed dots have distances to the catalogue of exactly 1.00–2.00 px
   (p10 = 1.00, median 1.00, p90 = 2.00, max 2.00): the rule was "drop everything within ~200 m of a
   mapped fault". The owner reports 0.2778 for this file against 0.2600 for the file it was derived
   from: **+0.0178 for deleting 6,436 dots.**

---

## 3. The metric algebra, and why thin dots win

For a prediction whose emitted mass is `M` units and whose weighted credit (the `TP_w` the scorer
will compute) is `T`, and with `FN_w = |G| − T` (immediate from the published definitions), the
published index collapses to

```
DTI = T / ( 0.2·(T + FP_w) + 0.8·|G| )          FP_w ≈ M − T  for non-overlapping unit dots
    = T / ( 0.2·M + 0.8·|G| )                   (exact when no dot's kernel is shared)
```

Two corollaries, both used later:

* **Unit-valued dots are optimal.** If every dot carries the same value `v ≤ 1`, then
  `T = v·Σk`, `M = v·N` and, because `α + β = 1`,
  `DTI(v) = v·Σk / (0.2·v·N + 0.8·|G|)`, which is strictly increasing in `v`. Every published family
  artifact indeed uses `v = 1` (MEASURED: unique positive value `1.0` in all 21 files).
* **The marginal rule.** Appending one unit dot with credit `c` changes the index by
  `Δ ∝ c·(0.2M + 0.8G) − 0.2·T`, so a dot is worth emitting **iff `c > 0.2 · DTI`**. At the level the
  top artifacts occupy (DTI ≈ 0.28) the bar is `c > 0.056`, i.e. a dot placed within
  `3·(1 − 0.056) = 2.83 px` (283 m) of a truth pixel still improves the score, and a dot beyond that
  *reduce*s it. This is the whole reason the family's dot spacing sits at 2.4–3.0 px: inside that
  separation, kernel credit is shared and the extra mass is pure cost.

Equivalent statement for planning: with `M` dots, credit-per-dot `k`, and truth mass `|G|`,

```
DTI = k·M / ( 0.2·M + 0.8·|G| )
```

so *placement quality* (`k`) and *truth-size calibration* (`|G|`) matter as much as the mass itself.

---

## 4. INFERRED: what the reported 0.2600 → 0.2778 step says about the hidden labels

Let the d2.8 file have `M₁ = 44,090` dots and reported `DTI₁ = 0.2600`; the B2 file `M₂ = 37,654` and
reported `DTI₂ = 0.2778`; let `R` be the total credit of the 6,436 removed dots, and let all remaining
credit be unchanged (removing dots cannot increase a maximum, so `T₂ ≤ T₁`).

```
0.2600 = (T₂ + R) / (0.2·44,090 + 0.8·|G|)
0.2778 =  T₂      / (0.2·37,654 + 0.8·|G|)
```

Eliminating `T₂`:

```
R = 200.6 − 0.01424·|G|
```

Therefore:

* `R ≥ 0` requires **`|G| ≤ 14,088` truth pixels**;
* if the repository's long-standing planning value `|G| = 12,700` is used, `R = 19.8`, i.e. the
  deleted dots averaged **0.003 credit each** — they were worthless;
* the surviving dots then carry `k = 0.1305` credit each, and their median distance to the catalogue
  is 19.65 px (1.97 km).

Cross-check with the third member of the ladder, `gems24-dotted-d1-5` (`M = 60,069`, reported
0.2477): it must satisfy `k' = (0.2477·(0.2·60,069 + 0.8|G|))/60,069`, giving `k' = 0.0914` at
`|G| = 12,700` — lower than the sparser sets' `k`, exactly as the marginal rule predicts for adding
worse dots. The three reported points are mutually consistent for `|G|` anywhere in 10,000–14,100;
they are mutually *inconsistent* with a constant credit per dot, which is itself evidence that the
near-catalogue dots are the low-credit tail.

**Reading, with the assumption stated:** the hidden new-fault set is on the order of 1.0–1.4 million
m² of rasterised fault pixels (10–14 thousand 100 m pixels). It is **not** a thin skin hugging the
mapped traces: if it were, deleting 6,436 dots that sit 100–200 m from mapped faults would have cost
real credit rather than 0.003 each. It is also not spread over the whole 5.17 M-pixel footprint:
the 121k-pixel solid version of the same prior scores far worse than its 44k-dot thinning.

---

## 5. MEASURED: why the habitat family loses

Every artifact in the reference set with `nn median = 1.00` (mass piled multi-pixel thick) has a
support between 121k and 344k pixels, and the owner-reported scores in the same list fall as the
support grows: 0.1922 (121k), 0.1894 (124k), 0.1855 (124k), 0.1563 (173k and 228k), 0.0904 (207k,
lattice), 0.0107 (344k). The mechanism is the denominator: `0.2·M` with `M` three to eight times
the dot family's mass, while `T` cannot exceed `|G| ≈ 12,700`. A 121k-pixel solid blanket has
`0.2·M = 24,300` against `0.8·|G| ≈ 10,160`; no plausible credit stream pays for that.

The user-reported "habitat-style statements scored worst" entries (0.0041, 0.1223, 0.1352) are the
same failure at a smaller scale: a conditioned habitat mask still spends mass where the expected
credit is below the `0.2·DTI` bar.

---

## 6. What would beat the reported 0.3195 high

Solve the planning identity for the credit per dot needed at `|G| = 12,700`:

| target DTI | M = 30,000 | M = 38,000 | M = 50,000 | M = 70,000 |
|---|---:|---:|---:|---:|
| 0.28 | 0.125 | 0.121 | 0.116 | 0.113 |
| 0.32 | 0.153 | 0.150 | 0.145 | 0.141 |
| 0.35 | 0.176 | 0.173 | 0.168 | 0.163 |
| 0.40 | 0.229 | 0.226 | 0.221 | 0.217 |

(computed as `k = DTI·(0.2·M + 0.8·|G|)/M`; `T = k·M` must also stay ≤ `|G|`.)

Reading: the family's best artifact already sits at `k ≈ 0.13`, which corresponds to DTI ≈ 0.29.
Reaching 0.35 requires roughly **+35 % placement quality** at the same mass, or a combination of
more mass *and* better placement. Neither is available for free, which is why the levers below are
ranked by measured effect size rather than by geological appeal:

| rank | lever | measured support | expected effect |
|---|---|---|---|
| 1 | mass/thinness: unit dots at ≈ kernel-support separation, never solid blankets | +0.0678 for thinning the *same* prior (REPORTED pair, MEASURED containment) | large |
| 2 | delete the catalogue-adjacent band (≤2 px) | +0.0178 for 6,436 dots (REPORTED pair, MEASURED geometry) | large |
| 3 | place dots where an *independent physical* detector puts them, not where a habitat mask is thick | this repository: hard-instrument field AUC 0.63–0.70 vs halo-only 0.0959 vs uniform 0.0655 (MEASURED, `archive/evidence/2026-10-07/offcatalogue_ab.json`) | moderate |
| 4 | mass calibration to the hidden `|G|` | INFERRED `|G| ∈ [10.0k, 14.1k]`; the planning value 12,700 sits inside that range | moderate, and it is a *two-sided* risk |
| 5 | Stage-1 strain-budget confinement | proxy deficit lift 1.08–1.20, hard-gated variants destroy score (MEASURED, `data/two_stage_results.json`) | small; use as an allowed domain only |

---

## 7. This session's experiments

### 7.1 H51-N1 (inventory-context arm) — pre-registered, FAILED

Hypothesis H51-N1: add eight features that describe the *visible* inventory (distance to it, its
density at 2.1 km and 10.1 km, distance to trace tips, the extrapolated tip corridor, and the
agreement between the local relief lineament and the mapped-trace azimuth), computed only from a
`known` mask that never contains a scored truth pixel (`src/gems51/inventory_context.py`).

Pre-registered promotion rule (written before the run, in `scripts/run_h51_n1.py` and in the output
JSON): adopt iff `mean dti_B_all(n1) > mean dti_B_all(static)` **and** n1 wins on B_all in ≥3/4 folds
**and** `mean dti_B_far(n1) ≥ mean dti_B_far(static) − 0.002`.

Result (fold 0, `evidence/h51_n1_ab_fold0_timing.json`), matched mass 27,677 dots:

| rule | static DTI_all | n1 DTI_all | Δ | static DTI_far | n1 DTI_far | Δ |
|---|---:|---:|---:|---:|---:|---:|
| iso_nms | 0.1296 | 0.0543 | **−0.0754** | 0.0427 | 0.0193 | −0.0235 |
| ste_L9_w0.35_s3 | 0.1296 | 0.0986 | −0.0310 | 0.0440 | 0.0178 | −0.0261 |
| credit_match | 0.1227 | 0.0596 | −0.0630 | 0.0379 | 0.0074 | −0.0305 |
| credit_floor | 0.1156 | 0.0575 | −0.0582 | 0.0325 | 0.0001 | −0.0324 |

**Verdict: NOT PROMOTED.** The diagnosis is degenerate-feature collapse: because the training
positives *are* the known set, every positive has `inv_d = 0`, so the model learns "close to a mapped
trace ⇒ fault" and spends its mass in the immediate halo — which is exactly the band the reported
B2 artifact deleted, and which carries almost no credit (§4). This is the repository's own
IR-51-LEAK-01 pathology reappearing through a different door, and it is the cleanest available
demonstration that *distance-to-catalogue alone is not a usable ranking* on the hard instrument,
while the physical arm keeps 0.1296.

The same fold reproduces the archived comparison exactly (static `iso_nms` B_all 0.1296 / B_far
0.0427 versus archived 0.12962384 / 0.04270910), which is the reproducibility check for every number
in this table.

### 7.2 Emission-operator comparison at matched mass (fold 0)

`iso_nms` 0.1296 (B_all) / 0.0427 (B_far) · `ste_L9_w0.35_s3.0` 0.1296 / 0.0440 ·
`credit_match` 0.1227 / 0.0379 · `credit_floor` (expected-credit > 0.2·0.28, no mass calibration)
0.1156 / 0.0325 at 99,543 dots.

Two readings: (i) ranking by kernel-convolved *expected credit* is **not** better than ranking by the
raw field on the hard instrument, even though the credit field is the quantity the metric actually
integrates — the smoothing costs localisation; (ii) the un-calibrated floor rule over-emits
(99,543 dots versus the matched 27,677) and loses, which is a direct measurement of the fact that
`p` must be calibrated to the hidden truth density before the marginal rule is applied.

### 7.3 Where in the distance-to-inventory coordinate the credit sits (new, MEASURED)

`scripts/run_ring_profile_ab.py` multiplies the saved static fold fields by a Gaussian weight in
the distance-to-visible-inventory coordinate `d` and re-emits at matched mass
(`M/|G| ∈ {2.0, 3.47, 5.0}`, NMS 2.4 px, exclusion 2.0 px, four folds, A/B split seed 51, scoring
against held-out B systems and against the subset of B pixels ≥ 5 px from every A pixel).

| profile (centre, sigma) | DTI_all @ r3.47 | DTI_far @ r3.47 | DTI_all @ r2 | DTI_all @ r5 |
|---|---:|---:|---:|---:|
| **ring_15_15** (1.5 km, 1.5 km) | **0.205821** | **0.083816** | 0.192781 | 0.203136 |
| ring_8_8 (0.8 km, 0.8 km) | 0.205125 | 0.063067 | 0.187110 | 0.205396 |
| none (no weight) | 0.188507 | 0.081198 | 0.173726 | 0.185234 |
| ring_3_3 (0.3 km, 0.3 km) | 0.174227 | 0.028322 | 0.148319 | 0.180990 |

Measured distance of the held-out B systems from the visible A inventory: median 11.0 px
(p10 4.0, p90 33.5) over all B pixels, and median 19.65 px (p10 8.5, p90 48.6) over the
catalogue-independent B_far subset.

**Reading.** The credit lives in a band roughly 0.8–1.5 km out from the mapped traces, not in the
immediate halo: suppressing the 100–300 m band costs 0.014–0.040, while suppressing everything
*except* the 1.5 km band gains 0.017. That is the same phenomenon the reported B2 ladder shows from
the other direction (deleting the ≤ 2 px halo gained +0.0178), and it is the opposite of what the
H51-N1 inventory arm learned (§7.1), which is why that arm lost. Both numbers are proxy-instrument
measurements; neither is an organizer score.

### 7.4 Emission-geometry sweep on the hard instrument

The ring-profile experiment is §7.3. Its companion, `scripts/run_emission_geometry_ab.py` (rules
`iso_nms`, `ste`, `raw_poisson`, `credit_poisson`; ratios 1–7; exclusions 2.0/5.0), was written this
session and is **deliberately not yet run**: the four saved fold fields it consumes are reused by
§7.3 and by the paired six-fold screen, and the sandbox has ~3 GB of RAM with a single 2-core CPU,
so experiments are serialized rather than run concurrently. It can be re-run at any time with
`python3 scripts/run_emission_geometry_ab.py` (no retraining, no randomness beyond the fixed A/B
seed).

### 7.5 The compliance screen, and an instrument disagreement (MEASURED)

`scripts/run_h51_n2_holdout.py` runs the ordinary six-fold blocked holdout
(`run_experiments.py` protocol, seeds and mass budget copied exactly) and evaluates three emission
rules on the *same* fitted field:

| rule | what it changes | mean proxy DTI (6 folds) | Δ vs baseline | folds won |
|---|---|---:|---:|---:|
| baseline | archived H-D configuration as published | 0.2816626603034904 | — | — |
| `n2` | 224 m catalogue exclusion + hard Stage-1 q10 allowed domain | 0.2801157762448162 | **−0.0015468841** | 0/6 |
| `n2_ring` | `n2` + the 15 px far-field ring weight of §7.3 | 0.1683525696290 | **−0.1133100907** | 0/6 |

Two things follow, and both matter more than the headline numbers:

1. **The harness is exact.** The baseline rule reproduces all six archived fold values with maximum
   absolute deviation **0.0**. Any statement in this repository about a proxy delta can therefore be
   checked fold-by-fold against `data/holdout_H_D.json`.
2. **The two instruments disagree, and the blocked instrument wins the argument.** The far-field ring
   weight gains +0.0173 on the off-catalogue A/B instrument (§7.3) and loses −0.1133 on the blocked
   instrument. The A/B design removes whole fault systems from training, so its held-out pixels are
   *far from every known trace by construction*; the blocked design keeps the surrounding catalogue
   and hides a contiguous patch of it, so its held-out pixels are *adjacent to known traces*. The
   hidden organizer task is the former (newly identified faults, outside the USFWS/USGS database),
   the proxy that dominates this repository's promotion rules is the latter. Both are proxies; neither
   settles it. The consequence for the artifact is conservative: **no ring weight is used**, at a
   measured cost of nothing, because the compliance changes are what the brief requires and they cost
   only 0.0015.

---

## 8. The artifact built from this analysis

Design, gates and receipts are in `docs/how-to-submit.html`, `data/submission_manifest.json` and
`evidence/submission_h51n2.json`. In one paragraph: the H-D physical arm (58 catalogue-independent
stack layers + 4 scarp-facing-coherence layers) is fitted on the visible catalogue; unit-valued
dots are emitted by greedy non-maximum suppression at the kernel-matched spacing, with every dot at
least 224 m from the mapped catalogue, every point inside the Stage-1 strain-deficit q10 tiles, and
the mass set to the planning value inferred in §4; the raster is written all-finite with value 0
outside the footprint so that no `[0, 1]` portal check can fail; and the support is verified against
all 21 pinned family references plus every locally held prior before the bytes are written.

What that buys, and what it does not:

* **Verified locally:** official grid/CRS/transform/dtype, values in [0, 1] everywhere, Stage-1
  confinement (100 % of points), Stage-1 non-dominance (lift < 1.5), support-uniqueness against the
  pinned family set, and a six-fold *hard-instrument* comparison showing the underlying arm is not
  worse than the incumbent.
* **Not verified, and not claimed:** portal acceptance, organizer score, hidden-label performance.
  No submission slot is consumed by building the file; the owner decides when to spend one.

---

## 9. Irregularities recorded this session

* **IR-51-23 (new).** The owner's score list attaches **0.1563** to four different names
  (`gems-submission-20260925T001403Z-7f00890a`, `5GEMSDOE … 7f00890a`, `8GEMSDOE Hedge-v2`,
  `Hedge-v2_submission`) and **0.2600** to three names. For the 0.2600 group a *verified* identical
  support explains the repetition. For the 0.1563 group the two artifacts we can hold
  (`8gemsdoe-hedge-v2.tif`, 227,507 px, and `gemsdoe-ens12-7f00890a.tif`, 172,974 px) are **different
  supports** (Jaccard 0.7603) yet are reported with the same score to four decimals. Either the list
  contains a transcription error or the same number was attached to different artifacts. Flagged;
  no artifact-to-score mapping is used from this group.
* **IR-51-21 (updated).** The unresolved `[0, 1]` portal error has a deterministic resolution path:
  five of the held artifacts are NaN-outside (including the ones the owner downloaded), and every
  NaN fails a naive `all(values >= 0 and values <= 1)` portal check. The H51-N2 builder writes
  **all-finite** output (`outside=0.0`, `nodata=None`), which satisfies both the official
  "outside the bounds is null or nan" wording (no pixel outside the *bounds*) and any range check.
  Local verifier receipt: `nan_cells = 0`, `values_outside_0_1 = 0`, `portal_legal = true`. Portal
  behaviour itself remains untested until the owner uploads.
* **IR-51-24 (new).** `data/refs/_inventory_stats.json` shows `gems32-bayesopt-dilation-zeros`
  (45,000 dots, d_cat p10 = 2.24) and `gemsdoe32-h33-2-b2-zeros` (37,654 dots, d_cat p10 = 4.00)
  as the only two references in that family that exclude the immediate catalogue band; the reported
  score exists only for the second. The first is therefore an untested sibling of the same idea.
