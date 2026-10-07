# Score-attribution correction and candidate follow-up — 2026-10-07

> **Correction:** a prior draft attributed a public 0.2778 result to GEMSDOE32 `H33-2-B2` and
> attempted to explain that result using local raster arithmetic. The attribution is **unsupported
> and contradicted by the sibling repository's own report**. Do not cite the earlier narrative as a
> fact about a scored file.

## Attribution and scientific limits

This repository does not store or monitor leaderboard standings, consistent with the official
[Terms of Use](https://www.drivendata.org/termsofuse/). The official [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
is an external source; its participant rows do not provide a verified TIFF hash, feature recipe, or
method. GEMSDOE32's owner README/site labels `H33-2-B2` **UNSCORED** and describes **0.2747** as a
modelled projection. No file-to-score link validates the proposed 0.2778 attribution.

The published distance-weighted Tversky index uses
`DTI = TP_w / (0.2 * (TP_w + FP_w) + 0.8 * |G|)` and a triangular credit kernel that reaches zero at
300 m ([official metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
Without the exact scored TIFF and hidden evaluation labels, weighted TP/FP, hidden `|G|`, and the
geological reason for any participant result are not identifiable. A score alone cannot establish a
causal operator or geological discovery. See the sanitized
`evidence/score_attribution_audit.json` for the correction and evidence classes; no standings are
mirrored here.

## H-M cross-scale crest experiment (local proxy only)

The stream-B H-M experiment adds cross-scale crest-coincidence features on `comp_det_elev` and
`lid_relief` to H-D. On six matched spatial blocks it averaged proxy DTI **0.282603** vs **0.281663**
for H-D (paired Δ **+0.000940**, positive in **3/6** folds; paired sample SD **0.003036**; approximate
paired 95% t interval **[−0.002246, +0.004127]**). Mean AUC is 0.674746 vs 0.672618. The within-H-M
soft-prior comparison is only +0.0000077 at w=0.10 vs ungated, positive in 3/6 folds. These values
use the visible catalogue, not hidden organizer labels; the point estimate is not a robust win.

The refreshed 54-repository public-corpus audit **fails** for the packaged H-M soft file because its
same-prediction NaN twin has Jaccard/cosine 1.0; H-M also exceeds the support-Jaccard limit against its
hard-q20 variant (0.634). A current full-map q70 Stage-1 dominance check is unavailable. H-M is
research-only and not slot-eligible. Evidence: `data/holdout_H_M.json`,
`evidence/uniqueness_gate_H_M_soft_20261007.json`, and `evidence/gate_sweep_H_M.json`.

## STE emission-method screen and H-G matched add-on

The mainline emission-geometry sweep's highest six-fold mean was STE L9 (`w=0.35`, spacing 2.4 px):
proxy DTI **0.283603** vs **0.281639** for isotropic NMS (paired Δ **+0.001963**, 4/6 folds higher;
paired SD about 0.003454; approximate paired 95% t interval **[−0.00166, +0.00559]**). This is a
repository-recorded emission-method result, not a new geological hypothesis, and the small-sample
interval includes zero. Its broad audit fails on a same-prediction NaN twin (Jaccard/cosine 1.0); no
current q70 full-map Stage-1 check exists. It is not slot-eligible. See `evidence/emission_geometry.json`
and `evidence/uniqueness_gate_STE_HD_20261007.json`.

The separately materialized H-G+H-D experiment (magnetic-gravity crossings added to H-D) averaged
**0.281056** vs H-D **0.281663** (paired Δ **−0.000606**, 3/6 folds higher; mean AUC 0.669619 vs
0.672618). It loses the matched holdout. Its unique prediction support passes the refreshed scoped
public-corpus audit, and its historical q70 Stage-1 diagnostic is non-dominant on the archived prior field (30.046% of footprint area approved; 19.728% of emissions inside; lift 0.657). The current signed/rate-selectable Stage-1 map was not regenerated, so this is not a current-formula dominance check. The NaN-outside format re-encoding
preserves in-footprint predictions exactly and passes the local format checker, but it remains
**research-only and not slot-eligible**. See `evidence/experimental_H_G_plus_H_D_artifact.json`,
`evidence/uniqueness_gate_H_G_HD_experimental_20261007.json`, and
`data/submission_manifest.json`.

## Hypothesis status and prior art

A parallel session proposed H51-L (trace-axis snap), H51-M (cross-scale crest coincidence), H51-P
(parallel-strand offset), H51-S (dilational-jog coincidence), and H51-V (vent alignment). They are
not all validated; each is a specific operator, not evidence that the broad family is globally novel.

The active four-hypothesis slate for this task, including target layers/signatures, sibling prior-art
comparisons, expected benefit, cost, and the matched H-G test, is
`evidence/hypothesis_slate_20261007.json`. The prior-art audit covers 582 selected public documents
from 54 sibling repositories and makes no global novelty claim:
`evidence/sibling_prior_art_audit_20261007.json`.
