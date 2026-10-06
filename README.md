# GEMSDOE51 — DOE GEMS Prize, DrivenData #306 (GeoDAWN / NW Nevada)

**Competition:** [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
· **Problem definition — the metric, verbatim:** [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
· **Leaderboard:** [page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
· **Official rules (DOE/NLR, Sept 2026):** [docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
· **Published site:** <https://buffedlizard55-lab.github.io/GEMSDOE51/docs/>
· **Short URL:** <https://buffedlizard55-lab.github.io/GEMSDOE51/> (a root `index.html`
forwards to `docs/index.html`, because Pages is configured to publish the branch root)

This repository holds **two independent, unique builds** of a legal submission for that
competition. Their positive-pixel overlap is 1,091 px — **Jaccard 0.0034** — so they are
near-disjoint answers rather than a copy of one another; the brief's *"must be unique"* rule
is satisfied by construction and by measurement, not by assertion. §4b documents the build
whose download is listed first; §1–§4 and §7–§9 document the earlier build, retained in full.

---

## ⬇ DOWNLOAD A SUBMISSION FILE — deliberately the first thing on this page

|  | **PRIMARY — Build B (this session, canonical)** | **ALTERNATE — Build A (previous session)** |
| --- | --- | --- |
| **download the .tif** | **[docs/downloads/gemsdoe51-strainbudget-s1-v1.tif](docs/downloads/gemsdoe51-strainbudget-s1-v1.tif)** | **[submissions/gems51-sbd-hridge-44090-20261006.tif](submissions/gems51-sbd-hridge-44090-20261006.tif)** |
| download the .zip | [docs/downloads/gemsdoe51-strainbudget-s1-v1.zip](docs/downloads/gemsdoe51-strainbudget-s1-v1.zip) | — |
| **file name to paste into the form** | `gemsdoe51-strainbudget-s1-v1.tif` | `gems51-sbd-hridge-44090-20261006.tif` |
| **note field (copy-paste)** | `GEMSDOE51 Build B — two-stage: geodetic-strain gate (the brief's Kostrov/Kreemer deficit was computed, tested and is reported as REFUTED) + 44-channel spatially-blocked detector, sparse off-catalogue dots; all values finite in [0,1], no nodata tag; sha256 bdc04593…` | `GEMSDOE51 Build A — strain-budget deficit allow-region + unsteered Hessian-ridge emission; 227,642 emitting pixels; sha256 e527ac89…` |
| positive pixels | 95,927 (0.78 % of the grid; 3.78 % of the approved region) | 227,642 (1.85 % of the grid; includes the masked catalogue core) |
| format contract | **ALL CHECKS PASSED** — `python3 scripts/check_submission.py <file>` | **ALL CHECKS PASSED** — same script |
| sha256 | `bdc045934e4a2e33…` (full value in [evidence/submission_receipt.json](evidence/submission_receipt.json)) | `e527ac899dc0b6593b4b0db824a51678fad87111604e74845f5cd71990a1db55` |
| bytes | 390,791 | 753,085 |
| reproducibility | byte-for-byte from the hash-pinned inputs by `python3 scripts/run_all.py` (8 stages, 473 s; receipt [evidence/submission_receipt.json](evidence/submission_receipt.json)) | `scripts/run_pipeline.py` (receipt [evidence/submission_sbd-hridge-v1.json](evidence/submission_sbd-hridge-v1.json)) |
| organiser score | **NONE — this file has never been submitted.** Every number below is a local measurement. | **NONE — never submitted.** |

**How to submit — four steps.** 1. Download one (or both) of the files above.
2. Open the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
and choose *Submit*. 3. Upload the `.tif` **unchanged** — do not unzip, rescale or re-save it;
the format audit was run against exactly these bytes. 4. Paste the note text from the table.
The official spec on [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
requires a single band, `float32`, EPSG:32611, 100 m pixels, the same extent as the training
data, values in **[0, 1]**, and out-of-bounds cells null or nan. Both files satisfy it, and
neither writes a `nodata` tag: a large negative sentinel such as
`-3.4028234663852886e+38` is itself outside [0, 1] and is the documented cause of the portal
error *"Predicted values must be in range [0, 1]"*.

**Why ship two files?** They were built independently, they overlap by 0.34 % of their union,
and the local evidence cannot rank one above the other (see §4b and §9). If two submission
slots are available, submitting both strictly dominates submitting one: the metric is
evaluated per file, and near-disjoint answers cannot cannibalise each other.

---

# THE BRIEF, VERBATIM (re-read at the start of every session)

> Geodetic strain-budget deficit, used strictly as a coarse first stage. Hypothesis: where
> the geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the
> catalogue is likelier to be missing structures. Precedent for balancing geodetic and
> geologic deformation exists in the UCERF3 deformation models (Field et al., Bulletin of
> the Seismological Society of America 104(3), 1122–1180, 2014, doi:10.1785/0120130164).
> Three of those models invert geodetic and geologic data together, and UCERF3 also models
> off-fault strain explicitly. A related USGS-listed paper ("A fault-based model for crustal
> deformation, fault slip-rates and off-fault strain rate in California") estimates off-fault
> moment rates separately. Convert each mapped fault's slip rate (the INGENIOUS compilation
> is reported to hold slip rates; confirm in the shapefile attributes) and trace length into
> an equivalent tile strain rate using a documented moment-tensor summation. State the exact
> formula and cite its source, because I haven't verified one. Subtract that from the
> dilatation and shear strain-rate layers, and keep the residual only as a prior over broad
> tiles. Strain rates are coarse, and the deficit can be distributed off-fault, aseismic or
> caused by wrong catalogue slip rates. Habitat-style statements scored worst in this project
> (0.0041, 0.1223, 0.1352), so a second, separately holdout-scored fine-scale model must
> place points only inside approved tiles. Report both stages' holdout results separately.
> Normalize, write the GeoTIFF, run the uniqueness gate, and confirm the submission isn't
> dominated by stage one's footprint.
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
> SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.
>
> We need to focus on being able to generate a submission into the competition. The site
> should be able to generate a TIF file that is required for submission. It should be as
> easy as download to click a File to submit into the competition. This needs to be in the
> executive summary or the very beginning of the site; it should be obvious when you visit
> the site.
>
> Work line by line verifying from official verified trusted sources, provide links for
> manual review. There should be no manual input, work on your own to complete tasks. Flag
> any irregularities for review. No hallucinations. Verify no hallucinations.

### Our Core Values — kept central to every decision in this repository

**Maximize P(Win).** *"Maximize the Probability of Winning"* is the decision-making
framework. In every decision we weigh tradeoffs, assess risk, and choose the path that
maximises the probability of winning. We set aside emotions and make tough decisions.

**Own the Outcome.** We own results end to end. When problems arise and we have the means to
act, we do so. We treat failure and success as signals and use them to improve. We stay
accountable to the final outcome.

**Applied here, concretely.** *Maximize P(Win)* is why this repository **refuses to ship a
candidate its own holdout does not promote**, and why the one experiment that failed is
published rather than buried (`evidence/holdout_run.json`, promotion_pass = **false**).
*Own the Outcome* is why every number carries an evidence class and a link, and why the
two defects found in this session's own code (a stage-1 gate that silently approved 90 % of
tiles, and a uniqueness gate that overflowed float32) were measured, fixed, and written up
instead of quietly deleted.

---

## 1. What was actually built

| stage | what it is | result |
| --- | --- | --- |
| **Stage 1** | Geodetic **strain-budget deficit** on 32 px (3.2 km) tiles: the Kostrov/Kreemer moment-tensor sum over mapped fault length is subtracted from the supplied geodetic strain layers. The residual is an **allow-region only** — it contributes **zero mass** to the submission. | 5,121 usable of 12,051 tiles; 1,793 approved = **35.0 % of usable tiles = 35.5 % of the footprint** |
| **Stage 2** | **Unsteered Hessian-ridge** rank fusion over all 19 supplied bands, emitted as a sparse 3-px-suppressed dot set **only inside stage 1's approved tiles**, plus a free **catalogue core** fill and a 1-px **shell**. | detector screen mean **AUC 0.8229**, 4/4 folds above chance |
| **Gate** | Uniqueness vs 211 published reference artifacts. | **PASS**: 0 matches, worst IoU 0.268, worst cosine 0.716 |

### The exact formula, with its source, stated because the brief asks for it

Kostrov (1974) moment-tensor summation in the **fault-slip-rate** form, as published by
**Kreemer, Haines, Holt, Blewitt & Lavallee (2000), *Earth Planets Space* 52, equation (3)** —
[PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf):

```
eps_dot_ij = (1/2) * SUM_k [ (L_k * u_dot_k) / (A * sin(delta_k)) ] * m_ij^k
```

with `L_k` the fault-segment length inside the tile, `u_dot_k` its slip rate, `delta_k` its
dip, `A` the tile area, and `m_ij^k` the segment's unit moment tensor. The earthquake-catalogue
form is Kostrov (1974) itself, `eps_dot_ij = (1/(2 mu V T)) SUM_k M_ij^k` (Kreemer et al.
eq. 2). Implemented in `src/gems51/stage1_strain.py`, with a slip-rate/dip **sweep** that
reports how stable the approved-tile set is to those two free parameters.

### The precedent, verified

* **Field et al. (2014)**, BSSA 104(3) 1122–1180, [doi:10.1785/0120130164](https://doi.org/10.1785/0120130164)
  — confirmed from Crossref/ASU records: the abstract states *"three deformation models are
  based on kinematically consistent inversions of geodetic and geologic data"*. ✔ matches the brief.
* **USGS OFR 2013-1165 Appendix C**, [PDF](https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf)
  — *"Deformation models provide the strain rate tensor on a 0.1 degree by 0.1 degree grid
  covering all of California. This grid of strain rates account for all modeled deformation
  that is **not accommodated on the faults**."* This is the official precedent that the
  residual is a legitimate published quantity.
* **Zeng & Shen (2016)**, BSSA 106(2) 766–784, [doi:10.1785/0120140250](https://doi.org/10.1785/0120140250)
  ([USGS pub. 70160311](https://pubs.usgs.gov/publication/70160311)) — the paper the brief
  names. Measured from its abstract: off-fault moment rate **0.88e19 N·m/yr** against a total
  California moment rate of **2.76e19 N·m/yr**, i.e. an **off-fault fraction of 31.9 %**.
  This is used as the empirical ceiling on how much of a deficit may legitimately be
  off-fault rather than evidence of a missing structure.

---

## 2. THE TWO OFFICIAL FACTS THAT DECIDE THE WHOLE SUBMISSION

These are not inferences. They are statements by DrivenData staff, and they are the reason
the emission looks the way it does.

**Fact 1 — mapped-fault pixels are MASKED out of the penalty terms.**
[Forum thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516),
DrivenData staff `chrisk-dd`, 2026-09-16:

> *"Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from
> evaluation, so they do not count towards penalty terms."*
>
> *"Re-evaluation will also mask/exclude the existing USGS/INGENIOUS faults."*

Consequence: mass placed **on** a mapped fault costs nothing in `FP_w`, while it can still
deliver `k`-weighted credit to any hidden fault within 300 m. `gems51` therefore sets the
catalogue core to 1.0. This is the single largest free lever in the competition.

**Fact 2 — the sample submission IS the catalogue rasterised.**
Measured here by reading both files: `sample_submission.tif` has 60,988 non-zero pixels;
`existing_faults.tif` has 60,988 fault pixels; `np.array_equal(sample>0, catalogue)` is
**True**. The competition's own "predict total fault absence" template is, byte for byte,
the known-fault map. Under an *unmasked* metric that template would score ≈ 1.0 and the
competition would be broken. This is an independent, structural confirmation of Fact 1.

**Fact 3 — "new fault" includes new geometry of *existing* systems.**
[Forum thread 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536),
DrivenData staff, 2026-09-23:

> *"'new fault' means 'any fault pixel not already captured by USGS/INGENIOUS' and can
> include newly mapped geometry of an existing fault system."*

Consequence: continuations, splays, step-overs and parallel strands **count**. A thin shell
around the mapped traces is therefore a legitimate target, not a wasted guess.

---

## 3. Results — both stages reported separately, as the brief requires

### Stage 1 (coarse prior) — `evidence/` via `scripts/run_pipeline.py`

| quantity | value |
| --- | --- |
| tiles | 32 px (3.2 km); 117 × 103 = 12,051 total; **5,121 usable** |
| usable = tile has geodetic data AND ≥ 25 % valid pixels | 42.5 % of tiles — the other 57.5 % are outside the data footprint |
| approved tiles (top 35 % of usable by deficit) | **1,793 tiles = 1,832,000 px = 35.5 % of the footprint** |
| deficit range (standardised units) | −11.104 … +5.991, threshold 1.226 |
| **stage-1 mass contributed to the submission** | **0.0 — it is an allow-region, never a value** |
| stage-1 dominance gate | **PASS** — emitted mass 158,789 ≪ 0.5 × 1,832,000; the emission is a sparse point set (1.85 % of the footprint), not the tile footprint |

### Stage 2 (fine-scale emission), scored separately

**Instrument A — detector screen, all 19 bands, 4 folds** ([`evidence/detector_screen.json`](evidence/detector_screen.json)]

| field | mean AUC vs held-out traces | folds above chance |
| --- | ---: | ---: |
| **fusion of all 19 bands (shipped)** | **0.8229** | **4/4** |
| Detrended elevation slope (band 19) | 0.8161 | 4/4 |
| Isostatic gravity anomaly slope (band 5) | 0.7951 | 4/4 |
| Detrended elevation (band 12) | 0.7945 | 4/4 |
| Tilt angle / total curvature (band 6) | 0.7901 | 4/4 |
| Distance to earthquake (band 10) | 0.4791 | 2/4 — **anti-informative** |

**Instrument B — spatially blocked 4-quadrant holdout, official metric, whole-map emission**
([`evidence/holdout_run.json`](evidence/holdout_run.json)). All arms at **matched** 44,090-dot budget.

| contrast | mean ΔDTI | folds positive |
| --- | ---: | ---: |
| A1 Hessian-ridge **−** A0 core+shell only | **+0.01881** | **4/4** |
| A1 Hessian-ridge **−** A2 strike-STEERED | **+0.01126** | **4/4** |
| A1 Hessian-ridge **−** A4 ungated (no stage-1 prior) | **+0.00242** | **4/4** |
| A1 Hessian-ridge **−** A3 uniform random | **−0.01363** | 1/4 |

**Promotion verdict (rule frozen before the run): FAIL** — the preregistered rule required
beating the random control, and under this protocol it does not. That negative result is
published, not hidden. Its cause is diagnosed in §4 and tested by a second protocol.

**Instrument C — leave-one-trace-out with truth SPREAD across the map**
([`evidence/holdout_spread.json`](evidence/holdout_spread.json)). Whole connected traces are
held out (no leakage), 25 % of traces per draw, 4 draws, whole-map emission, retained
catalogue as the mask — the correct analogue of "new faults everywhere".

Arms: **A0** core+shell only · **A1** top-of-ranking peak packing · **A2** strike-steered peaks ·
**A3** uniform random · **A5** field-weighted sampling · **A6** hybrid · **A7** buffered peaks.

| arm | mean DTI | vs A3 random | draws positive | verdict |
| --- | ---: | ---: | ---: | --- |
| **A5 field-weighted sampling — SHIPPED** | **0.033237** | **+0.001323** | **4/4** | **PROMOTED** |
| A6 hybrid (½ peaks + ½ weighted) | 0.031100 | −0.000825 | — | not shipped |
| A1 top-of-ranking peaks | 0.025600 | −0.006315 | 0/4 | rejected |
| A7 buffered peaks (5 px) | 0.025310 | −0.006605 | — | not shipped |
| A2 strike-steered peaks | 0.024790 | −0.007125 | — | rejected (IR-51-06) |
| A0 core+shell only | 0.017670 | −0.014180 | 0/4 | baseline |
| A3 uniform random | 0.032650 | — | — | control |

**Promotion verdict: PASS for A5** — highest mean DTI among candidates and beats uniform random
in **4/4** draws. The rule is recorded in `evidence/holdout_spread.json`
(`shipped_arm_evaluation`) before the shipped file was built.

**The finding that matters most, and it is counter-intuitive.** The detector's dots have a
**2.3× higher** per-dot credit density than random (`credit_density_novel` +0.0020, 4/4 draws)
and yet top-of-ranking peak packing **loses** to random (−0.0063 DTI, 0/4). Cause: the published
credit term `TP_w = Σ_g max_x p(x)k(d(x,g))` is a sum **over the truth**, so each truth pixel pays
at most once no matter how many dots cover it. **Breadth of coverage is the binding constraint;
the field only sets the bias.** Field-weighted sampling gives both, and wins every contrast.
This is the single most consequential measurement in this repository.

---

## 4. Why `h33-h33-2-b2` scored 0.2778, and whether 0.3774 is reachable

**The metric is a budget, not a segmentation score.** From the published definitions on
page 967, with `T = TP_w`, `S = Σp(x)`, `M = Σ p(x)·max_g k`, `K = |truth|`:

```
FP_w = S − M          (exact)
FN_w = K − T          (exact)
DTI  = T / ( 0.2·(T + S − M) + 0.8·K )        (derived here, algebraically)
```

Differentiating at fixed `T, M, K` gives the metric's own first-order condition:

> **adding a unit of mass raises DTI  ⟺  its realised kernel weight `k > 0.2·DTI`.**

At DTI = 0.2778 the bar is **0.0556**; at 0.3774 it is 0.0755. This single inequality
explains every macro pattern in the leaderboard:

1. **Why thinning won.** A file that is a wide rasterisation of a good field spends
   `0.2 × n` of denominator on mass whose realised `k` is below the bar. Removing that tail
   raises `T/S`. The group measured the live break-even at 0.0548 against an analytic bar of
   0.0520 — two independent routes, one answer.
2. **Why the leader's advantage is a detector problem.** Holding emitted mass and the
   hidden truth fixed, moving from the group's 0.2600 to 0.3774 needs the mean realised
   credit of the top-ranked pixels to rise by roughly **+45 %**. No public catalogue can
   supply that (measured here: the newest official compilation lies within 300 m of the
   given catalogue for 59,064 of its 59,065 px). Architecture cannot supply it either —
   only a field whose *high-rank tail* is genuinely better.
3. **Why the masked core is worth more than any architectural change.** Under Fact 1, the
   60,988 catalogue pixels cost **0** and can still earn credit. That is up to 60,988 units
   of free mass in a competition where the winner's total credit is on the order of 5×10³.
   The marginal return on *zero-risk* mass dwarfs the marginal return on a better ranking of
   *risky* mass.

**Is > 0.3774 reachable?** Honest answer: not provable, and this repository does not claim
it. What it does claim, with measurements, is that the frozen 0.2778-class family left the
masked core and the geometry statistics on the table, and that the correct next experiments
are named in §6.

---

## 4b. Build B — this session's independent pipeline (the canonical download above)

Build B was written from scratch on branch `arena/a66904bf-gemsdoe51`. It shares only the two
official facts of §2 and the metric implementation of §1 with Build A; every number below was
measured by the scripts named beside it, and the whole thing reproduces:

```bash
python3 scripts/fetch_data.py --group core      # 4 organiser rasters, sha256-verified
python3 scripts/run_all.py --skip-data          # 8 stages, ~473 s, rewrites the same bytes
```

| stage | what it does | measured result |
| --- | --- | --- |
| **A — the brief's rule** | Kostrov/Kreemer eq. (3) budget on 116 tiles of 25 km: `eps_geo = (1/(2 A)) Σ_k L_k · u̇_k / sin δ_k`, INGENIOUS/GDR-1391 slip rates × clipped trace length, dip per slip sense from Siler (2022) | median geodetic **21.03** ns/yr vs mapped-fault **6.00** ns/yr → ratio **0.455**, median deficit **0.545** (`evidence/stage_a_budget.json`) |
| **A — falsification** | the brief's literal instruction: keep the residual as the coarse prior | **REFUTED on three instruments**: blocked-holdout label-density lift **0.949** (1/4 folds, ρ −0.338); ρ **−0.048** vs lidar scarp intensity; ρ **−0.228** vs off-catalogue SGMC fault density (`evidence/stage_a_holdout.json`, `stage_a_independent_test.json`) |
| **A — adopted gate** | top half of tiles by **geodetic strain magnitude** (band 4), used as a mask that contributes **zero mass** | 58 tiles, **2,537,841 px = 49.1 %** of the footprint; ρ **+0.376** / top-quartile lift **1.393** on the lidar instrument, ρ **−0.166** on the SGMC instrument → **split decision, flagged as IR-51-04**, not claimed as a clean pass (`evidence/stage_a_gate_comparison.json`) |
| **B — detector** | 44-channel stack (19 official bands + 12 lidar scarp bands + 4 radiometric + 4 extension rasters + SGMC fault-density + 4 derived transforms) → HistGradientBoosting, 4 spatially blocked folds, 600 m boundary band removed from training and scoring | fold AUC **0.6719 / 0.7987 / 0.7034 / 0.7331**, mean **0.7268**; beats both sibling out-of-fold fields in **4/4** folds (`evidence/stage_b_folds.json`, `evidence/auc_comparison.json`) |
| **B — paired contrast** | matched-mass DTI against the best sibling field, 4 folds × 2 budgets | **+0.0482 mean, 8/8 rows positive** (`work/detector_contrast.json`) |
| **emission shape** | thin belief-priority dots, 4 % of the candidate area, 3 px minimum separation, deleted within 2 px of the catalogue | mass sweep at spacing 3 px: 0.005→0.1796, 0.01→0.2318, 0.02→0.2803, **0.04→0.2997**, 0.08→0.2585 (`work/detector_contrast.json`) |
| **off-catalogue instrument** | fault *systems* split into train A and truth B, B_far ≥ 6 px from A, official DTI | thin d0.04 s3 = **0.0812**; the best alternative (lattice q0.20) = 0.0850 but positive on only **2/4** folds → **not promoted** (preregistered rule: mean > 0 **and** ≥ 3/4 folds) (`evidence/offcat_holdout.json`) |
| **gates on the shipped file** | uniqueness vs the 12 scored sibling artifacts; stage-A dominance | max Jaccard **0.0322** (limit 0.25; worst overlap 8,426 px of 174,232); vs Build A **0.0034**; coverage inside the approved region **1.0**; tile concentration **1.537×** (uniform 0.145 → ours 0.222) (`evidence/uniqueness_gate.json`, `evidence/stage_dominance.json`, `evidence/emission_audit.json`) |
| **audit + CI** | `scripts/check_submission.py` re-reads the written bytes and re-derives every contract item; `pytest tests -q` = **15 passed**; GitHub Actions re-runs both plus a site-staleness check | `ALL CHECKS PASSED`, exit 0 (`.github/workflows/ci.yml`) |

**What is explicitly NOT claimed for Build B.** The *ranking* beats the sibling fields, but the
alternative *emission shapes* do not beat the incumbent thin-dot rule at matched budget:
credit-density ordering scores −0.0000 mean (1/4 folds), and the expected-budget packer
+0.0002 on 3/8 fold-budget rows — which fails the corrected promotion criterion (mean > 0 AND
≥ 75 % of rows) and is recorded as a failed candidate (IR-51-12, `registry/claims.json`
C51-015). The shipped file therefore combines an old, empirically better *shape* with a new,
empirically better *ranking*, and says so instead of blending the two into a single flattering
number.

### 4b.1 The exact formula, and where it comes from

`eps_geo = (1/(2·A_tile)) · Σ_k (L_k · u̇_k / sin δ_k)` over every mapped segment `k` whose
centroid lies in the 25 km tile, with `L_k` the clipped trace length inside the footprint,
`u̇_k` the INGENIOUS/GDR-1391 slip rate, `δ_k` the dip for that segment's slip sense, and
`A_tile = 250 × 250` px × 100 m. This is **Kreemer, Haines, Holt, Blewitt & Lavallee (2000),
*Earth Planets Space* 52, eq. (3)** — [PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf) —
the fault-slip-rate form of the **Kostrov (1974)** moment-tensor summation (their eq. 2):
`eps_dot_ij = (1/(2 μ V T)) Σ_k M_ij^k`. Dips are not guessed: they are the per-sense medians
of the Siler (2022) USGS release (normal 61.9°, right-lateral 85.8°, left-lateral 81.6°,
unspecified 62.8°; the overall median across all 83,234 measured rows is 64.3°) —
[ScienceBase item 6296974dd34ec53d276bb33d](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d).

---

## 5. Irregularities flagged for review (Build A's register; prefix IR-51A-*)

> The consolidated, canonical register is [`registry/irregularities.json`](registry/irregularities.json)
> with **16 items, IR-51-01 … IR-51-16**. The table below is Build A's own 10-item register,
> preserved with an `IR-51A-` prefix so that no id in this repository means two different things.


| id | finding | evidence | status |
| --- | --- | --- | --- |
| **IR-51A-01** | The brief asks to confirm **slip rates in the INGENIOUS shapefile attributes**. **Not possible from this sandbox** — `gdr.openei.org`, `mrdata.usgs.gov`, `sciencebase.gov` and every other non-GitHub/non-PyPI host return **HTTP 000**. The slip rate is therefore a *documented parameter* (1.0 mm/yr default) with a published sweep (0.1/0.5/1.0/2.0 mm/yr × dip 50/60/70°), **not** a claimed attribute value. | `curl` exit 000 to gdr.openei.org, recorded in the session log; the sweep is in `stage1_strain.slip_rate_sweep` | **OPEN — needs an unrestricted machine** |
| **IR-51A-02** | Competition data cannot be downloaded here: `drivendata.org` returns HTTP 000 and the data page is login-walled. The four core rasters were obtained from the group's own integrity-pinned mirrors and **verified by SHA-256** against the pins. | `registry/data_manifest.json` — all four hashes match | **RESOLVED by hash-pinned mirror**, but the mirrors are *owner-supplied*, not organiser-authenticated |
| **IR-51A-03** | The **stage-1 gate silently approved 90 % of tiles** on the first run, because 57.9 % of the raster carries the float32 nodata sentinel and those empty tiles were being counted as "deficit = 0". Measured: 7,113,308 nodata cells of 12,279,160. | first pipeline log (`approved 10,829 tiles, 213.4 % of footprint`) vs the fixed run (1,793 tiles, 35.5 %) | **FIXED** — usable-tile test added; before/after both recorded |
| **IR-51A-04** | The **uniqueness gate overflowed float32** on its first run (cosine 8773, containment 8773) because some references are not submissions at all (distance-in-metres layers with untagged sentinels). | first gate log vs the fixed run | **FIXED** — values clipped to the legal [0,1] range; null model added |
| **IR-51A-05** | `labels.tif` and `existing_faults.tif` are **byte-identical** (`7ba308cc…`, 425,830 B each). The "labels" and the "existing faults" are the same raster, so any holdout using `labels.tif` as truth is scoring against the training target. | `registry/data_manifest.json` | **FLAGGED** — this repository uses `existing_faults.tif` explicitly and never treats `labels.tif` as independent truth |
| **IR-51A-06** | **The strike-steering hypothesis failed.** It was implemented as originally conceived (Hessian ridge orientation gated by catalogued-fault strike) and scored **AUC 0.4542** vs 0.7005 for the unsteered field and **ΔDTI −0.01126** on the blocked holdout, 0/4 folds. Kept in the code as an ablation, not shipped. | `evidence/holdout_run.json`, `evidence/detector_screen.json` | **REJECTED by measurement** — the honest negative result |
| **IR-51A-07** | Under the contiguous-quadrant protocol the detector **loses to uniform random** (−0.01363), so the preregistered rule returned FAIL. Diagnosed as a protocol artefact *and* as a real property of the metric (T sums over the truth ⇒ coverage beats sharpness). The spread protocol confirmed it: field-**weighted** sampling beats random 4/4 (+0.00132) and peak packing 4/4 (+0.00765). | `evidence/holdout_run.json` (promotion_pass **false**), `evidence/holdout_spread.json` | **RESOLVED** — validated rule shipped; the failure is kept in the record |
| **IR-51A-09** | The organisers' reference solution contains **no metric implementation and no masking**, and its own notebook says *"NOTE: it may be advantageous to threshold this map for better scoring"*. It cannot verify a metric implementation, so verification is against the published equations and the published worked example instead. | reference notebook, read in full this session | **NOTED** |
| **IR-51A-10** | **Every score of this repository's artifacts is a local measurement.** The 0.2600 / 0.2778 / 0.3774 figures are *other people's* leaderboard positions read manually. | this README; all `evidence/*.json` | **STANDING DISCLAIMER** |
| **IR-51A-08** | DrivenData's terms prohibit automated monitoring of the leaderboard, so all leaderboard values here are **dated manual reads** via the page-fetch tool, never a scraper. | `registry/leaderboard_reads.json` | **POLICY** |

---

## 6. Candidate hypotheses — ranked by expected DTI improvement × implementation cost

These are the *next* experiments, each with the specific free official source it needs and
whether that source is reachable **from this environment** (checked, not assumed).

| # | hypothesis | layers / signature | why it should catch a fault the catalogue LACKS | differs from everything already built | cost | source & obtainability |
| --- | --- | --- | --- | --- | --- | --- |
| **H52-1** | **Masked-core completion with tip-extrapolated continuity** | catalogue geometry + the ridge field's *orientation*, continued along-strike past trace endpoints | organisers state new geometry of existing systems counts; tips are exactly where maps stop, not where faults stop | no prior GEMSDOE artifact extrapolates tips under an explicit orientation-continuity constraint | **low** — reuses the field already computed | internal |
| **H52-2** | **Radiometric–magnetic concordance on the *masked* core** | bands 1,2,3,6,9,14,17 | a fault that is kiln-altered along its whole length shows up in BOTH K/Th and RTP magnetics; concordance suppresses the one-channel noise that dominates a single-band ridge | this repo already fuses bands by mean rank; concordance is a *product* (AND) not a mean, and is not used anywhere in the family | **low** | internal |
| **H52-3** | **Post-2023 rupture and deformed-terrain detection** | needs data NOT in the 19 bands: InSAR / optical change or relocated seismicity | a fault that ruptured in 2020 is a fault; if it is not in the Quaternary catalogue it is a hidden-truth candidate by construction | nothing in this repo or the group's has ever used ground-deformation change | **high** | USGS ComCat + ARIA — **HTTP 000 from here**; `earthquake.usgs.gov` and `sciencebase.gov` both unreachable. **Not proposable as viable until an unrestricted machine confirms it.** |
| **H52-4** | **Deep-seated / blind structure via the long-wavelength gravity–magnetic joint anomaly** | bands 5,11,13,18 with a ≥ 10-px (1 km) smoothing | the brief's own caveat: a deficit may be distributed off-fault or **aseismic**; a blind structure produces a broad gravity/magnetic anomaly with no surface scarp | the group's best families are all short-wavelength/topographic; a 1 km-scale joint anomaly is a different physical object | **medium** | internal |
| **H52-5** | **INGENIOUS / SGMC cross-catalogue disagreement, gated** | external fault vectors vs the given catalogue | measured here: SGMC has a large off-catalogue population. If a **state-geological-survey** line is absent from the Quaternary catalogue, that is a candidate the competition's own training labels cannot contain | the group measured this and it is in their record; what is new is gating it with the metric's credit bar `k > 0.2·DTI` rather than unioning it | **medium** | `mrdata.usgs.gov/geology/state/` — **HTTP 000 from here**. **Blocked pending an unrestricted machine.** |

**Ranking by expected P(Win) per unit of cost: H52-1 → H52-2 → H52-4 → H52-5 → H52-3.**
H52-3 has the largest *physical* upside (it is the only one that can find something no
catalogue can contain) and the largest cost; it is data-blocked and is therefore **named but
not claimed**.

---

### 6b. Build B's hypothesis ledger — implemented, falsified, and what survived

The five hypotheses this session actually built and tested, in expected-gain-per-cost order.
Full text, layers, formulas and falsification criteria: [`registry/hypotheses.json`](registry/hypotheses.json).

| # | hypothesis | what the layers gave | verdict (measured) |
| --- | --- | --- | --- |
| **H51-1** | Stage-A **geodetic-strain gate** after the literal rule failed | band 4 `geod_2ndinv` (+7/8 as comparison); GDR slip rates; Siler dips | **REFUTED as a locator, promoted as a mask.** Removes 51 % of the emission domain at no measured cost in credit. The single most important negative result in the repository. |
| **H51-2** | **Lidar scarp-feature ensemble** as the decisive fine-scale channel | 12 external lidar curvature/step channels + 19 official bands + radiometric/extension rasters | **PROMOTED.** 4/4 folds above both sibling fields by AUC, +0.0482 paired matched-mass DTI (8/8 rows). |
| **H51-3** | The **literal deficit** (geodetic − mapped-fault moment) as the prior — the brief's own rule | as H51-1 | **FALSIFIED** on all three instruments (0.949 lift, ρ −0.048, ρ −0.228). Kept as a diagnostic column and as the headline negative result. |
| **H51-4** | **Per-sense dip / slip-sense weighting** inside the Kostrov sum | Siler dip-by-sense table | **PARTIAL.** Dips applied; only 36 % of trace length has a resolved sense (6,286 of 17,375 km). The full **moment-tensor** version is *not tested*: no free rake source exists for INGENIOUS traces. |
| **H51-5** | **Independent-compilation gap closure** — score lineaments by agreement with the pre-Quaternary SGMC map | SGMC state-map faults, 83,593 px | **REJECTED on both grounds**: wrong sign (ρ −0.166 against the adopted gate, −0.205 against the deficit) and the wrong target class (pre-Quaternary bedrock structures, not geothermal-indicative Quaternary faults). |

---

## 7. Reproduce everything

```bash
# ---- Build B (the canonical download above) -----------------------------------------
# 1. restore the four organiser rasters (sha256-pinned; fails closed on any mismatch)
python3 scripts/fetch_data.py --group core          # also: --group all|external|scored

# 2. the whole pipeline: stages A and B, gates, receipt, site  (8 steps, ~473 s)
python3 scripts/run_all.py --skip-data

# 3. verifiers
python3 scripts/check_submission.py docs/downloads/gemsdoe51-strainbudget-s1-v1.tif
pytest tests -q                                     # 15 tests (1 skips without the 557 MB data)
python3 scripts/run_offcat_holdout.py               # the faithful off-catalogue instrument
python3 scripts/check_stage_a_convention.py         # the Stage-A instrument convention test

# 4. rebuild the emission under another rule, e.g. the refuted lattice (do NOT ship)
python3 scripts/rebuild_submission.py --rule lattice --density 0.04 --quantile 0.10 --spacing 3

# 5. site
python3 scripts/build_site.py
```

```bash
# ---- Build A (retained, alternate download) -----------------------------------------
# Build A's pipeline keeps its own paths from PR #1 (src/gems51/{scoring,stage1_strain,
# stage2_emission}.py, scripts/{run_pipeline,run_holdout,run_holdout_spread,run_detector_screen,
# run_uniqueness_gate,prepare_data}.py, scripts/download_competition_data.sh). It is NOT covered
# by CI and shares only grid.py/metric.py/emission.py with Build B.
PYTHONPATH=src GEMS_DATA_DIR=data python3 scripts/run_pipeline.py \
    --tag sbd-hridge-v1 --budget 44090 --shell 1 --approve-quantile 0.35 \
    --out submissions/gems51-sbd-hridge-44090-20261006.tif
python3 scripts/check_submission.py submissions/gems51-sbd-hridge-44090-20261006.tif  # re-verified here: PASS
```

## 8. Repository map

```
src/gems51/metric.py        exact official DTI + brute-force oracle + the marginal-credit theorem
src/gems51/grid.py          raster I/O, masks, tiles (lru-cached) + Build-A compatibility shims
src/gems51/paths.py         filesystem layout; data is never committed
src/gems51/strain.py        Stage A: Kostrov/Kreemer budget, deficit, gate comparison, falsification
src/gems51/features.py      44-channel stack builder (19 official + 12 lidar + 4 rad + 4 ext + derived)
src/gems51/detector.py      blocked 4-fold HistGradientBoosting detector + fold protocol
src/gems51/emission.py      dot emission rules (thin / lattice / packer / credit density)
src/gems51/submission.py    naming, notes, zip, receipts
scripts/run_all.py          THE canonical 8-stage pipeline for the shipped file
scripts/fetch_data.py       hash-pinned restore of every byte (fails closed)
scripts/check_submission.py format contract + receipt digest, exit 0/1, used by CI
scripts/rebuild_submission.py, run_offcat_holdout.py, run_strategy_sweep.py, build_site.py
tests/                      15 tests: metric (9) + submission contract (6)
evidence/                   machine-readable receipts for every claim here
registry/                   claims (24), hypotheses (5), irregularities (16), preregistration,
                            leaderboard snapshot, data manifest, sources (24)
docs/                       the published site (GitHub Pages) + downloads/ (both artifacts)
src/gems51/{scoring,stage1_strain,stage2_emission}.py
                            Build A's modules, kept at their original paths; grid.py carries
                            compatibility shims so they still resolve. Not covered by CI.
knowledge/                  Build A's research digest
work/                       caches (git-ignored; rebuilt in ~8 min by run_all.py)
```

## 9. Limitations, stated plainly

1. **No organiser score exists for any artifact here.** The 0.2778 and 0.3774 figures are
   leaderboard reads for *other people's* submissions. Nothing in this repository has been
   submitted or scored.
2. **The holdout's truth is the mapped catalogue**, so it structurally cannot reward a
   genuinely new fault, and its distance statistics differ from the hidden set's. This is the
   same limitation the group registered (`IR-32-PROXY-01`, `IR-51-06`); it is not new and it
   is not fixed. Build B adds the off-catalogue A/B instrument as a partial countermeasure.
3. **The masked-core argument rests on a forum statement**, not on the rules PDF. It is
   corroborated independently (the sample submission is the catalogue), but it is a statement
   by staff, and if it is implemented differently than stated the core fill becomes a
   liability. It is the highest-variance decision in this repository and it is flagged as such.
4. **Slip rates were never confirmed from the organiser's own shapefile attributes**
   (`IR-51A-01` in Build A's register; the canonical `IR-51-14` covers the mirror provenance).
   Build B does use slip rates — from the GDR-1391 mirror table (median 0.100 mm/yr, max
   4.500) — so every Stage-A number is conditional on that mirror being a faithful copy.
5. **The detector loses to uniform random under the contiguous-quadrant protocol**
   (IR-51-07). The spread protocol in §3 is the test of whether that is an artefact. If it
   also says random wins, the correct action is to ship the core+shell-plus-random
   configuration and say so.

---

## 10. Remaining work and blockers (handover for the next session)

**Blockers that a different environment removes immediately**

1. **No organiser score exists for either file, and none can be obtained here.** DrivenData
   requires a login; this sandbox has no credentials and cannot reach `drivendata.org`. Both
   receipts say so, and every score quoted in this README is somebody else's leaderboard read.
   Action for a human or an unrestricted runner: submit the two files, then paste the returned
   scores back here — they are the only feedback signal that can rank Build A against Build B,
   and they would also calibrate the local PROXY instruments.
2. **GitHub Pages is live but publishes the branch ROOT, not `docs/`.** Measured, not guessed:
   the deployment API reports `status: built` for `main`
   (`repos/buffedlizard55-lab/GEMSDOE51/pages/builds`), and
   <https://buffedlizard55-lab.github.io/GEMSDOE51/docs/> serves the committed site, while the
   bare project URL <https://buffedlizard55-lab.github.io/GEMSDOE51/> returns *404 File not
   found* because the root has no `index.html`. Two consequences, both handled here:
   a root [`index.html`](index.html) was added that forwards to `docs/index.html` (so the short
   URL now works), and **the owner may prefer one click**: Settings → Pages → *Deploy from a
   branch* → `main` / `/docs`, which serves the site at the bare URL with no redirect. The
   integration token cannot change that setting (`gh api .../pages` → 403, *Resource not
   accessible by integration*), which is why the redirect exists.
3. **`1m_DEM_links.csv` was never obtained** (the 3DEP tile index behind the lidar layer). The
   scarp bands were used from the sibling mirror instead. If a new area or a re-derivation is
   ever needed, this is the missing input.

**Work that is specified but not done**

4. **H51-4 tensor version** — the moment-tensor variant of the Kostrov sum needs a **rake**
   source; INGENIOUS/GDR-1391 carries slip *sense*, not rake. Until a free rake compilation is
   found and fetched, the scalar `u̇/sin δ` reduction is the honest maximum.
5. **Stage-A geometry (IR-51-08)** — a trace is credited entirely to the tile containing its
   centroid. Median trace length 7.7 km against 25 km tiles, so boundary crossings are
   mis-credited; a line-clipping implementation is the obvious fix and has not been written.
6. **Lidar bands 7–12 remain unlabelled (IR-51-10).** They are carried as generic
   scarp-sharpness channels. Naming them requires the producer's metadata, not a guess.
7. **Leaderboard ranks ≥ 25 were never read** (the read page returned in two chunks and only
   the first was consumed). The snapshot therefore holds 12 rows, all dated 2026-10-06.
8. **The two §6 hypotheses that are data-blocked stay data-blocked**: H52-3 (post-2023 rupture
   / InSAR / relocated seismicity) and H52-5 (state-geological-survey cross-catalogue
   disagreement) both need hosts that this environment cannot reach
   (`earthquake.usgs.gov`, `mrdata.usgs.gov`, `sciencebase.gov`: HTTP 000). They are named and
   **not** claimed, per the brief's rule.

**Reconciliations already closed this session** (so they are not re-opened as open questions)

9. Uniqueness max Jaccard is **0.0322** against `gems10-h25-ctx-ridge…tif`; the older 0.0171
   figure in one intermediate file was a pre-`stage_dominance` run and is superseded by
   `evidence/uniqueness_gate.json`, which is what the site and this README render.
10. The Siler **"Unspecified"** dip is **62.8°** as a per-sense median; **64.3°** is the median
    over all 83,234 rows. Both figures are now labelled in `registry/claims.json`,
    `registry/hypotheses.json` and `registry/irregularities.json`.
11. The deficit's SGMC correlation appears as **−0.205** in `stage_a_gate_comparison.json`
    (114 tiles, footprint-mean convention) and **−0.228** in `stage_a_independent_test.json`
    (116 tiles, whole-tile convention). The convention difference and its null test are
    documented in `scripts/check_stage_a_convention.py` and
    `evidence/stage_a_instrument_consistency.json`; both numbers are correct as labelled.

**Next experiments with the highest expected P(Win) per unit of cost** — in order, each must
clear the off-catalogue instrument **before** it can consume a submission slot:

1. **Tip-extrapolated catalogue continuity** (H52-1, Build A's list, not yet built): continue
   the candidate field along-strike past trace endpoints under an orientation-continuity
   constraint. Lowest cost of anything left; the organisers have stated on the record that new
   geometry of existing systems counts.
2. **Radiometric–magnetic concordance on the masked core** (H52-2): a product/AND of K–Th and
   RTP channels instead of a mean rank — different object from every mean-fusion built so far.
3. **Long-wavelength gravity–magnetic joint anomaly** (H52-4, ≥ 1 km smoothing) as the
   blind-structure arm — the brief's own "distributed off-fault" caveat made operational.
4. Only then, the two data-blocked arms above, on a machine that can reach USGS/ScienceBase.

**Standing rules kept from the brief** (unchanged, and the reason several of the above are
*not* shipped): work line by line against official sources with links
([`registry/sources.json`](registry/sources.json)); no unvalidated idea spends a submission
slot; report both stages separately; no hallucinations — every number is a receipt in
[`evidence/`](evidence/) produced by a named script; flag irregularities
([`registry/irregularities.json`](registry/irregularities.json), 16 items).
