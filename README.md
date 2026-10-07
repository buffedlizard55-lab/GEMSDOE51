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

**No competition slot is authorized.** The guarded H-D `w=0.20` build stopped before writing because its support was too similar to the existing soft-`w=0.10` raster: Jaccard **0.8613** and candidate containment **0.9255** (limits 0.50 and 0.60). The narrowed H51-X1 magnetic/gravity edge-normal concordance test also lost to the frozen H-D blocked holdout; its two-input implementation did not exhaust the broader preregistered layer family.

A distinct H-G+H-D **research-only** GeoTIFF is available for inspection: [`gemsdoe51-hg-hd-xing-exp-r347-20261007T034048Z-nan.tif`](docs/downloads/gemsdoe51-hg-hd-xing-exp-r347-20261007T034048Z-nan.tif) (one-file ZIP also available). The underlying predictions pass the refreshed, finite public-corpus uniqueness audit but lose their matched six-fold proxy holdout (0.281056 vs H-D 0.281663; paired Δ −0.000606; 3/6 folds higher). Its final NaN-outside format re-encoding passes the local CLI checker: one-band float32, 3730×3292, EPSG:32611, in-footprint predictions in [0,1], and NaN outside the footprint. It exactly preserves all in-footprint predictions; this is **not** an authorized submission. The site's download label is research-only; do not upload it.

H-M and strike-coherent STE provide higher mean point estimates, not a robust win: both have noisy six-fold differences, both fail the refreshed broad uniqueness gate because packaged same-prediction NaN twins are present, and their required fresh q70 Stage-1 checks are not available in this checkout. No candidate currently clears every promotion gate.

### Evidence summary — keep Stage 1 and Stage 2 separate

**Stage 1: geodetic strain-budget deficit, used only as a coarse prior.** The exact fault-slip tensor summation cited by the implementation is Kreemer et al. (2000), Eq. 3:

\[
\dot{\varepsilon}_{ij}=\frac{1}{2}\sum_k\frac{L_k\dot{u}_k}{A\sin\delta_k}\,m_{ij}^{k},\qquad
m_{ij}^{k}=n_i^k s_j^k+n_j^k s_i^k.
\]

Here `L_k` is trace-segment length, `u_dot_k` the slip-rate component, `A` tile support area, `delta_k` dip, and `n,s` unit fault-normal and slip vectors. Under a pure normal-fault assumption, a **total fault-plane** rate yields the horizontal coefficient `L*u_plane*cos(delta)/A`; if the source value is **vertical displacement** rate, the coefficient is `L*u_vertical*cot(delta)/A`. Vertical strike slip yields `L*u/(2A)`, with RL and LL signs opposite. The source component convention and exact dip are unresolved here; the code exposes both rate conventions, defaults to the explicitly provisional vertical interpretation, uses a 60-degree normal-fault dip, and applies a provisional mm/yr conversion. See [`src/gems51/strain_budget.py`](src/gems51/strain_budget.py), the focused tests, and the [public UNR paper](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf).

This is an approximate horizontal tensor budget, not a full geodetic inversion: trace geometry is raster-derived, slip rates are assigned from the nearest trace centroid, the table does not provide per-segment rake, slip-sense categories are simplified, and the geodetic second-invariant convention cannot be recovered exactly from the supplied dilatation/shear layers. The copied slip-rate field is provisionally interpreted as mm/yr, but the NBMG service schema does not declare the `SLIPRTNUM` units and the linked GDR field-definition text was not audited locally; absolute strain values are not source-validated. The implementation compares quantile-ranked tile fields rather than making an absolute unit claim. Do **not** subtract observed scalar dilation or shear from the tensor invariant as though their definitions and units were interchangeable.

The latest formula audit changed the implementation to make the slip-rate component convention selectable and RL/LL shear signs opposite. **A current-formula, leakage-controlled Stage-1 rerun is not available in this checkout.** The table is the historical mainline trace-split receipt: its runner removed held-out trace rows, but its old code used an implicit unsigned/total-slip approximation. Keep these numbers as context only, not validation of the current implementation. The separate four-scenario formula audit in [`evidence/stage1_formula_audit.json`](evidence/stage1_formula_audit.json) is not a valid holdout: its runner passed held-out trace attributes into the catalogue-derived budget term. Full reconciliation is in [`evidence/stage1_reconciliation_20261007.json`](evidence/stage1_reconciliation_20261007.json).

