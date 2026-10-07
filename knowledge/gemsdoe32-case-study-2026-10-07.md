# GEMSDOE32 result review and GEMSDOE51 Stage-1/Stage-2 decision

**Review date:** 2026-10-07 (UTC)
**Purpose:** analyze the GEMSDOE32 result described on the sibling project's public pages; record geological hypotheses and their tests; decide whether any new GEMSDOE51 GeoTIFF is justified.
**Evidence policy:** this record separates official rules, owner-reported claims, and measurements reproduced in this repository. It does not infer causation from an unscored projection, and it contains no copied leaderboard standings.

## 1. What GEMSDOE32 actually reports

GEMSDOE32's public index page presents the artifact named `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, with 37,654 positive pixels. The same page gives the proposed submission name `GEMSDOE32-H33-2-B2`, describes removing dots within 200 m of the known-fault catalogue, and reports a **projected 0.2747**. Crucially, the page labels the artifact **UNSCORED** and says that no organizer score exists for any artifact in that repository. Its `+0.004870` over a `0.2708` base and its “4/4 folds” / “safety factor 2.08” are owner-reported local or model-based calculations, not a score returned by DrivenData for those bytes.

**Interpretation:** the reported projection is not evidence that H33-2-B2 achieved a high official score, and it cannot establish that the B=2 prune caused any leaderboard result. The artifact is a useful design case, not a verified performance result. The earlier base value is also not treated here as organizer-authenticated.

Reviewable owner sources:

