# Three-pass review — H53-A status update

Date: 2026-10-08 UTC

Branch: `arena/0b18398a-gemsdoe51`

Scope: frozen H53-A experiment, baseline gate, fail-closed Stage-2 runner, README/manifest, generated GitHub Pages, and repository checks.

## Pass 1 — Implement and verify

- Preserved the three-candidate, ranked pre-score slate in [`hypothesis-slate-20261008.md`](hypothesis-slate-20261008.md): H53-A finite-lag surface/gravity edge pairing; H53-B multi-kilometre chord persistence; H53-C LiDAR face-polarity contrast. Each names inputs, physical signature, missing-catalogue rationale, specific difference from existing operators, expected benefit, cost, and whether new data are required. H53-A was top-ranked; it uses existing pinned inputs, so no new external dataset was needed.
- Kept the frozen experiment protocol in [`../registry/preregistration_h53.json`](../registry/preregistration_h53.json). Built six label-blind H53 feature layers to ignored `data/prepared/arm_h53a.dat`.
- Separately evaluated Stage 1 on five whole-record splits. Nominal means: q10 area `0.9019044`, held-out visible-catalogue trace-pixel recall `0.9290894`, recall/area lift `1.0301461`. One matched-mass uniform draw per split gave proxy DTI `0.0483903` inside the mask and `0.0490248` across the footprint. This is weak/noisy local proxy evidence, not an organizer result.
- Ran the baseline-only audit. Fresh canonical H-D/H-H mean `0.2853151549` vs frozen cached-field mean `0.2853406027`; delta `−0.0000254478`, beyond the locked `1e-5` tolerance. Fold 0 differs by `−0.0001526867`; folds 1–5 match. Legacy cached field bytes and exact generation metadata are missing; no cause is assigned.
- The Stage-2 script was invoked only to verify its guard. It exited before candidate fitting with the expected fail-closed message; no H53 candidate score or Stage-2 receipt was produced. No H53 prediction TIFF, ZIP, portal note, uniqueness result, format result, upload, or slot exists.
- Updated README, AGENTS, submission manifest, latest-report renderer and generated site so the H53 blocker and separate Stage-1 numbers lead. The site identifies the earlier P1 TIFF as research-only, keeps its measured negative holdout visible, and does not label it as an H53 artifact.

## Pass 2 — Bugs, assumptions, and edge cases

- **Fixed a fail-open provenance edge case in the Stage-2 code path.** Before this review, the runner trusted a successful status flag without verifying that the exact H-D/H-H field files it would consume still matched the baseline receipt. The runner now verifies the frozen baseline receipt hash, audited input-manifest/feature-arm hashes, all six cached H-D/H-H field hashes, field shape/dtype, and the pass/tolerance fields before candidate scoring. The audit writer now records receipt and arm-cache digests for any future qualifying audit. Added tests for exact-cache acceptance, changed bytes, incomplete folds, and wrong geometry.
- This instrumentation hardening does **not** change the preregistered scientific threshold or this result. The failed 2026-10-08 receipt predates these extra input-hash fields; it remains failed and cannot be promoted. The current runner rejects it on its failed status before opening a candidate arm. A future passing path needs a newly authorized, fully auditable baseline under a frozen protocol; do not patch the old receipt or use an unreceipted cache.
- **Preregistration wording ambiguity recorded, not edited:** the frozen JSON's `sensitivity_not_used_for_selection` list redundantly names “fault-plane rate convention,” although fault-plane is already the nominal convention. The executed receipt is explicit: nominal `1e-8/year` fault-plane, sensitivity `1e-9/year` fault-plane, and sensitivity `1e-8/year` vertical-rate. No fourth case is claimed; the preregistration was not changed after results.
- The Stage-1 result is not described as enrichment or fault confirmation: area is about 90%, lift about 1.03, and the matched-mass in-mask uniform DTI is lower than the full-footprint draw on average. The one-draw-per-split control is noisy. Coarse Stage 1 remains an allowed-domain prior only.
- The split catalogue is reused and is not an untouched hidden-label lockbox. No external data were downloaded or required. The source slip-rate units were previously checked against the official DBF; fault-plane component, dip, geodetic unit conversion, omitted unknown sense, off-fault/aseismic deformation and interpolation remain assumptions or limitations.
- The user-reported `[0,1]` portal error has no verified triggering filename. Local P1 format checks are not portal validation. GEMSDOE32 `0.2778` and the user-supplied `0.3195` are not attributed to a verified file or treated as organizer evidence.
- Inspected the pre-existing `data/restore_receipt.json` diff: its only changes are per-entry `cached` → `fetched` statuses. It is unrelated to this documentation update and is intentionally not included in this change set.

## Pass 3 — Full request and acceptance-criteria review

| Requirement | Result |
|---|---|
| 3–5 untried, ranked hypotheses before implementation | **Met:** three operator-level hypotheses were frozen before H53 scoring; top candidate and data/cost distinctions are documented. |
| Geodetic budget as coarse Stage 1 only; source units and summation | **Implemented and separately audited:** official DBF unit check and sourced tensor formula; all component/unit/dip choices are explicit. Stage 1 never places points. |
| Separate Stage-1 and fine-scale Stage-2 holdouts | **Stage 1 complete; Stage 2 blocked before candidate fit/score.** Reported separately; no fake Stage-2 number. |
| No competition slot until a candidate beats holdout best | **Met:** no candidate reached promotion and no slot was used. |
| Unique H53 GeoTIFF and scoped uniqueness/geometry/range checks | **Not produced, correctly:** promotion gate failed before a candidate raster existed. Site says no H53 research download and no submission. Earlier P1 remains explicitly research-only. |
| Stage-1 non-dominance, approved-tile confinement | **Not scoreable for H53:** no Stage-2 points exist. The future paired runner contains these frozen checks. H53 Stage-1 area/lift are reported separately. |
| Portal `[0,1]` error and official submission instructions | **Status made explicit:** user-reported error remains unresolved; local range checks are not portal acceptance. How-to-submit page prohibits using any present file. |
| Identifier and short submission note | **No submission name/note issued for H53** because no eligible H53 TIFF exists. The research identifier is clearly marked not a portal name. Earlier research artifact labels are marked not to paste. |
| Owner-reported scores and organizer-score attribution | **Kept separate:** no unverified file attribution or organizer-score claim. |
| README, executive summary, clean generated site | **Updated:** first-screen H53 status, receipts, slate/preregistration, and research-only historical downloads; site checker confirms links and manifest/download consistency. |
| Tests, repository and site checks | **PASS:** `107 passed, 6 skipped`; repo-health imports/API/test collection passed; 13-page site/link/download check passed; compile and `git diff --check` passed. Stage-2 guard produced the expected refusal and no receipt. |
| PR and merge | **Pending at review write time.** No claim of PR checks or merge until the GitHub actions are actually completed. |

## Decision

`GEMSDOE51-H53-A-20261008` is a research/preregistration identifier only. H53-A has a separate Stage-1 result, but the baseline provenance/reproduction gate failed, so **H53 Stage 2 is blocked; no H53 score or TIFF exists; download for H53 research: NO; submit: NO.** Preserve the failure. Recover auditable lineage or preregister a new baseline before scoring another candidate; do not weaken the frozen rule.