| Historical Stage-1 check (known-catalogue proxy) | Result | Interpretation |
|---|---:|---|
| Trace-held-out deficit Spearman vs held-out fault density | 0.0392 | Weak association; old formula |
| Raw geodetic-only Spearman | 0.0993 | Higher than deficit in the historical test |
| Deficit top-50% lift | 1.0829 | Small enrichment; not a strong locator |
| Raw geodetic-only top-50% lift | 1.2386 | Higher than deficit |
| Stage-1-only randomized DTI | 0.1481 vs 0.1862 uniform | Historical setting; uses provisional g_hidden=12,700, not an organizer count |
| Stage-2 DTI with hard q50 gate | 0.1815 vs 0.2816 ungated | Historical setting; hard gating substantially harms Stage 2 |

The archived H-D soft-prior gate sweep is also tied to the old Stage-1 field: `w=0.10` gives mean proxy DTI 0.28213 and is positive in 3/6 folds; `w=0.20` gives 0.28212 and is positive in 4/6, for paired mean gain about +0.00048. The w=0.20 artifact failed uniqueness, and neither weight has been reproduced against the current formula. Stage 1 remains a coarse prior only—not a validated fine-scale locator or hard gate. Restore the raw inputs and rerun Stage 1 before applying it operationally.

**Stage 2: fine-scale detector.** The current H-D baseline has six-fold mean proxy DTI **0.2816627** at `M/|G|=3.47` and mean AUC **0.6726183**. The narrowed H51-X1 test (rank-normalized `comp_tmi` + `comp_iso_grav_anom` edge-normal agreement at 200 m and 500 m; the planned RTP/HG/VG derivative products were not used by the new transform, though they remained in the common baseline stack) has mean proxy DTI **0.2796713**, AUC **0.6666622**, and beats H-D on only 3/6 folds: it fails promotion by −0.0019913 mean DTI. This does not falsify every version of the broader preregistered layer-family hypothesis. All these numbers use a visible known-fault raster as holdout truth; they are **proxy measurements**, not hidden-test predictions or competition scores.

The six-fold gate sweep is in [`data/gate_sweep.json`](data/gate_sweep.json); Stage-1 trace holdout and separate two-stage results are in [`data/stage1_trace_holdout.json`](data/stage1_trace_holdout.json) and [`data/two_stage_results.json`](data/two_stage_results.json). The frozen hypothesis screen and outcome are in [`knowledge/preregistration-2026-10-07.md`](knowledge/preregistration-2026-10-07.md).

**Post-branch candidate audit (separate from the preregistered geology hypotheses):** the mainline six-fold emission sweep's best mean was STE `ste_L9_w0.35_s2.4_nothin`: proxy DTI **0.2836026** versus **0.2816394** for its isotropic `r=2.4` comparator (paired Δ +0.0019632; 4/6 folds higher; paired SD ≈0.003454). The small-sample paired t interval is approximately [−0.00166, +0.00559], so the point estimate is not a robust win. H-M cross-scale crest coincidence scored **0.2826030** vs H-D **0.2816627** (paired Δ +0.0009404; 3/6 folds higher; paired SD 0.003036; approximate 95% t interval [−0.00225, +0.00413]); its soft-prior increment over ungated H-M was only +0.0000077. These are visible-catalogue proxy measurements, not organizer scores.

Fresh full-corpus uniqueness audits cover the refreshed 54-repository inventory. The H-G+H-D research TIFF **passes**: 365 payloads SHA-verified, 364 comparable, one unrelated 32×48 fixture skipped, zero download errors/matches; maximum Jaccard 0.3216, cosine 0.4867, and containment 0.9933 (2.36× random-emission lift, below the 3× flag). On the archived Stage-1 field used to create the artifact, its q70 diagnostic approves 30.046% of footprint area and contains 19.728% of emissions (lift 0.657), so that historical field does not dominate. The current signed/rate-selectable Stage-1 map was not regenerated, so this is not a current-formula dominance check; the negative matched holdout independently blocks promotion. H-M **fails** uniqueness on its same-prediction NaN twin (Jaccard/cosine 1.0) and its hard-q20 alternate (Jaccard 0.634); STE **fails** on its NaN twin (Jaccard/cosine 1.0). No refreshed q70 Stage-1 dominance result is available for the H-M or STE full maps. H-D soft also remains a uniqueness failure (hard-q20 Jaccard 0.631; NaN twin 1.0). Evidence: [`evidence/uniqueness_gate_H_G_HD_experimental_20261007.json`](evidence/uniqueness_gate_H_G_HD_experimental_20261007.json), [`evidence/uniqueness_gate_H_M_soft_20261007.json`](evidence/uniqueness_gate_H_M_soft_20261007.json), and [`evidence/uniqueness_gate_STE_HD_20261007.json`](evidence/uniqueness_gate_STE_HD_20261007.json). These finite-repository checks are not global uniqueness proofs.

