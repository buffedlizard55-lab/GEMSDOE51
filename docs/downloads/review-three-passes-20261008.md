# Three-pass review — H53-K2x research result + latest H53-A blocker

**Date:** 2026-10-08 UTC
**Branch:** `arena/c2b2ea5e-gemsdoe51`
**Purpose:** reconcile the completed, earlier H53-K2x research screen and unique TIFF with the H53-A baseline-reproduction blocker from `main`. Preserve both as distinct H53-family experiments and identify H53-A as the latest within that family. The later overall K2-08 experiment from updated `main` is a separate record and is not attributed to either H53 result.

## Pass 1 — Ranked hypotheses, frozen protocols, implementation

- **Earlier K2x slate:** ranked four previously untried mechanisms before implementation: H53-K2x conductive-ribbon anisotropy, H53-LID paired scarp-face polarity, H53-RAD radiometric composition breaks conditioned on independent structure, and H53-GEO sparse geochemistry/warm-water alignment. Only top-ranked H53-K2x proceeded. Slate and preregistration: [`candidate-hypotheses-2026-10-08.md`](candidate-hypotheses-2026-10-08.md) and [`evidence/candidate_hypotheses_prereg_20261008.json`](../evidence/candidate_hypotheses_prereg_20261008.json).
- **Later H53-A slate:** a separate three-candidate slate ranked H53-A bounded surface/gravity edge lag above H53-B multi-kilometre chord persistence and H53-C LiDAR face-polarity contrast. H53-A and its Stage-1/Stage-2 protocol were frozen independently; see [`hypothesis-slate-20261008.md`](hypothesis-slate-20261008.md) and [`../registry/preregistration_h53.json`](../registry/preregistration_h53.json). Do not combine the two slates or attribute one candidate's score to the other.
- K2x added a deterministic, two-scale, rank-space conductive-anisotropy feature using the supplied conductivity, depth-to-base, gravity, and magnetic bands. No physical units, depth sensitivity, or verified source lineage are asserted for local `cond_surf`. Hash-pinned inputs were restored programmatically; no manual placement or external acquisition was needed.
- H53-A built six label-blind feature layers to ignored prepared data and separately ran a five-split Stage-1 audit. Its Stage-2 runner was guarded by the baseline audit and refused candidate fitting/scoring when the baseline missed its frozen tolerance.
- No earlier TIFF was reused or relabeled. The H53-K2x TIFF was freshly generated from the K2x model output and is a research-only artifact, not an H53-A output.

## Pass 2 — Independent outcome, provenance, edge cases, and artifact review

### Earlier H53-K2x completed screen — NOT PROMOTED

- Stage 1 is reported separately from Stage 2. Five whole-official-trace splits gave mean approved area `0.9015271`, held-out trace recall `0.9601246`, and recall/area lift `1.0650105`. In each of the six Stage-2 spatial folds the q10 mask was recomputed without held-out trace rows; approved area was 90.06–90.36%, all evaluated points were inside approved tiles, and Stage-1 score weight was zero. These are separate domain/confinement diagnostics, not a Stage-2 gain.
- Stage 2: q10-gated K2x mean proxy DTI `0.2850361457010805`; paired same-fold q10-gated H-D/H-H baseline `0.28489865707511947`; delta `+0.00013748862596105657`, 4/6 folds. The candidate remained `0.0003044569552385079` below frozen best `0.285340602656319`. Fresh ungated baseline `0.28531515486970865` drifted `−0.000025447786610344192`, outside the frozen `1e-5` tolerance. **NOT PROMOTED.** This screen does not clear the competition-slot rule.
- Fresh TIFF: [`docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif`](../docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif), SHA-256 `15c12778486e5a15f6cced0e9d61c6cf32f2c916128fb37f5ff2f09edd7bb144`. One-band float32, EPSG:32611, 3730×3292, template transform, 44,069 binary points, all finite in `[0,1]`, zeros outside, no NoData tag. ZIP contains exactly that TIFF. These are local byte/format results, not portal validation.
- Current local inventory uniqueness passed 8 comparisons (maximum support Jaccard `0.216804`, containment `0.356350`). The broader committed-family audit is **NOT_CLEARED**: 365/365 payloads fetched; no exact same-grid duplicate among 364 comparisons, maximum Jaccard `0.149561`, maximum containment `1.0`, and one different-grid toy artifact could not be compared. Do not claim global uniqueness. Portal interpretation of outside-footprint zeros vs the official null/NaN wording remains unresolved.
- K2x code review confirmed fixed seeds/protocol, no post-result tuning, and separate Stage-1 and Stage-2 accounting. The visible catalogue is proxy truth, not hidden expert labels. The user-reported portal error has no authenticated triggering filename. No upload, organizer score, hidden-label result, or slot use is claimed.

