# Three-pass review and next-session handoff

## Pass1 — implement and measure

- Read repository README, prior K1 rejection, frozen H-H/H-D receipt, format/uniqueness gates, source registry and current pipeline.
- Restored ten hash-pinned data inputs without user data placement. CPU feature preparation,18 fold fits, two full-grid fits and new TIFF generation completed.
- Preregistered four hypotheses before P1 scoring. Kept fixed six-fold protocol, q10 mask, seeds, model size and emission parameters. Candidate failed:0.2839869 vs paired0.2848987;2/6 positive. No slot.
- Official-source acquisition succeeded on Actions after local direct/artifact redirects were blocked. Extracted original DBF attributes, source definitions, geometry and archive checksums. All1,126 mirrored rows match source rates/names/senses.
- Implemented geometry-clipped tensor summation and separate source-defined scalar residuals and five-way whole-trace holdout. Did not swap a new prior into an already frozen Stage2 experiment.
- Generated a new P1 research TIFF; no prior prediction raster in its model/emitter inputs. Wrote explicit unique name/comment; reread final bytes and verified full-grid finite[0,1] and no NoData. All44,069 points confined; broadness and ablation measured.

## Pass2 — bug/assumption/edge-case review

- Fixed input acceptance of invalid outside values and illegal negative NoData sentinels; tests include ±Inf, negative sentinel and values>1.
- Removed false “guaranteed portal acceptance” language. Published null/NaN-outside wording versus zero-outside compatibility remains a real unresolved distinction.
- Tested clipped segment length conservation, exact tile-boundary ownership, zero-length and outside segments, tensor reversal invariance, signed strike-slip, normal-fault units and source shear.
- Tested P1 constant fields, datum invariance, missing shoulders, step versus symmetric ridge, parameter validation. Changed no P1 coefficients after results.
- Official metadata disproved the old “unknown shear definition/no scalar identity” explanation. Added the correct identity and measured its remaining sampled mismatch without inventing a processing history.
- Corrected raw-mass DTI identity in old explanatory prose. Raw point count is not TP+FP.
- Kept bulk official ASCII data out of the final tree, with an extraction-size guard. Dataset geometry/attributes are small enough to audit in Git; bulk rasters/archives remain ignored.
- Detected broader inventory fetch failures due to paths removed from main; immutable Git-blob fallback verifies both object hash and size rather than substituting changed files.
- Prohibit repeat completed P1 scoring to shop for a positive result. Pin the tested Python environment in requirements-tested.txt; exact old frozen environment remains unknown.

## Pass3 — requirements and release review

- New TIFF appears first on site and README, clearly downloadable but NOT FOR SUBMISSION. Old historical files remain labeled historical/research-only.
- Stage1 and Stage2 have separate receipts. Official-vector Stage1 and legacy P1 gate are clearly distinguished, not conflated.
- No causal explanation of0.2778 is asserted: owner site remains UNSCORED. No claimed0.3195 improvement. No leaderboard monitoring or automatic competition submission.
- Numeric format is measured, portal acceptance is not claimed. Known-fault proxy results are not geothermal discoveries or hidden expert-label scores.
- Rebuild site, check every local HTML link and manifest download, compile sources, run full tests and health checker; rerun after final receipt changes before merge.
- PR12 created from the fixed session branch. Merge only after passing final CI; do not claim merge success until GitHub confirms it.

## Next session: highest-value work first

1. Reproduce the frozen0.2853406027 baseline in its original source/environment; current reconstruction consistently gives0.2853151549. Do not loosen the1e-5 gate to conceal drift.
2. Introduce an untouched geography/trace-family lockbox and catalogue-selection-bias diagnostics. Reusing the six development folds is not independent validation.
3. Resolve the geodetic metadata's literal10E-9/yr notation and slip-component/dip assumptions. Run the official-vector prior with a separately preregistered Stage2 candidate, not the rejected P1 dressed up with a new gate.
4. Test P2 bounded geophysical/topographic edge lag only after preregistration, with missing-data and lithologic-contact negative controls. Don't infer faults from broad strain/thermal habitat.
5. Verify portal outside-footprint semantics and source-data/rule/license requirements. The historical error-triggering upload has not been identified; finite byte checks cannot reveal portal implementation.
6. Refresh the family inventory and public-source records when legitimately needed; log retrieval date, immutable identity, omissions and licenses. No copied leaderboard feed.

## Remaining limitations / not fully satisfied

- No new candidate has earned an upload recommendation, and no leaderboard gain is demonstrated. This is a failed scientific experiment with a real new diagnostic TIFF, not the requested prize-winning result.
- Source-corrected vector Stage1 is audited but not yet validated jointly with a promoted fine-scale model. Legacy P1 Stage1 uses raster/centroid approximations for frozen comparability.
- No GPU or DrivenData login was necessary for this CPU pipeline; no authenticated competition submission/acceptance is available. Shell egress is restricted; GitHub Actions supplied official-source downloads.
- README preserves the complete operational mandate, urgency, source links and supplied score inventory, but repeated prose is consolidated rather than a verbatim chat transcript.

Final measured checks:73 pytest tests passed; independent final TIFF/ZIP/tile-mask verification passed;13 HTML pages passed local-link/download-manifest checks; site regeneration is byte-idempotent; compile and repository-health checks passed. Broader audit restored365/365 pinned payloads, compared364 same-shape maps, found no exact byte/support duplicate, but **NOT_CLEARED** under unchanged containment threshold (dense maps contain the sparse support) and one different-grid toy format-test file. This is prominently reported rather than hidden behind the narrower gate's PASS. The base model retains coarse feature inputs; a complete coarse-feature ablation remains undone.
