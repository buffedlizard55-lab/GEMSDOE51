# GEMSDOE51 — DOE GEMS Prize Challenge

> **Start every project session here.** This README is the persistent project brief, current evidence ledger, and handoff. Keep the values **Maximize P(Win)** and **Own the Outcome** focal: choose experiments for expected value rather than slot volume, and own the full chain from scientific claim through format verification.

## Persistent project brief

Build an auditable, scientifically grounded fault-discovery workflow for DrivenData's DOE GEMS Prize (#306). Review the competition brief and repository before making changes. Rank **3–5 distinct geological hypotheses** before implementation; for each, record the layer(s), physical signature, why it could indicate an uncatalogued fault, novelty versus this repository, expected benefit/cost, and external-data requirements. Preregister the leading candidate and test it on a spatially blocked holdout before any competition entry. Separate coarse Stage 1 evidence from fine-scale Stage 2 evidence. Stage 1 may only be a broad-tile prior; it must not dominate or hard-gate fine-scale placement unless holdout evidence warrants it.

Create a **new, unique** competition-format GeoTIFF only when all of these are true: it passes the official format verifier, a source-aware uniqueness check, a Stage-1 dominance check, and a preregistered spatial holdout promotion rule against the current best. Do not spend a weekly submission slot on an unpromoted candidate. Never copy a previous submission to satisfy the file requirement. If no candidate passes, say so and withhold the file rather than relabeling an old artifact. When a candidate is eligible, make its download obvious, state a unique submission name and short note, and include a concise upload guide.

Maintain source-linked research records, verify claims against official or trusted sources, flag irregularities, explain external-data access needs, and state limitations candidly. Do not claim a competition score unless the organizer returned it for the submitted artifact. Run at least three review passes: implement/verify; audit/fix; re-check the original requirements and improve. Update this brief as project decisions change.

### Operating constraints

- The official [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) says not to use automated tools to access, monitor, or copy website material, and not to use a manual process to monitor or copy it without prior written consent. **This repository therefore does not scrape, mirror, or manually transcribe leaderboard standings.** The official leaderboard may be linked as a source; no standings are stored here. No written consent is on record.
- GEMS Prize rules require a narrative disclosure of whether and how generative AI was used. Any eventual submission narrative must include an accurate disclosure (template below); local testing is not a competition score.
- Competition files restored from public owner mirrors are hash-checked but are **not organizer-authenticated**. Keep this provenance limitation visible.

## Executive summary — current status

**No new TIF was generated. No competition slot is recommended.** The tested, narrowed H51-X1 magnetic/gravity edge-normal concordance implementation did not beat the frozen H-D holdout baseline. The preregistration listed a broader layer family; the evaluated builder used only rank-normalized total-magnetic and isostatic-gravity bands, so the broader layer-family hypothesis is not fully falsified. A separate H-D soft-prior setting at `w=0.20` narrowly cleared the numeric promotion rule, and its Stage-1 dominance diagnostic was benign, but its emitted support was too similar to an existing candidate: Jaccard **0.8613** and candidate containment **0.9255** against the existing soft-`w=0.10` raster (uniqueness limits: 0.50 and 0.60). The builder stopped before writing a GeoTIFF. That is the intended fail-closed behavior.

The prior zero-outside TIFFs are not current downloads: the official format requires null/NaN outside the footprint, and local verification confirms those legacy zero-outside files fail that check. A previous NaN-outside twin is locally format-valid, but it is not a new or promotion-cleared candidate and is not offered as a submission. The site therefore shows **no eligible download** until a genuinely distinct candidate clears the gates.

### Evidence summary — keep Stage 1 and Stage 2 separate

**Stage 1: geodetic strain-budget deficit, used only as a coarse prior.** The exact fault-slip tensor summation cited by the implementation is Kreemer et al. (2000), Eq. 3:

\[
\dot{\varepsilon}_{ij}=\frac{1}{2}\sum_k\frac{L_k\dot{u}_k}{A\sin\delta_k}\,m_{ij}^{k},\qquad
m_{ij}^{k}=n_i^k s_j^k+n_j^k s_i^k.
\]

Here \(L_k\) is trace-segment length, \(\dot u_k\) slip rate, \(A\) tile support area, \(\delta_k\) dip, and \(n,s\) the unit fault-normal and slip vectors. For the horizontal pure dip-slip projection, the normal and slip projections yield the code's \(L\dot u\cos\delta/A\) coefficient; the strike-slip coefficient is \(L\dot u/(2A\sin\delta)\). See [`src/gems51/strain_budget.py`](src/gems51/strain_budget.py) and the [public UNR paper](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf).