## GEMSDOE32 case study — what the reported result does and does not show

The GEMSDOE32 owner page presents H33-2-B2 with **37,654 dots**, a claimed 200 m catalogue-flank prune, and a **projected 0.2747** result. The page itself labels the artifact **UNSCORED** and explicitly says no organizer score exists for that artifact. Its reported `+0.00487` over a `0.2708` base is an owner-reported live-mirror/model comparison, not an organizer-returned score linked to those bytes. A previously proposed attribution of the public `0.2778` row to H33-2-B2 is **unsupported and contradicted by the sibling's own UNSCORED label and 0.2747 projection**; no artifact-to-score mapping has been verified. Because of the official Terms of Use, this repository does not store leaderboard standings.

There is **no scientifically attributable GEMSDOE competition score** for H33-2-B2 in the evidence reviewed: its owner page labels it unscored, and the proposed 0.2778-to-H33-2-B2 link is unsupported and contradicted by that status and the 0.2747 projection. The official metric is `DTI = TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w)`; for binary predictions, `FN_w = |G| - TP_w`, so this is `TP_w / (0.2*(TP_w + FP_w) + 0.8*|G|)`. Its 300 m triangular distance-credit kernel makes false-positive cost depend on proximity to truth. A catalogue-flank prune could raise credit per emitted unit if removed pixels are unlikely to receive hidden-fault credit, and the competition's test set comprises expert-identified faults absent from the existing public database. But neither the metric nor this plausible mechanism establishes that the prune caused a result: H33-2-B2 is unscored, 0.2747 is a modelled projection rather than an observation, and no organizer-controlled comparison is linked to the file. The only defensible interpretation is a falsifiable sparsification hypothesis—not a causal explanation or transferable score.

Source trail: [GEMSDOE32 index / artifact status](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), [GEMSDOE32 research](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/research.html), [its ranked hypotheses](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/hypotheses.html), and [its irregularity register](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/irregularities.html). These are owner-published pages, not organizer verification.

## Current geological hypothesis slate (specific operators, not novelty claims)

The four-item slate and results are recorded in [`evidence/hypothesis_slate_20261007.json`](evidence/hypothesis_slate_20261007.json). This is a literature- and owner-documentation-bounded prior-art comparison, not a claim of global novelty. The broad thermal/geothermal-expression, river-profile, geophysical edge-orientation, cross-physics co-location, step-over, and relay families all have substantial sibling prior art; exact source links and caveats are in [`evidence/sibling_prior_art_audit_20261007.json`](evidence/sibling_prior_art_audit_20261007.json). A documented concept is not evidence that it was implemented successfully.

1. **H-G — high-angle TMI–gravity boundary crossings (tested; rejected).** **Layers/signature:** `tmi` and `iso_grav_anom`; normalized-convolution gradients at 400/800 m, edge-magnitude-weighted axial discordance, with negligible edges suppressed. **Rationale:** independently oriented magnetic and gravity boundaries may mark a structural intersection or transfer zone, but are not themselves proof of a fault. **Prior work/difference:** magnetic–gravity edge-orientation agreement is already documented in sibling projects; H-G is only the exact high-angle, magnitude-weighted, two-scale operator, not a new family. **Expected benefit/cost:** low-to-moderate, uncertain benefit; low–medium cost using existing bands. **Result:** matched H-G+H-D mean proxy DTI 0.281056 vs H-D 0.281663 (Δ −0.000606; 3/6 folds higher); do not promote or spend a slot.
2. **H-H — paired potential-field edge terminations with a conductive relay bridge (next to preregister, not yet tested).** **Layers/signature:** `tmi_hg` or `iso_grav_anom_hg`, `depth_to_base_surf`, `cond_surf`, and lidar step/coherence as an independent surface check; pair aligned, offset finite edge endpoints 0.3–2 km apart only when a conductivity anomaly bridges them. **Rationale:** buried strands can terminate or transfer beneath basin fill; relay zones may localize fractured rock, while conductivity is non-unique. **Prior work/difference:** stepovers, fault-tip continuation, and local co-location are established sibling concepts; this proposal is the specific endpoint-pair plus independent bridge operator, not an untried relay family. **Expected benefit/cost:** potentially moderate localization if the multi-layer bridge is selective; uncertain. Medium–high implementation cost for edge thinning, graph construction, pairing, scale controls, and leakage-safe ablation. Uses existing bands.
3. **H-I — directional conductivity contrast across an independent structural edge (proposed; lower priority).** **Layers/signature:** `cond_surf`, `depth_to_base_surf`, `iso_grav_anom_hg`, and `tmi_hg`; compare along-edge versus cross-edge conductivity at 150–800 m and multiple scales. **Rationale:** an elongated conductor adjoining a basement/potential-field step may be more compatible with a fault corridor than broad basin conductivity, but clay and lithology are confounders. **Prior work/difference:** H-E already screened broad co-location and cross-physics edge agreement has sibling prior art; H-I tests directional anisotropy and offset response instead of magnitude or co-location. **Expected benefit/cost:** low-to-moderate and uncertain; medium cost, no new data.
4. **H-J — earthquake-density modulation of independent structural edges (blocked on metadata check).** **Layers/signature:** `ieq_n100a15`/`deq_n100a15` conditioned on `tmi_hg`, `iso_grav_anom_hg`, and `depth_to_base_surf`; retain an edge only when it coincides with a local earthquake-density ridge, compared to edge-only and seismicity-only controls. **Rationale:** local seismicity may indicate active uncatalogued structures, while geophysical edges constrain geometry; completeness gradients and diffuse seismicity can mislead. **Prior work/difference:** seismicity-lineament research is already documented; this is the specific conditional interaction, not a claim that either input family is new. **Expected benefit/cost:** modest at best, uncertain; low–medium after verifying source-band semantics, coordinate support, and spatial scale.

