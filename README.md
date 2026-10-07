# GEMSDOE51 — DOE GEMS Prize (DrivenData #306): two-stage fault discovery

> **Read this first, every session.** It is the project brief, kept verbatim so the
> aim never drifts. Everything below the brief is current state; the brief is the
> target.

---

> **Time-sensitive correction (2026-10-07):** The owner brief below is preserved verbatim, including
> its historical “0.3195 is the highest” target. The official public leaderboard now shows 0.3774
> at rank 1 and 0.3195 at rank 7. The 0.2778 row is `extradr19` at rank 13; no verified link ties
> it to GEMSDOE32 H33-2-B2, which that repository labels UNSCORED with a 0.2747 modelled projection.
> The historical habitat-style score values in the owner brief are owner-reported and not
> independently authenticated to files. See the evidence and status section below; do not use old
> score attributions as fact.

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

From the published definitions, `FN_w = |G| − TP_w`, so

```
DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)
    = TP_w / ( 0.2·(TP_w + FP_w) + 0.8·|G| )
```

Here `TP_w` and `FP_w` are distance-weighted terms. `|G|` is fixed by the hidden truth; the metric
trades weighted true-positive credit against weighted error and a fixed truth-size term. The sum
`TP_w + FP_w` is not the raw number of emitted pixels.

`TP + FP` is the metric's effective weighted cost, not the raw number of emitted pixels. For an
increment with weighted changes `ΔTP = c` and `ΔFP = f`, the exact local improvement condition is

```
c · (1 − 0.2·DTI) > 0.2·DTI·f
```

The familiar `c > 0.2·DTI` is only the special case `c + f = 1`; it is not a universal per-pixel
threshold. The identities and the general/special-case tests are in `tests/test_metric.py`.

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


## 5. Current evidence and decision (2026-10-07)

### Executive decision

The existing H-D soft research TIFF is
`docs/downloads/gemsdoe51-h_d-softw0p1-r347-bag3-20261006T222111Z-zeros.tif`.
It is a one-band float32 GeoTIFF on the competition grid, EPSG:32611, 100 m, 3730×3292,
with every cell finite and values in [0, 1]; 44,069 positive pixels, SHA-256
`5db55c064eb0b920beb84cd4d6de426a347206b7b8a2c9adc8cfb343084a570b`. Its format is verified,
but its fresh full-corpus uniqueness audit **fails**: it overlaps the current repository's hard-q20
alternate at Jaccard 0.631 and has a same-prediction NaN-format twin at Jaccard 1.000. Do not use it
as a unique submission. Its suggested identifier is `GEMSDOE51-HD-SOFT-W010`; its note is only a
label, not permission to upload.

To produce a distinct research artifact without spending a competition slot, the matched H-G+H-D
feature recipe was materialized as
`docs/downloads/gemsdoe51-hg-hd-xing-experimental-r347-20261007T034048Z-zeros.tif`.
It is a single-band float32 GeoTIFF, EPSG:32611, 3730×3292, all finite in [0,1], 44,069 positive
pixels, SHA-256 `c02930644a5c3b1051a57c5f2092bb1c942d6adb07d6ca76be205ad8e0d46ab9`. Its fresh
public-artifact uniqueness audit **passes**: 359 TIFF payloads were fetched and SHA-verified, 358
were pixel-comparable, zero download errors, one unrelated 32×48 format-test fixture skipped, zero
matches, maximum support Jaccard 0.3216 (limit 0.50), maximum cosine 0.4867 (limit 0.90). Stage-1
q70 diagnostics show 30.046% of footprint approved and 19.728% of emissions inside (lift 0.657),
so Stage 1 does not dominate.

**Do not spend a competition slot or upload this experimental TIFF.** The matched six-block H-G+H-D
holdout averaged 0.281056 proxy DTI vs H-D 0.281663 (paired Δ −0.000606; 3/6 folds higher) and lower
mean AUC. The separate H-D soft-prior gain is +0.000367 (4/6 folds), small/inconclusive, not a
win. Thus one artifact passes the scoped uniqueness gate, but it fails the locked incumbent holdout;
no candidate has passed both promotion and uniqueness gates. The portal-formatted research TIFF is
not a leaderboard claim and is not authorized for Phase 1 upload. Full records:
`evidence/experimental_H_G_plus_H_D_artifact.json`,
`evidence/uniqueness_gate_H_G_HD_experimental_20261007.json`, and
`evidence/holdout_H_G_plus_H_D.json`.

