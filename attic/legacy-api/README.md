# Quarantined legacy APIs and unsafe builder variants

This directory contains scripts and modules from two different experimental lines that are not part of the current evidence or submission path.

## PR #1 / PR #2 API lineage

Most files here call APIs no longer provided by the active `src/gems51` package. The active health checker parses those runners and flags stale method calls; do not run them as current experiments.

| file | stale calls / reason |
|---|---|
| `src/gems51/scoring.py` | `metric.dti_components` |
| `src/gems51/strain.py` | `grid.PIXEL_M`, `grid.tiles`, `grid.SHAPE`, `grid.footprint`, `grid.catalogue`, `grid.spatial_blocks`, `grid.catalogue_distance` |
| `src/gems51/stage2_emission.py` | `grid.LINEAMENT_BANDS` |
| `src/gems51/stage1_strain.py` | imports the retired scalar `gems51.strain` module |
| `scripts/run_all.py` | old grid, detector, metric, and submission writer APIs |
| `scripts/run_pipeline.py` | old grid and emission APIs |
| `scripts/run_detector_screen.py` | old band names and scoring module |
| `scripts/run_holdout_spread.py` | old emission packer and Stage-1 module |
| `scripts/run_offcat_holdout.py` | old features, detector, and metric APIs |
| `scripts/run_strategy_sweep.py` | old detector fold and metric APIs |
| `scripts/rebuild_submission.py` | old writer and uniqueness APIs |
| `scripts/check_stage_a_convention.py` | old grid and strain APIs |

Their superseded receipts are under `archive/evidence/legacy-2026-10-06/` and `archive/data/legacy-2026-10-06/`, not in the active evidence directory.

## PR #6 submission-writer variant

`build_submission_v2.py` was retired after repository reconciliation. It called a writer API that no longer matches `gems51.submission`, wrote zero-outside and NaN-twin artifacts before uniqueness checks, and included stale promotion/format claims. The active `scripts/build_submission_v2.py` is a fail-closed stub; the full historical source is retained here for audit only. Do not execute the archived builder.

## Current replacements

| quarantined | current path |
|---|---|
| legacy holdout/emission experiments | `scripts/run_experiments.py`, `scripts/run_autocontext.py`, `scripts/run_emission_geometry.py`, and dedicated current holdout runners |
| legacy submission writers | `scripts/build_submission.py` (fail-closed; only after promotion, format, uniqueness, and Stage-1 checks) |
| old scalar Stage-1 modules | `src/gems51/strain_budget.py` |
| old emission code | `src/gems51/emission.py` and `src/gems51/trace_emission.py` |
| old site/data outputs | current files under `data/`, `knowledge/`, `registry/`, and `docs/`; archived material is historical-only |
