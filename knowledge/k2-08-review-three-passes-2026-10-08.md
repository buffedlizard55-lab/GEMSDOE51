# K2-08 three-pass review and handoff — 2026-10-08

## Pass 1 — implement and verify

- Re-read the repository's current decision, source notes, previous hypothesis ledgers and the frozen H-H/H-D holdout. Created the four-hypothesis K2/RAD/MAG/SEIS slate and machine-readable preregistration before implementing or scoring K2. K2's candidate rule explicitly compares against the fresh H-D/H-H blend and the frozen best.
- Audited the official GDR/QFault v2 slip-rate fields and the mirrored trace rows. `SLIPRT2023` is defined in mm/year; `SLIPRTNUM` is its numeric component; all 1,126 mirrored records matched source names, rates and senses. Projected 84,331 source trace segments; physical Stage 1 retains only supported geometry and counts unknown slip sense rather than imputing it.
- Implemented a separate segment-clipped 20 km tile tensor budget and physical residual prior. Stage 1 subtracts predicted fault dilation and source-defined scalar shear from the supplied dilation and shear layers under both declared geodetic unit scales and both slip-component assumptions. It does not use the legacy rank-space second-invariant residual as physical subtraction.
- Implemented four K2 directional conductivity-contrast/persistence features, generated the feature store, and ran the frozen six-fold comparison. Candidate: ungated 0.2845355; q10 0.2748879. Fresh H-H/H-D q10 comparator: 0.2755433; paired delta −0.0006554; 2/6 folds positive. The fresh ungated baseline discrepancy (0.2853152 vs 0.2853406, −0.00002545) is retained outside the 1e-5 tolerance.
- Built one new, feature-fitted research TIFF, not a copied or format-only reissue: 44,069 0/1 points, exact template grid and NaN outside the footprint. All points are inside full-map q10 tiles. Download is explicitly research-only; no slot was used.

## Pass 2 — review assumptions, bugs, and edge cases; fix findings

- Reviewed the method boundary: source slip component, fault dips/rake simplification, and geodetic README `10E-9/yr` notation remain unresolved. Both unit scales and both slip-component scenarios are included. Stage 1 is explicitly a coarse prior only.
- Reviewed the result against the correct comparator, not an H-D-only baseline. The candidate fails the frozen mean and paired q10 gates; no tuning, candidate re-emission, or competition slot followed the failed score.
- Fixed the full-map writer's earlier receipt crash: NaN NoData remains NaN in the TIFF but is represented as the JSON-safe string `"NaN"` in the evidence receipt. Added a resume path restricted to the matching research-only tagged artifact; it re-reads serialized values and verifies in-footprint finiteness/range, outside-footprint NaN, q10 confinement and point count. The resumed builder wrote the evidence receipt with `allow_nan=False`.
- Independently ran the local final-byte verifier. It reports one float32 band, EPSG:32611, 3730×3292, template transform, finite in-footprint [0,1], outside NaN/NoData and zero values outside the range. This addresses the known range-error hazard locally but does not emulate or prove portal acceptance.
- Ran the committed strict family audit over 365/365 hash-verified payloads. Exact duplicate is false and max Jaccard is 0.15347, but max containment is 1.0 and one explicitly named format-test TIFF has an incompatible grid. The unchanged gate is `NOT_CLEARED`; this failure is surfaced rather than waived because dense positive maps contain sparse support.
- Found the static site is generated. Updated the manifest, site generator, latest-report renderer and analysis source; rebuilt the site and verified links/downloads. Kept earlier TIFFs as historical prior art and did not replace them.

## Pass 3 — check against the full request

- New raster and status are prominent in README and site: **download for research: yes; submit: no**. TIFF tags/receipt say `SAFE_TO_SUBMIT=NO` and `PORTAL_VALIDATION=NOT_PERFORMED`.
- Competition format and serialized range guards cover single-band float32, EPSG:32611, exact 100 m template shape/transform/bounds, finite in-footprint values in [0,1], NaN/NoData outside, and points confined to approved tiles. The prior portal error's triggering file is unknown; no portal acceptance is claimed.
- The K2 holdout reports both H-H/H-D and candidate, gated and ungated, per fold. No promotion: q10 mean 0.2748879 vs 0.2755433, paired Δ −0.0006554, 2/6 positive; frozen best 0.2853406. The independent fresh-baseline discrepancy is disclosed.
- Stage 1 and Stage 2 are separately reported. Stage 1 mean area is 90.3288%, trace recall 90.9983%, lift 1.00747, Spearman 0.14227; uniform DTI in approved area is 0.0633556 vs 0.0636448 over support (Δ −0.0002892). It is weak/broad and does not dominate the fine-scale emission.
- Four distinct hypotheses include layers, geological signature, why faults may be uncatalogued, prior-code differences, qualitative expected benefit and cost. Full operator/source details are versioned in the hypothesis slate and preregistration.
- GEMSDOE32 H33-2-B2 remains explicitly owner-reported **UNSCORED** (owner projection 0.2747); the 0.2778 attribution and 0.3195 high are unverified and not promised. The task remains fault mapping, not vent prediction.
- Research report, copied site receipts, claims ledger, submission manifest and official source table are refreshed. No prior TIFF is reissued. No leaderboard standings are scraped or stored.

## Verification recorded

- `py_compile` — new/changed K2, Stage-1, audit, site and core modules passed.
- `scripts/check_repo_health.py --json /tmp/gems51_repo_health.json` — PASS.
- Full merged-branch pytest suite: **121 passed, 6 skipped**.
- `scripts/check_submission.py` on the K2-08 NaN-outside TIFF and the historical R1 all-finite/zero-outside TIFF — both local format checks PASS; the tool explicitly does not infer portal acceptance.
- `scripts/build_site.py` and `scripts/check_site.py` — PASS; 13 pages, local links resolve, public TIFF/ZIP set matches the manifest, and K2 is current while R1/H53 are historical.
- `git diff --check` — PASS.

## Decision and remaining work

The artifact is a genuinely new fitted research experiment and hash-distinct, but the strict family support audit is **not cleared**. The candidate also fails the paired holdout, so it must not be submitted. The official portal has not validated it. Maintain the TIFF and receipts as evidence, not as an upload-ready candidate.

PR #19 was created from `arena/55b7ede4-gemsdoe51` and pushed only to that session branch. During review, `main` advanced through PR #17 while this branch was in progress. Its R1 research TIFF, H53-A audit and receipts are retained as historical prior art; K2-08 remains the later, current experiment. The upstream merge is being incorporated into this session branch before the PR merge attempt. PR #19's final CI state and merge are recorded only after GitHub confirms them. No portal action is claimed.

Next scientific work should first resolve the baseline reproduction irregularity and acquire a genuinely untouched spatial/trace-family lockbox. Do not retune K2 on the reused folds. Clarify slip-component and geodetic unit semantics with source documentation before another physical Stage-1/Stage-2 candidate. Preserve the failed K2 experiment as negative evidence.
