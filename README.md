# GEMSDOE51 — DOE GEMS / GeoDAWN fault-discovery research record

**Current decision (2026-10-07): NO NEW UPLOAD-ELIGIBLE TIFF. NO COMPETITION SLOT USED.**

The existing local H-H/H-D blend is retained as the best reproducible local benchmark (six-fold visible-catalogue proxy mean DTI `0.2853406`), but it is an earlier artifact, not the new TIFF requested in this work. It has not been uploaded or accepted by DrivenData. A user-reported submission-form error—“Predicted values must be in range [0, 1]”—is unresolved, and the exact file that triggered it was not identified. The local verifier does not emulate the portal.

The preregistered H51-K1 candidate was implemented and evaluated on the six spatial folds with a fold-specific, leakage-controlled broad Stage-1 q10 mask. It **did not pass** the preregistered promotion gates. No candidate TIFF or replacement ZIP was written. Do not treat the earlier local benchmark as portal-ready or upload-eligible.

## Full user task brief and standing acceptance criteria

This full working brief is retained so a future session can continue without asking for manual design input. It consolidates the original request and subsequent corrections; it is not a claim that every result below succeeded.

> Review the repository and complete the end-to-end DOE GEMS project. Critically assess the claimed GEMSDOE32 `0.2778` result attributed to `H33-2-B2` and the stated `0.3195` leaderboard high; do not hallucinate a score-to-file or geological explanation. Use trusted, checked sources, link them, and distinguish owner reports, local measurements, user-supplied claims, and organizer facts.
>
> Before implementation, propose and rank 3–5 distinct geological hypotheses. For each, identify its layers, target physical signature/operator, why it could expose fault geometry missing from the existing USGS/INGENIOUS catalogue rather than merely recover known-fault habitat, how it differs from implemented repository/prior-art work, expected benefit, and implementation cost. If outside data is needed, name the free official source and verify availability before treating it as viable.
>
> Validate the leading candidate on the same spatially blocked holdout before using any competition submission slot. Do not spend a slot on an idea that has not beaten the current spatially blocked best under a preregistered rule. Report Stage 1 and Stage 2 holdouts separately. Stage 1 must remain coarse and non-dominant. Reconcile that with the requirement that every Stage-2 prediction point lie inside an approved Stage-1 tile; implement and validate the actual allowed-domain mask rather than assuming `stage1_weight=0.0` provides confinement.
>
> If and only if a candidate passes promotion, Stage-1 confinement/non-dominance, scoped uniqueness, and format gates, generate a substantively new, uniquely named and commented single-band GeoTIFF. Do not copy, relabel, or merely re-encode a previous submission to satisfy the requirement. Make file/download/submission status obvious. Check exact grid, CRS, affine transform, dtype, `[0,1]` values (including the outside-footprint encoding against the live portal issue), and the official submission format. Never claim upload, organizer score, or acceptance without evidence.
>
> Review and update the site, preserve auditable research and source links, include this full prompt in README, and autonomously attempt a pull request and merge to `main`. State blockers and irregularities. No manual user input is expected.

This session is fixed to branch `arena/ec87b811-gemsdoe51`. Do not switch branches. The repository's leaderboard policy is link-only: DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) prohibit automated monitoring/copying and manual monitoring/copying without prior written permission; none is recorded. No standings feed or copied leaderboard values are maintained here.

## Current status and local benchmark

| Item | Status / result |
|---|---|
| Existing local H-H/H-D blend + STE L9 | Historical local best only; not portal-validated, not uploaded, no organizer score |
| Six-fold H-H/H-D proxy DTI | `0.2853406027`, visible known-fault catalogue; `4/6` folds beat H-D |
| Existing H-D proxy comparator | `0.2816626603` |
| H51-K1 new-operator screen | **NOT PROMOTED**; no new TIFF; no slot |
| Portal `[0,1]` validation error | **OPEN BLOCKER**; triggering file identity unknown |
| Organizer score / acceptance | None verified for GEMSDOE51 |

The existing local benchmark artifacts are linked for audit only:

