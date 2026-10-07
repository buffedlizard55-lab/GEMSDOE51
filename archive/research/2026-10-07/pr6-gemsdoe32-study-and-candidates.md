# Historical PR #6 research draft — superseded

> This draft was moved out of the active research path during repository reconciliation. Some early causal language, hypothesis ranking, and owner-reported calculations below were not independently validated and must not be treated as current findings. For the current source-checked, non-causal account of the GEMSDOE32 result, see [`../../../knowledge/gemsdoe32-case-study-2026-10-07.md`](../../../knowledge/gemsdoe32-case-study-2026-10-07.md). The leaderboard-derived section was removed under the Terms of Use.

## Original heading (historical owner-reported result): 0.2778 and candidate hypotheses — session 2026-10-07

Everything here is either **[OFFICIAL]** (read from an organizer/USGS/DOE page, linked),
**[MEASURED]** (computed in this checkout or read from a hash-pinned artifact with the path
named), **[REPO]** (read from a sibling family repository via the GitHub API, path named) or
**[INFERENCE]** (reasoning that combines the above). Nothing is recalled from memory.

---

## 1. Why `h33-h33-2-b2` scored 0.2778 — the group's best

**[REPO, `buffedlizard55-lab/GEMSDOE32@main:README.md` § "Round 4" and
`docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json`]**

The 0.2778 file is **not** a better detector. It is a *removal*. Two of the group's own files
differ by exactly one mechanism:

| file | dots | owner-reported live score |
|---|---:|---:|
| dotted D2.8 (`GEMS28-H27-4-R1-SOLO-D2.8`) | 44,090 | **0.2600** |
| B=1 prune (delete dots ≤ 1 px / 100 m of the catalogue) | 40,199 | **0.2708** |
| B=2 prune (delete dots ≤ 2 px / 200 m of the catalogue) — `h33-h33-2-b2` | 37,654 | **0.2778** |

`existing_faults.tif` is byte-identical to `labels.tif` (sha256 `7ba308ccdc…`, re-verified here:
`data/labels.tif` and `data/existing_faults.tif` are the same 425,830-byte file), so each prune
removed *only* dots near the mapped catalogue.

**Why removing dots near mapped faults raises the score.** Known USGS/INGENIOUS fault pixels are
masked out of the evaluation entirely [OFFICIAL, forum 11516]. The hidden truth is faults the
catalogue *lacks*, and those rarely run within 200 m of a mapped trace without being part of it.
A dot within 200 m of the catalogue therefore almost always pays the full α = 0.2 false-positive
cost and earns little or no kernel credit: its 300 m neighbourhood is dominated by masked pixels.
GEMSDOE32 inverted the 0.2600→0.2708 pair through the official metric (their
`src/gems32/live_anchor.py`) and recovered: weighted TP 5,073.3, denominator 18,734.4
(⇒ |G| ≈ 12,226 hidden truth pixels), mean credit per dot 0.1262, live break-even bar
τ = 0.0542. The B=2 prune spends 58.6 units of off-catalogue weighted credit against a budget of
125.1 — safety factor 2.08 — and won their live-mirror holdout in 4/4 quadrants. B=3 spends the
safety down to 1.27 and won only 3/4, so 200 m is the measured stopping point.

**Mechanism, in one sentence:** the score is a budget `DTI = TP / (0.2·(TP+FP) + 0.8·|G|)`, and
mass near the catalogue is dead mass; cutting it raises the ratio without touching recall much.

## 2. Superseded leaderboard-derived analysis

An earlier version of this historical note included a manual leaderboard snapshot and an inferred
placement gap. Those standings and the derived comparison were removed during repository
reconciliation under DrivenData's Terms of Use. No copied standings or rank-based target are
retained here. The official leaderboard URL may be used as a source link, but the project does not
monitor or transcribe its contents without prior written consent.

The remaining local holdout evidence concerns proxy recovery of visible catalogue labels only; it
does not establish a gap to hidden organizer labels or a competitor-specific mechanism.

## 3. Five candidate hypotheses we have not tried, ranked

Novelty was checked against `registry/hypotheses.json` (this repo: H-A…H-E), the GEMSDOE32
H33-A…E register [REPO, `GEMSDOE32:docs/research/h33-hypotheses.md`] and the family score ledger
in the owner brief. Expected gain is against the current holdout best (H_D, proxy DTI 0.2817 at
M/|G| = 3.47, in-block AUC 0.6726 — both re-confirmed in `data/holdout_H_D.json`).

### Rank 1 — H-51-L, trace-axis snap (positional refinement of every emitted dot)
* **Layers:** `lidar_scarp_features_u8` bands `ex_max`, `step_max`, `relief` (owner-quantised
  1 m-DEM scarp stack, hash-pinned in `registry/data_manifest.json`) and `comp_det_elev` (band 12
  of `training_features.tif`, official band description "Detrended elevation").
* **Signature:** a crest (max(0, −λ_min) of the Gaussian Hessian, σ = 1.5 and 2.5 px) rank-fusion
  of those fields, used as a *move target*: each NMS-selected dot may relocate to the best crest
  cell inside its 5×5 neighbourhood, provided the move stays outside the 2 px catalogue exclusion,
  inside the footprint, and does not collide with another dot.
* **Why it should catch faults the catalogue lacks:** it is not a structure finder — it moves
  dots that the detector already selected onto the geometric axis of their own lineament. Hidden
  faults are disproportionately low-throw traces whose 100 m cell-average smears the scarp across
  one or two cells; the cell centre that NMS picks is then off-axis by up to ~150 m, and kernel
  credit decays linearly with that offset. Snapping recovers exactly that credit.