### Public leaderboard and score attribution

A manual fetch of the official board on 2026-10-07 shows the highest public row as 0.3774 at rank 1
for participant `xiaofanhu`; 0.2778 appears at rank 13 for `extradr19`. These are leaderboard
observations, not identified TIFFs. The board identifies participants and scores, not TIFF hashes or
methods. The earlier claim linking 0.2778 to GEMSDOE32 H33-2-B2 is
**unsupported and contradicted by GEMSDOE32's own reporting**: its README/site labels H33-2-B2
UNSCORED, with a modelled projection of 0.2747. There is no verified file-to-score link. We cannot
scientifically explain the 0.2778 row beyond the metric mechanics without the scored file, its
positions, and the hidden labels. See `evidence/score_attribution_audit.json` and
`registry/scored_submissions.json`.

Scientifically, the public score can only be interpreted through the published metric—not as a
geological success rate or a known model result. With the 300 m triangular distance kernel, each
truth pixel contributes at most its best nearby prediction credit; off-target prediction mass adds
weighted false-positive cost. The score 0.3774 is not 37.74% recall, accuracy, or trace coverage. The
effective `TP_w + FP_w` term is not raw emission count. For a proposed increment with weighted
changes `c=ΔTP_w` and `f=ΔFP_w`, the exact local improvement condition is
`c·(1−0.2·DTI) > 0.2·DTI·f`; `c > 0.2·DTI` is only a special case. Local holdouts below are
catalogue proxies and are not directly comparable to public scores.

### Stage 1 — exact formula, rate sensitivity, and limitation

Kreemer et al. (2000), Eq. 3, gives the fault-slip-based horizontal strain-rate sum:

```
epsilon_dot_ij = 1/(2 A_tile) * sum_k [L_k * u_dot_k / sin(delta_k)] * m_ij^k
m_ij^k = s_i^k*n_j^k + s_j^k*n_i^k
```

For pure normal motion the horizontal component is `L*u_vertical*cot(dip)/A` if the table rate is
vertical displacement, or `L*u_fault_plane*cos(dip)/A` if it is total fault-plane slip. For a pure
vertical-plane strike-slip fault it is `L*u/(2A)`, with opposite signs for right- and left-lateral
motion. Source: [Kreemer et al. (2000), Eq. 3](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf).

The local table has 1,126 rows and 49 distinct numeric `slip_rate` values. The USGS QFaults REST
alias labels the string field “Slip Rate (mm/year)”, but exact component semantics are not
authenticated here: the GDR v2 archive's field-definition text could not be read. `dip_direct` is
direction metadata, not numeric dip. The code assumes 60° normal-fault dip and 90° strike-slip
dip; unknown slip sense is either assumed normal or excluded in sensitivity runs. Stage 1 is
quantile-space tile ranking only, a low-confidence broad prior—not a fine-scale point placer.

Five trace-level splits (not spatial blocks) show that the deficit is worse than raw geodetic-only
on mean Spearman and q50 recall/area lift under all four formula/sense cases. The random-dot
comparison uses 44,069 dots from `3.47 × 12,700`; 12,700 is a planning proxy only, not a measured
hidden-truth size or a deduction from a public leaderboard row:

| rate/sense case | Spearman: deficit / geodetic-only | q50 lift: deficit / geodetic-only | single-draw q50 proxy DTI: deficit / geodetic-only |
|---|---:|---:|---:|
| vertical-rate assumption, unknown sense→normal | 0.0318 / 0.0993 | 1.099 / 1.239 | 0.04972 / 0.05629 |
| fault-plane-rate assumption, unknown sense→normal | 0.0313 / 0.0993 | 1.097 / 1.239 | 0.05020 / 0.05598 |
| vertical rate, known senses only | 0.0273 / 0.0993 | 1.101 / 1.239 | 0.05063 / 0.05537 |
| fault-plane rate, known senses only | 0.0269 / 0.0993 | 1.104 / 1.239 | 0.05187 / 0.05567 |