- [GEMSDOE32 executive summary / artifact status](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
- [GEMSDOE32 research and instrument limitations](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/research.html)
- [GEMSDOE32 candidate hypotheses](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/hypotheses.html)
- [GEMSDOE32 irregularity register](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/irregularities.html)

Those are owner-published sources, not organizer records. They are used only to establish what that project says about its own artifact and methods.

## 2. A defensible mechanism, not a causal claim

The [official problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) defines a distance-weighted Tversky index with `alpha=0.2`, `beta=0.8`, and a 300 m triangular kernel. In the binary setting used by the local holdouts, write `T=TP_w`, `F=FP_w`, and `K=|G|`; since `FN_w=K-T`,

\[
DTI=\frac{T}{T+0.2F+0.8(K-T)}
   =\frac{T}{0.2(T+F)+0.8K}.
\]

This objective can favor sparse, high-credit predictions. Removing a dot is beneficial only when the credit lost is smaller than the false-positive mass cost avoided, with the answer depending on the hidden truth and its distance kernel. A 200 m removal rule is therefore a plausible *testable* hypothesis: mass near mapped faults may be less likely to match newly identified faults, and the official problem says its initial hidden test faults are not in the existing public USGS database.

That rationale does not prove H33-2-B2's projected gain. A causal attribution would require a controlled comparison on the relevant target labels or an organizer-returned score tied to each exact artifact. The sibling page explicitly says that score does not exist. No claim is made that pruning near known faults produced a specific official score.

## 3. Stage 1: exact formula and its limits

The source used for the fault-slip tensor is Kreemer, Haines, Holt & Blewitt (2000), Eq. (3), [public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf):

\[
\dot{\varepsilon}_{ij}
=\frac{1}{2}\sum_k\frac{L_k\dot{u}_k}{A\sin\delta_k}\,m_{ij}^{k},
\qquad m_{ij}^{k}=n_i^k s_j^k+n_j^k s_i^k.
\]

Here `L_k` is the fault-segment length contributing to tile `A`, `u_dot_k` its slip rate, `delta_k` its dip, `n` the unit fault-plane normal, and `s` the unit slip direction. For a vertical pure strike-slip segment, the local shear coefficient is `L*u_dot/(2*A*sin(dip))`. For a pure dip-slip segment, horizontal projections of `n` and `s` contribute `sin(dip)*cos(dip)`; after the prefactor and symmetric tensor sum, the horizontal extension/contraction coefficient is `L*u_dot*cos(dip)/A`. Those are the coefficients in [`src/gems51/strain_budget.py`](../src/gems51/strain_budget.py).

The implementation builds a horizontal tensor from the rasterized trace geometry, nearest trace-centroid slip-rate assignment, simplified slip-sense/dip categories, and actual footprint-supported tile area. It does **not** have complete segment rake or per-trace dip measurements and is not a full geodetic inversion. The copied slip-rate field is provisionally treated as mm/yr; the NBMG layer schema lists `SLIPRTNUM` but does not declare units, and the linked GDR v2 field-definition text has not been audited locally. Absolute strain values are therefore not source-validated. A uniform slip-rate rescaling leaves the current model-field quantile ranks unchanged, but mixed units, categories, or record-specific errors need not. The competition geodetic second-invariant convention cannot be exactly recovered from its supplied dilatation and shear layers. We therefore use quantile-ranked fields and avoid unsupported subtraction of observed scalar dilation/shear from a fault tensor invariant.

### Corrected Stage-1 holdout evidence

The corrected five-split trace holdout removes complete trace-table rows associated with held-out catalogue pixels before constructing the fault budget. This avoids reusing those trace records in the held-out fold. Results in [`data/stage1_trace_holdout.json`](../data/stage1_trace_holdout.json):

| Measure | Corrected mean | Context |
|---|---:|---|
| Deficit Spearman vs held-out fault density | 0.03916 | Weak rank relation |
| Geodetic-only Spearman | 0.09930 | Higher than deficit |
| Dilation-only Spearman | 0.05288 | Higher than deficit |
| Shear-only Spearman | 0.09157 | Higher than deficit |
| Deficit top-50% lift | 1.08290 | Small enrichment over area share |
| Geodetic-only top-50% lift | 1.23864 | Better than deficit |
| Deficit top-20% lift | 1.19644 | Modest; still not a fine locator |
| Geodetic-only top-20% lift | 1.27319 | Better than deficit |

Stage 1 is **weak and not independently useful as an emission rule**. In six-fold two-stage results ([`data/two_stage_results.json`](../data/two_stage_results.json)), Stage-1-only randomized DTI is 0.14810 versus 0.18615 for uniform, using the provisional `g_hidden=12,700` full-map mass assumption (not an organizer count); a q50 hard gate drops Stage 2 from 0.28164 to 0.18153. The hard gate is rejected. Soft weights are only marginal: `w=0.10` mean DTI 0.28213, positive against ungated in 3/6 folds; `w=0.20` mean 0.28212, positive in 4/6, paired gain +0.000483. These are proxy values on known-fault holdout labels, not competition scores.

The Stage-1 evidence is a broad-tile prior diagnostic only. It must not dominate the fine-scale candidate locations.

## 4. Stage 2: fine-scale holdout and candidate outcome

The current fine-scale incumbent is H-D, six spatial folds, 3x3 contiguous blocks with a 1.2 km boundary band removed from training, and emission/scoring at matched mass ratio `M/|G|=3.47`:

| Candidate | Mean proxy DTI | Mean AUC | Paired/fold result | Decision |
|---|---:|---:|---:|---|
| H-D baseline | 0.2816627 | 0.6726183 | six-fold incumbent | Baseline |
| H51-X1 narrowed magnetic/gravity edge-normal implementation | 0.2796713 | 0.6666622 | delta -0.0019913; wins 3/6 | **Fail; do not promote this implementation** |
| H-D + soft prior `w=0.20` | 0.2821227 | — | +0.000483 paired mean; wins 4/6 | Numeric holdout screen passed; failed uniqueness |

The proposed `w=0.20` field was produced in memory using the same full-fit H-D build settings, before any output file was created. The independent Stage-1 dominance diagnostic at top-half tile approval gave area share 0.50154, emission share in approved tiles 0.49447, and lift 0.98592. This indicates that Stage 1 did not dominate placement. However, positive-support overlap with the existing local soft-`w=0.10` output was **Jaccard 0.86130** and containment of the candidate within that prior was **0.92548**, exceeding the local uniqueness limits (0.50 and 0.60). The builder stopped at preflight and wrote no TIFF. This was the correct outcome: the marginal metric gain is not a license to reissue nearly the same dot map.

A narrowed H51-X1 implementation was tested before any competition slot was used. The plan listed RTP, TMI HG/VG, and gravity HG/VG derivative products, but the measured feature builder used only rank-normalized total magnetic (`comp_tmi`) and isostatic gravity (`comp_iso_grav_anom`) as inputs to the new transform. Derivative bands remained in the common baseline stack but were not inputs to that transform. This partial test failed the frozen rule and was not promoted; it does not falsify every version of the broader preregistered layer-family hypothesis. Full folds and feature counts are in [`data/holdout_H_X1.json`](../data/holdout_H_X1.json); the frozen screen plus appended outcome is in [`preregistration-2026-10-07.md`](preregistration-2026-10-07.md).

## 5. Ranked geological hypotheses and data requirements

Ranks are qualitative expected value per implementation cost, not promised DTI gains. The local target is a known-fault proxy, so it cannot validate that a proposed signature identifies genuinely new fault styles. Numeric benefits are deliberately withheld where no valid experiment exists.

| Rank / ID | Layers and physical signature | Why it could find missing faults | Novelty in this repository | Expected benefit / cost | External-data needs and status |
|---|---|---|---|---|---|
| **1 — H51-X1: cross-physics edge-normal concordance** | Preregistered family: `rtp`, `tmi_hg/vg`, `iso_grav_anom`, and gravity gradients; normalize edge strength and compare magnetic/gravity edge-normal orientation at matched 200 m and 500 m scales. **Measured new-transform inputs:** rank-normalized `comp_tmi` and `comp_iso_grav_anom` only; derivative products remained in the common baseline stack but were not inputs to this transform. | Magnetic susceptibility and density contrasts can persist beneath cover; matching edge orientation could be more structure-specific than a broad anomaly or terrain-habitat mask. This is a geological rationale, not a measured causal result. | Existing features include single-field lineament transforms; H-E tests multi-physics coincidence but not magnetic/gravity edge-*orientation* agreement at matched scale. | **Moderate, uncertain upside; medium cost.** The narrowed measured implementation underperformed H-D and failed promotion; the broader listed band family remains untested. | No extra download; the required base bands are competition features. The exact hidden target remains unavailable locally. |
| **2 — H51-X2: paired scarp-face asymmetry** | Existing 1 m DEM directional up-face/down-face, cross-face, step, and relief layers; use polarity/asymmetry ratios rather than raw scarp amplitude. | An asymmetric surface step may trace a fault where amplitude alone is weak; ratios may suppress absolute relief variation. Surface expression and preservation can still confound it. | H-D targets directional gradient coherence/persistence; no paired face-asymmetry ratio was in the tested feature set. | **Low-to-moderate, uncertain upside; low cost.** Not tested. | Uses the locally mirrored DEM-derived layers; provenance is hash-checked but not organizer-authenticated. |
| **3 — H51-X3: geothermal manifestation aligned to an independent lineament** | INGENIOUS/GDR well-spring coordinates, temperature and geochemistry joined to a separately detected structural edge; target a point-to-lineament alignment, not a broad thermal polygon. | A spatially coherent set of warm springs or wells aligned on a lineament may indicate a permeable fluid pathway and thus a fault, rather than merely favorable geothermal habitat. | No current detector feature uses the point chemistry/temperature and its directional relationship to a lineament. Prior broad habitat approaches are weak evidence against broad emission, not a verdict on this constrained alignment test. | **Low-to-moderate, high uncertainty; medium cost.** Not tested. | Requires validating owner-mirrored `gdr_wellspring_in_footprint.csv` provenance, duplicates, units, coordinate transforms, and source row IDs before feature construction. The public [GDR 1391 record](https://gdr.openei.org/submissions/1391) describes well/spring chemistry resources; the local mirror itself is not organizer-authenticated. |
| **4 — H51-X4: stress-compatible structural corridors** | USGS Siler slip-/dilation-tendency polygons/attributes joined to independently detected lineament orientation; use as a coarse prior only. | Fault orientations favorable for slip or dilation under the ambient stress field may be more permeable; a corridor aligned with a geophysical edge could identify a hidden continuation/splay. | Existing Stage 1 is a geodetic-vs-mapped-fault budget, not a local stress/tendency layer. | **Potentially moderate, very uncertain; high cost and blocked.** Do not promote from rationale alone. | The official [USGS ScienceBase record, DOI 10.5066/P9YL58W6](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) identifies the release, but the archive download and field definitions/units were not validated in this checkout. The file must be obtained, hashed, inspected, spatially joined, then tested on the same blocked holdout. |

## 6. Submission, rules, and no-monitoring policy

The [official submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) requires EPSG:32611, 100 m resolution, matching bounds, a single float32 band with values in `[0,1]`, and null/NaN outside bounds. `src/gems51/submission.py` now encodes NaN outside the footprint, tags NaN NoData, and verifies the written bytes. This proves only local format conformance; it does not prove portal acceptance.

Section 3.2 of the [September 2026 GEMS Prize Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) allows generative AI but requires a narrative (outside the word count) stating whether and how it was used, including across submission elements. A future submission narrative must accurately disclose the actual tool use and must be reviewed before entry.

DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) prohibits use of automated means to monitor/copy site content and manual monitoring/copying without prior written consent. This repository implements no leaderboard scraper and retains no leaderboard standings. No written consent was located. Do not add a standing/monitoring feed unless that consent is first obtained.

## 7. Decision and next work

- **No new TIF was generated**; no weekly submission slot was consumed.
- The H-D `w=0.20` setting cleared the exact numeric gate but failed uniqueness. The prior `w=0.10` output remains only a historical reference; it is not being re-issued.
- The narrowed H51-X1 implementation failed; the broader preregistered layer family was not fully tested, and H51-X2–X4 remain untested. Any future submission needs a genuinely distinct candidate that clears a prewritten holdout rule and all format/uniqueness/dominance checks.
- The Siler data is not locally validated. GDR well/spring mirror provenance and point-level units/duplicates need audit before H51-X3.
- Keep all local DTI/AUC values explicitly labeled as proxy. No organizer score is claimed for any GEMSDOE51 artifact.
- The static site should show no current download until an eligible file exists; legacy zero-outside TIFFs must not be linked or submitted.

## Source register for manual review

1. [DrivenData problem description, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
2. [GEMS Prize Official Rules, September 2026 (AI narrative disclosure, §3.2)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
3. [DrivenData Terms of Use (automated/manual monitoring and copying)](https://www.drivendata.org/termsofuse/)
4. [Kreemer et al. (2000), Eq. 3, public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf)
5. [INGENIOUS / GDR submission 1391, DOI 10.15121/1881483](https://gdr.openei.org/submissions/1391)
6. [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
7. [USGS Siler slip-/dilation-tendency release, DOI 10.5066/P9YL58W6](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d)
8. [GEMSDOE32 owner index and unscored status](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
9. [GEMSDOE32 owner research page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/research.html)
10. [GEMSDOE32 owner hypotheses page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/hypotheses.html)
11. [GEMSDOE32 owner irregularities page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/irregularities.html)
