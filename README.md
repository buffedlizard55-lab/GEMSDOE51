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
registry/     hash-pinned data manifest, source register, irregularity register
src/gems51/   metric, grid, features, stack, detector, emission, holdout,
              strain_budget (Stage 1), extras (candidate hypotheses), submission, uniqueness
scripts/      restore_data, prepare_data, run_experiments, run_two_stage, build_submission, build_site
tests/        metric identity tests (run: python -m pytest tests -q)
docs/         GitHub Pages site (executive summary, one-click download)
data/         raw + prepared rasters (gitignored; restored by scripts/restore_data.py)
```

## 3. Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 scripts/restore_data.py --group all     # hash-verified mirrors via `gh api`
python3 scripts/prepare_data.py                 # -> data/prepared/
python3 -c "import sys; sys.path.insert(0,'src'); import gems51.stack as s; s.build()"
python3 scripts/build_extras.py                 # candidate-hypothesis feature groups
python3 scripts/run_experiments.py --arm base   # spatially blocked holdout
python3 scripts/run_two_stage.py                # Stage 1 / Stage 2, scored separately
PYTHONPATH=src python -m pytest tests -q
```

## 4. Known irregularities — see `registry/irregularities.json`

* **IR-51-01** GEMSDOE32's index page labels `gems32-probe-S1-ANCHOR-identical-to-live-02600.tif`
  as the "0.2708 anchor", but that repository's own audit JSON for the same
  digest (`4dc4cc54…`) calls it the **0.2600** reference anchor, and its mask is
  byte-identical to the GEMSDOE25 file scored 0.2600. The 0.2708 label is not
  reproducible from the artifacts; we treat the file as the 0.2600 anchor.
* **IR-51-02** The three geodetic layers satisfy no exact algebraic identity
  (`sqrt(dil²+shear²)`, `sqrt((dil²+shear²)/2)`, `|dil|+|shear|` all miss by
  >30 % locally; best r = 0.993), so the invariant convention behind
  `geod_2ndinv` is **not recoverable** from the shipped data. Stage 1 is
  therefore stated in quantile space, which is invariant to it.
* **IR-51-LEAK-01** Any feature derived from the catalogue is a *perfect* training
  leak in a blocked holdout (every positive has `d_cat = 0`). Measured: in-block
  AUC collapsed to exactly 0.500. Catalogue-derived columns are excluded from the
  model and used only at emission time.
* **IR-51-03** The DrivenData data page is login-walled and this sandbox's egress
  is allow-listed (PyPI + github.com + api.github.com only). All rasters are
  therefore re-fetched as hash-pinned public GitHub blobs; provenance is
  owner-mirror, **not** organizer-authenticated.


## 5. What shipped this session

### The deliverable

`docs/downloads/gemsdoe51-h_d-softw0p1-r347-bag3-20261006T222111Z-zeros.tif` — 44,069 emitted pixels,
sha256 `5db55c064eb0…`.

Two files are offered, both from the same detector and the same 3-bag ensemble, differing only in
how Stage 1 is allowed to touch them:

| role | gate | holdout cost vs ungated | max Jaccard vs any prior GEMSDOE submission | uniqueness |
|---|---|---|---|---|
| PRIMARY | soft | +0.0004 | 0.017 | PASS |
| SECONDARY | hard | -0.0025 | 0.015 | PASS |

The **PRIMARY** uses the soft prior, because it is the only Stage-1 setting that is not negative on
the blocked holdout. The **SECONDARY** is the brief's literal design — points only inside
stage-one-approved tiles — shipped as ordered, with its measured cost printed next to it rather than
hidden.

### Stage 1 and Stage 2, reported separately

*Stage 1* (Kostrov strain-budget deficit, 10 km tiles) is scored on a **trace-level** holdout,
because a spatial block would zero the fault-accommodated term inside the block and the question
would be circular: with the block's own faults removed there is nothing to accommodate. A fifth of
the mapped traces is withheld, the remaining four fifths supply the budget, and uniform random dots
are thrown down inside the approved tiles versus everywhere. No model is fitted, so there is no
leakage to control.

| prior | approved | area share | truth recall | lift | proxy DTI |
|---|---|---|---|---|---|
| deficit | top 50 % of tiles | 0.501 | 0.551 | 1.100 | 0.0507 |
| geodetic_only | top 50 % of tiles | 0.500 | 0.620 | 1.239 | 0.0578 |
| deficit | top 30 % of tiles | 0.301 | 0.319 | 1.059 | 0.0448 |
| geodetic_only | top 30 % of tiles | 0.301 | 0.375 | 1.247 | 0.0534 |
| deficit | top 20 % of tiles | 0.201 | 0.240 | 1.193 | 0.0459 |
| geodetic_only | top 20 % of tiles | 0.201 | 0.256 | 1.273 | 0.0489 |
| none | whole footprint | 1.000 | 1.000 | 1.000 | 0.0494 |

Spearman rank correlation of each tile field against held-out fault density: deficit = +0.032, geodetic_only = +0.099, dil_deficit = +0.013, shear_deficit = +0.024.

The deficit is **worse than the raw geodetic field** on every column. Subtracting the
fault-accommodated term removes signal instead of isolating it: the mapped-fault term tracks where
faults cluster, mapped faults are surrounded by unmapped ones, so it carries *positive* information
about where the missing ones are. Stage 1 is retained as a prior, not as a filter.

*Stage 2* (the detector), spatially blocked holdout:

