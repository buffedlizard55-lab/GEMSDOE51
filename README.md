# GEMSDOE51 — DOE GEMS Prize research and submission record

**Working status: `HOLDOUT_PROMOTED_UNSCORED` (local only; no organizer upload or score).**

This repository is a reproducible, guarded research record for DrivenData competition #306,
the DOE GEMS Prize / GeoDAWN Northwest Great Basin task. The current primary is a new
H-H/H-D blend that passed the repository's frozen local promotion and artifact gates. It is
obvious to download below, but it has **not** been uploaded to DrivenData and no portal
acceptance, leaderboard score, or hidden-label result is claimed.

## Master Prompt & Competition Directives

```text
Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.

Geodetic strain-budget deficit, used strictly as a coarse first stage. Hypothesis: where the geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the catalogue is likelier to be missing structures. Precedent for balancing geodetic and geologic deformation exists in the UCERF3 deformation models (Field et al., Bulletin of the Seismological Society of America 104(3), 1122–1180, 2014, doi:10.1785/0120130164). Three of those models invert geodetic and geologic data together, and UCERF3 also models off-fault strain explicitly. A related USGS-listed paper ("A fault-based model for crustal deformation, fault slip-rates and off-fault strain rate in California") estimates off-fault moment rates separately. Convert each mapped fault's slip rate (the INGENIOUS compilation is reported to hold slip rates; confirm in the shapefile attributes) and trace length into an equivalent tile strain rate using a documented moment-tensor summation. State the exact formula and cite its source, because I haven't verified one. Subtract that from the dilatation and shear strain-rate layers, and keep the residual only as a prior over broad tiles. Strain rates are coarse, and the deficit can be distributed off-fault, aseismic or caused by wrong catalogue slip rates. Habitat-style statements scored worst in this project (0.0041, 0.1223, 0.1352), so a second, separately holdout-scored fine-scale model must place points only inside approved tiles. Report both stages' holdout results separately. Normalize, write the GeoTIFF, run the uniqueness gate, and confirm the submission isn't dominated by stage one's footprint.

The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.
...
WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:
https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778
Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?
Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.
...
Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.
...
I tried to submit the document that i downloaded from the site but it returned this error on the submission form:
"Predicted values must be in range [0, 1]"
Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25
...
Create a executive summary subpage that explains exactly how to make a submission into the contest.
...
Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.
```

## Read this brief before changing the project

The operating objective is **Maximize P(Win)** while **Owning the Outcome**:

- Work autonomously, but flag irregularities rather than hiding them.
- Verify claims and data line by line. Do not turn a local measurement, owner report,
  projection, or proxy holdout into an organizer fact.
- Never copy, relabel, or repackage a prior submission to satisfy a file requirement.
  A candidate must be substantively generated by the current pipeline and pass the scoped
  uniqueness gate. Prior artifacts are for audit and learning only.
- Do not spend a competition slot on an idea that has not beaten the current spatially
  blocked holdout best under a predeclared rule.
- Keep Stage 1 coarse and non-dominant. It may be a diagnostic or broad-tile prior, but it
  must not hard-gate or dictate fine-scale Stage 2 without evidence.
- Use free public official or trusted sources for external data. Check provenance,
  availability, license, units, spatial alignment, and missingness before treating a source
  as viable.
- Keep the final single-band GeoTIFF and its one-file ZIP easy to find. It must satisfy the
  competition grid, CRS, dtype, footprint null behavior, and `[0,1]` requirements.
- The participant's DrivenData authentication is unavailable in this checkout. Never imply
  that an upload, score, or weekly slot exists unless the organizer actually returns it.
- Do not scrape, copy, or mirror leaderboard standings. Owner-reported and user-supplied
  score claims remain unverified unless tied to an organizer-authenticated artifact.

The fixed working branch for this session is `arena/c5badd9d-gemsdoe51`. Do not switch to,
create, or push another branch.

## Current primary — download only this file for a future upload

**Candidate:** fixed 50/50 H-H/H-D probability blend, emitted with STE line length 9,
continuity weight 0.35, and spacing 2.4 pixels. Stage 1 is retained as a diagnostic only;
the emitted artifact uses `stage1_weight=0.0`.

- **GeoTIFF:** [`docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif`](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif)
- **One-file ZIP:** [`docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.zip`](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.zip)
- **Checks receipt:** [`docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z-checks.json`](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z-checks.json)
- **Manifest:** [`data/submission_manifest.json`](data/submission_manifest.json)
- **SHA-256:** `9bd1e50d86114daa7c944d0c6d4f9f7cba6ba5070ae98ba5e45a965d78650777`
- **Predicted pixels:** `44,069`; total mass `44,069.0`
- **Submission name:** `GEMSDOE51-HH-HD-BLEND-STE-R347-20261007`
- **Note:** `H-H potential-field edge-termination/conductive-relay features plus H-D, fixed 50/50 probability blend, STE L9 w0.35 spacing 2.4; holdout-promoted but no organizer score claimed.`