### Latest H53-A audit — Stage 2 blocked, not a candidate failure

- Stage 1, five whole-record splits: mean approved q10 area `0.901904429968574`, held-out visible-catalogue trace-pixel recall `0.9290894120384197`, recall/area lift `1.0301461034883945`. Matched-mass uniform-dot proxy DTI was `0.04839029619807429` inside approved tiles vs `0.04902479022212286` across the footprint; one random draw per split is descriptive and noisy.
- Baseline-only provenance audit: fresh canonical H-D/H-H mean `0.28531515486970865` vs frozen cached-field mean `0.285340602656319`, delta `−0.000025447786610344192`, beyond tolerance `1e-5`. Folds 1–5 match; fold 0 differs by `−0.0001526867`. Legacy field bytes and exact generator metadata are missing; no mismatch cause is assigned.
- H53-A Stage 2 was blocked **before candidate fitting/scoring**. There is no H53-A candidate score, TIFF, uniqueness result, or format result. This is a baseline provenance/reproduction gate failure, **not a measured H53-A candidate failure**. Do not treat K2x as an H53-A result or substitute artifact.
- Code review hardened the fail-closed runner to verify the frozen receipt hash, input/arm hashes, all six H-D/H-H field hashes, field shape/dtype, and pass/tolerance fields before any future candidate scoring. This integrity check does not change the frozen scientific threshold or retroactively pass either baseline receipt.
- Preregistration irregularity preserved: the H53-A sensitivity list redundantly names a fault-plane rate case also used as nominal. The executed receipt records nominal `1e-8/year` fault-plane, sensitivity `1e-9/year` fault-plane, and sensitivity `1e-8/year` vertical-rate; no fourth case is claimed and the frozen preregistration was not edited after results.

## Pass 3 — Integrated user-facing status and release recheck

| Acceptance item | Reconciled status |
|---|---|
| Keep experiment chronology accurate | **H53-A is the latest within the H53 family.** Its Stage 1 is complete; Stage 2 is blocked before candidate scoring. H53-K2x is a separate earlier completed screen. K2-08 is the later overall experiment from main, with its own artifact, metrics, and review; none of its results are attributed to H53. |
| Stage 1 broad-tile prior, separate from Stage 2 | **Preserved.** Both experiments report Stage-1 and Stage-2 records separately; K2x Stage-2 uses fold-specific q10 approved domains and all evaluated points were confined. Stage-1 score weight is zero. |
| Maximize P(Win); no slot until a valid candidate beats the current best | **No slot authorized or used.** K2x did not beat frozen best; H53-A has no Stage-2 candidate result. |
| Unique fresh TIFF and easy research download | **K2x TIFF exists and is linked** with ZIP, hash, receipt, unique research label, and a short explicit `RESEARCH ONLY / NOT FOR SUBMISSION` comment. It is not H53-A and not cleared for upload. H53-A has no TIFF. |
| Local format vs portal acceptance | **Distinguished.** K2x local checks passed; outside-footprint semantics and portal acceptance remain unresolved and untested. |
| Source claims and irregularities | **Caveated.** Official task/source and trusted literature do not establish the local `cond_surf` units or lineage. Conductivity–fault association is non-unique. User/leaderboard scores remain unauthenticated and unattributed. |
| Executive summary and submission guidance | README and generated site distinguish K2-08 as the later overall research experiment, H53-A as the latest H53-family experiment, and H53-K2x as the earlier H53 screen. They link the K2x research TIFF, receipts, how-to-submit, and explicit no-slot/portal caveats. |
| Three-pass review | This record retains the K2x implementation/review/recheck and H53-A blocker review as distinct evidence streams. |
| Tests/build after merge reconciliation | **PASS.** `.venv/bin/python scripts/build_site.py` rebuilt the site with K2-08 and both H53 records; `scripts/check_site.py` passed (13 pages, local links, and manifest/download state); `.venv/bin/pytest -q` passed (124 passed, 6 skipped); `py_compile` passed for the edited Python modules. These validate the local merge result, not GitHub checks or portal acceptance. |
| PR #18 merge | Local integration is validated; push and required GitHub checks remain pending. Do not merge until the PR reports all required checks passed; no merge is claimed here. |

## Decision

`GEMSDOE51-H53-A-20261008` is the latest research/preregistration identifier only; H53-A has no TIFF and no candidate score. H53-K2x is an earlier measured result with a fresh research-only TIFF, but it failed promotion and its broader family uniqueness gate is not cleared. **Download: YES for the H53-K2x research artifact only. Submission: NO for either H53 artifact. No competition slot was used or authorized. No portal acceptance, organizer score, or hidden-label result is claimed.**