**Next experiment:** H-H is the highest-priority untested proposal after H-G's negative matched test. Preregister its finite endpoint/bridge operator and edge-only controls, evaluate on the same blocked holdouts against H-D, and require a promotion-rule pass before producing any candidate artifact. Stage 1 remains a coarse-tile prior only. Literature context: [USGS integrated Great Basin blind geothermal play-fairway study](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and) and [Faulds & Hinz on Great Basin structural settings](https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf); neither validates any raster operator above.

The earlier frozen **H51-X1–X4** screen is retained in [`knowledge/preregistration-2026-10-07.md`](knowledge/preregistration-2026-10-07.md) as a historical preregistration: its narrowed X1 test lost, and X2–X4 were not all implemented. Do not conflate it with the newer H-G–H-J slate or describe the broader X1 family as disproven.
## Outstanding work and limitations

- Restore the official training-feature raster, prepared footprint/catalogue arrays, and the QFaults slip-rate table (absent from this checkout). Then rerun the current signed/rate-selectable Stage-1 trace holdout while excluding every held-out trace row from the budget, and independently rerun the archived PR #6 Stage-2 emission sweep. Until then, keep Stage 1 as a broad prior only and treat `0.2836026` as a provisional Stage-2 lead, not a promoted incumbent; only a fresh, guarded build from a best holdout-cleared configuration can be considered for a slot.
- Before any future build, fetch the commit-pinned prior-family TIFF references with `scripts/fetch_gate_refs.sh` for support comparison only (never as candidate pixels). The guarded builder scans `data/refs/`, `data/prior/`, current downloads, and archived submissions; a missing reference set is a limitation to report, not a reason to loosen the gate.
- The full H51-X1 preregistered band-family transform was not implemented; the tested two-input transform failed promotion. If revisited, define the aggregation of RTP/TMI/gravity derivative channels before running a new blocked holdout, and treat it as a new/expanded preregistered experiment.
- H51-X2 (paired scarp-face asymmetry) and H51-X3 (well/spring-to-lineament alignment) remain untested; validate owner-mirror provenance, units, duplicates, and coordinate transformations before feature use.
- H51-X4 is blocked until the official USGS Siler shapefile can be obtained and its fields/units, geometry, and spatial join are verified locally.
- The available spatial holdout reuses the public known-fault labels; it cannot validate recall of genuinely new expert faults. Hidden test labels, hidden truth size, and any organizer score are unavailable locally. A participant must use the official competition account to upload a future eligible file and obtain organizer feedback.
- No leaderboard standings are mirrored or monitored. The official DrivenData Terms of Use prohibits automated monitoring/copying and manual monitoring/copying without prior written consent; no such consent is on record.

## Submission status and guide

There is currently **no upload-eligible GeoTIFF**. For scientific review only, the site links the distinctive H-G+H-D experimental TIFF above; it is not a competition recommendation because its matched holdout is below H-D, and it must not be uploaded. The current guarded H-D `w=0.20` proposal stops at its pre-write support-uniqueness check. Future builds must satisfy the current official-format verifier, source-aware uniqueness, q70 Stage-1 non-dominance, and the frozen spatial-holdout promotion rule before any file is shown as eligible.

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
 data/            manifests and measured results; raw training features/prepared arrays are absent from this checkout
 docs/             GitHub Pages site; only manifest-listed files are exposed, with research-only files visibly marked
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