DTI is one seeded random-dot draw per field/split and not paired across masks; treat its small
changes as descriptive noise. Complete formula, input-field caveats, and split-level values:
`evidence/stage1_formula_audit.json`.

### Stage-1 dominance audit for the soft primary

The soft primary's configured diagnostic is **q70** (approve the top 30% of deficit values), not
q20. Its original build-time check reports 30.046% of footprint approved and 20.307% of emitted
pixels inside that area (lift 0.676). A current-code rerun reports 30.046% area, 19.560% inside
(lift 0.651). Both are below the area share, so neither indicates Stage-1 dominance. The existing
TIFF predates the signed strike-slip code revision; both records are preserved rather than
conflated. The old q20/top-80% figures (80.051% area, 78.091% emitted) belong to the hard secondary
threshold and are retained only as a comparator. See `evidence/submission_manifest_reconciliation.json`.

### Stage 2 — spatially blocked proxy holdout

| arm | in-block AUC | proxy DTI at M/|G|=3.47 | evidence |
|---|---:|---:|---|
| H-D incumbent | 0.67262 | 0.28166 | `data/holdout_H_D.json` |
| H-G high-angle TMI–gravity crossings, replacing H-D extras (not matched) | 0.66358 | 0.27678 | `evidence/holdout_H_G.json` |
| H-G crossings added to H-D (matched) | 0.66962 | 0.28106 | `evidence/holdout_H_G_plus_H_D.json` |

The first H-G arm replaced H-D's four coherence features and lost by 0.004879 mean proxy DTI
(1/6 folds higher); it was not an add-on comparison. The matched H-G + H-D add-on was then evaluated
on the same six blocks, truth counts, block sizes, negative-sample plan, and M/|G|=3.47. It scored
0.281056 versus H-D 0.281663 (paired delta −0.000606; 3/6 folds higher); mean AUC was 0.669619
versus 0.672618. H-G is not promoted. Stage 2 is six contiguous spatial blocks with a 1.2 km
training buffer, fixed negative-sample seed per fold, and emissions/scoring inside the held-out
blocks. All local results use the visible catalogue as proxy truth; none establishes hidden-fault
or geothermal resource discovery.

### Hypotheses and prior art

The four-candidate date-stamped slate (target layers/signatures, rationale, exact difference from
inspected prior work, expected benefit, engineering cost, and both the initial and matched H-G
results) is
`evidence/hypothesis_slate_20261007.json`. Prior-art review covers 582 keyword-selected public
documents from 54 sibling repositories and makes no global novelty claim. Broad river-profile,
hydrothermal-expression, radiometric, relay/stepover, and magnetic–gravity orientation families
have substantial sibling prior art. H53's default branch had only an 11-byte README with its title.
The H-G high-angle operator is a specific variant of an already documented edge-orientation family,
not an untried family.

### Known limitations that change decisions

1. **IR-51-08:** the obtainable `labels.tif` is byte-identical to the known-fault raster/catalogue;
   the real competition training labels are not authenticated. This is the largest blocker.
2. **IR-51-05:** the organizer does not disclose hidden-label provenance; the hidden fault style may
   differ from the visible catalogue.
3. **Stage 1:** rate component, slip sense fallbacks, assumed dip, and geodetic invariant convention
   remain uncertain; the deficit loses as a locator and stays a broad prior only.
4. **Score attribution:** public participant rows do not identify artifacts; no local organizer
   score is claimed.
5. **Uniqueness:** the H-D soft TIFF fails the fresh audit (hard-q20 Jaccard 0.631; its NaN twin
   Jaccard 1.000). A newly materialized H-G+H-D experiment passes the scoped corpus gate (359
   SHA-verified TIFF payloads; 358 comparable; zero matches; one format-test shape skip), but its
   matched holdout is negative, so it is not slot-eligible. Neither result substitutes for the
   historic 211-reference Hridge PASS; that input corpus is absent. See both
   `evidence/uniqueness_gate_H_D_soft_20261007.json` and
   `evidence/uniqueness_gate_H_G_HD_experimental_20261007.json`.