### What “promoted” means here

The artifact passed a **local** six-fold spatially blocked proxy rule using the visible known-fault
catalogue, plus a source-aware uniqueness preflight, a q70 Stage-1 non-dominance check, and written
GeoTIFF checks. “Promoted” does not mean submitted, accepted, scored, or validated against the
hidden expert labels. The measured improvement belongs to the fixed blend; it does not prove that
pure H-H alone caused the gain.

Measured local promotion receipt:

| quantity | result |
|---|---:|
| primary mean proxy DTI | `0.2853406027` |
| H-D incumbent mean proxy DTI | `0.2816626603` |
| paired mean improvement | `+0.0036779424` |
| folds higher | `4/6` |
| maximum support Jaccard against scoped prior corpus | `0.2476890191` (limit `0.50`) |
| maximum support containment | `0.3970364655` (limit `0.60`) |
| q70 approved footprint share | `0.3005457512` |
| emitted share inside q70 approved area | `0.1635389957` |
| q70 emission lift over area share | `0.5441401018` |

These are repository-local proxy measurements. The official target consists of hidden expert labels;
the local holdout cannot establish performance on those labels.

## Artifact format and upload guide

The final TIFF is locally checked as:

- one band, `float32`;
- CRS `EPSG:32611`;
- template shape `3730 × 3292` and matching transform/bounds;
- finite in-footprint predictions in `[0,1]`;
- `NaN` outside the footprint with a NaN NoData tag;
- `44,069` predicted pixels and total mass `44,069.0`.

Run the repository check before handling the file:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_submission.py \
  docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif
