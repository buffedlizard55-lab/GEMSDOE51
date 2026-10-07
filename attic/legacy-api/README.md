# Quarantined: modules and scripts written against a different `gems51` API

These files arrived from the PR #1 / PR #2 lineage (see `attic/pr1-2/` and
irregularity **IR-51-07**).  They call an API that the merged `src/gems51`
package does not provide, so **every one of them raises `AttributeError` the
moment it is run**.  They were sitting in the live tree looking runnable.

Verified-missing attributes (checked by AST against the live package on
2026-10-07, reproducible with `python3 scripts/check_repo_health.py`):

| file | calls that do not exist |
|---|---|
| `src/gems51/scoring.py` | `metric.dti_components` |
| `src/gems51/strain.py` | `grid.PIXEL_M`, `grid.tiles`, `grid.SHAPE`, `grid.footprint`, `grid.catalogue`, `grid.spatial_blocks`, `grid.catalogue_distance` |
| `src/gems51/stage2_emission.py` | `grid.LINEAMENT_BANDS` |
| `src/gems51/stage1_strain.py` | imports `gems51.strain` |
| `scripts/run_all.py` | `grid.SHAPE`, `grid.EPSG`, `detector.run_folds`, `metric.evaluate_binary`, `emission.ExpectedBudgetPacker`, `submission.write_submission`, … |
| `scripts/run_pipeline.py` | `grid.read_catalogue`, `emission.weighted_sample`, `grid.write_submission`, … |
| `scripts/run_detector_screen.py` | `grid.data_root`, `grid.BAND_NAMES`, `gems51.scoring` |
| `scripts/run_holdout_spread.py` | `emission.pack_by_threshold`, `gems51.stage1_strain` |
| `scripts/run_offcat_holdout.py` | `features.load_or_build`, `detector.BUFFER_PX`, `metric.evaluate_binary` |
| `scripts/run_strategy_sweep.py` | `detector.fold_masks`, `metric.evaluate_binary` |
| `scripts/rebuild_submission.py` | `submission.build_emission`, `submission.uniqueness_gate`, … |
| `scripts/check_stage_a_convention.py` | `grid.tiles`, `strain.TILE_PX` |

The JSON they once produced is still in `evidence/` and is still cited, with
provenance, as a **previous-session measurement**.  Nothing was deleted.

The live replacements are:

| quarantined | live equivalent |
|---|---|
| `run_offcat_holdout.py` | `scripts/run_offcatalogue_ab.py` (clean reimplementation, same instrument) |
| `run_all.py` / `run_pipeline.py` | `scripts/run_experiments.py` → `run_autocontext.py` → `build_submission.py` |
| `scoring.py` | `gems51.metric` + `gems51.holdout` |
| `strain.py` / `stage1_strain.py` | `gems51.strain_budget` |
| `stage2_emission.py` | `gems51.emission` + `gems51.trace_emission` |
