# H53-K2x three-pass implementation, review, and release check

**Date:** 2026-10-08 UTC  
**Decision:** H53-K2x is **NOT PROMOTED**. Its new TIFF is available for research download only. No competition slot is authorized or used; no organizer score or portal acceptance is claimed.

## Pass 1 — research design and fresh implementation

- Re-read the repository brief, prior candidate outcomes, current best receipt, source/format constraints, and prior-art records.
- Ranked four distinct, previously unimplemented mechanisms before coding: H53-K2x conductive-ribbon anisotropy, H53-LID paired scarp-face polarity, H53-RAD radiometric composition breaks conditioned on independent structure, and H53-GEO sparse geochemistry/warm-water alignment. Only the top-ranked H53-K2x proceeded to the frozen test. Full slate and source caveats: [`candidate-hypotheses-2026-10-08.md`](candidate-hypotheses-2026-10-08.md).
- Checked official/trusted task, INGENIOUS, USGS conductance, and fault-zone-conductor references. The task is fault discovery, not vent prediction. Public context does not establish the units, depth sensitivity, calibration, or source lineage of the local `cond_surf` band; H53-K2x therefore uses rank-space values only and asserts no physical conductivity units.
- Added a deterministic two-scale feature and its build/evaluation pipeline. Restored hash-pinned inputs without manual placement. Ran the full-catalogue fit and generated `docs/downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif` from the new model output. No earlier TIFF was used as input or relabeled.

## Pass 2 — holdout, assumptions, and artifact review

- Kept Stage 1 and Stage 2 separate. Stage 1: five whole-trace splits, mean approved area 90.15%, held-out trace recall 96.01%, lift 1.065. For Stage 2, each spatial fold recomputed its own q10 allowed-domain mask after removing held-out trace rows; mask area was 90.06–90.36%, all tested baseline/candidate points were confined, and Stage-1 score weight was zero.
- Applied the unchanged six-fold, spatially blocked Stage-2 rule. Fresh ungated baseline mean 0.2853151549 drifted −0.0000254478 from frozen best 0.2853406027, outside the fixed 1e-5 tolerance. H53-K2x q10-gated mean 0.2850361457 was 0.0003044570 below frozen best. It beat its same-fold q10-gated comparator by +0.0001374886 in 4/6 folds, but these do not override baseline-reproduction/frozen-best failures. No tuning followed the result.
- Independently reread final TIFF bytes: one float32 band, EPSG:32611, 3730×3292, exact template transform, 44,069 binary points, all finite in [0,1], zeros outside, no NoData tag. Verified the ZIP contains exactly that one TIFF and its member hash matches the TIFF SHA-256 `15c12778486e5a15f6cced0e9d61c6cf32f2c916128fb37f5ff2f09edd7bb144`.
- Current local uniqueness passes 8 comparisons (max Jaccard 0.216804, containment 0.356350). The broader 54-repository audit retrieved 365/365 payloads but is **NOT CLEARED**: one different-grid test TIFF is incomparable; among 364 same-grid comparisons there is no exact duplicate, maximum Jaccard is 0.149561, and maximum containment is 1.0. No global uniqueness claim is made.
- Local format checks are not portal acceptance. The official null/NaN outside-footprint wording remains unreconciled with the research TIFF's finite zeros outside. The portal was not tested, no artifact was uploaded, no slot was used, and no hidden-label or geothermal-vent outcome is claimed.

## Pass 3 — user-facing integration and release recheck

- Updated `data/submission_manifest.json`, README, generated executive summary, latest report, how-to-submit guide, method, hypotheses, and holdout pages. The new research TIFF, one-file ZIP, final-byte receipt, holdout/source/uniqueness receipts, and ranked slate are linked. Latest download and **DOWNLOAD YES / SUBMIT NO** are shown before older artifacts. P1 remains linked as an explicitly historical research result.
- Site build: `python scripts/build_site.py` completed. `scripts/check_site.py` passed all 13 pages, local links, and manifest/download consistency. `scripts/check_repo_health.py` passed API/import checks and test collection.
- Tests: `pytest -q` — 98 passed, 6 skipped. Python compilation and final TIFF/ZIP SHA/member checks passed.
- Final release decision remains **BLOCKED_NOT_FOR_UPLOAD**. The broader family uniqueness gate and portal outside-footprint semantics are unresolved; do not spend a competition slot.
