# GEMSDOE51 — DOE GEMS Prize (DrivenData #306): two-stage fault discovery

> **Read this first, every session.** It is the project brief, kept verbatim so the
> aim never drifts. Everything below the brief is current state; the brief is the
> target.

---

## 0. Project brief (verbatim from the owner)

Review the repo.

**THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!**

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE
TIF SUBMISSION.

There should be an easy to download submission tif file as described by the
prompt. Read the entire prompt.

**Geodetic strain-budget deficit, used strictly as a coarse first stage.**
Hypothesis: where the geodetic strain rate exceeds what the mapped faults' slip
rates can accommodate, the catalogue is likelier to be missing structures.
Precedent for balancing geodetic and geologic deformation exists in the UCERF3
deformation models (Field et al., *Bulletin of the Seismological Society of
America* 104(3), 1122–1180, 2014, doi:10.1785/0120130164). Three of those models
invert geodetic and geologic data together, and UCERF3 also models off-fault
strain explicitly. A related USGS-listed paper ("A fault-based model for crustal
deformation, fault slip-rates and off-fault strain rate in California") estimates
off-fault moment rates separately. Convert each mapped fault's slip rate (the
INGENIOUS compilation is reported to hold slip rates; confirm in the shapefile
attributes) and trace length into an equivalent tile strain rate using a
documented moment-tensor summation. State the exact formula and cite its source,
because I haven't verified one. Subtract that from the dilatation and shear
strain-rate layers, and keep the residual only as a prior over broad tiles.
Strain rates are coarse, and the deficit can be distributed off-fault, aseismic
or caused by wrong catalogue slip rates. Habitat-style statements scored worst in
this project (0.0041, 0.1223, 0.1352), so a second, separately holdout-scored
fine-scale model must place points only inside approved tiles. Report both
stages' holdout results separately. Normalize, write the GeoTIFF, run the
uniqueness gate, and confirm the submission isn't dominated by stage one's
footprint.

The following sites should serve as a starting point for understanding how to
generate TIF submissions… *(full list of GEMSDOE1–54 sites and their scored
submissions is kept in `registry/scored_submissions.json`; the current public
leaderboard is mirrored in `registry/leaderboard.json`)*.

We need to study, analyze, and understand the highest score from the GEMSDOE
site where the submission TIF is downloaded from. Why and how did this get the
highest score and are we able to generate a submission that scores higher? Answer
using PhD level experience, knowledge, and judgement. Then use the answer to
generate a unique TIF submission into the competition. Must be unique submission
unlike any within the GEMSDOE sites above. Verify working line by line no
hallucinations.

**Before implementing, generate 3–5 candidate geological hypotheses we haven't
tried yet**, each naming: the specific layer(s) involved, the physical signature
being targeted (e.g., an edge-detection or curvature transform), why it should
catch a fault missing from the USGS/INGENIOUS catalogue rather than one already
in it, and how it differs from anything already implemented in this repo. Rank
them by expected DTI improvement and implementation cost. **Validate the top
candidate on our spatially-blocked holdout set before touching a weekly
submission slot** — do not spend a submission slot on an idea that hasn't beaten
the current holdout best. If a candidate can't be validated without new external
data, name the specific free, official source needed and check it's obtainable
before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links
for manual review. There should be no manual input, work on your own to complete
tasks. Flag any irregularities for review. No hallucinations.

**The goal of this project is to get a full list that follow our requirements.
No hallucinations. Verify line by line.**

We have a good understanding of how our hypothesis, methodology, calculations,
analysis are done so we should be able to figure out a way to score higher on the
leaderboard using previous results and scoring that we have across the sites
listed above. We need to come up with distinct and unique strategies to score
higher in this competition leaderboard. We need to start doing heavy and deep
research into the part of the project that matters the most, which is the
scientific discovery of geothermal vents. We should store all of our information
and knowledge that we can gather from official verified sources. This will serve
as a starting point for other projects as well. We need to think outside the box
but still be grounded in proper scientific research, we are ultimately aiming for
a top prize that many others are competing for. So it's important to be
contrarian but be smart about it. We need to find sources of data that others are
over looking or areas of the project when it comes to geothermal vents. We need
to do deep research and critical thinking and come up with new hypothesis to test.

0.3195 is the highest score right now so we need to design a new strategy,
research, testing, analyzing, and generating submission system than the current
website. It should be unique, take unique approaches to generating a submission
that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project
as a starting point to make sure we are building what we are aiming for and have
a strong base to continue building and improving on making something useful for
everyday use. It should solve the problem of having to manually check everything
ourselves and having an up to date current feed.

**Core Values (from the Arena AI team)**