This is an approximate horizontal tensor budget, not a full geodetic inversion: trace geometry is raster-derived, slip rates are assigned from the nearest trace centroid, the table does not provide per-segment rake, slip-sense categories are simplified, and the geodetic second-invariant convention cannot be recovered exactly from the supplied dilatation/shear layers. The copied slip-rate field is provisionally interpreted as mm/yr, but the NBMG service schema does not declare the `SLIPRTNUM` units and the linked GDR field-definition text was not audited locally; absolute strain values are not source-validated. The implementation compares quantile-ranked tile fields rather than making an absolute unit claim. Do **not** subtract observed scalar dilation or shear from the tensor invariant as though their definitions and units were interchangeable.

| Stage-1 check | Result | Interpretation |
|---|---:|---|
| Trace-held-out deficit Spearman vs held-out fault density | 0.0392 | Weak association |
| Raw geodetic-only Spearman | 0.0993 | Higher than the deficit in this test |
| Deficit top-50% lift | 1.0829 | Small enrichment; not a strong locator |
| Raw geodetic-only top-50% lift | 1.2386 | Higher than the deficit |
| Stage-1-only randomized DTI | 0.1481 vs 0.1862 uniform | Uses provisional g_hidden=12,700, not an organizer count; Stage 1 alone is worse than uniform |
| Stage-2 DTI with hard q50 gate | 0.1815 vs 0.2816 ungated | Hard gating substantially harms Stage 2 |

Soft Stage-1 weights are marginal: `w=0.10` gives mean proxy DTI 0.28213 and is positive in 3/6 folds; `w=0.20` gives 0.28212 and is positive in 4/6, for a paired mean gain of only about +0.00048. The latter passed the numeric promotion rule but failed uniqueness against the existing candidate. Stage 1 remains a weak tie-breaking prior, never a fine-scale locator or hard gate.

**Stage 2: fine-scale detector.** The current H-D baseline has six-fold mean proxy DTI **0.2816627** at `M/|G|=3.47` and mean AUC **0.6726183**. The narrowed H51-X1 test (rank-normalized `comp_tmi` + `comp_iso_grav_anom` edge-normal agreement at 200 m and 500 m; the planned RTP/HG/VG derivative products were not used by the new transform, though they remained in the common baseline stack) has mean proxy DTI **0.2796713**, AUC **0.6666622**, and beats H-D on only 3/6 folds: it fails promotion by −0.0019913 mean DTI. This does not falsify every version of the broader preregistered layer-family hypothesis. All these numbers use a visible known-fault raster as holdout truth; they are **proxy measurements**, not hidden-test predictions or competition scores.

The six-fold gate sweep is in [`data/gate_sweep.json`](data/gate_sweep.json); Stage-1 trace holdout and separate two-stage results are in [`data/stage1_trace_holdout.json`](data/stage1_trace_holdout.json) and [`data/two_stage_results.json`](data/two_stage_results.json). The frozen hypothesis screen and outcome are in [`knowledge/preregistration-2026-10-07.md`](knowledge/preregistration-2026-10-07.md).

