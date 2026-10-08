# Session entrypoint

Before any work, read `README.md` (current decision, standing user brief and appendices),
`knowledge/hypothesis-slate-20261008.md`, `knowledge/candidate-hypotheses-2026-10-08.md`,
`registry/preregistration_h53.json`, `knowledge/preregistration-2026-10-08.md`, and the latest
receipts in `evidence/`. The workspace contains two distinct H53-A operationalizations; do not
conflate their results:

- **Current finite-lag H53-A:** Stage 1 was audited, but Stage 2 is fail-closed because the fresh
  canonical H-D/H-H baseline missed its frozen mean by `−0.000025448`, outside `1e-5`. No
  candidate score or TIFF exists for this operationalization. Do not weaken its frozen gate, rerun
  to shop for a passing result, or substitute the H52 seed-2000 cache. Recover auditable baseline
  lineage or preregister a new baseline before any future candidate scoring.
- **Separate componentwise budget-q10 H53-A variant:** this was scored independently and produced
  a fresh TIFF, but it is **RESEARCH ONLY / DO NOT SUBMIT**. Stage 1 showed no meaningful
  residual enrichment; Stage 2 failed promotion; the pinned public-family support-containment
  gate failed. Its file and evidence are recorded separately in `data/submission_manifest.json`
  and the H53 receipts. A local format or scoped-uniqueness pass is not submission clearance.
- **R1:** the current primary manifest entry is also research-only; its paired confinement rule
  was not promoted. No artifact is cleared for a competition slot.

Never reuse an old TIFF as a new submission. A candidate must beat the current local holdout best
under a valid, reproducible, preregistered comparison before any competition slot is considered.
A research download must be unmistakably marked NOT FOR SUBMISSION. Do not claim portal acceptance
from local checks or attribute user/community scores to a file without verified evidence. Preserve
failed experiments and do not tune until a valid holdout passes.

Keep Stage 1 coarse and separate from Stage 2. Validate on spatial holdouts, verify official
sources and attributes, test artifact uniqueness and format, and report limitations and
irregularities. Do not claim hidden-label performance, organizer scores, or portal acceptance
without direct evidence. Retain the repository's link-only/no-automatic-leaderboard-monitoring
policy unless permission is explicitly established.

Work on the Arena-provided session branch only. Data/raw, data/prepared and work are regenerable
and ignored. Keep bulk official archives out of Git. Read source definitions before converting
physical quantities; distinguish evidence from assumptions. Historical slates and session notes
remain available for context but must not override the relevant current preregistration or receipt.
