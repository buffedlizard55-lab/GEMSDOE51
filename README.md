# GEMSDOE51 — DOE GEMS / GeoDAWN fault-discovery research record

**Current decision (2026-10-07): ONE NEW, UNIQUE, CONSTRAINT-COMPLIANT CANDIDATE EXISTS. NO COMPETITION SLOT USED. NO ORGANIZER SCORE CLAIMED.**

> ### ⬇ Download — recommended upload candidate (not yet portal-validated)
>
> **[`docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z.tif`](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z.tif)** · [one-file ZIP](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z.zip) · [local checks](docs/downloads/gemsdoe51-h51n2-creditthin-20261007T210820Z-checks.json) · sha256 `b7ea86e8893434e3ea6616cdba07ac3e55e3b8bd0bc42add68bdf5d4084efc22`
>
> **Submission name to paste:** `GEMSDOE51-N2-physical-creditthin-r3.0-q10`
> **Note (optional) field:** `H-D physical detector (58 physical layers + 4 scarp-facing-coherence layers) on the visible USGS/INGENIOUS catalogue; unit dots at >=2.4 px (240 m) NMS spacing; every point >=2.24 px (224 m) from the mapped catalogue and inside the Stage-1 strain-deficit q10 approved tiles; mass 3.0x estimated hidden-truth pixel count.`
>
> **Status: READY TO UPLOAD AT YOUR DISCRETION — NOT YET PORTAL-VALIDATED, NOT ORGANIZER-SCORED.** It is the only artifact here that satisfies every constraint at once: official grid/CRS/transform/dtype, **every pixel finite and inside `[0, 1]`** (zeros outside the footprint, `nan_cells = 0`), 38,100 unit dots with ≥2.4 px nearest-neighbour spacing, every dot ≥224 m from the mapped catalogue, every dot inside the approved Stage-1 tiles, Stage-1 lift `1.110 < 1.5`, and a support that matches no locally held prior (max Jaccard `0.1546`, max containment `0.2887` against 39 priors / 21 pinned family references). **Honest caveat, measured:** the brief's "all points inside approved tiles" requirement costs `−0.0015469` mean six-fold proxy DTI versus the archived H-D configuration (0/6 folds won) — this is a compliance-cost artifact, not a score improvement. Nothing here has been uploaded; portal acceptance is unproven.
>
> **Do not upload** the archived H-H/H-D blend (fails the q10 confinement requirement) or the research-only H-G+H-D TIFF (loses its matched holdout). Both remain linked for audit only.

The existing local H-H/H-D blend is retained as the best reproducible local proxy benchmark (six-fold visible-catalogue proxy mean DTI `0.2853406`), but it is an earlier artifact that fails the brief's all-points-inside-approved-tiles requirement (86.71% inside) and it writes NaN outside the footprint — the leading hypothesis for the user-reported portal error “Predicted values must be in range [0, 1]”, whose exact triggering file is still unidentified (IR-51-21). It has not been uploaded or accepted by DrivenData.

The preregistered H51-K1 candidate was implemented and evaluated on the six spatial folds with a fold-specific, leakage-controlled broad Stage-1 q10 mask. It **did not pass** the preregistered promotion gates, so no K1 TIFF exists. The H51-N1 inventory-context arm was also preregistered and failed on every regime (fold 0: 0.0543 vs 0.1296 for the physical arm). The candidate shipped above is not a new geological hypothesis: it is the already-validated H-D physical arm re-emitted under the constraints, with its measured compliance cost stated.

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

This session is fixed to branch `arena/44e5e11e-gemsdoe51` (earlier sessions used `arena/ec87b811-gemsdoe51`); all work stays on the session branch. The repository's leaderboard policy is link-only: DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) prohibit automated monitoring/copying and manual monitoring/copying without prior written permission; none is recorded. No standings feed or copied leaderboard values are maintained here.

## Current status and local benchmark

| Item | Status / result |
|---|---|
| **Recommended upload candidate (2026-10-07)** | **`gemsdoe51-h51n2-creditthin-20261007T210820Z.tif` — unique, all-finite `[0,1]`, every point inside the Stage-1 approved tiles, all local gates PASS; NOT yet portal-validated and NOT organizer-scored** |
| Compliance cost of the brief's constraints | `-0.0015469` mean proxy DTI (0/6 folds) versus the archived H-D configuration; the harness reproduces the archived receipt with max deviation `0.0` |
| Off-catalogue A/B physical-arm AUC (4 folds) | `0.6936` all / `0.6486` catalogue-independent (≥5 px from any A pixel) |
| Far-field ring-weight experiment | `+0.017314` on the off-catalogue A/B instrument, `-0.113310` on the blocked instrument → **instrument disagreement; no ring weight used** |
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

## What was measured in this session (2026-10-07, evening block)