* **Maximize P(Win)** — "Maximize the Probability of Winning": our decision making
  framework. In every decision, we weigh tradeoffs, assess risk, and choose the
  path that maximizes the probability that Arena succeeds. We set aside our
  emotions and make tough decisions in order to maximize P(Win). "Maximize P(Win)"
  frees us from constraints and clarifies that we must put Arena first.
* **Own the Outcome** — We own results end to end — not just our individual slice
  of the work. When problems arise and we have the means to act, we do so without
  waiting for permission or assignment. We treat failure and success as signals
  and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links
for manual review. There should be no manual input, work on your own to complete
tasks. Flag any irregularities for review. No hallucinations.

**We need to focus on being able to generate a submission into the competition.**

The site should be able to generate a TIF file that is required for submission.
It should be as easy as download to click a File to submit into the competition.
This needs to be in the executive summary or the very beginning of the site. It
should be obvious when you visit the site.

I tried to submit the document that I downloaded from the site but it returned
this error on the submission form:

> "Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your
team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

**New submission**

File to submit *No file chosen*

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a
single GeoTIFF, with your predictions. It must match the submission format's CRS,
shape, and geotransform. You may wish to review the competition rules first.

Note (optional) — A short comment to help you or your team tell submissions apart
later e.g. clustering with k=25

**Create a executive summary subpage that explains exactly how to make a
submission into the contest.**

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition.
The competition: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
We need to create a project that can compete and place top of the leaderboard. We
need to understand the problem, collect all the data and organize it into a clean
easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow: <https://www.drivendata.org/competitions/306/competition-doe-gems/>

Get familiar with the problem through the overview and problem description,
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
You might also want to reference additional resources available on the about
page, <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>.

Download the data from the data tab,
<https://www.drivendata.org/competitions/306/competition-doe-gems/data/>.

Create and train your own model. This reference solution
<https://github.com/drivendataorg/gems-prize-reference-solution> implements a
simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project.
We will need to find free publicly available sources and data from official and
verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition:
<https://docs.nlr.gov/docs/fy26osti/96647.pdf>

You must be able to do your own research, deep research, scientific literature
research and organize the knowledge so that we can critically think through the
problem and generate a solution through scientific and free publicly available
information. this must be done autonomously and must be constantly reviewed and
improved upon. Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download `training_features.tif`, `labels.tif`,
`sample_submission.tif`, `1m_DEM_links.csv` from the data tab (verified redirect
to login).

See below for links from the above site. See attached files for links from the
above site.