6. **Provenance:** rasters come from hash-pinned owner mirrors, not an authenticated organizer
   download.

### Reproduction

```bash
PYTHONPATH=src .venv/bin/python scripts/audit_stage1_formula_results.py
PYTHONPATH=src .venv/bin/python scripts/reconcile_submission_manifest.py
PYTHONPATH=src .venv/bin/python scripts/run_public_uniqueness_audit.py \
  --candidate docs/downloads/gemsdoe51-h_d-softw0p1-r347-bag3-20261006T222111Z-zeros.tif
# Optional research build only; H-G+H-D failed its matched holdout and must not be uploaded.
PYTHONPATH=src .venv/bin/python scripts/build_experimental_hg_hd_tiff.py \
  --basename gemsdoe51-hg-hd-xing-experimental-r347-20261007T034048Z
PYTHONPATH=src .venv/bin/python scripts/run_public_uniqueness_audit.py \
  --candidate docs/downloads/gemsdoe51-hg-hd-xing-experimental-r347-20261007T034048Z-zeros.tif \
  --out evidence/uniqueness_gate_H_G_HD_experimental_20261007.json
.venv/bin/python scripts/build_site.py
PYTHONPATH=src .venv/bin/python -m pytest -q
```

### Repository history: two independent implementations

PR #1/#2 (an earlier session on a different branch) and this session each built the same library
from scratch in parallel, so 27 paths conflicted add/add at the same names. This session's versions
were kept for the shared code and site paths because they are what produced the shipped artifacts.
Nothing was lost at that merge: every conflicting PR #1/#2 file is preserved verbatim under
`attic/pr1-2/`, while the 74 non-conflicting files were retained. This follow-up now regenerates
`docs/claims.html` from `registry/claims.json` and replaces the obsolete `docs/strategy.html`
narrative with a score-attribution correction notice; original merge handling remains recorded as
**IR-51-07**.

### Limitations, in the order they matter

1. **IR-51-08 — target labels are not authenticated.** The obtainable `labels.tif` is byte-identical
   to the known-fault raster/catalogue. All local holdouts therefore test recovery of visible
   catalogue structure, not the hidden target distribution.
2. **No artifact-to-score mapping.** The highest public row in the 2026-10-07 fetch is 0.3774
   (`xiaofanhu`); it reveals no TIFF or method. The 0.2778 row belongs to `extradr19` in that
   snapshot, and must not be attributed to GEMSDOE32 H33-2-B2, which the sibling reports as
   UNSCORED with a 0.2747 modelled projection.
3. **Stage 1 is not a locator.** Its deficit ranks below raw geodetic-only on the audited trace-level
   splits under all four rate/sense cases. It is retained only as a low-confidence broad-tile prior;
   slip-rate component semantics, unknown-sense handling, dip assumptions and geodetic invariant
   conventions remain uncertain.
4. **No hypothesis has passed the promotion gate.** H-D soft's +0.000367 mean delta is small and
   inconclusive; the matched H-G add-on is −0.000606 and only 3/6 folds higher. No slot is authorized.
5. **Uniqueness scope is finite.** The fresh audit covers indexed TIFFs under public sibling
   `docs/downloads/` and `submissions/` paths in the pinned inventory; it is not proof of global
   uniqueness or a complete source-code/data-history search.
6. **No organizer-authenticated raster bytes.** The available inputs are hash-pinned owner mirrors;
   hashes establish consistency with those mirrors, not organizer provenance.

### Next actions

* Finish the fresh uniqueness audit for the current candidate and report its exact corpus scope,
  Jaccard/containment results, and Stage-1 dominance check separately.
* Rebuild and inspect the generated site, then run the full tests and Python syntax checks.
* Keep H-G rejected unless new, preregistered evidence changes its paired result. Any H-H/H-I/H-J
  implementation must be tested on the locked spatial blocks before any slot is considered.
* Obtain organizer-authenticated training labels if access becomes available, then rerun all holdouts;
  until then, all local DTI/AUC figures remain visible-catalogue proxies.
* Do not infer the winning model's layers, mass, fault styles, or point placement from a participant
  score alone. No local leaderboard score or geothermal discovery is claimed.