- [GeoTIFF](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif)
- [One-file ZIP](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.zip)
- [Local checks receipt](docs/downloads/gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z-checks.json)
- [Submission manifest](data/submission_manifest.json)
- SHA-256: `9bd1e50d86114daa7c944d0c6d4f9f7cba6ba5070ae98ba5e45a965d78650777`
- Earlier identifier (do **not** paste until the portal issue is resolved): `GEMSDOE51-HH-HD-BLEND-STE-R347-20261007`
- Earlier note: `H-H potential-field edge-termination/conductive-relay features plus H-D, fixed 50/50 probability blend, STE L9 w0.35 spacing 2.4; holdout-promoted but no organizer score claimed.`

This old raster is locally verified as one-band `float32`, EPSG:32611, shape `3730 × 3292`, correct template transform, finite in-footprint values in `[0,1]`, and NaN outside with a NaN NoData tag. **The portal's reported range error remains unresolved**: local validity is not evidence that the portal accepts NaN outside. The exact file used in the reported portal attempt was not recorded. Do not infer that the old H-H/H-D TIFF either caused or fixes the error.

## Preregistered candidate slate and result

The full four-item slate, exact operators, source checks, prior-art boundaries, costs, and outcome are in [`knowledge/candidate-hypotheses-2026-10-07.md`](knowledge/candidate-hypotheses-2026-10-07.md) and [`evidence/candidate_hypotheses_prereg_20261007.json`](evidence/candidate_hypotheses_prereg_20261007.json). They are also linked from the [hypotheses page](docs/hypotheses.html).

1. **H51-K1 (top):** cross-scale potential-field tilt-like partial-gradient edge persistence using `tmi_hg/tmi_vg` and `iso_grav_anom_hg/iso_grav_anom_vg`.
2. **H51-K2:** directional conductivity contrast across an independent basement/potential-field edge.
3. **H51-K3:** radiometric-ratio lineaments conditional on independent structural edges.
4. **H51-K4:** earthquake-density ridge conditioned on independent structural edges; blocked until source semantics are verified.

The slate is operator-level and inspection-bounded, not a claim of global novelty. The local gravity HG band is signed; its available metadata does not establish whether it is a full 2-D magnitude or a directional component. K1 therefore tests a precisely coded **tilt-like partial-gradient proxy**, not a conventional total-horizontal-derivative tilt angle.

### H51-K1 Stage-2 holdout (separate from Stage 1)

Receipt: [`evidence/hk1_spatial_holdout_20261007.json`](evidence/hk1_spatial_holdout_20261007.json). This is a six-fold 3×3 contiguous spatial holdout, 12-pixel/1.2-km training buffer, 250,000 sampled negatives per fold, fixed seeds, `M/|G|=3.47`, and the same STE L9 / continuity `0.35` / spacing `2.4` rule. The proxy truth is the visible known-fault catalogue, not the hidden expert labels.

| Fold | Fresh H-D/H-H, ungated | H51-K1 blend, ungated | H-D/H-H, q10-gated | H51-K1, q10-gated | Paired gated Δ |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.283432 | 0.283529 | 0.283432 | 0.283529 | +0.000097 |
| 1 | 0.271784 | 0.275603 | 0.270436 | 0.274444 | +0.004008 |
| 2 | 0.290270 | 0.292220 | 0.289119 | 0.290417 | +0.001298 |
| 3 | 0.243359 | 0.242234 | 0.243359 | 0.242234 | −0.001126 |
| 4 | 0.305049 | 0.304764 | 0.305049 | 0.304764 | −0.000286 |
| 5 | 0.317996 | 0.315072 | 0.317996 | 0.315072 | −0.002924 |
| **Mean** | **0.285315** | **0.285570** | **0.284899** | **0.285077** | **+0.000178** |

The fresh ungated H-D/H-H reconstruction missed the frozen `0.2853406027` receipt by `−0.00002545`, outside the preregistered `1e-5` reproduction tolerance. The final K1 q10-gated mean (`0.2850766`) did not exceed the frozen ungated best (`0.2853406`), and the paired q10-gated gain over the same-fold q10-gated baseline was positive in only `3/6` folds. It is therefore **not promoted**, despite the ungated K1 point estimate of `0.2855703`. The separate receipts preserve every fold and metric. No K1 TIFF was built.