| arm | in-block AUC | proxy DTI at M/|G| = 3.47 | folds |
|---|---|---|---|
| base | 0.6668 | 0.2794 | 6 |
| H_E | 0.6633 | 0.2768 | 6 |
| H_D | 0.6726 | 0.2817 | 6 |
| H_C | 0.6322 | 0.2544 | 6 |
| H_ALL | 0.6293 | 0.2552 | 6 |

### Gate sweep

Hard gate versus soft prior, six folds, paired against the ungated run:

| gate | setting | mean proxy DTI | paired Δ | folds better |
|---|---|---|---|---|
| soft prior | w = 0.0 | 0.2816 | +0.0000 | 0/6 |
| soft prior | w = 0.05 | 0.2818 | +0.0001 | 3/6 |
| soft prior | w = 0.1 | 0.2820 | +0.0004 | 4/6 |
| soft prior | w = 0.2 | 0.2818 | +0.0002 | 4/6 |
| soft prior | w = 0.4 | 0.2810 | -0.0007 | 2/6 |
| hard gate | top 100 % of tiles | 0.2816 | +0.0000 | 0/6 |
| hard gate | top 90 % of tiles | 0.2803 | -0.0013 | 0/6 |
| hard gate | top 80 % of tiles | 0.2791 | -0.0025 | 0/6 |
| hard gate | top 70 % of tiles | 0.2779 | -0.0038 | 0/6 |
| hard gate | top 60 % of tiles | 0.2721 | -0.0095 | 0/6 |
| hard gate | top 30 % of tiles | 0.2055 | -0.0762 | 0/6 |
| hard gate | top 10 % of tiles | 0.1372 | -0.1445 | 0/6 |

The hard gate is monotone-harmful: it never wins a fold at any setting. It is shipped anyway, at the
mildest setting that still passes the anti-dominance test, because the brief asks for it — and its
cost is disclosed on the download page rather than hidden.

### Honest expectation, written down before the score is known

Our instrument says **0.282** proxy DTI at the live mass ratio, against
**0.279** for the previous stack. That brackets the group's best owner claim (0.2778)
and sits below the current public leader (0.3774). **Expect this file to land in the high 0.2s.** It
is a genuinely new, independently verified, portal-legal submission — it is not yet a leaderboard
win.

### Phase 1 entries are not free

The organizer has stated that the Phase 2 test set "will use a test set that is updated by expert
review of all Phase 1 submissions, so your fault predictions have an impact on final evaluation even
if they are not the most performant in Phase 1" (chrisk-dd, 2026-09-23, thread 11527 post 7). Every
emitted dot is therefore required to be individually defensible: all lie outside the 200 m exclusion
zone, none sits on a catalogued trace, and the argument for looking in any given tile is published
on the method page. The same organizer post declined to disclose the data sources, fault types or
coverage behind the hidden labels, so **no** validation instrument here — including ours — can be
shown to match the hidden label style (IR-51-05).

### Repository history: two independent implementations

PR #1/#2 (an earlier session on a different branch) and this session each built the same library
from scratch in parallel, so 27 paths conflicted add/add at the same names. This session's versions
were kept for the shared code and site paths because they are what produced the shipped artifacts.
Nothing was lost: every conflicting PR #1/#2 file is preserved verbatim under `attic/pr1-2/`, and
all 74 non-conflicting files — the `evidence/*.json` register, `docs/claims.html`,
`docs/strategy.html`, `docs/executive-summary.html`, `docs/assets/`, the CI workflows,
`data/labels.tif`, `data/existing_faults.tif` and `data/sample_submission.tif` — carry through
untouched. Recorded as **IR-51-07**.

### Limitations, in the order they matter

1. **IR-51-08 — the training labels are a duplicate of the known-fault raster.** Byte-identical
   files, identical sha256, identical to the catalogue we derived independently from INGENIOUS. The
   real target distribution has never been seen by any model in this repository. **This is the first
   thing next session should chase**, because everything measured here measures our detector against
   a proxy, not against the truth.
2. **IR-51-05 — the organizer will not disclose the hidden labels' provenance.** We cannot tell
   whether the truth is topographic, geophysical or field-mapped, and Phase 2's test set is rebuilt
   from expert review of Phase 1 submissions.
3. **The instrument's ceiling.** In-block AUC 0.673 and proxy DTI 0.282 is about as good as the
   detector that produced the group's best 0.2778. Closing a 0.095 gap to the leader is a modelling
   problem, not an emission-tuning problem.
4. **Stage 1 does not work as specified.** The strain-budget deficit is worse than the raw geodetic
   field on every measure. It is shipped as a soft prior because that costs nothing; the brief's
   hard-gate version is shipped too, with its cost disclosed.
5. **No authenticated data.** Every raster is an owner-mirrored public GitHub blob; provenance is
   hash-consistent, not organizer-authenticated.
6. **Regenerable bulk is not in git.** `data/raw/` and `data/prepared/` (~7 GB, the 2.67 GB feature
   stack and 0.9 GB static extras) are rebuilt by `scripts/restore_data.py` → `prepare_data.py` →
   `stack.build()` → `build_extras.py`, roughly four minutes end to end.

### What next session should do

* Get the real `labels.tif` (IR-51-08) and re-run the blocked holdout against it. If the mirror is
  simply mislabelled, every number in this repository needs re-measuring.
* Attack the localisation problem directly: the leader's implied ~200 m mean dot-to-trace distance
  versus our ~260 m is the whole gap, so the next candidate hypothesis should be judged on that
  statistic, not on AUC.
* Try a sub-pixel emission position: the metric's triangular kernel rewards being *on* the trace,
  and every dot here is snapped to a 100 m cell centre.