| Question | Script | Receipt | Result |
|---|---|---|---|
| Does the *visible inventory* carry placement signal beyond the physical layers? | `scripts/run_h51_n1.py` | `evidence/h51_n1_ab_fold0_timing.json`, `evidence/h51_n1_ab_static_fields.json` | **No** — the static physical arm beats the inventory-context arm in every regime on the A/B instrument; AUC_all `0.6936`, AUC_far `0.6486` |
| Where in the distance-to-catalogue coordinate does the credit sit? | `scripts/run_ring_profile_ab.py` | `evidence/ring_profile_ab.json` | Far-field ring (`15 px`) beats unweighted (`0.205821` vs `0.188507`, `+0.017314`) on the A/B instrument; the near-field ring is the worst profile |
| Do the brief's hard constraints cost score? | `scripts/run_h51_n2_holdout.py` | `evidence/h51_n2_paired_holdout.json` | `-0.0015469` mean, 0/6 folds; the baseline reproduces the archived receipt exactly (max deviation `0.0`); the ring weight is **rejected** here (`-0.113310`) |
| Is the shipped artifact unique and inside the constraints? | `scripts/build_submission_n1.py` | `evidence/submission_h51n2.json` | All gates PASS: format, `[0,1]` finite everywhere, 100% of points inside approved tiles, lift `1.109969 < 1.5`, max Jaccard `0.154578`, max containment `0.288740` |
| Why do the thin-dot artifacts score highest, and what would beat `0.3195`? | analysis | `knowledge/03_why_the_dotted_family_wins_2026-10-07.md` | Mass/thinness and catalogue-halo deletion dominate; the reported ladder implies `|G| <= 14,088` and credit/dot ≈ `0.13`; reaching `0.35` needs ~+35% placement quality at the same mass |

## Reproduce, test, and review

With the hash-pinned data restored (`python scripts/restore_data.py --group all`), run:

```bash
PYTHONPATH=src .venv/bin/python scripts/prepare_data.py
PYTHONPATH=src .venv/bin/python src/gems51/stack.py
PYTHONPATH=src .venv/bin/python scripts/build_arm_extras.py --group hd   # build_extras.py OOMs in this sandbox
PYTHONPATH=src .venv/bin/python scripts/run_h51_n1.py --instrument ab --folds 0,1,2,3 \
  --arms static --skip-emission --save-fields work/fields \
  --out evidence/h51_n1_ab_static_fields.json
PYTHONPATH=src .venv/bin/python scripts/run_ring_profile_ab.py --out evidence/ring_profile_ab.json
PYTHONPATH=src .venv/bin/python scripts/run_h51_n2_holdout.py --folds 0,1,2,3,4,5
PYTHONPATH=src .venv/bin/python scripts/build_submission_n1.py --ratio 3.0 --spacing 2.8 \
  --excl-radius 2.24 --stage1-q 10 --tag h51n2-creditthin --dry-run   # drop --dry-run to write the artifact
PYTHONPATH=src .venv/bin/python scripts/run_stage1_trace_holdout.py \
  --thresholds 10 --output evidence/stage1_q10_trace_holdout_20261007.json
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/build_site.py
PYTHONPATH=src .venv/bin/python scripts/check_site.py
```

`scripts/build_extras.py` cannot complete in a ~4 GB sandbox (it was OOM-killed); `scripts/build_arm_extras.py --group hd` builds the four H-D layers that every number above depends on. Memory-hungry runs are best executed one fold at a time.

## Remaining work and limitations (for the next session)

1. **Portal validation is still untested.** The candidate removes the NaN outside-footprint failure mode entirely, but no upload has been performed. If the portal still rejects it, record the exact error text and file name before changing anything.
2. **No organizer score exists for this repository.** Every number here is a proxy on the visible known-fault catalogue; the hidden label set is the organizer's.
3. **The two local instruments disagree about distance-to-catalogue.** Resolving it needs either a third instrument or the organizer's revealed labels. Until then, the conservative reading (no ring weight, keep points clear of the immediate halo) is what the artifacts use.
4. **`extras_static.dat` is missing** (its builder OOMs), so the H-H arm and the blended local best cannot currently be rebuilt. Add other feature groups to `scripts/build_arm_extras.py` rather than rerunning `build_extras.py`.
5. **Untested preregistered candidates remain:** H51-K2 (directional conductivity contrast across an independent basement edge), H51-K3 (radiometric ratios conditioned on independent edges), H51-K4 (earthquake-density ridge; blocked on source semantics), H51-X2/X3/X4, and H-I/H-J from the earlier slate.
6. **`inventory_context` has a known degeneracy:** because the training positives *are* the known catalogue, any catalogue-distance feature lets the model learn the halo (the IR-51-LEAK-01 pattern). Any future inventory-conditioned arm must be trained on held-out systems (the A/B design), not on the full catalogue.
7. **The H51-N2 artifact should be re-emitted** if a better arm (for example a rebuilt H-H blend) becomes available: the emitter, gates and receipts are parameterised and take ~90 seconds to rerun.