### Stage 1 q10 trace holdout (reported separately)

The q10 Stage-1 prior was evaluated before K1's six-fold comparison by holding out complete trace-table rows and removing held-out rows from the fault-budget tensor. Receipt: [`evidence/stage1_q10_trace_holdout_20261007.json`](evidence/stage1_q10_trace_holdout_20261007.json).

- q10 deficit mask mean approved area: `0.90063` of footprint.
- Held-out trace recall inside mask: `0.95390`; mean lift `1.05915`.
- Uniform-random-dot proxy DTI inside mask: `0.0506274`, versus `0.0485643` over the full footprint.
- During the six spatial Stage-2 folds, the separately rebuilt fold-specific q10 masks approved `0.90135` of footprint on average. Confining every K1 point to them gave Stage-1 lift `1.10945`, below the preregistered non-dominance limit `1.5`; all evaluated candidate points were inside the approved mask.

This is weak coarse enrichment, not a strong predictor. Slip-rate units/component remain provisional (see IR-51-12 and the [irregularities page](docs/irregularities.html)); Stage-1 has zero soft score weight. The q10 mask is only a broad allowed-domain constraint for the tested K1 comparison. The old local H-H/H-D TIFF was created before this q10 allowed-domain requirement and fails it: on the current full-data q10 deficit mask, 38,211 of 44,069 predicted points (86.71%) are inside the 90.09% approved area (lift 0.9624). It was not rebuilt under the q10 constraint.

## GEMSDOE32 `0.2778` and the stated `0.3195` high

The file-to-score story for `H33-2-B2 = 0.2778` is **unsupported**. The sibling GEMSDOE32 owner README/site labels `H33-2-B2` as **UNSCORED** and describes `0.2747` as a modeled projection. No organizer-authenticated mapping from the named TIFF to an observed score, exact prediction field, or hidden labels has been verified. A public DTI value alone cannot reveal a method's causal contribution or geological mechanism. See [`evidence/score_attribution_audit.json`](evidence/score_attribution_audit.json) and the [case-study page](docs/analysis.html).

The `0.3195` “current leaderboard high” is preserved as a **user-supplied, unverified claim**, not a verified fact in this repository. We do not mirror or manually monitor leaderboard rows because of the current Terms of Use. Use the [official leaderboard link](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) directly; no GEMSDOE51 score is claimed.

The official metric is the published distance-weighted Tversky index, `DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|)`, with a triangular distance-credit kernel that reaches zero at 300 m. Explaining a score requires the exact scored raster, hidden truth geometry and size, and weighted TP/FP; none can be inferred from the number alone.

## Site review and submission-status pages

The static site is generated from current records by `scripts/build_site.py` and checked by `scripts/check_site.py`. The key pages are:

- [Executive summary](docs/index.html)
- [Submission instructions and current block](docs/how-to-submit.html)
- [Hypotheses and K1 result](docs/hypotheses.html)
- [Separate Stage-1 / Stage-2 holdouts](docs/holdout.html)
- [GEMSDOE32 score-attribution review](docs/analysis.html)
- [Irregularity register](docs/irregularities.html)
- [Leaderboard policy / official link only](docs/leaderboard.html)

The site must say clearly that no new file is upload-eligible, that the K1 TIFF was not written, and that portal validation is unresolved. The old local benchmark link is for audit only. Before any future upload, identify the exact file from the user-reported error and resolve whether outside-footprint NaNs are accepted; do not assume the local verifier is the portal.

## Sources and provenance

