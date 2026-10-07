> **ARCHIVED / SUPERSEDED.** This 2026-10-06 digest predates the corrected 2026-10-07 evidence and contains methods and conclusions that were later revised. Do not treat its Stage-1 claims, hidden-label assumptions, or candidate result as current. Current status and corrections are in `../../../README.md`, `../../../knowledge/analysis.md`, and `../../../knowledge/gemsdoe32-case-study-2026-10-07.md`. It contains no organizer-verified score.

# Research digest — session 2026-10-06 (GEMSDOE51)

Everything here is either **official** (read from a competition page, with a link) or
**measured-here** (produced by a script in this repository). Nothing is recalled from memory.

## 1. The five facts that shape the whole problem

| # | fact | class | where |
|---|---|---|---|
| 1 | Metric = distance-weighted Tversky, α=0.2, β=0.8, triangular kernel R=300 m (3 px) | official | [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| 2 | **Known USGS/INGENIOUS fault pixels are MASKED out of the penalty terms** | official | [forum 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) |
| 3 | **“New fault” includes new geometry of an existing system** — continuations, splays, step-overs | official | [forum 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536) |
| 4 | The hidden set is expert-labelled faults **absent from the public database**; round 2 rescoring is against an expert-expanded label set | official | page 967 |
| 5 | `sample_submission.tif` **IS** the catalogue rasterised (60,988 px both; `np.array_equal` True) | measured-here | `registry/data_manifest.json` |

Fact 5 is the structural confirmation of fact 2: the template described as “total fault absence”
is in fact the known-fault map. Under an unmasked metric it would score ≈ 1.0 and the competition
would be broken.

## 2. The derived identities that drive every design choice

With `T=TP_w`, `S=Σp`, `M=Σ p·max k`, `K=|truth|`:

```
FP_w = S − M        FN_w = K − T        DTI = T / (0.2(T + S − M) + 0.8K)
adding a unit of mass raises DTI   ⇔   k > 0.2·DTI
```

Verified in two independent ways: brute-force O(N²) transcription (worst |diff| **4.23e−07**) and
the official worked example (published 3.00/1.89/2.00/0.60 → measured 3.0049/1.8857/1.9951/0.603624).

## 3. The counter-intuitive result that matters most

`TP_w` is a sum **over the truth**, so each truth pixel pays at most once regardless of how many
predictions cover it. Measured consequence, leave-one-trace-out, 4 draws, matched 44,090-dot budget:

| arm | mean DTI | vs random |
|---|---:|---:|
| **field-weighted sampling (SHIPPED)** | **0.033237** | **+0.001323 (4/4)** |
| uniform random | 0.032650 | — |
| top-of-ranking peak packing | 0.025600 | −0.006315 (0/4) |
| core + shell only | 0.017670 | −0.014180 |

Peak packing had a **2.3× higher per-dot credit density** than random and still lost.
**Breadth of coverage is the binding constraint; the detector sets the bias, not the set.**

## 4. Band-level detector screen (Hessian ridge, 4 blocked folds)

`all19` fusion **0.8229** (4/4). Best single bands: 19 detrended-elevation slope **0.8161**,
5 isostatic-gravity slope **0.7951**, 12 detrended elevation **0.7945**, 18 gravity horizontal
gradient **0.7936**, 11 gravity vertical gradient **0.7933**, 6 tilt/curvature **0.7901**.
**Band 10 (distance to earthquake) is 0.4791 — anti-informative; do not use it alone.**

## 5. Failed hypotheses, kept on the record

* **Strike-steering** (gate the Hessian ridge by alignment with the mapped-fault strike):
  AUC **0.4542** vs 0.7005 unsteered; **−0.01126** DTI, 0/4 folds. Rejected by measurement.
* **Contiguous-quadrant protocol as a promotion instrument**: it rewards uniform spreading
  regardless of ranking quality, because every dot outside the evaluated quadrant is pure cost.
  It returned promotion FAIL and that result stands in `evidence/holdout_run.json`.

## 6. Data blocker

The competition data page is login-walled and `drivendata.org`, `gdr.openei.org`,
`mrdata.usgs.gov`, `sciencebase.gov`, `earthquake.usgs.gov` and every non-GitHub/non-PyPI host
return **HTTP 000** from this sandbox. Consequence: the INGENIOUS shapefile slip-rate attributes
**could not be confirmed** (IR-51-01) and the slip rate is a documented parameter with a published
sweep, not a claimed observation. The four core rasters were obtained from the group's own
integrity-pinned mirrors and all four SHA-256 pins match.
