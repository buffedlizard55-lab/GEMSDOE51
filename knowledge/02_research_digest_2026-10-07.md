# Research digest — session 2026-10-07 (GEMSDOE51)

> **Attribution and status correction:** a prior claim linked a public 0.2778 result to
> GEMSDOE32 H33-2-B2. That attribution is **unsupported and contradicted by the sibling's own
> UNSCORED label and 0.2747 modelled projection**. No verified artifact-to-score mapping exists.
> The official Terms of Use prohibits leaderboard monitoring/copying without permission, so this
> repository stores no standings. See `evidence/score_attribution_audit.json`. This is a
> historical research digest, not current upload authorization.

Every line below is either **official** (read from a competition/USGS/publisher page during
this session, with the link), **measured-here** (produced by a script in this repository in
this session, with the file that holds the number), or **inherited** (carried from an earlier
session, labelled as such). Nothing is recalled from memory without a check.

---

## 0. What changed this session, in one paragraph

A later repository synchronization recorded auto-context, strike-coherent emission, and H-M
screens. The completed H-H model arm was then evaluated in the predeclared fixed 50/50 H-H/H-D
blend with STE: mean visible-known-fault proxy DTI **0.2853406** versus H-D **0.2816627**, paired
Δ **+0.0036779**, positive in **4/6** folds. A new full-catalogue GeoTIFF passed the local format,
scoped uniqueness, and Stage-1 non-dominance gates. It is the current primary artifact, but it has
not been uploaded and no DrivenData score or portal acceptance is claimed. This result is for the
blend; it is not evidence that pure H-H alone caused the gain. Stage 1 remains diagnostic only with
weight 0.0. H-M and the old STE-only screen remain noisy research leads, and H-G+H-D remains below
H-D.

---

## 1. Official facts re-verified this session (not inherited)