**Post-branch synchronization audit (kept separate from the preregistered geology test):** the later merged [PR #6](https://github.com/buffedlizard55-lab/GEMSDOE51/pull/6) added a six-fold Stage-2-only emission-geometry sweep. Its best recorded rule, `ste_L9_w0.35_s2.4_nothin`, had mean proxy DTI **0.2836026**, versus **0.2816394** for that sweep's isotropic incumbent (+0.0019632; better in 4/6 folds). This is a repository-recorded, not independently rerun, *emission-method* result—not a new geological hypothesis or an organizer score. The packaged H-D map applied a Stage-1 soft prior at `w=0.10`, and its manifest reports a **0.0020 holdout cost** against the ungated version; the separate H-M arm scored 0.2826030, below the Stage-2-only emission lead. For the packaged H-D map, Stage 1 approved 80.05% of the footprint and contained 77.10% of emitted dots (lift 0.963), so it did not dominate placement, but it did not improve holdout performance. The archived local audit records both NaN-outside twins as passing; those twins were not rerun in this review. The zero-outside counterparts were rerun and fail the current local format checker. These maps were already published on `main`, and their portal/slot status is unverified, so none is being reissued or relabelled. The best Stage-2-only setting has no freshly built file in this review; its evidence remains a **provisional lead pending reproduction**. See [`data/holdout_archive_review.json`](data/holdout_archive_review.json); all PR #6 TIFF/ZIP files are archived and not linked as downloads.

## GEMSDOE32 case study — what the reported result does and does not show

The GEMSDOE32 owner page presents H33-2-B2 with **37,654 dots**, a claimed 200 m catalogue-flank prune, and a **projected 0.2747** result. The page itself labels the artifact **UNSCORED** and explicitly says no organizer score exists for that artifact. Its reported `+0.00487` over a `0.2708` base is an owner-reported live-mirror/model comparison, not an organizer-returned score linked to those bytes.

A plausible mechanism is metric-driven sparsification: DrivenData's distance-weighted Tversky index has \(\alpha=0.2\), \(\beta=0.8\), and a 300 m triangular kernel. Removing near-catalogue mass may improve credit per emitted unit when those pixels are unlikely to receive hidden-fault credit. The competition also defines the test faults as faults not in the existing public database. But these facts do **not** establish that the prune caused an actual leaderboard gain: the cited file is unscored, the projection is not a test result, and the comparison is not an organizer-controlled experiment. Treat the B=2 prune as a useful, falsifiable design idea—not causal proof or a transferable score.

Source trail: [GEMSDOE32 index / artifact status](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), [GEMSDOE32 research](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/research.html), [its ranked hypotheses](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/hypotheses.html), and [its irregularity register](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/irregularities.html). These are owner-published pages, not organizer verification.

## Ranked geological hypotheses

The full feature/data/source matrix and preregistration are in [`knowledge/preregistration-2026-10-07.md`](knowledge/preregistration-2026-10-07.md). In brief:

1. **H51-X1 — cross-physics magnetic/gravity edge-normal concordance.** Preregistered family: magnetic (`rtp`, `tmi_hg/vg`) and gravity (`iso_grav_anom`, gradients) bands. The evaluated new transform used only rank-normalized `comp_tmi` + `comp_iso_grav_anom` edge-normal agreement at 200/500 m (derivatives remained in the common baseline stack). Moderate cost; no external data. This narrowed implementation **failed** the six-fold promotion rule; the broader family was not fully tested.
2. **H51-X2 — paired scarp-face asymmetry.** Existing 1 m DEM directional-face and step/relief layers; compare up-facing/down-facing response, not just amplitude. Low cost; local layer source is owner-mirrored. Not yet tested.
3. **H51-X3 — geothermal manifestation alignment.** GDR/INGENIOUS wells and spring temperatures/geochemistry aligned with an independently detected lineament, not broad habitat emission. Medium cost; requires provenance, duplicate, and coordinate checks on the owner-mirrored point table. Not yet tested.
4. **H51-X4 — stress-compatible structural corridors.** Use USGS Siler slip/dilation tendency as an orientation prior for independent lineaments. Potentially useful but high cost and **blocked** until the official shapefile, field definitions/units, download, and spatial join are validated. Archive source: [USGS ScienceBase DOI 10.5066/P9YL58W6](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d).

## Outstanding work and limitations

- Restore the official training-feature raster and prepared arrays (absent from this checkout), then independently rerun the archived PR #6 emission-geometry sweep and its Stage-1 ablation. Until that reproduction, treat `0.2836026` as a provisional Stage-2 lead, not a promoted incumbent; only a fresh, guarded build from the best holdout-cleared configuration can be considered for a slot.
- Before any future build, fetch the commit-pinned prior-family TIFF references with `scripts/fetch_gate_refs.sh` for support comparison only (never as candidate pixels). The guarded builder scans `data/refs/`, `data/prior/`, current downloads, and archived submissions; a missing reference set is a limitation to report, not a reason to loosen the gate.
- The full H51-X1 preregistered band-family transform was not implemented; the tested two-input transform failed promotion. If revisited, define the aggregation of RTP/TMI/gravity derivative channels before running a new blocked holdout, and treat it as a new/expanded preregistered experiment.
- H51-X2 (paired scarp-face asymmetry) and H51-X3 (well/spring-to-lineament alignment) remain untested; validate owner-mirror provenance, units, duplicates, and coordinate transformations before feature use.
- H51-X4 is blocked until the official USGS Siler shapefile can be obtained and its fields/units, geometry, and spatial join are verified locally.
- The available spatial holdout reuses the public known-fault labels; it cannot validate recall of genuinely new expert faults. Hidden test labels, hidden truth size, and any organizer score are unavailable locally. A participant must use the official competition account to upload a future eligible file and obtain organizer feedback.
- No leaderboard standings are mirrored or monitored. The official DrivenData Terms of Use prohibits automated monitoring/copying and manual monitoring/copying without prior written consent; no such consent is on record.

## Submission status and guide

There is currently **no eligible GeoTIFF to download or submit**. The generator is deliberately fail-closed: it checks the frozen holdout promotion rule, compares positive-pixel support with all available local prior TIFFs, checks Stage-1 dominance, writes a staged NaN-outside GeoTIFF, re-reads its format, runs the full local uniqueness gate, and only then promotes the file to the downloads directory. The current H-D `w=0.20` proposal stops at the pre-write uniqueness check.

When a future candidate passes, the executive-summary card will display the `.tif`, unique submission name, short note, checksum, and exact format receipt. Upload steps will be: download that eligible `.tif` (or its single-file `.zip`), open the official [DrivenData submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/), choose the file, enter the displayed name and note, and include the narrative disclosure. Do not upload an archived file just because it is locally format-valid.

**Narrative disclosure to adapt accurately if/when submitting:**

> Generative AI was used as a coding and research assistant to inspect this repository, propose and rank hypotheses, draft and revise code and documentation, and help debug and test the workflow. The competition-format output, if submitted, is produced by the documented geospatial feature and machine-learning pipeline. The team reviewed the scientific claims and is responsible for the data provenance, code, predictions, and all representations in this narrative. No organizer score is claimed unless returned for the submitted file.

The exact disclosure must describe the actual tools and their use in the final submission elements; see Section 3.2 of the [September 2026 official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf). This repository's narrative is only a template and must be checked against the eventual submission.

## Repository map

```text
src/gems51/       metric, grid, feature stack, detector, strain_budget, submission verifier
scripts/          experiments, blocked holdouts, safe submission builder, static-site builder
knowledge/        preregistration, case study, source-linked research records
registry/         source/data manifests, irregularities, prior-submission references
 data/            source/prepared arrays and measured results; bulk inputs are restored locally
 docs/             GitHub Pages site; only currently eligible downloads are exposed here
 archive/          prior submission files and old site receipts retained for audit, not download
 tests/            metric, strain-budget, feature, submission, and legacy-guard tests
```

The old scalar prototypes `strain.py` and `stage1_strain.py` are quarantined under `attic/legacy-api/src/gems51/` and are not part of the active evidence path; report functions in the archived `strain.py` fail closed. Current Stage 1 is `src/gems51/strain_budget.py`. Legacy `run_all.py`, `run_pipeline.py`, `rebuild_submission.py`, the earlier holdout runners, the old uniqueness checker, and the README-results generator are retired to prevent stale evidence or ungated files. Use only the dedicated current scripts listed above; the historical receipts remain under `archive/`.

## Reproduce and verify

```bash
./.venv/bin/python scripts/run_experiments.py --arm H_D --ratios 2,3.47,4.5,6 --save-fields
./.venv/bin/python scripts/run_experiments.py --arm H_X1 --ratios 3.47
./.venv/bin/python scripts/run_stage1_trace_holdout.py --n-splits 5 --tile-px 100 \
  --thresholds 40,50,60,70,80 --ratio 3.47 --g-hidden 12700 --seed 3 --min-heldout 2000
./.venv/bin/python scripts/run_two_stage.py --fields 'data/prepared/field_H_D_fold{}.npy'
./.venv/bin/python scripts/sweep_gate.py --arm H_D --folds 6 --tile-px 100 \
  --ratios 3.47 --nms-radius 2.4 --excl-radius 2.0 \
  --weights 0,0.05,0.1,0.2,0.4,0.8 --hard-q 70,90
./.venv/bin/python -m pytest tests -q
```

Within the preregistered isotropic H-D gate sweep, the soft Stage-1 weight `0.20`, ratio `3.47`, NMS `2.4 px`, and exclusion `2 px` is the only gate setting to clear that numeric screen, but it is **not promotion-cleared**: it fails source-aware uniqueness. This does not supersede the separate, provisional PR #6 emission-geometry result above. Do not rerun that unchanged candidate, bypass the guard, or copy an archived TIFF to make a submission. A substantively distinct candidate needs its own preregistration, blocked holdout evidence, and complete gate pass.

The hidden test-set mass \(|G|\) is not published. The fixed `g_hidden=12,700` value used only for an illustrative full-map dot budget is an inherited, provisional local working assumption; its calibration is not independently validated here and it is not an organizer label count. Holdout model comparisons use each held-out block's observed truth mass at the same ratio; that does not validate the full-map count. Re-check sensitivity to this assumption before any future build or slot.

## Trusted source links

- [Official competition problem, metric, and GeoTIFF format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official GEMS Prize Rules, September 2026](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/)
- [Kreemer et al. (2000), Eq. 3 — public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS / GDR submission 1391, DOI 10.15121/1881483](https://gdr.openei.org/submissions/1391)
- [NBMG QFaults INGENIOUS layer schema](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson) — `SLIPRTNUM` is listed without a declared unit; see IR-51-12.
- [USGS Siler slip-/dilation-tendency release, DOI 10.5066/P9YL58W6](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d)
- [GEMSDOE32 owner-published case study](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
