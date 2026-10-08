# Executive submission guide — 2026-10-08

## Decision: no upload-eligible file

**Do not spend a competition slot or upload any current raster.** No organizer score has been received for a GEMSDOE51 artifact, and no portal acceptance is known. The new H53-A map is available for research/audit only and is explicitly named `RESEARCH-ONLY-DO-NOT-SUBMIT`.

### H53-A diagnostic artifact

- GeoTIFF: [`docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.tif`](../docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.tif)
- One-file ZIP: [`docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.zip`](../docs/downloads/gemsdoe51-h53a-budget-q10-hd-hh-r44069-20261008T030347Z-RESEARCH-ONLY-DO-NOT-SUBMIT.zip)
- Identifier and optional-note string are **research labels**, not portal fields. Do not paste them into DrivenData.
- Binary support: 44,069 points. The fixed mass only matches the existing local-best artifact's number of points; it is not an estimate of hidden truth size.
- SHA-256: `2f6e74e4d48ad47d07671cee4e73f08d012178e337a9045a9b57e51012b3613a`.

## Why it is not cleared

1. **Stage 1, coarse only:** under the primary fault-plane / `1e-8` interpretation, q10 approved 91.64% of holdout area and recalled 91.65% of visible-catalogue truth; recall/area lift was 0.9996 and tile Spearman was 0.0608. The geodetic-only control was similar (lift 0.9961). These measurements do not show meaningful residual enrichment. The source-defined residual may instead reflect off-fault or aseismic deformation, the source-rate convention, dip/rake/geometry/unit assumptions, geodetic processing, or model error.
2. **Stage 2, fine-scale separately:** fresh ungated H-D/H-H mean was 0.2853152 versus frozen local-best 0.2853406. Reproduction drift (−0.00002545) exceeds the fixed `1e-5` tolerance. The q10-constrained mean was 0.2665098 (−0.0188308 versus frozen; 0/6 paired folds positive). All scores are visible-known-fault proxy DTI, not hidden-label or organizer scores.
3. **Support uniqueness:** the local available-artifact gate passed. The broader pinned public-family gate fetched and SHA-verified 365 unique TIFF Git blobs across 54 repositories, compared 364 same-grid references plus local files, found no byte duplicate, and saw maximum support Jaccard 0.184778. It nevertheless **failed** the existing max-containment threshold: multiple dense family maps fully contain this sparse point support (1.0 > 0.6). Full receipt: [`evidence/h53_public_uniqueness_20261008.json`](../evidence/h53_public_uniqueness_20261008.json). Do not describe the map as globally or broadly unique.
4. **Format:** local checks pass: one float32 band, EPSG:32611, exact 3730×3292 grid and transform, all cells finite in `[0,1]`, zeros outside the footprint, and one TIFF inside the ZIP. This does **not** prove portal acceptance. The historical portal range error's triggering file remains unknown.

The full measured receipts are [`evidence/h53_stage1_holdout_20261008.json`](../evidence/h53_stage1_holdout_20261008.json), [`evidence/h53_stage2_holdout_20261008.json`](../evidence/h53_stage2_holdout_20261008.json), and [`evidence/h53_artifact_20261008T030347Z.json`](../evidence/h53_artifact_20261008T030347Z.json). Source attributes are independently reconciled in [`evidence/official_attribute_audit_20261008.json`](../evidence/official_attribute_audit_20261008.json).

## Required future gate sequence

Do not use a weekly slot unless a new, frozen candidate:

1. is genuinely new (no prior raster copied/re-encoded as a prediction input);
2. has a preregistered geological rationale, official/source-verified inputs, and 3–5 ranked alternatives;
3. beats the current same-instrument, same-fold local best under a leakage-safe blocked holdout, with separate Stage-1 and Stage-2 results;
4. demonstrates Stage 1 is a broad prior rather than the dominant locator, including a same-domain Stage-2 control;
5. passes final-byte grid, CRS, transform, dtype, value-range, and outside-footprint checks;
6. clears both local and pinned-family uniqueness checks (or transparently documents why an inventory is out of scope); and
7. is labeled with a unique identifier/comment only after every gate passes. Format validation alone does not authorize upload.

The official competition target is **fault geometry**, not geothermal-vent labels. See the [official problem / format / metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).

## Score attribution and leaderboard policy

The GEMSDOE32 owner page marks H33-2-B2 **UNSCORED** and describes 0.2747 as a modeled projection; the user-reported 0.2778 file-score mapping is unverified. The official leaderboard page was manually checked on 2026-10-08: 0.3195 was not the page high, but leaderboard standings cannot authenticate the H33 file attribution. The project does not persist a leaderboard snapshot or automatically monitor standings. See the [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) and [Terms of Use](https://www.drivendata.org/termsofuse/).

**Session handoff:** read the current top section of [`README.md`](../README.md) and the [H53-A preregistered slate](candidate-hypotheses-2026-10-08.md) before the next change. Keep work on `arena/922033c2-gemsdoe51`; no competition slot is authorized by the current evidence.
