# Current analysis index

The up-to-date, source-linked result review is [`gemsdoe32-case-study-2026-10-07.md`](gemsdoe32-case-study-2026-10-07.md). Prior analysis versions contained leaderboard-derived calculations and copied standings; these are not reproduced in the active record. Superseded local experiment receipts are kept under `archive/` with a historical-only notice. DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) prohibits automated monitoring/copying and manual monitoring/copying without prior written consent.

## Current measured evidence

- H-D six-fold baseline: mean proxy DTI 0.2816627 and mean AUC 0.6726183 at `M/|G|=3.47` ([`data/holdout_H_D.json`](../data/holdout_H_D.json)).
- Narrowed H51-X1 implementation: mean proxy DTI 0.2796713; delta -0.0019913 versus H-D; wins 3/6 folds; not promoted. The measured features used only rank-normalized `comp_tmi` and `comp_iso_grav_anom`, not the full preregistered derivative-band family (those layers remained in the common baseline stack but were not inputs to the new transform), so the broader hypothesis remains incompletely tested ([`data/holdout_H_X1.json`](../data/holdout_H_X1.json), [`preregistration-2026-10-07.md`](preregistration-2026-10-07.md)).
- Corrected Stage-1 trace holdout: deficit Spearman 0.03916 and top-50% lift 1.08290, below the geodetic-only comparator; Stage 1 is weak ([`data/stage1_trace_holdout.json`](../data/stage1_trace_holdout.json)).
- Hard Stage-1 gates substantially reduce Stage-2 proxy DTI ([`data/two_stage_results.json`](../data/two_stage_results.json), [`data/gate_sweep.json`](../data/gate_sweep.json)).
- H-D soft `w=0.20` clears the numerical promotion test only marginally but fails local uniqueness against the archived soft-`w=0.10` map (support Jaccard 0.86130, containment 0.92548). The generator stopped before writing a new GeoTIFF; no slot was used.

## Scope limits

These are local blocked holdout results against the known-fault catalogue, not against the hidden new-fault test labels. They cannot validate that a geological signature finds genuinely unmapped faults or predict an organizer score. The archived 2026-10-06 official leaderboard read is not retained in the active research record; no automated or manual leaderboard monitoring/copying is implemented.
