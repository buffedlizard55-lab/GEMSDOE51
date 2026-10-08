# Three-pass review and handoff — 2026-10-08

**Current decision: H53-A is RESEARCH ONLY / DO NOT SUBMIT. No weekly slot is authorized.** This document records the three requested passes, including failures and remaining blockers; it is not a scientific certification.

## Pass 1 — implement and verify

- Ranked four distinct geological candidates in `knowledge/candidate-hypotheses-2026-10-08.md` and `evidence/candidate_hypotheses_prereg_20261008.json` before implementing/scoring H53-A. H53-A was selected; H53-B–D remain blocked or untested for their stated reasons.
- Audited official INGENIOUS/QFault shapefile attributes against the preserved DBF and actual clipped trace segment export. `SLIPRT2023`/`SLIPRTNUM` in mm/year and row identity are verified; component convention, dip/rake, and observed undocumented `RL`/`LL` codes are explicit unresolved items. Formula is Kreemer et al. (2000), Eq. 3, with source link and assumptions recorded.
- Evaluated Stage 1 alone over six spatially blocked folds and separately evaluated Stage 2 under the frozen q10 protocol. Full fold-level receipts are linked in the executive guide and latest site report.
- After holdout rejection, generated one fresh full-map 44,069-point diagnostic TIFF, not by copying/re-encoding an earlier prediction. Rechecked the final bytes, ZIP contents, CRS, grid, dtype, and `[0,1]` range. The local format and local-inventory gates pass; broad-family support uniqueness fails.

## Pass 2 — review for defects, omissions, assumptions, and edge cases

### Scientific/validation findings

- Stage-1 primary lift is `0.999618`; the geodetic-only control is `0.996075`. This fails to demonstrate residual enrichment over the area baseline. It is not evidence that the residual locates an unmapped fault.
- The Stage-2 candidate is below the frozen local best; the fresh baseline itself misses the registered reproduction tolerance. Those failures were preserved, not tuned away.
- Mean Stage-1 non-dominance meets the preregistered mean rule, and full-map support/area lift is `1.10973`; however, one held block approves only `54.98%` of its area (implied confinement lift `1.819`). That instability is disclosed rather than hidden by the mean.
- Broad support uniqueness fails at containment `1.0 > 0.6`, despite zero byte duplicates and a passing local-artifact gate. No global uniqueness claim is justified.
- Format pass does not resolve the unknown historical portal-triggering file or prove portal acceptance.

### Repository/site defects corrected

- Updated README’s current status, current branch (`arena/922033c2-gemsdoe51`, verified by `git branch --show-current`), H53 evidence links, leaderboard-attribution note, ranked current slate, and future-session entrypoint. Retained earlier experiments as historical material.
- Updated `AGENTS.md` to point to the current brief, guide, slate, and receipts instead of stale 2026-10-07 notes.
- Updated `data/submission_manifest.json` before the site build so the manifest-pruning builder retains H53-A, its one-file ZIP, and final-byte checks. H53-A is explicitly `safe_to_submit=false`; `recommended_upload_candidate` remains null and the previous local best remains intact.
- Fixed `current_hypothesis_table()` to load the H53 schema and overlay H53’s measured result; split the prior H-G/H-J table into an explicitly historical renderer so the same slate/fields are not mislabeled or repeated as current.
- Replaced the P1-only `scripts/latest_report.py` with a receipt-driven H53-A report, added H53-specific current site/holdout/method content, and changed the submission guide to a no-go state. Added H53 no-go assertions to `scripts/check_site.py`.
- Added an executive submission guide and updated current source metadata. The official leaderboard is link-only; a single dated comparison is described without storing standings rows.
- Marked the old P1 section in README as historical so it cannot be confused with the current H53-A artifact or current no-go status.

**Verification (2026-10-08):** the default system `python` lacks NumPy, so the first site-build attempt failed before writing pages; using the repository `.venv` succeeded. `./.venv/bin/python scripts/build_site.py` passed; `./.venv/bin/python scripts/check_site.py` passed (13 pages, local links and download state match manifest); `./.venv/bin/pytest -q` passed (100 passed, 6 skipped); and `git diff --check` passed. The final H53-A TIFF was rechecked with `scripts/check_submission.py`: one float32 band, EPSG:32611, 3730×3292 template grid/transform, finite values in `[0,1]`, zero outside footprint, 44,069 emitted points, local format pass. SHA-256: `2f6e74e4d48ad47d07671cee4e73f08d012178e337a9045a9b57e51012b3613a`. The one-TIFF ZIP passed `unzip -t` and its archived bytes match the TIFF. None of these local checks means portal acceptance.

## Pass 3 — recheck against the full standing brief

| Acceptance criterion | Current disposition |
|---|---|
| 3–5 ranked hypotheses before implementation | **Done:** four H53 candidates preregistered. |
| Official sources, equation, source attributes, limitations | **Documented:** Eq. 3 source linked; mm/year verified; rate component/dip/rake and codebook irregularities remain explicit. |
| Stage 1 coarse holdout, Stage 2 separate holdout | **Done; H53-A rejected:** visible-catalogue proxy only; Stage 1 uninformative, Stage 2 below frozen best. |
| Candidate beats local blocked best before slot | **No:** H53-A fails. **No slot used or authorized.** |
| Full-map GeoTIFF normalized and checked | **Local checks pass:** 44,069 points, required grid, float32, finite `[0,1]`; portal not tested. |
| Local and broad uniqueness gate | **Local pass; broad gate fails:** max containment 1.0. Artifact is not cleared as unique for the audited family. |
| Stage-1 support dominance | **Reported both ways:** full-map lift 1.10973; one spatial holdout fold is more restrictive (1.819). |
| H33 / leaderboard comparison | **Qualified:** owner marks H33-2-B2 UNSCORED; `0.2778` attribution unverified; one manual official-page check on 2026-10-08 contradicts `0.3195` as page high. No standings snapshot or automatic monitor. |
| README/site/guide and review passes | **Implemented and checked:** generated site has 13 pages; local-link/download checker and full test suite pass; three passes are documented here. |
| PR and merge | **Not yet attempted.** Must remain on `arena/922033c2-gemsdoe51`; report any branch protection or permission blocker. |

### Remaining work / next session

1. **Completed before PR:** rebuilt the site after this review-note edit; `scripts/check_site.py`, `git diff --check`, and the full test suite passed. The final generated pages/downloads and H53-A warning were inspected.
2. **Pending:** create a PR from the fixed Arena branch and attempt the requested merge; never switch branches. Record the PR link and any merge blocker in this review after PR creation.
3. Do not spend a competition slot on H53-A or any other current TIFF. A future candidate requires a new slate, frozen holdout, broad uniqueness clearance, byte checks, and explicit review of the one-fold Stage-1 restriction issue.