| # | fact | source read on 2026-10-07 |
|---|---|---|
| 1 | Metric is the distance-weighted Tversky index, α=0.2, β=0.8, triangular kernel `k(d)=max(1-d/R,0)`, **R = 300 m = 3 px** | [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric) |
| 2 | Worked example on that page: TP_w=3.00, FP_w=1.89, FN_w=2.00 → DTI=0.60 | same page |
| 3 | Submission = single-band **float32** GeoTIFF, EPSG:32611, 100 m, same bounds, **values between 0 and 1**, outside bounds null/NaN | same page, "Submission format" |
| 4 | Test set for the Initial Prize Round = faults experts identified that are **not** in the public USGS database; the Final Round rescores the *same* submission against an expert-expanded label set built by reviewing **every team's** submission | same page, "Competition structure" |
| 5 | The reference solution trains a U-Net on patches with `FAULT_LABELS_PATH = data/labels.tif` and a Tversky loss at α=0.2, β=0.8 | [reference solution notebook](https://github.com/drivendataorg/gems-prize-reference-solution), cells 2, 6, 16 |
| 6 | The official leaderboard is an external page and is not mirrored or monitored by this repository under the Terms of Use; a public participant row without its scored artifact cannot support a scientific attribution. | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) and [Terms of Use](https://www.drivendata.org/termsofuse/) |

**Correction to the brief.** A historical target score in the owner brief is not a current or
verified leaderboard claim. The official board is linked but not mirrored here. Without an
organizer-authenticated artifact, no public score can be scientifically attributed to a TIFF or
method, and no local target-to-beat number is recorded.

---

## 2. IR-51-08 is resolved: `labels.tif` is *supposed* to equal `existing_faults.tif`

Previous session's top-priority open question was that the mirrored `labels.tif` and
`existing_faults.tif` are byte-identical (sha256 `7ba308cc…`, 425,830 B both), and it was
suspected the mirror was wrong and "the real target distribution has never been seen".

It is not a mirror fault. The competition's own framing is that *"ground truth data for
currently known faults is publicly available"* and that the hidden test set is the set of
expert-identified faults **absent from** that public database
([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
The organizer's reference solution trains directly on `data/labels.tif` as the positive class
([notebook](https://github.com/drivendataorg/gems-prize-reference-solution), cell 6:
`FAULT_LABELS_PATH = Path("data/labels.tif")`, `y_orig[y_orig < 1] = 0`). So `labels.tif`
*is* the known-fault catalogue, by design, and there is no hidden training target to recover.

Measured here (`data/prepared/prepared_manifest.json`, produced by `scripts/prepare_data.py`):

```
footprint_pixels      5,167,373
catalogue_pixels         60,988
analysable_pixels     5,164,300     (3,073 footprint cells miss at least one of the 19 bands)
labels outside footprint are -1 : True
```

**Consequence, and it is the central limitation of every number in this repository:** the only
label set we can train or validate against is the catalogue itself. Every local score is a
*rediscovery* proxy. Recorded as **IR-51-11** (replaces IR-51-08, which is closed).

---

## 3. The metric is a budget, and the budget is already tuned

From the published definitions, `FN_w = |G| - TP_w`, and since `1 - β = α`:

```
DTI = TP / (TP + α·FP + β·FN) = TP / ( α·(TP + FP) + β·|G| )
```

Both identities are asserted numerically against a brute-force transcription of the published
equations in `tests/test_metric.py` (11 tests, all passing; the worked example reproduces to
0.6036 against the published 0.60).

Write `m = M/|G|` (emitted pixels per truth pixel), `c = TP/M` (credit per emitted dot) and
`b = B/M` where `B = Σ_x p(x)·max_g k(d(x,g))` is the self-kernel at the emitted pixels. Then

```
DTI = c·m / ( 0.2·m·(c + 1 − b) + 0.8 )
```

**Measured on fold 0 of the blocked holdout** (`evidence/emission_geometry.json`):
`|G| = 12,803`, `M = 44,426`, `m = 3.47`, `c = 0.1217`, `b = 0.063` → DTI 0.2752, which the
closed form reproduces exactly. Differentiating in `m` gives the stopping rule

```
emit one more dot  ⇔  marginal credit  >  0.2·DTI·(1 − b) / (1 − 0.2·DTI) ≈ 0.056
```

and the measured sweep (`data/emission_sweep.json`, 6 folds × 6 ratios × 5 radii, inherited,
plus this session's re-measurement at ratios 2.5/3.47/4.5/6) puts the optimum at **m ≈ 3.5**.
Mass is therefore **not** where the remaining score is.

**What the local metric algebra can and cannot say.** It can express how DTI changes with
weighted true-positive credit, false-positive cost, and emission mass for a given hidden `|G|`.
It cannot translate an external participant score into a required credit-per-dot target here:
the exact scored raster, hidden labels, and artifact-to-score mapping are unavailable, and this
repository does not store leaderboard standings.

---

## 4. Why a per-pixel model is the wrong shape for this problem (and the fix)

The scored object is a *trace*: a thin, locally straight, kilometre-scale curve. A gradient
boosted tree over per-pixel features cannot express "this pixel sits on a 5 km lineament",
so it ranks isolated high-amplitude pixels above long, low-amplitude, continuous ones — and
low-amplitude-but-long is precisely the population a scarp-amplitude-biased catalogue misses.
The reference solution buys that context with a U-Net over 128×128 patches; this environment
has 2 CPU cores and 3 GB of RAM, so a U-Net is out of reach.

**Auto-context** buys the same thing for a tree. Tu & Bai, *Auto-Context and Its Application
to High-Level Vision Tasks and 3D Brain Image Segmentation*, IEEE TPAMI **32**(10), 1744–1757
(2010), [doi:10.1109/TPAMI.2009.186](https://doi.org/10.1109/TPAMI.2009.186): train a level-1
classifier, summarise its belief map over multiple neighbourhoods, append those summaries to
the raw features, train level-2. The eight summaries used here are in
`gems51.autocontext.CONTEXT_NAMES`.

Leakage control is the whole game in stacking. The level-2 *training* rows must not see a
level-1 belief that was fitted on their own labels. We cross-fit over two contiguous slabs —
Breiman, *Stacked regressions*, Machine Learning **24**(1), 49–64 (1996),
[doi:10.1007/BF00117832](https://doi.org/10.1007/BF00117832) — and contiguity (not a random
split) is required here because a randomly interleaved split would let a level-1 model
memorise a trace in one part and be asked about the same trace 100 m away in the other.

---

## 5. Emission geometry: three standard transforms, one metric argument

`TP_w` sums over the *truth* and takes a max over nearby predictions. Two consequences:

* a second dot inside the same 3 px neighbourhood earns ≈ 0 and costs a full unit of mass;
* a dot on the crest of a correct lineament collects `1 + 2/3 + 1/3` on each side along the
  trace (≈ 2.33), while a dot 2 px off the crest collects at most `k(2) = 1/3`.

So localisation across strike is worth up to ~3× in credit per unit mass, and spacing along
strike should be exactly the kernel support. The incumbent rule — isotropic greedy NMS at
2.4 px on the raw belief — is blind to both. `gems51.trace_emission` replaces it with:

1. multi-scale **Frangi vesselness** of the belief field — Frangi, Niessen, Vincken &
   Viergever, *Multiscale vessel enhancement filtering*, MICCAI 1998, LNCS 1496, 130–137,
   [doi:10.1007/BFb0056195](https://doi.org/10.1007/BFb0056195);
2. an **along-strike line accumulator** over 12 orientations — Vanderbrug, *Line detection in
   satellite imagery*, IEEE Transactions on Geoscience Electronics **14**(1), 37–44 (1976),
   [doi:10.1109/TGE.1976.294466](https://doi.org/10.1109/TGE.1976.294466);
3. optional **across-strike non-maximum suppression** — the thinning step of Canny,
   *A computational approach to edge detection*, IEEE TPAMI **8**(6), 679–698 (1986),
   [doi:10.1109/TPAMI.1986.4767851](https://doi.org/10.1109/TPAMI.1986.4767851);
4. greedy **along-trace spacing** at the kernel support.

Gaps in the input are handled by normalised convolution — Knutsson & Westin, *Normalized and
differential convolution*, CVPR 1993, 515–523,
[doi:10.1109/CVPR.1993.341081](https://doi.org/10.1109/CVPR.1993.341081) — so a derivative is
never estimated by smearing zeros across a data hole.

**Recorded six-fold screen** (`evidence/emission_geometry.json`, detector held fixed, mass
matched): STE L9 (`w=0.35`, NMS spacing 2.4 px) averaged **0.283603** versus **0.281639** for
isotropic NMS (paired Δ +0.001963; 4/6 folds higher; approximate paired 95% t interval
−0.00166 to +0.00559). The interval includes zero. A refreshed uniqueness audit fails for the
packaged STE TIFF because its NaN-format twin has identical support. Treat the sweep as a noisy
research lead, not a robust win or competition score.

---

## 6. What the hidden "new faults" probably look like — the geology, with sources

The GeoDAWN footprint is the Walker Lane and an east-trending arm into north-central Nevada
([USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)).
The INGENIOUS project's own description of how Quaternary faults were extended and
re-characterised in exactly this footprint is explicit about method:

> "LiDAR and hill shades were utilized to identify the extent and location of Quaternary
> faults in combination with other datasets. Available one-meter LiDAR from the GeoDAWN
> (Geoscience Data Acquisition for Western Nevada) project was provided by the USGS… Gravity
> surveys were the most useful geophysical dataset in defining the extent and geometries of
> the major Quaternary faults… where basin fill conceals many faults and geothermal upwellings
> may have altered rocks and generated low magnetic and low resistivity anomalies."
>
> — Giddens et al., *Step-overs in the Great Basin*, PROCEEDINGS, 50th Workshop on Geothermal
> Reservoir Engineering, Stanford University, 2025,
> [PDF](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf)

Three operational implications, each testable here:

1. **1 m lidar scarps dominate.** The mirrored `lidar_scarp_features_u8.tif` covers
   **3,894,460** of the 5,167,373 footprint pixels (75.4 %) and holds **79.5 %** of the
   catalogue — a lift of only **1.054**, so lidar coverage alone is a weak prior and is *not*
   worth gating on (measured here, this session).
2. **Gravity defines concealed range-front geometry.** The standard USGS tool for that is the
   horizontal-gradient-maximum ("maxspot") method of Blakely & Simpson, *Approximating edges
   of source bodies from magnetic or gravity anomalies*, Geophysics **51**(7), 1494–1498
   (1986), [doi:10.1190/1.1442197](https://doi.org/10.1190/1.1442197)
   ([USGS publication record](https://www.usgs.gov/publications/approximating-edges-source-bodies-magnetic-or-gravity-anomalies)).
   The repository currently uses the gravity horizontal gradient as an *amplitude* only; the
   maxima-tracking step, and its stacking across upward-continuation heights, is **not**
   implemented. See hypothesis H-51-J.
3. **Geothermal upwelling makes magnetic lows and resistivity lows**, not highs — so a
   detector that treats |magnetic gradient| symmetrically is throwing away the sign that
   matters for the geothermally relevant subset of faults.

---

## 7. Instruments in this repository, and what each is good for

| instrument | script | truth | answers | known bias |
|---|---|---|---|---|
| spatially blocked holdout | `scripts/run_experiments.py`, `scripts/run_autocontext.py` | catalogue inside a held-out 1/9 block | "does feature set A rank better than B?" | in-block truth density is several × the regional average; the block contains *no* mapped fault, so it cannot test behaviour near known faults |
| emission-geometry sweep | `scripts/run_emission_geometry.py` | same | "does emission rule A beat B at identical detector and identical mass?" | inherits the above |
| off-catalogue A/B split | `scripts/run_offcatalogue_ab.py` | half the catalogue's *fault systems*, hidden, detector trained on the other half with the hidden half left in the negative class | "does the rule find structures the training catalogue does not contain, with the visible ones masked?" | A and B come from the same compilation and interleave; the `halo_ring` control measures how much that flatters a halo rule |
| Stage-1 trace holdout | `scripts/run_stage1_trace_holdout.py` | 1/5 of mapped traces | "is the coarse geodetic prior informative at tile scale?" | no model is fitted, so it measures the prior only |

None of them is a competition score. The organizer has declined to disclose the provenance, fault types or
coverage of the hidden labels, so **no** offline instrument can be shown to match the hidden
label style (inherited, IR-51-05). **Stage-1 evidence is additionally under reconciliation:**
`data/stage1_trace_holdout.json` is a historical result under the pre-audit unsigned/implicit
formula, while the four-scenario `evidence/stage1_formula_audit.json` runner retained held-out
trace rows in its catalogue-derived budget and is not a valid holdout. The current signed,
rate-selectable implementation has not been rerun on restored inputs. Until then, report Stage 1
only as a coarse-prior research question; see `evidence/stage1_reconciliation_20261007.json`.

---

## 8. Open, named, and obtainable external data (for the next session)

All of these are free and official. None is reachable from this sandbox (egress is
allow-listed to PyPI + github.com + api.github.com, IR-51-03), so each needs a mirroring step
on an unrestricted machine before it can be used.

| what | why it would help | official source |
|---|---|---|
| USGS 3DEP **1 m** DEM tiles for the GeoDAWN footprint | the experts mapped from 1 m hillshade; our lidar features are pre-aggregated to 100 m and lose the scarp | the competition's own `1m_DEM_links.csv`; [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) |
| USGS Quaternary Fault and Fold Database vector | exact trace geometry, slip rate and slip sense attributes (the Kostrov term in Stage 1 currently uses the GDR-1391 CSV mirror) | <https://www.usgs.gov/programs/earthquake-hazards/faults> |
| GeoDAWN magnetic/radiometric **grids** at native resolution | the competition's 100 m stack is already resampled; maxspot tracking wants the native grid | <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> |
| USGS SGMC (state geologic map compilation) | lithology, to normalise radiometric ratios per unit | <https://mrdata.usgs.gov/geology/state/> |
| NGDB / NURE radiometric | independent check on the K/Th alteration ratio | <https://mrdata.usgs.gov/nure/> |

---

## 8. Current primary and Stage-1 residual reconciliation — measured here

The current primary is [`docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif`](../docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif), with a matching one-file ZIP and receipt in `docs/downloads/`. Its SHA-256 is `9bd1e50d86114daa7c944d0c6d4f9f7cba6ba5070ae98ba5e45a965d78650777`; it contains 44,069 predicted pixels, is a single-band float32 EPSG:32611 GeoTIFF, and passes the local `[0,1]`/NaN-outside checks. The fixed 50/50 H-H/H-D blend plus STE passed the frozen six-fold local promotion rule. This is a local visible-known-fault proxy result; no organizer upload, score, or acceptance is claimed.

The current trace-held-out Stage-1 runner now reports the requested dilatation and shear controls. Held-out trace rows are removed from the catalogue-derived budget before every field is calculated. Because the scalar geodetic layers and the fault-tensor invariant do not have a source-verified shared convention, the controls are rank residuals `rank(observed scalar) - rank(fault tensor second invariant)`, not absolute strain subtraction. Mean results from `data/stage1_trace_holdout.json` are:

| field | mean Spearman rank | mean q70 lift |
|---|---:|---:|
| second-invariant deficit | 0.0402 | 1.0929 |
| dilatation rank residual | 0.0204 | 1.0653 |
| shear rank residual | 0.0306 | 1.0722 |
| combined residual diagnostic | 0.0353 | 1.1477 |
| geodetic-only control | 0.0993 | 1.2469 |

The combined residual is an auditable diagnostic, not an approved fine-scale prior. The promoted artifact uses `stage1_weight=0.0`; Stage 1 remains coarse/non-dominant and does not hard-gate Stage 2. The reconciliation is recorded in [`evidence/stage1_reconciliation_20261007.json`](../evidence/stage1_reconciliation_20261007.json).