```

A local format pass is not portal acceptance. If an entrant later uploads, they must use the exact
primary file or its one-file ZIP, verify the checksum, paste the unique name and note above, and
include an accurate narrative disclosure required by the official rules. The official submission
page is <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/>.

The current generated guide is [`docs/how-to-submit.html`](docs/how-to-submit.html), and the
one-click site card is [`docs/index.html`](docs/index.html). Do not upload the research-only H-G
artifact or any archived zero-outside TIFF.

## Stage 1 — current trace holdout, still coarse and separate

Stage 1 uses the approximate Kreemer et al. (2000) Eq. 3 fault-slip tensor to compare a geodetic
field with a catalogue-derived fault budget. The implementation is in
[`src/gems51/strain_budget.py`](src/gems51/strain_budget.py); the current runner is
[`scripts/run_stage1_trace_holdout.py`](scripts/run_stage1_trace_holdout.py).

A five-split trace holdout now removes complete held-out trace rows from the catalogue-derived
budget before calculating each field. The current configuration is recorded in
[`data/stage1_trace_holdout.json`](data/stage1_trace_holdout.json). The source slip-rate component
and absolute units remain unresolved; the default run uses the explicit vertical-rate convention,
provisionally treats values as mm/yr, and uses an explicit normal-fault fallback for unknown sense.

### Rank-space residual convention

The supplied dilatation and shear scalar layers are not source-verified to share units, signs, or
tensor definitions with the fault second invariant. Therefore the runner reports:

```text
rank(observed scalar) - rank(fault tensor second invariant)
```

for dilatation and shear. These are coarse rank diagnostics, **not** absolute strain-rate
subtractions. The combined residual diagnostic is the pixelwise maximum of the second-invariant,
dilatation, and shear rank residuals. It was not used to place the primary's Stage 2 points.

Current five-split means:

| field | mean Spearman rank | mean q70 lift |
|---|---:|---:|
| second-invariant deficit | `0.0402193` | `1.0929273` |
| dilatation rank residual | `0.0203654` | `1.0653125` |
| shear rank residual | `0.0305876` | `1.0722356` |
| combined residual diagnostic | `0.0352657` | `1.1476560` |
| geodetic-only control | `0.0992971` | `1.2469427` |

The geodetic-only control is stronger than the budget residuals in this diagnostic. This is why
Stage 1 is not allowed to dominate the fine detector: the promoted builder locks its operational
weight to `0.0`. The current reconciliation, including the old invalid formula-sensitivity audit,
is in [`evidence/stage1_reconciliation_20261007.json`](evidence/stage1_reconciliation_20261007.json).

The q70 diagnostic for the full primary is separately recorded in the manifest: only `16.3539%`
of emitted pixels lie in `30.0546%` of the footprint, a lift of `0.5441`. That is non-dominance,
not evidence that Stage 1 improves the competition target.

## Stage 2 — model and holdout evidence

The H-D incumbent is the fine-scale detector baseline. The H-H arm adds the exact
potential-field edge-termination / conductive-relay feature construction described in the active
hypothesis slate. The current primary blends the two predicted probability fields 50/50 and uses
one fixed STE emission rule.

The promotion evidence is [`evidence/hh_blend_holdout.json`](evidence/hh_blend_holdout.json):

- same six spatial folds and visible known-fault proxy truth;
- same ratio `M/|G| = 3.47`;
- fixed blend weight `H-H = 0.5`;
- fixed STE L9 / `w=0.35` / spacing `2.4`;
- improvement over H-D on 4 of 6 folds.

The H-H gate sweep showed that a Stage-1 soft/hard gate did not justify an operational nonzero
weight. Do not silently rerun an old H-D soft candidate: the earlier `w=0.20` support was too
similar to an existing artifact and failed uniqueness before writing.

## Hypotheses and research record

The active operator-level slate is [`evidence/hypothesis_slate_20261007.json`](evidence/hypothesis_slate_20261007.json)
and its generated view is [`docs/hypotheses.html`](docs/hypotheses.html). The important status is:

1. **H-G magnetic/gravity crossing add-on:** tested and rejected on the matched proxy holdout;
   research-only despite passing its scoped uniqueness audit.
2. **H-H potential-field terminations plus conductive relay bridge:** implemented as a model arm
   and evaluated in the fixed 50/50 blend. The blend passed the local rule, but no pure-H-H causal
   claim is made.
3. **H-I directional conductivity cross-edge contrast:** not tested; lower priority.
4. **H-J earthquake-density modulation of structural edges:** not tested and blocked pending
   source-band semantics.

The prior H51-X1 partial magnetic/gravity edge-normal test lost to H-D (`0.2796713` vs `0.2816627`,
3/6 folds higher) and does not falsify the broader family. The historical H-M and STE-only positive
point estimates remain research leads; their packaged variants fail the refreshed uniqueness audit.

Research notes and hypothesis decisions:

- [`knowledge/02_research_digest_2026-10-07.md`](knowledge/02_research_digest_2026-10-07.md)
- [`knowledge/02_gemsdoe32_study_and_candidates_2026-10-07.md`](knowledge/02_gemsdoe32_study_and_candidates_2026-10-07.md)
- [`knowledge/preregistration-2026-10-07.md`](knowledge/preregistration-2026-10-07.md)
- [`registry/hypotheses.json`](registry/hypotheses.json)
- [`registry/claims.json`](registry/claims.json)
- [`registry/irregularities.json`](registry/irregularities.json)

## Sources and provenance

Use the official or trusted source links below for future review. Local mirrors and owner-supplied
files are hash-checked where recorded, but are not organizer-authenticated.

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description, metric, data, and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData rules / GEMS Prize PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS / GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [Kreemer et al. (2000), public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf)
- [NBMG QFaults INGENIOUS schema](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson)
- [USGS Siler (2022) ScienceBase release](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d)
- [EPSG:32611](https://epsg.io/32611)

## Build and review commands

The canonical current writer is [`scripts/build_submission_hh_blend.py`](scripts/build_submission_hh_blend.py).
It is fail-closed around the frozen 50/50 promotion receipt, reference coverage, uniqueness,
Stage-1 non-dominance, GeoTIFF format, and final-byte checks. The legacy
[`scripts/build_submission.py`](scripts/build_submission.py) is an H-D-only historical path and
is not the current primary writer.

The generated site is built and checked with:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_site.py
PYTHONPATH=src .venv/bin/python scripts/check_site.py
```

The final review should also include:

```bash
python -m py_compile scripts/run_stage1_trace_holdout.py \
  scripts/build_submission_hh_blend.py scripts/build_site.py scripts/check_site.py
PYTHONPATH=src .venv/bin/pytest -q
PYTHONPATH=src .venv/bin/python scripts/check_submission.py \
  docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif
```

Before changing the primary, fetch the 21 commit-pinned family references with
[`scripts/fetch_gate_refs.sh`](scripts/fetch_gate_refs.sh). References are comparison inputs only;
never use them as candidate pixels.

## Limitations and irregularities that must remain visible

- The hidden expert labels are unavailable. All local DTI/AUC/holdout values are visible-known-fault
  rediscovery proxies, not organizer scores.
- `SLIPRTNUM` units and component semantics are not fully source-authenticated. Absolute Stage-1
  nanostrain claims are therefore provisional; rank comparisons are used where appropriate.
- The source scalar geodetic layers do not have a verified common invariant identity. Do not claim
  dimensional dilatation/shear subtraction from the fault tensor.
- Scoped uniqueness against the local inventory is not a global proof of uniqueness.
- A locally format-valid file is not proof that DrivenData will accept it.
- The final primary has not been uploaded. There is no claimed weekly slot, portal receipt,
  organizer score, leaderboard position, or expert-label result.
- H-G, H-M, old STE-only, and archived H-D variants remain research/audit artifacts and must not
  be relabeled as the current primary.

If a future review finds a contradiction, stop the promotion path, record the irregularity in
`registry/irregularities.json`, and do not loosen a gate merely to obtain a file.