- [DrivenData problem description, metric, data layers and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS / GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [NBMG QFaults INGENIOUS REST schema](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson); its schema does not establish the local slip-rate units
- [Kreemer et al. (2000), public UNR PDF](https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf), Eq. 3
- [Miller & Singh (1994), potential-field tilt paper](https://doi.org/10.1016/0926-9851(94)90022-1); K1 is explicitly not claimed to be the conventional total-horizontal-derivative tilt angle
- [USGS blind geothermal systems / Great Basin report](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and)
- [USGS GeoDAWN ScienceBase record, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)

All large rasters and owner-mirrored datasets are out of Git. Hash pins establish local mirror consistency, not organizer authentication.

## Reproduce, test, and review

With the hash-pinned data restored (`python scripts/restore_data.py --group all`), run:

```bash
PYTHONPATH=src .venv/bin/python scripts/prepare_data.py
PYTHONPATH=src .venv/bin/python src/gems51/stack.py
PYTHONPATH=src .venv/bin/python scripts/build_extras.py
PYTHONPATH=src .venv/bin/python scripts/run_stage1_trace_holdout.py \
  --thresholds 10 --output evidence/stage1_q10_trace_holdout_20261007.json
PYTHONPATH=src .venv/bin/python scripts/evaluate_hk1_holdout.py
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/build_site.py
PYTHONPATH=src .venv/bin/python scripts/check_site.py
```

`evidence/hk1_spatial_holdout_20261007.json` is the authoritative K1 outcome. It is `NOT_PROMOTED_NO_TIFF`; do not rerun the same configuration to shop for a passing result. Any new candidate requires a new preregistration and must clear every holdout, Stage-1 allowed-domain/non-dominance, uniqueness, format, portal-range, and provenance gate before it can produce a submission artifact.

---

## Standing user prompt — 2026-10-07 intake supplement

Read this brief **every session before implementation**, along with the full working brief above and the latest evidence. Repeated verification boilerplate is consolidated here; this is an operational transcription, not an organizer statement or a verbatim chat export.

> **THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!**
>
> **MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.
>
> Geodetic strain-budget deficit, used strictly as a coarse first stage. Hypothesis: where the geodetic strain rate exceeds what the mapped faults' slip rates can accommodate, the catalogue is likelier to be missing structures. Precedent for balancing geodetic and geologic deformation exists in the UCERF3 deformation models (Field et al., Bulletin of the Seismological Society of America 104(3), 1122–1180, 2014, doi:10.1785/0120130164). Three of those models invert geodetic and geologic data together, and UCERF3 also models off-fault strain explicitly. A related USGS-listed paper ("A fault-based model for crustal deformation, fault slip-rates and off-fault strain rate in California") estimates off-fault moment rates separately. Convert each mapped fault's slip rate (the INGENIOUS compilation is reported to hold slip rates; confirm in the shapefile attributes) and trace length into an equivalent tile strain rate using a documented moment-tensor summation. State the exact formula and cite its source, because I haven't verified one. Subtract that from the dilatation and shear strain-rate layers, and keep the residual only as a prior over broad tiles. Strain rates are coarse, and the deficit can be distributed off-fault, aseismic or caused by wrong catalogue slip rates. Habitat-style statements scored worst in this project (0.0041, 0.1223, 0.1352), so a second, separately holdout-scored fine-scale model must place points only inside approved tiles. Report both stages' holdout results separately. Normalize, write the GeoTIFF, run the uniqueness gate, and confirm the submission isn't dominated by stage one's footprint.
>
> Study GEMSDOE32 H33-2-B2, reported score0.2778, and whether a unique submission can exceed it and the stated leaderboard high0.3195. Use PhD-level scientific judgment, official checked sources and links. Do not infer causation from a score alone. Before implementing, generate3–5 previously untried geological hypotheses, each naming layers, physical signature/operator, missing-catalogue rationale, differences from existing code, expected DTI benefit and implementation cost. Rank and validate the top candidate on spatially blocked holdouts. **Do not spend a submission slot on an idea that hasn't beaten the current holdout best.** If new data are needed, identify free official sources and verify availability before calling the idea viable.
>
> Work autonomously without requesting manual data placement; review the repo and next steps from previous sessions first. Research official scientific literature and data, organize an auditable knowledge base with manual-review links, propose distinct grounded approaches, and keep the project useful and current. Do not hallucinate or claim unperformed verification. Flag irregularities and explain limitations/access blockers. The long-term geothermal-discovery goal must not be confused with the actual fault-pixel competition target.
>
> Build a clean, simple, user-friendly GitHub Pages site. The first screen/executive summary must make the new TIFF download and submission-readiness decision obvious. Include a uniquely identifiable filename and short comment for the optional submission note. Add an executive-summary/instructions subpage. Address the reported portal error **“Predicted values must be in range [0, 1]”**. Portal accepts a single-band GeoTIFF or ZIP containing one GeoTIFF matching required CRS, shape and geotransform; values must be[0,1]. Local checks and actual portal acceptance are separate evidence.
>
> Understand official competition overview, problem description, rules, datasets, reference solution and metric; obtain data, train, infer, normalize and validate. Use free public third-party sources with appropriate rights. The previous “single blocker is data placement / GPU needed” assertion must be tested rather than repeated. No DrivenData authentication is supplied; do not invent access. Use available authorized mirrors and official downloads autonomously where possible.
>
> **Core Values — Maximize P(Win):** weigh tradeoffs and risks, choose the path maximizing the probability of success, set aside attachment to a favored idea. **Own the Outcome:** own results end to end, fix problems without waiting for permission, treat failure and success as signals, and remain accountable for the final outcome.
>
> **Three passes required.** Pass1 implement and verify; Pass2 review bugs, missing requirements, incorrect assumptions and edge cases, fixing findings; Pass3 recheck against the original request and improve accuracy, reliability, completeness and quality. Do not stop at pass1. Create a pull request, merge onto main, and leave explicit next-session work and limitations. Never claim a leaderboard improvement or fully satisfied scientific requirement without evidence.

### User-supplied score/site inventory (unverified claims, not a leaderboard feed)

Sites below are starting points for studying prior methods, not permissible sources of a copied “new” submission. Blank scores mean no result supplied. The existing sibling audit inventories54 repositories; it does not establish organizer score-to-file attribution.

| Repository/site | User-supplied identifiers and scores |
|---|---|
| [GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html) | gems-submission-20260925T001403Z-7f00890a:0.1563 |
| [6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/) | gems6_hgb88-topk03_33cec71ff0:0.0286 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | pindrop-v4-nodes:0.1193; discovery:0.0830; ridge:0.1152 |
| [GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html) | dual-family-union-f68e590f:0.1560 |
| [GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/) | gems-submission-20260926T163915Z-237f0063:0.0343 |
| [5GEMSDOE](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html) | gems-submission-20260926T175114Z-7f00890a:0.1563 |
| [7GEMSDOE](https://buffedlizard55-lab.github.io/7GEMSDOE/) | lidarscarp-ridge-top2pct-36c3a3f341c8:0.1461 |
| [8GEMSDOE](https://buffedlizard55-lab.github.io/8GEMSDOE/) | Hedge-v2_submission:0.1563 |
| [GEMSDOE9](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html) | 2314b599:0.0107 |
| [11GEMSDOE](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html) | gems-structural-area06-v1:0.0202 |
| [12GEMSDOE](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html) | r7-nms3-dem10-scarp_0c9199f14e62 and allfinite twin:0.1294 |
| [15GEMSDOE](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html) | gems-tso1-conj_alteration_mag:0.0782 |
| [14GEMSDOE](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html) | GEMS_r5-geom-horse-ensemble:0.0020 |
| [17GEMSDOE](https://buffedlizard55-lab.github.io/17GEMSDOE/) | F-ensemble-2pct:0.0187 |
| [18GEMSDOE](https://buffedlizard55-lab.github.io/18GEMSDOE/) | H19-C_c11e495e:0.0297 |
| [19GEMSDOE](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html) | h19-4-691e4dfa:0.1894; h19-5-e27054cf:0.1922 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | h16-continuation:0.0461; h20-dem10-scarp-thin:0.0921; H25-ctx-ridge:0.1280; h28-dotted-ridge:0.1839 |
| [13GEMSDOE](https://buffedlizard55-lab.github.io/13GEMSDOE/) | r13-lattice-s5_v2_nan-outside:0.0904 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | h16-1-df20f65e:0.1855; h18-3a-c502dfab:0.0976; h18-4-aef8f42c:0.0360 |
| [GEMSDOE21](https://buffedlizard55-lab.github.io/GEMSDOE21/) | h19-4-reference:0.1894 |
| [20GEMSDOE](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html) | h20-1-be0e8f6b:0.1890; h20-5-824ce73a:0.1859 |
| [GEMSDOE22](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html) | h23-a-e2ec4b49:0.1002; h23-b-86176698:0.0748 |
| [GEMSDOE23](https://buffedlizard55-lab.github.io/GEMSDOE23/) | h30-arrangement-matched-habitat:0.1352 |
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | h25-1-dotted-h19-5-d1-5-989f59505db1:0.2477 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | dotted-h19-5-d2-8-e56ea318af89:0.2600 |
| [GEMSDOE26](https://buffedlizard55-lab.github.io/GEMSDOE26/) | dilcond-oof-v1-47629f496133:0.1223 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | topo-gap-closure-t-v2-on-d1-5:0.2449 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | h27-4-r1-solo-d2-8:0.2708; h32-1-prethin-tip-euler:0.2649; h36-1-rung30-blind-r1:0.2710; h38-1-hf-euler-r30-r1:unreported |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | efd28-repro:0.2600; repo-c0-habitat-emission:0.0041; sgmc-off-catalogue-44k:0.0512; wormrank-d28, wormsurv-filter, xfit-c0-habitat, xfit-h41-union-qfaults:unreported |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | d28-poisson300m-offcat-44090:0.2600 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | h27-4-solo-d28:0.2708 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros:0.2778 (user report; owner site UNSCORED) |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | h33d-analog-tip-stepover-r30:0.2632 |
| [GEMSDOE34](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html) | h34-scatter-q50-arr-matched:0.0778 |
| [GEMSDOE35](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html) | h35-06-aaa86efb25-candidate:0.0418 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | anderson-geothermal-pinn-38854:0.2750 |
| [GEMSDOE37](https://buffedlizard55-lab.github.io/GEMSDOE37/) | h6-physics-dotted-80k:0.1193 |
| [GEMSDOE38](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html) | D-step-3p0-07pct-tipProt:0.0763 |
| [GEMSDOE39](https://buffedlizard55-lab.github.io/GEMSDOE39/) | h40-e-disc-h40e-30k-zeros:unreported |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | h8-euler-lineament-depthcluster (soft/hard), h45-eulerdepthreadcluster:unreported |
| [GEMSDOE41](https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html) | h42-submission-primary:unreported |
| [GEMSDOE42](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html) | xscale-worm-persistence:0.0581 |
| [GEMSDOE43](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html) | sup01-hgb21-sep40-n40000:0.0424 |
| [GEMSDOE44](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/) | h46-twostageAB:unreported |
| [GEMSDOE45](https://buffedlizard55-lab.github.io/GEMSDOE45/) | h51-km-faultzone:0.0106 |
| [GEMSDOE46](https://buffedlizard55-lab.github.io/GEMSDOE46/) | r11f-scarp-radiometric-fusion:0.1589; r12-scarp-rad-concordance:unreported |
| [GEMSDOE47](https://buffedlizard55-lab.github.io/GEMSDOE47/) | unreported |
| [GEMSDOE48](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html) | unreported |
| [GEMSDOE49](https://buffedlizard55-lab.github.io/GEMSDOE49/) | gate_ortho_w0.25-40k:0.2376 |
| [GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/) | unreported |
| [GEMSDOE51](https://buffedlizard55-lab.github.io/GEMSDOE51/) | unreported |
| [GEMSDOE52](https://buffedlizard55-lab.github.io/GEMSDOE52/) | unreported |
| 53GEMSDOE,54GEMSDOE | unreported; no explicit site URLs supplied |

### Competition/data links supplied with the task

- [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/format/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard — link only](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [EPSG32611](https://epsg.io/32611), [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS project](https://gbcge.org/current-projects/ingenious/), [GDR1391](https://gdr.openei.org/submissions/1391)
- User mirrors, not independently authenticated official downloads: [GEMS PDF](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0), [example submission](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0), [existing faults](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0), [numerical features](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0), [DEM links PDF](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)