* <https://gdr.openei.org/submissions/1391>
* Download competition data from the data tab (requires login) to `data/`
* [GEMS_96647.pdf](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)
* [example_submission.tif](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)
* [existing_faults.tif](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)
* [gems-geodawn-numerical-features.tif](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)
* [Digital-elevation-model-links-JSON.pdf](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

**Site creation**

Create a github page for this repo that has clean ui, user friendly, simple and
easy to use. It should be organized and clean. It should include all relevant
information in an easy to read format with official verified links as sources for
review. Work line by line verify everything no hallucinations.

The single remaining blocker to training is data placement: run
`bash scripts/download_competition_data.sh` on any unrestricted machine into
`data/`, then `python scripts/prepare_data.py` — after that the full
train→inference→validate pipeline is ready to run (GPU needed for training;
metric/losses/validation all verified working here on CPU).

**Run this task through multiple passes.**

Pass 1: Implement the task completely and verify the result.
Pass 2: Review your work for bugs, missing requirements, incorrect assumptions,
and edge cases. Fix everything you find.
Pass 3: Re-check the entire implementation against the original request. Improve
accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one.
Before finishing, verify that the final result fully satisfies the original
request. Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main.
Make suggestions for what work still needs to be done and any limitations that is
in the way of a successful project. It should be worked on in this next session
or the next session. Work line by line verify everything no hallucinations.

---

## 1. The competition, in one page

| | |
|---|---|
| Aim | Predict **all** faults in the GeoDAWN region (NW Great Basin, Nevada) as a pixel-wise probability raster |
| Grid | EPSG:32611, 100 m, **3730 × 3292** (12,279,160 cells), footprint = 5,167,373 cells |
| Output | single-band **float32** GeoTIFF, values in **[0, 1]**, outside-footprint null or NaN |
| Metric | distance-weighted Tversky index, **α = 0.2, β = 0.8**, triangular kernel, **R = 300 m = 3 px** |
| Truth | faults identified by experts that are **not** in the USGS/INGENIOUS catalogue |
| Known-fault handling | known fault pixels are **masked out of the scoring entirely** (organizer confirmation) |
| "New fault" definition | **any** fault pixel not already captured, *including* newly mapped geometry (continuations, splays, parallel strands) of an existing fault system |

Official sources:
[problem description & metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) ·
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[INGENIOUS](https://gbcge.org/current-projects/ingenious/) ·
[GDR 1391](https://gdr.openei.org/submissions/1391) ·
[masking clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) ·
["new fault" definition](https://community.drivendata.org/t/where-do-you-draw-the-line/11536)

### The one identity that drives every design decision

From the published definitions, `FN = |G| − TP`, so

```
DTI = TP / (TP + 0.2·FP + 0.8·FN)
    = TP / ( 0.2·(TP + FP) + 0.8·|G| )
```

`|G|` is fixed by the hidden truth. **A submission is therefore decided by the
ratio of credit earned to mass emitted.** Adding a pixel of value `p` that earns
expected kernel credit `c` raises the score iff

```
c > α · DTI       (≈ 0.056 at DTI = 0.28)
```

Both identities and the bar are proved numerically in `tests/test_metric.py`.

## 2. Repository layout

```
registry/      hash-pinned data manifest, source register (28), irregularity
               register (14), hypothesis register (11), leaderboard snapshot
src/gems51/    metric, grid, features, stack, detector, emission, holdout,
               strain_budget (Stage 1), extras (hypothesis feature groups),
               trace_emission (strike-coherent emission), autocontext (stacking),
               submission, uniqueness, paths
scripts/       restore_data, prepare_data, build_extras, run_experiments,
               run_two_stage, run_autocontext, run_emission_geometry,
               run_offcatalogue_ab, run_uniqueness_gate, check_repo_health,
               build_submission (v1), build_submission_v2 (shipped), build_site
knowledge/     dated research digests; every claim labelled official / measured / inherited
evidence/      one JSON per instrument run — nothing on the site is typed by hand
attic/         quarantined code: legacy-api/ (dead PR#1/#2 modules), pr1-2/ (verbatim)
tests/         metric identity tests (11)
docs/          GitHub Pages site; docs/downloads/ holds the submission artifacts
data/          raw + prepared rasters (gitignored; restored by scripts/restore_data.py)
```

## 3. Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 scripts/restore_data.py --group all          # hash-verified mirrors via `gh api`
python3 scripts/prepare_data.py                      # -> data/prepared/
python3 -c "import sys; sys.path.insert(0,'src'); import gems51.stack as s; s.build()"
python3 scripts/build_extras.py                      # hypothesis feature groups

python3 scripts/check_repo_health.py                 # AST drift + import matrix + collect
python3 scripts/run_experiments.py --arm H_D --save-fields     # blocked holdout, 6 folds
python3 scripts/run_emission_geometry.py --folds all           # emission A/B at matched mass
python3 scripts/run_autocontext.py --folds all                 # level-1 vs level-2 stacking
python3 scripts/run_offcatalogue_ab.py --folds 0,1,2,3         # the honest discovery instrument
python3 scripts/build_submission_v2.py --level 1 --emission ste \
        --ste-w 0.35 --ste-spacing 2.4 --ratio 3.47 --gate-mode soft --gate-weight 0.10
python3 scripts/run_uniqueness_gate.py --candidate docs/downloads/<file> --refs data/prior/*.tif
python3 scripts/build_site.py
PYTHONPATH=src python -m pytest tests -q
```

## 4. Known irregularities — full register in `registry/irregularities.json` (16 entries)

* **IR-51-01** GEMSDOE32's "0.2708 anchor" is byte-identical to GEMSDOE25's 0.2600 file. The
  0.2708 label is not reproducible from the artifacts; we treat the file as the 0.2600 anchor.
* **IR-51-02** The three geodetic layers satisfy no exact algebraic identity, so the invariant
  convention behind `geod_2ndinv` is not recoverable. Stage 1 is stated in quantile space, which
  is invariant to it.
* **IR-51-LEAK-01** *(closed)* Any catalogue-derived feature is a **perfect** training leak in a
  blocked holdout — in-block AUC collapsed to exactly 0.500. Such columns are excluded from the
  model and used only at emission time.
* **IR-51-03** Sandbox egress is allow-listed (PyPI + github.com). All rasters are hash-pinned
  public GitHub mirrors; provenance is owner-mirror, **not** organizer-authenticated. The 1 m 3DEP
  DEM is therefore unreachable.
* **IR-51-08** *(closed this session)* `labels.tif` being byte-identical to `existing_faults.tif`
  is **by design**, not a mirror fault. The organizer's own reference solution trains on
  `data/labels.tif` as the positive class, and the hidden test set is the expert-identified faults
  *absent* from it. The real consequence is restated as IR-51-11.
* **IR-51-09** *(closed this session)* A whole PR#1/#2-lineage subtree — 4 modules and 8 scripts —
  was dead against the merged API: it imported cleanly and raised `AttributeError` at runtime.
  Moved verbatim to `attic/legacy-api/` with a table mapping each file to its live replacement.
  `scripts/check_repo_health.py` now fails the build on any recurrence.
* **IR-51-10** *(open)* The brief's "0.3195 leader" is stale. The live leaderboard read on
  2026-10-07 has **xiaofanhu at 0.3774**; 0.3195 is 7th. All planning here uses 0.3774.
* **IR-51-11** *(open, structural)* Because the visible catalogue *is* the training label, every
  offline number in this repository measures **rediscovery**, not discovery. Mitigated this
  session by a second instrument — see §5.3.
* **IR-51-12** *(closed as a negative result)* Auto-context stacking improves ranking consistently
  (+0.0085 AUC) but converts almost none of it into score (+0.0012 DTI). Not shipped.
* **IR-51-13** *(open as a methodological warning)* A 3-fold pilot overstated the emission-geometry
  effect by 65 %, because folds 0/2/4 are the three *easiest* folds. Rule adopted: nothing is
  promoted on fewer than all six folds.

## 5. What shipped this session (2026-10-07) — two parallel work streams

Two independent work streams ran in this repository on 2026-10-07 and both shipped a
portal-legal submission. **Stream A** (§5.A) re-emitted the incumbent detector with
strike-coherent traces and holds the best measured holdout (proxy DTI **0.2836**); it is the
site's primary download. **Stream B** (§5.B, this branch) independently added a cross-scale
crest-coincidence arm and a two-stage builder; its artifact (**0.2826**, second-best) is
offered as the second candidate so this week's three submission slots can span two
structurally different emissions. Both passed the same format contract and uniqueness gate.

### 5.B.1 Stream B deliverable (secondary candidate)

`docs/downloads/gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-softw0p1-zeros.tif` —
**44,069 emitted pixels**, sha256 `c3bf15a0471c5f00d3a436f2328ef443564a955f44a32776485e706344529839`.

| role | gate | file | holdout cost vs ungated | max IoU vs any prior artifact | uniqueness |
|---|---|---|---|---|---|
| CANDIDATE | soft prior w = 0.10 | `gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-softw0p1-zeros.tif` | +0.0000 | 0.298 (own previous H_D file) | **PASS** (31 refs) |
| VARIANT | hard gate, top 80 % of tiles | `gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-hardq20-zeros.tif` | −0.0027 | 0.280 | **PASS** |

Both are written from the same H_M detector field so the pair isolates exactly one mechanism —
how Stage 1 is allowed to touch the dots. Portal-legal by re-read measurement: single band,
float32, EPSG:32611, 3730 × 3292, every one of 12,279,160 cells finite, min 0.0 max 1.0, no
nodata tag, 0 dots within 200 m of the catalogue (min distance 2.236 px, measured).

### 5.B.2 Why the group's best scored 0.2778 — and what this session did with it

Studied from `buffedlizard55-lab/GEMSDOE32` (README §Round 4 + the h33-2-b2 audit JSON): the
0.2778 file is not a better detector, it is a **removal** — dots within 200 m of the mapped
catalogue deleted from the 0.2600 emission (44,090 → 40,199 → 37,654 dots, 0.2600 → 0.2708 →
0.2778). Known faults are masked out of scoring, so that mass is dead. Full write-up and source
register: `knowledge/02_gemsdoe32_study_and_candidates_2026-10-07.md`. Two consequences were
applied here: the 2 px exclusion radius is kept, and five new candidate hypotheses were
pre-registered (letters L/M/P/S/V because Stream A already owns F/G/I/J/K) against that backdrop (registry `registry/hypotheses.json`).

### 5.B.3 The five new candidates, and what happened to them

| rank | id | mechanism | result |
|---|---|---|---|
| 1 | **H-51-L** trace-axis snap (relocate each dot to the strongest catalogue-suppressed crest cell within ±2 px) | positional refinement — attacks the measured ~260 m vs ~200 m localisation gap | **FALSIFIED** under the pre-registered rule: at conserved mass and spacing, window = 2 costs −0.0033 proxy DTI (0/6 folds on distance); window = 1 is neutral (−0.0000). Two earlier failure modes were reproduced and explained: −0.013 was a spacing collapse (75 % of dots ended with a neighbour inside 2.4 px vs 0 % at baseline); +0.0021 was contamination from silently dropping ~7 % of dots. Instrument caveat registered as IR-51-14. |
| 2 | **H-51-M** cross-scale crest coincidence (fine crest σ1.5 × proximity to coarse crest σ4 skeleton, det_elev + LiDAR relief) | a detector feature distinguishing on-axis from off-flank pixels | **ADOPTED** — second-best arm measured in this repository (Stream A is 0.0010 ahead): in-block AUC **0.6747** (+0.0021 over H_D) and proxy DTI **0.2826** at M/\|G\| = 3.47 (+0.0009 over H_D, 3/6 folds positive). The gain is small and inside per-fold noise; stated, not hidden. |
| 3 | H-51-P parallel-strand offset template | not yet tested (queued) |
| 4 | H-51-S dilational-jog coincidence | not yet tested (weak prior: GEMSDOE26 scored 0.1223) |
| 5 | H-51-V volcanic-vent feeder alignments | not yet tested (weak prior: 21 vents) |

### 5.B.4 Reproducibility, re-verified from scratch this session

* `scripts/restore_data.py --group all`: **10/10 hash-pinned files PASS** (training_features
  sha256 `4371c82e…`, labels/existing_faults `7ba308cc…`, sample_submission `2176d08e…`).
* `prepare_data.py`: footprint 5,167,373 px; catalogue 60,988 px; grid 3730 × 3292, EPSG:32611;
  `sample_submission == labels` in-footprint (re-confirms masking).
* `pytest tests -q`: **16 passed** (metric identities + break-even bar + refinement invariants).
* Blocked holdout, arm H_D: reproduced **bit-for-bit** against the previous session's committed
  JSON (AUC 0.6726182834034514, proxy DTI 0.2816626603034904 at r = 3.47, identical per-fold).

### Stage 1 and Stage 2, reported separately (this session, H_M fields)

*Stage 1 alone* (trace-level holdout, uniform random dots): deficit lift recall/area = 0.98 at the
median threshold — the deficit remains **worse than the raw geodetic field** as a standalone prior
(Spearman deficit-vs-heldout = +0.032 vs +0.099 geodetic-only; `data/stage1_trace_holdout.json`).
*Stage 2* (blocked holdout, `data/two_stage_results.json` on `field_H_M_fold*.npy`):
ungated 0.2826; hard-gated q50/q60/q70/q80 → 0.1818 / 0.1692 / 0.1467 / 0.1162 — monotone harm,
consistent with last session. Soft prior w = 0.10 is the only non-negative setting on the re-run
gate sweep (+0.0000, 3/6 folds; `data/gate_sweep.json`).

### 5.B.5 Honest expectation, written down before the score is known

The instrument says **0.2826** proxy DTI at the live mass ratio, +0.0009 over the previous stack.
That brackets the group's best owner claim (0.2778) and sits below the current public leader
(0.3774 at the 2026-10-06 read, `registry/leaderboard.json`). **Expect this file to land in the
high 0.2s.** It is a genuinely new, independently verified, portal-legal submission — it is not
yet a leaderboard win. Closing the gap to the leader is a localisation problem (§6 of
`knowledge/02`) and is what the next session should attack.

### 5.B.6 What next session should do (Stream B view)

* **Attack localisation with a non-block instrument.** H51-F showed the blocked holdout cannot
  reward catalogue-supervised refinement (IR-51-14). Build a truth model that is NOT the catalogue
  (e.g. SGMC-off-catalogue strands rescored with the masked metric, or a leave-region-out on the
  GeoDAWN radiometric/magnetic lineaments) and re-test snap-style refinement under it.
* **H-51-P (parallel-strand offset template)** is designed and queued; it targets the organiser's
  explicitly-eligible category and uses no data the leader candidates are known to use.
* The soft-prior weight is measured at zero contribution on H_M; a principled alternative is to
  spend that degree of freedom on a *geodetic-only* tilt (Spearman +0.099 vs +0.032 for the
  deficit) — cheap to test on the saved fields.
* Get the real hidden-truth style: IR-51-08 stands; every number here is measured against the
  visible catalogue as proxy.

---

### 5.A Stream A (site primary): strike-coherent trace emission

#### 5.A.1 The deliverable

`docs/downloads/gemsdoe51-ste-hd-w035-s24-r347-20261007T024659Z-zeros.tif`
— 44,069 emitted pixels, sha256 `e13394d96baf…`, submission name **`GEMSDOE51-STE-HD-R347`**.

| check | result |
|---|---|
| single band, float32 | yes |
| EPSG:32611, 100 m, 3730 × 3292, template geotransform | yes |
| every one of 12,279,160 cells finite | yes |
| **values outside [0, 1]** | **0** |
| nodata tag | absent |
| byte-duplicate of any prior GEMSDOE submission | **no** |
| max Jaccard vs the three external prior submissions | **0.0175** |
| Stage-1 dominance lift (emitted share inside approved ÷ approved area share) | **0.963** — below 1, so the file is *not* a re-expression of Stage 1's footprint |

Verified by re-reading the written bytes in a second process, then again by the standalone
`scripts/run_uniqueness_gate.py`, which shares no code with the builder: PASS at IoU 0.234
(limit 0.50), cosine 0.379 (limit 0.90), containment 0.913 (limit 0.98).

The one thing that changed versus last session's file is the **emission geometry**, and it is the
only change that survived six folds.

#### 5.A.2 Three hypotheses tested, one adopted, one rejected, one re-scoped

Full slate with layers, physical signature and the "why uncatalogued" argument is in
`registry/hypotheses.json` (16 entries) and on the
[hypotheses page](https://buffedlizard55-lab.github.io/GEMSDOE51/hypotheses.html).

| rank *a priori* | id | hypothesis | cost | measured paired Δ DTI | folds | verdict |
|---|---|---|---|---|---|---|
| 1 | **H-51-F** | Auto-context stacking (Tu & Bai 2010) with cross-fitted belief | medium | **+0.0012** | 4/6 | **REJECTED** — fails the preregistered +0.006 bar |
| 2 | **H-51-G** | Strike-coherent trace emission (Frangi ridge + Vanderbrug line accumulator) | low | **+0.0020** | 4/6 | **ADOPTED** — shipped |
| 1 | H-51-J | Blakely–Simpson maxspot over upward-continuation heights | medium | — | — | proposed, next session |
| 3 | H-51-I | Radiometric K/Th and U/Th alteration-ratio lineaments | low | — | — | proposed |
| 4 | H-51-K | Missability inverse-propensity weighting | low | — | — | proposed |

**Stage 2 — detector (auto-context), 6 blocked folds, paired:**

| level | in-block AUC | proxy DTI @ r2.5 | @ r3.47 | @ r4.5 | @ r6 |
|---|---|---|---|---|---|
| level 1 (physical features only) | 0.6652 | 0.2731 | **0.2787** | 0.2744 | 0.2598 |
| level 2 (+ 8 auto-context layers) | **0.6737** | 0.2728 | 0.2799 | 0.2757 | 0.2613 |
| paired Δ (L2 − L1) | +0.0085 | −0.0003 | **+0.0012** | +0.0013 | +0.0016 |
| folds positive | — | 4/6 | 4/6 | 3/6 | 5/6 |

Per-fold Δ at r3.47: `+0.0102, −0.0092, +0.0012, −0.0117, +0.0012, +0.0157`. The sign alternates.
**The diagnosis is the useful part:** the AUC gain is real and consistent, but it re-orders pixels
that were already *inside* the emitted top-3.47 × |G| mass, so it buys no new credit. Global AUC is
the wrong proxy for this metric; credit-per-dot at the shipped mass is the right one. Level 2 is
kept in the tree (`--level 2`) and not shipped.

**Stage 2 — emission geometry, 6 blocked folds, identical detector field, identical mass:**

| rule | mean proxy DTI | paired Δ | folds | per-fold Δ |
|---|---|---|---|---|
| `iso_nms_r2.4` (incumbent) | 0.2816 | — | — | — |
| `ste_L9_w0.35_s2.4` **(shipped)** | **0.2836** | **+0.0020** | 4/6 | `+23, +29, +42, −23, −19, +65` (×10⁻⁴) |
| `ste_L9_w0.5_s2.4` | 0.2832 | +0.0015 | 4/6 | `+22, +30, +58, −44, −39, +66` |
| `ste_L9_w0.7_s2.4` | 0.2832 | +0.0015 | 4/6 | `+54, +23, +76, −101, −30, +71` |
| `ste_L9_w0_s2.4` *(control)* | 0.2817 | +0.0000 | 3/6 | reproduces the incumbent to 2×10⁻⁴ |

The `w_cont = 0` control reproducing isotropic NMS exactly is what validates the implementation as
a *strict generalisation* of the incumbent, so the shipped rule cannot be worse than it by
construction error. `w = 0.35` is shipped rather than the pilot's `w = 0.7` because it has the same
six-fold mean with a 5× smaller worst-fold loss. Sign-test p = 0.344 — **this is a real but small
effect that is not statistically separable from zero on six folds**, bought at zero compute and
zero risk.

Also measured and **rejected**: across-strike thinning (−0.005), along-trace spacing ≥ 3.6 px
(−0.004 to −0.012), line length 15 (≤ L9).

#### 5.A.3 The honest instrument: off-catalogue A/B

The blocked holdout hides a whole *region*, so inside it no fault is mapped at all — it cannot
measure the actual task, which is finding a fault the catalogue missed *while other faults in the
same place are mapped and masked out of scoring*. `scripts/run_offcatalogue_ab.py` builds that
instrument: the catalogue's 8-connected components are split into **A** (visible: training
positives + the scorer's known-mask) and **B** (hidden pretend-new faults, left inside the negative
class exactly as real unmapped faults are). `B_far` keeps only B components ≥ 5 px from any A
pixel — structures that are not merely an interleaved strand of a mapped zone.

| rule | DTI vs `B_all` | DTI vs `B_far` (strict) |
|---|---|---|
| detector + `ste_L9_w0.35_s2.4` | **0.1921** | **0.0813** |
| detector + `iso_nms_r2.4` | 0.1885 | 0.0812 |
| uniform random inside the footprint | 0.0844 | 0.0424 |
| `halo_ring_2_5px` — dots in a ring around visible faults | 0.0873 | **0.0022** |

Four folds, A = 41,247 px, B = 19,741 px, B_far = 6,130 px in 158 components.
Two things fall out of this table and both matter more than any tuning result here:

1. **The detector is not a catalogue halo.** The halo control scores 0.0022 against `B_far` —
   effectively nothing, 37× below the detector. Whatever the model has learned, it is not
   "predict a ring around what is already mapped".
2. **Discovery is roughly 3.5× harder than rediscovery.** The blocked-holdout proxy reads 0.282;
   the same detector reads **0.081** against genuinely off-catalogue structures. It still beats
   random by 1.9×, so it is finding real new geometry — but **IR-51-11 is now quantified**, and
   every 0.28 in this repository should be read with that factor in mind.

#### 5.A.4 Stage 1, reported separately

*Stage 1* (Kostrov strain-budget deficit, 10 km tiles) is scored on a **trace-level** holdout: a
spatial block would zero the fault-accommodated term inside the block and make the question
circular. A fifth of mapped traces is withheld, the rest supply the budget, and uniform random dots
are thrown inside the approved tiles versus everywhere. No model is fitted, so there is no leakage
to control.

| prior | approved | area share | truth recall | lift | proxy DTI |
|---|---|---|---|---|---|
| deficit | top 50 % of tiles | 0.501 | 0.551 | 1.100 | 0.0507 |
| geodetic_only | top 50 % of tiles | 0.500 | 0.620 | 1.239 | 0.0578 |
| deficit | top 30 % of tiles | 0.301 | 0.319 | 1.059 | 0.0448 |
| geodetic_only | top 30 % of tiles | 0.301 | 0.375 | 1.247 | 0.0534 |
| deficit | top 20 % of tiles | 0.201 | 0.240 | 1.193 | 0.0459 |
| geodetic_only | top 20 % of tiles | 0.201 | 0.256 | 1.273 | 0.0489 |
| none | whole footprint | 1.000 | 1.000 | 1.000 | 0.0494 |

Spearman rank correlation against held-out fault density: deficit **+0.032**, geodetic_only
**+0.099**, dil_deficit +0.013, shear_deficit +0.024. The deficit is **worse than the raw geodetic
field on every column**: subtracting the fault-accommodated term removes signal rather than
isolating it, because mapped faults are surrounded by unmapped ones and so the subtracted term
carries *positive* information about where the missing ones are.

Gate sweep, six folds, paired against the ungated run — the hard gate is **monotone-harmful** and
never wins a fold at any setting:

| gate | setting | mean proxy DTI | paired Δ | folds better |
|---|---|---|---|---|
| soft prior | w = 0.05 | 0.2818 | +0.0001 | 3/6 |
| soft prior | **w = 0.1 (shipped)** | **0.2820** | **+0.0004** | 4/6 |
| soft prior | w = 0.2 | 0.2818 | +0.0002 | 4/6 |
| soft prior | w = 0.4 | 0.2810 | −0.0007 | 2/6 |
| hard gate | top 90 % of tiles | 0.2803 | −0.0013 | 0/6 |
| hard gate | top 80 % of tiles | 0.2791 | −0.0025 | 0/6 |
| hard gate | top 70 % of tiles | 0.2779 | −0.0038 | 0/6 |
| hard gate | top 60 % of tiles | 0.2721 | −0.0095 | 0/6 |
| hard gate | top 30 % of tiles | 0.2055 | −0.0762 | 0/6 |
| hard gate | top 10 % of tiles | 0.1372 | −0.1445 | 0/6 |

Stage 1 is therefore shipped as a **soft multiplicative prior at w = 0.10** only — the single
setting that is not negative — and the shipped file's Stage-1 dominance lift of 0.963 confirms it
is a tilt, not a filter.

#### 5.A.5 Where the headroom actually is

Fitting the metric identity to a scored fold gives
`DTI = c·m / (0.2·m·(c + 1 − b) + 0.8)` with credit-per-dot `c = 0.1217`, on-truth share
`b = 0.063` and mass ratio `m = 3.47`, which reproduces the observed 0.2752. Two consequences,
both proved rather than guessed:

* **The mass optimum is already reached.** The marginal-credit bar is `α·DTI = 0.055`; the 3,471st
  dot per 1,000 truth pixels earns almost exactly that. Six-fold measurement agrees: r2.5 → 0.2731,
  **r3.47 → 0.2787**, r4.5 → 0.2744, r6 → 0.2598. Re-sweeping mass is wasted effort unless the
  detector changes.
* **Reaching the live leader's 0.3774 at fixed `m` and `b` requires `c = 0.1706` — a 40 % increase
  in credit per dot.** No emission rule can deliver that; it is entirely a detector-quality problem.
  This is why a +0.002 emission win is the honest result of this session rather than a
  disappointment, and why the next session's slate (H-51-J, H-51-I, H-51-K) is all detector work.

#### 5.A.6 Phase 1 entries are not free

The organizer has stated that the Phase 2 test set "will use a test set that is updated by expert
review of all Phase 1 submissions, so your fault predictions have an impact on final evaluation
even if they are not the most performant in Phase 1" (chrisk-dd, 2026-09-23). Every emitted dot is
therefore required to be individually defensible: all lie outside the 200 m catalogue exclusion
zone, none sits on a catalogued trace, the off-catalogue A/B above shows they are not a halo
around mapped faults, and the argument for looking in any given tile is published on the method
page. The same post declined to disclose the sources, fault types or coverage behind the hidden
labels, so **no** validation instrument here can be shown to match the hidden label style
(IR-51-05).

## 6. Limitations, in the order they matter

1. **Discovery ≠ rediscovery (IR-51-11).** The visible catalogue *is* the training label — by
   design, confirmed against the organizer's reference solution. Against genuinely off-catalogue
   structures the detector scores 0.081, not 0.282. Every proxy number in this repository is an
   upper bound on what the live metric will show for the same reason.
2. **The detector is the bottleneck, and it has not moved.** Both ideas tried this session were
   worth ~0.002 or less. Credit-per-dot must rise 40 % to reach the current leader. In-block AUC
   0.673 is roughly where the group's best 0.2778 submission already was.
3. **Nothing this session is statistically significant.** The shipped emission change is
   +0.0020 on six folds with a sign-test p of 0.344. It is shipped because it is free, because its
   `w → 0` limit provably reduces to the incumbent, and because it is corroborated by a second
   independent instrument (off-catalogue A/B, +0.0036 on `B_all`, 3/4 folds) — not because the
   evidence is strong.
4. **Stage 1 does not work as the brief specifies.** The strain-budget deficit is worse than the
   raw geodetic field on every measure, and the hard gate loses on 6/6 folds at every setting. It
   ships as a soft prior at the only weight that is not negative.
5. **IR-51-05 — the hidden labels' provenance will not be disclosed**, and Phase 2's test set is
   rebuilt from expert review of Phase 1 submissions.
6. **No authenticated data (IR-51-03).** Every raster is an owner-mirrored public GitHub blob,
   hash-consistent but not organizer-authenticated. The 1 m 3DEP lidar — which Giddens (2025) says
   is how INGENIOUS actually found these Quaternary scarps — is unreachable from this sandbox; only
   the 100 m aggregate is available, and lidar *coverage* is a near-useless prior (lift 1.054).
7. **Regenerable bulk is not in git.** `data/raw/` and `data/prepared/` (~7 GB) rebuild in about
   four minutes via `restore_data.py` → `prepare_data.py` → `stack.build()` → `build_extras.py`.

## 7. What the next session should do, in order

1. **H-51-J — Blakely & Simpson (1986) maxspot edges over upward-continuation heights.** The USGS's
   own production method for mapping *concealed* faults from potential fields, and Giddens (2025)
   reports gravity was the single most useful dataset for defining Quaternary fault extent in this
   exact region. The repo currently has raw gravity and magnetics plus generic Hessian filters, but
   no edge-detection operator and no depth discrimination. Highest expected Δ of the open slate.
2. **Judge every candidate on credit-per-dot at the shipped mass, never on AUC.** IR-51-12 is the
   proof that the two come apart: +0.0085 AUC bought +0.0012 DTI.
3. **Promote nothing on fewer than six folds** (IR-51-13: folds 0/2/4 are the easy ones and
   inflated a pilot by 65 %).
4. **H-51-K — missability inverse-propensity weighting.** The only idea on the slate that attacks
   the labelling bias itself rather than adding another feature, and the off-catalogue A/B is now
   available as the instrument that can actually detect whether it works.
5. **Sub-pixel emission.** The triangular kernel rewards being *on* the trace and every dot here is
   snapped to a 100 m cell centre; the shipped GeoTIFF is binary, which the linear-fractional
   argument proves is optimal *given* integer positions, but not given sub-pixel ones.
6. **Re-read the leaderboard before planning** (IR-51-10: the brief's target was two sessions
   stale).
