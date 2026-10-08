# Session entrypoint

Before any work, read `README.md` (current decision and standing user task brief),
`knowledge/k2-08-results-2026-10-08.md`, `knowledge/k2-08-candidate-hypotheses-2026-10-08.md`,
`registry/preregistration_k2_stage1_20261008.json`, the current K2 receipts in `evidence/`,
all three H53 slates (`registry/preregistration_h53sr_20261008.json` this session's
strain-residual; `registry/preregistration_h53.json` finite-lag; and
`evidence/candidate_hypotheses_budget_q10_prereg_20261008.json` budget-q10),
`knowledge/candidate-hypotheses-2026-10-08.md` (earlier H53-K2x slate),
`knowledge/pr20-h53-r1-review-three-passes-2026-10-08.md`,
`knowledge/review-three-passes-20261008.md`, and
`knowledge/executive-submission-guide-2026-10-08.md`. Treat versioned receipts and
`data/submission_manifest.json` as authoritative; older pages and owner reports do not
override them.

**Merged-session state (2026-10-08, three parallel sessions):** the H53-SR two-stage artifact
(`docs/downloads/gemsdoe51-h53-twostage-20261008T040951Z-9a0b32c871.tif`) is the RECOMMENDED
UPLOAD CANDIDATE — every local gate passed (all-finite [0,1] encoding, 100% of points inside
q10 approved tiles, Stage-1 non-dominance, uniqueness), but it has NOT been uploaded; portal
acceptance and any organizer score are unproven, and the entrant decides on the weekly slot.
See `registry/preregistration_h53sr_20261008.json`, `evidence/h53sr_holdout_20261008.json`,
and `knowledge/h53sr-session-results-2026-10-08.md`. Three parallel sessions each
preregistered an `H53-A` for a DIFFERENT hypothesis; they are disambiguated under IR-H53-05
and IR-H53-06 — do not conflate this session's H53-A (strain-residual ridge, validated, NOT
PROMOTED) with the finite-lag H53-A (Stage 2 blocked) or the budget-q10 H53-A variant
(NOT PROMOTED, research-only TIFF).

K2-08 is the parallel sessions' latest overall completed candidate. It failed the frozen paired
spatial promotion rule and the strict family uniqueness gate; its GeoTIFF is research-only and
must not be submitted. Do not tune or rescore K2-08 on the same holdout. Preserve the failed
result as evidence.

## Current scientific state

- **Latest overall completed experiment: K2-08.** It is **RESEARCH ONLY / DO NOT SUBMIT**. It failed the frozen paired spatial-promotion rule and strict pinned-family support-uniqueness audit (`NOT_CLEARED`; maximum containment 1.0; one incompatible-grid reference). Stage 1 is a broad, weak coarse prior; Stage 2 is reported separately and below its fresh comparator and frozen best. Do not retune/rescore K2-08 on the same folds, waive either gate, claim global uniqueness, or spend a competition slot.
- **Latest H53-family experiment: finite-lag H53-A.** Its separate Stage-1 audit completed, but Stage 2 was blocked before candidate scoring when fresh canonical H-D/H-H baseline reproduction missed the frozen mean by `−0.000025448`, outside `1e-5`. There is no candidate score or TIFF for this operationalization. Do not weaken its gate, substitute the H52 seed-2000 cache, or shop for a passing result.
- **Separate componentwise budget-q10 H53-A variant.** This distinct operationalization has its own research-only TIFF and Stage-1/Stage-2 receipts; it is not the finite-lag H53-A candidate, H53-K2x, or K2-08. Stage 1 showed no meaningful residual enrichment; Stage 2 was not promoted (`0/6` paired folds positive; q10 mean `0.2665098` vs frozen `0.2853406`). Its local 21-reference check passed, but the pinned public-family support-containment gate failed (max containment `1.0`); do not describe it as broadly unique or upload-cleared.
- **Earlier H53-K2x.** A distinct six-fold screen with a separate research-only TIFF, not an H53-A or K2-08 result. It was not promoted and its broader family uniqueness gate is not cleared. Preserve its slate, receipt, and artifact separately.
- **R1.** The all-finite, zero-outside confinement regeneration is a separate historical research artifact. It failed its paired restriction rule (Δ `−0.0014061`, `0/6` folds won); it is not cleared for upload.
- **No current artifact is cleared for a competition slot.** Local format checks are not portal validation; the portal range-error trigger remains unknown. Do not claim hidden-label performance or organizer scores from proxy DTI.

Never reuse an old TIFF as a new prediction. Generate and rank 3–5 hypotheses before implementation, name layers/signatures/missing-fault rationale/differences/costs, use official sources and verify attributes, and validate the leading candidate on a spatially blocked holdout before any weekly slot. Keep coarse Stage 1 separate from Stage 2 and measure Stage-1 dominance; enforce actual allowed-domain confinement. Require a new candidate to beat the local holdout best, clear format and applicable uniqueness gates, and preserve negative results. Do not conflate distinct variants, owner/user-reported scores, and organizer-scored results or attribute a score to a file without evidence.

Keep the repository's link-only/no-automatic-leaderboard-monitoring policy unless permission is established. The official target is fault geometry, not geothermal-vent labels. Treat the user-reported `0.3195` as stale (a one-time official-page check found it was not the page high); do not persist standings or automate monitoring. Distinguish source-verified values from assumptions and state irregularities explicitly.

Work only on the Arena session branch `arena/922033c2-gemsdoe51`; do not switch branches. Use `./.venv/bin/python` and `./.venv/bin/pytest` (system Python lacks project dependencies). `data/raw`, `data/prepared`, and `work` are regenerable/ignored; keep bulk data out of Git. Historical slates and notes provide context but do not supersede the current receipts, the manifest, or the relevant preregistration.