* **Differs from everything shipped:** no emission path in GEMSDOE1–52 refines position after NMS
  [REPO check of `gems51/emission.py`, `stage2_emission.py`]; GEMSDOE32's H34 positional
  experiment blurred the *belief field* (a different mechanism that did not beat their incumbent)
  whereas this moves *points* on a scarp-specific crest surface.
* **Cost:** ~1 min of CPU; no retraining. **Validatable locally:** yes, on the blocked folds.

### Rank 2 — H-51-M, cross-scale crest coincidence
* **Layers:** `comp_det_elev`, `lid_relief`.
* **Signature:** a static feature `xscale_coincide = Q(crest σ1.5) · exp(−d/1.5)` where `d` is
  the distance to the skeletonised crest at σ = 4.0 and `Q` is the footprint percentile rank:
  "a fine crest that sits exactly on a coarse crest axis".
* **Why it catches missing faults:** asymmetric scarps displace the single-scale crest response
  off the trace axis; the two scales agree only on the axis. A detector given this column can
  separate on-axis from flank pixels, which is the localisation distinction the metric pays for.
* **Differs from:** the lineament bank carries each scale independently; no shipped feature
  combines scales *positionally* (H33-A required orientation agreement of different physics, a
  different object).
* **Cost:** ~3 min to build + one 6-fold retrain. **Validatable locally:** yes.

### Rank 3 — H-51-P, parallel-strand offset template
* **Layers:** catalogue strike field (from `labels.tif` geometry only) + crest bank above.
* **Signature:** crest response where (a) local mapped-strike coherence > 0.5, (b) response
  direction is within 15° of the mapped strike, and (c) orthogonal offset to the nearest mapped
  trace is in [1, 6] px. An additive emission attractor, not a training feature.
* **Why it catches missing faults:** the organiser confirmed parallel strands of an existing
  system count as new faults [OFFICIAL, forum 11536]; catalogues typically map the dominant
  strand of a normal-fault system and leave the 100–600 m companion strand unmapped.
* **Differs from:** `stage2_emission.steered_field_from_provider` multiplies ridges by alignment
  everywhere without an offset condition; GEMSDOE33's step-over analog targeted tips, not strands.
* **Cost:** ~2 min. **Validatable locally:** yes (as an emission-time reweighting on the folds).

### Rank 4 — H-51-S, dilational-jog coincidence
* **Layers:** `comp_geod_dilaterate` (band 8, official description "Dilatation strain rate") ×
  crest bank.
* **Signature:** positive dilatation-rate cells coincident with a topographic crest: releasing
  jogs and extensional stepovers on normal faults.
* **Why it catches missing faults:** jogs are where a fault system is geometrically complex and
  therefore where single-trace mapping most often breaks a system into pieces.
* **Differs from:** H-B used the geodetic field only in tile-quantile space; nothing multiplies
  the sign of dilatation with a crest response.
* **Cost:** trivial. Prior is weak: GEMSDOE26's dilatation-conditioned emission scored 0.1223.

### Rank 5 — H-51-V, volcanic-vent feeder alignments
* **Layers:** `external/gdr_volcanic_vents_in_footprint.csv` (21 vents, hash-pinned mirror of
  [GDR 1391](https://gdr.openei.org/submissions/1391)).
* **Signature:** pairwise vent-alignment corridors (great-circle segments between vent pairs)
  intersected with crest response.
* **Why it catches missing faults:** [MEASURED, prior session] 0 of the 21 vents lie within
  300 m of the catalogue; their feeder structures are unmapped by construction.
* **Differs from:** GEMSDOE32 listed vents as a contrarian angle but never built a corridor
  surface; GEMSDOE15's alteration arm used geothermometry, not vent geometry.
* **Cost:** trivial. Prior is weak: 21 points define few corridors and GEMSDOE23's
  arrangement-matched-habitat scored only 0.1352.

## 4. Pre-registration for validation (frozen before running)

Top candidate **H-51-L** is validated on the 6 spatially-blocked folds (grid 3×3, buffer 12 px,
min truth 500 — identical to `data/holdout_H_D.json` config) using the saved H_D fold fields:

* emission: NMS radius 2.4 px, exclusion radius 2.0 px, block-restricted, M = 3.47·|truth_block|;
* primary statistic: **mean distance from an emitted dot to the nearest held-out truth pixel**
  (the statistic the README names as the whole gap to the leader);
* decision rule: promote iff mean distance improves in ≥ 5/6 folds **and** mean proxy DTI at
  matched mass does not fall by more than 0.0005. A candidate that fails this rule does not spend
  a submission slot.

## 5. Source register (manual-review links)

| # | source | URL | class |
|---|---|---|---|
| 1 | GEMSDOE32 README, Round 4 (live-anchored removal rule) | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/README.md | repo |
| 2 | GEMSDOE32 h33-2-b2 audit JSON | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json | repo |
| 3 | GEMSDOE32 H33 hypothesis register | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/research/h33-hypotheses.md | repo |
| 4 | GEMSDOE32 geothermal knowledge base (Faulds citations inside) | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/research/geothermal-vents-knowledge.md | repo |
| 5 | Known-fault masking, organizer staff | https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516 | official |
| 6 | "New fault" includes new geometry, organizer staff | https://community.drivendata.org/t/where-do-you-draw-the-line/11536 | official |
| 7 | Problem description & metric | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | official |
| 8 | Official competition leaderboard (source link only; no standings reproduced) | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | official |
| 9 | GDR 1391 INGENIOUS (vent/well/spring compilations, CC BY 4.0) | https://gdr.openei.org/submissions/1391 | official |

**No-hallucination statement:** every score attributed to a file above is an owner report carried
in the brief or in the cited repository; none is represented as an organizer-verified result. The
local holdout numbers are proxy measurements and carry their producing paths.
