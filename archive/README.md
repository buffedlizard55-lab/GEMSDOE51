# Archived outputs and research (not active downloads or recommendations)

Nothing under this directory is a current submission recommendation. The current eligibility state is in `../data/submission_manifest.json`; the website intentionally serves no archived TIFF or ZIP from `docs/downloads/`.

## 2026-10-06 artifacts

`submissions/2026-10-06/` contains earlier candidate maps and receipts retained only for audit and uniqueness comparisons. They were not newly created in the current review and must not be submitted. Some zero-outside GeoTIFFs fail the official null/NaN-outside requirement. A format-valid NaN twin is not thereby promoted or eligible.

`site-artifacts/2026-10-06/`, `evidence/legacy-2026-10-06/`, `data/legacy-2026-10-06/`, `research/2026-10-06/`, and `registry/2026-10-06/` contain superseded receipts, holdouts, and pre-registration text. They are historical evidence, not current results or organizer scores. Consult the current evidence under `../data/`, `../knowledge/`, and `../registry/` first.

## PR #6 artifacts and research (dated 2026-10-07)

When this branch was reconciled with the then-current `main`, PR #6's candidate TIFFs, manifest, checks, and supporting experiment outputs were found. They were moved here rather than left in the public download directory or reissued under a new name. The source pull request is [#6](https://github.com/buffedlizard55-lab/GEMSDOE51/pull/6); the archived manifest is `submissions/2026-10-07/submission_manifest-pr6.json`.

The PR #6 Stage-2-only emission sweep records `ste_L9_w0.35_s2.4_nothin` at mean proxy DTI 0.2836026, versus 0.2816394 for its isotropic incumbent (+0.0019632, better in 4/6 folds). This is a previously recorded, not independently rerun, metric-geometry result; it is not a geological-hypothesis result or organizer score. The packaged H-D artifact used a separate Stage-1 soft weight of 0.10 and the manifest reports a 0.0020 holdout cost versus the ungated field. Its Stage-1 approved-area share was 0.8005 and emitted share inside those tiles was 0.7710 (lift 0.963). The alternate H-M arm records mean proxy DTI 0.2826030, below the Stage-2-only emission result. Keep Stage 1 and Stage 2 distinct; the candidate's non-dominant Stage-1 share does not erase its holdout cost.

The archived NaN-outside H-D STE and H-M soft-weight TIFF variants pass this checkout's local format check against the sample-submission footprint; their zero-outside counterparts fail the official null-outside test. Format validity alone does not establish eligibility, uniqueness, a new model run, portal acceptance, or a competition result. The maps were already published on `main`; their competition-slot/portal status is unverified, so they are not reused or relabelled. No fresh output for the Stage-2-only lead was built in this review because the raw training-feature raster and prepared arrays are absent. The next step is to restore those inputs, reproduce the sweep and separate Stage-1 ablation, then use the current guarded builder only if a genuinely new candidate clears every gate.

The archived PR #6 research notes are kept for provenance, not as current scientific guidance. Any former leaderboard snapshot or copied standings are excluded from this branch's active records; this repository does not scrape, mirror, or manually transcribe leaderboard standings. See the current Terms-of-Use note in `../README.md`.

The source-aware builder scans archived TIFFs when checking support uniqueness. Moving old rasters out of the public download directory does not exempt them from the gate.
