# New candidate slate — preregistered before implementation/scoring

## Decision and evidence classes

2026-10-07. Optimize fault discovery, not geothermal-vent classification. Rankings below are qualitative research judgments, **not predicted DTI values**. Novelty is bounded to inspection of src/gems51, archived hypothesis records and the existing 54-repository keyword audit, not all published work. No new external data is required for these four tests; the pinned competition and DEM-derived mirrors are now restored. Mirror hashes do not authenticate organizer provenance.

| Rank / ID | Layers and physical operator | Missing-fault rationale and confound | Difference from implemented work | Expected DTI benefit / cost |
|---|---|---|---|---|
| 1 / P1 | Detrended elevation; bilinear samples at ±2 and ±5 pixels along the smoothed local gradient. Antisymmetric step amplitude versus symmetric crest/valley curvature; agreement of near/far step polarity. | A weathered scarp may retain a one-sided height step despite weak peak slope. Rejecting symmetric ridges/valleys may reduce fluvial false positives. Not proof: terraces and lithologic contacts also make steps. | H-D aggregates scarp-facing coherence; H-H models potential-field endpoints/relays; K1 uses derivative-ratio persistence. None computes this paired odd/even topographic profile decomposition in current code. | Highest of this slate, uncertain; medium, three additional features and six paired folds. |
| 2 / P2 | Detrended elevation and isostatic gravity anomaly: compare normal-profile step *locations* at two scales, using local cross-correlation lag, not just gradient alignment. | Burial may offset surface break from basement contrast; bounded nonzero lag may reveal subdued covered extensions. Lithologic contacts remain a confound. | X1 uses coedge and orientation agreement; this tests bounded spatial lag explicitly. | Moderate, uncertain; high, requires reliable lag/scale sensitivity tests. |
| 3 / P3 | Supplied magnetic anomaly and radiometric K/Th/U: thin magnetic edge with **absence** of an aligned radiometric composition break. | An edge without surface lithologic contrast could be a buried displacement rather than a mapped contact. Soil/cover/alteration can invalidate that inference. | Unlike K3's corroborating ratio lineament, this tests a conditional negative control; missing radiometry must never count as absence. | Moderate-to-low, uncertain; medium. |
| 4 / P4 | Detrended elevation and DEM-derived scarp step/relief: along-edge second derivative of local step amplitude, looking for a finite taper bracketed by coherent shoulders. | A dying displacement profile may expose an unmapped segment end; drainage can also taper. | Unlike catalogue-tip continuation and H-H potential-field endpoint counts, measures topographic displacement-proxy taper independent of catalogue geometry. | Low-to-moderate, uncertain; high. |

## Frozen P1 screen

Only P1 will be scored in this pass. No post-result tuning. Use existing 6 spatial folds, 12 px buffer, 250,000 negatives, seed 1000+fold, HGB 250 iterations. Candidate = 0.5 H-D + 0.5 (H-H + three P1 profile features). Baseline = fresh 0.5 H-D + 0.5 H-H. Fixed STE L9 / w0.35 / spacing2.4, mass ratio3.47, fold-specific q10 Stage-1 mask, catalogue exclusion2px. Report Stage1 trace holdout separately from Stage2.

Promotion requires candidate gated mean > frozen best0.285340602656319; paired gated mean improvement and >=4/6 positive folds; reproduced frozen baseline within1e-5; every emitted point in approved tiles; approved fraction>=2/3. A failure may still produce a **new research-only diagnostic TIFF** to satisfy the request for an inspectable file, but NEVER an upload recommendation or a competition slot. This distinction supersedes the previous README's blanket no-artifact policy; it does not relax promotion.

Format policy: new artifacts use float32, exact template CRS/shape/affine, all cells finite and strictly in[0,1], zeros outside footprint and no NoData tag. This removes common range-error inputs; it is not evidence of portal acceptance. Binary normalization (0/1) preserves the tested point emitter.

## Scientific sources checked this session

- Official organizer task, labels, data and metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (fetched2026-10-07). Faults, not vents, are the target. Catalogue incompleteness is explicit.
- GDR dataset and CC-BY4.0 / redistribution attribution: https://gdr.openei.org/submissions/1391 (fetched2026-10-07). Lists official v2 Qfault shapefile AND field definitions, geodetic grids, MT, and geothermal observations.
- Kreemer et al.(2000), Eq3: https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf (fetched2026-10-07). Supports tensor summation, **not** the assumption that every residual is an unmapped fault.
- GEMSDOE32 primary owner record: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html (fetched2026-10-07). Reports 37,654 dots, pruning within200m of catalogue, and UNSCORED status; no authenticated0.2778 mapping.

P1–P4 are proposed physical discriminants, not literature-validated discoveries or numerical performance claims. No external-source availability assumption is needed beyond the restored inputs. A new independent lockbox is required before strong generalization claims: these six folds have already been reused across many hypotheses.
