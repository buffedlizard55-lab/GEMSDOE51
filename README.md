# GEMSDOE51 — DOE GEMS Prize, round 1 (DrivenData #306, GeoDAWN / NW Nevada)

> **This README is the standing starting point. Re-read it before doing anything.**
> Status: one **unique, legal, unscored** submission is built, gated and downloadable.
> It has **never been scored by DrivenData** — no credentials are available in the build environment —
> so every number in this repository is either measured on the visible catalogue (**PROXY**), read
> from a live page (**UNVERIFIED-LIVE**), or explicitly marked as an inference.

---

## 0. THE STANDING PROMPT (verbatim, re-read every session)

> **Goal.** Place top of the DOE GEMS Prize leaderboard (DrivenData competition #306, GeoDAWN /
> NW Nevada): find geothermal-indicative faults that are missing from the USGS/INGENIOUS
> catalogue and emit them as a legal single-band float32 GeoTIFF.
>
> **Highest urgency.** Generate a **UNIQUE** `.tif` submission. Copying a previous submission is
> acceptable only for learning/education, never as the deliverable. Ship it from the project site
> as an easy one-click download, with a unique name and a short note to paste into the submit form.
>
> **Portal constraint.** The portal rejects files whose values fall outside `[0, 1]`. Emit values in
> `[0, 1]`, avoid the large-negative float32 nodata sentinel (`-3.4028234663852886e+38`), and prefer
> **all-finite with no nodata tag**.
>
> **Two stages, holdouts reported SEPARATELY.** (1) A coarse prior over broad tiles from a geodetic
> strain-budget **deficit** = geodetic strain rate minus fault-accommodated strain traced from
> INGENIOUS slip rates × trace length via a documented moment-tensor summation — state the exact
> formula and cite its source, because the user has not verified one. Treat the deficit as a **loose
> prior only** and acknowledge that it may be off-fault, aseismic, or simply the wrong catalogue
> slip rates. (2) A separately holdout-scored fine-scale model emitting points **only inside
> approved tiles**. Normalize, write the GeoTIFF, run the uniqueness gate, and confirm the
> submission is **not dominated by stage one's footprint**. Habitat-style statements scored worst
> (0.0041 / 0.1223 / 0.1352) — avoid that failure mode.
>
> **Research question, to PhD depth, no hallucinations, line-by-line verification against official
> sources.** Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (GEMSDOE32, quoted as 0.2778)
> score highest, and can we beat it? The public leaderboard leader is at 0.3262 (`nchuzhoy`) and the
> stated score to beat is 0.3195 (DARD). Design a strategy that can exceed it.
>
> **New hypotheses.** Produce 3–5 candidate geological hypotheses not yet tried, each naming the
> specific layer(s), the physical signature targeted, why it would catch a fault missing from the
> catalogue rather than one already in it, and how it differs from everything already implemented.
> Rank by expected DTI gain vs. implementation cost. **Validate the top candidate on the
> spatially-blocked holdout before spending a submission slot** — never spend a slot on an
> unvalidated idea. If new external data is needed, name the specific free official source and
> confirm it is obtainable first.
>
> **Method.** Deep autonomous research into geothermal-vent/fault science; store knowledge from
> official verified sources with links for manual review; flag irregularities; no manual input
> required from the user. Run the work through **3 passes** (implement + verify; review for bugs,
> missing requirements and edge cases and fix; re-check against the original request for accuracy,
> reliability, completeness and code quality), then verify the final result satisfies the request.
> Open a pull request and merge it onto `main`; list remaining work and blockers for next session.
> Build a clean, user-friendly GitHub Pages site with all relevant info, official verified links and
> an obvious one-click submission download; executive summary subpage at the very top.
>
> **Core values.** *Maximize P(Win)* and *Own the Outcome* are the focal decision criteria.
> **Acceptance criteria.** Work line by line; verify everything against official/verified/trusted
> sources; provide links for manual review; no hallucinations; work autonomously; flag
> irregularities.

---

## 1. What to do in the next session (pick up here)

1. **Score the file.** Nothing converts the numbers below into a real score except a submission.
   Log in to <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/> and
   upload `gemsdoe51-strainbudget-s1-v1.zip` (or the `.tif`). The site's first panel repeats this
   with a copy-paste form note.
2. **Re-derive the ratio, if desired, with per-trace clipping** (remaining work, IR-51-08).
3. **The two untested hypotheses** in `registry/hypotheses.json` (H51-4 tensor version, H51-5
   re-open) are the only scientific ideas not yet measured. Everything else that was tested is
   recorded — including the refuted ones — so it is not re-litigated.
4. **Do not re-run the coverage-lattice emission.** It was refuted (IR-51-05); it remains in the
   code behind `rule="lattice"` for reproducibility only.

---

## 2. The shipping artifact

| Item | Path | Facts |
|---|---|---|
| Submission raster | `docs/downloads/gemsdoe51-strainbudget-s1-v1.tif` | 3730×3292, EPSG:32611, 100 m, float32, **all 12,279,160 cells finite**, min 0.0, max 1.0, **no nodata tag**, 95,927 emitting px, 390,791 bytes, sha256 `bdc045934e4a2e33a90093ef07e4968f9fffb016ce3ff3e780bbe7fa5c32977a` |
| Zip | `docs/downloads/gemsdoe51-strainbudget-s1-v1.zip` | 301,373 bytes, sha256 `b29ad51d6fdad0bd07fefd3da60372c992416b8d22f4a2398367f65a1444db9c` |
| Checks | `docs/downloads/checks-gemsdoe51-strainbudget-s1-v1.json` | machine-readable format receipt (dtype, CRS, transform, nodata, finiteness, range, count) |
| Receipt | `evidence/submission_receipt.json` | build parameters and digests |
| Uniqueness gate | `evidence/uniqueness_gate.json` | max Jaccard **0.0322** against the 12 scored sibling submissions (limit 0.25); no subset/superset relation |
| Stage-dominance gate | `evidence/stage_dominance.json` | fill **3.8 %** of the approved area, coverage inside approved tiles **1.000**, tile concentration **1.537×** the uniform control → "fine-scale selectivity present" |
| Site | `docs/index.html` (+ subpages) | executive summary first, one-click download, verified sources, hypotheses, irregularities |

**How the file was placed.** Stage A approves tiles (top half by geodetic strain magnitude: 58
tiles, 2,537,841 px). Stage B trains a 44-channel gradient-boosted detector under spatially blocked
CV and scores every pixel. The emission is **95,927 one-pixel dots** (belief-priority greedy with a
3.0 px minimum separation, sized at 4 % of the candidate area), each **inside an approved tile,
inside the footprint, and at least 200 m from every visible-catalogue pixel**.

The submission is UNSCORED. This repository does not know its leaderboard value and does not claim
one.

---

## 3. Two-stage architecture, with holdouts reported separately

### Stage A — coarse prior over 25 km tiles (holdout: PROXY)

The brief's literal rule was implemented exactly, with the formula and its source:

```
eps_geo(tile) = (1 / (2 * A_tile)) * SUM_k [ L_k * u_dot_k / sin(dip_k) ] * m_ij
```

Kreemer, Haines, Holt, Blewitt & Lavallée (2000), *On the determination of a global strain rate
model*, Earth Planets Space **52**(10):765–770, doi:10.1186/BF03352279 — **equation (3)**, the
fault-slip variant of the Kostrov (1974) summation, obtained from
<https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf> and independently
restated in GJI 212(2):988 and GJI 146(2):399. `L_k` = clipped trace length, `u_dot_k` = slip rate
(INGENIOUS / GDR-1391), `dip_k` = per-sense dip measured from Siler (2022, USGS ScienceBase
`6296974d`): normal 61.9°, right-lateral 85.8°, left-lateral 81.6°, unspecified 64.3° (medians of
83,234 rows), `A_tile` = tile area, `m_ij` the unit moment tensor (contracted to a scalar here,
which the source permits only as a magnitude reduction — stated as a limitation).

| Stage-A quantity | Value |
|---|---|
| Tiles | 116 × 25 km |
| Median geodetic second invariant | 21.03 ns/yr |
| Median mapped-fault equivalent | 6.00 ns/yr |
| Median ratio geologic / geodetic | 0.455 |
| Median deficit = 1 − ratio | 0.545 |
| **Deficit as a locator** | **REFUTED** — holdout label-density lift 0.949 (1/4 folds), rho −0.048 vs lidar scarp intensity, rho −0.228 vs off-catalogue SGMC density |
| Gate that ships instead | top-half tiles by **geodetic strain magnitude** — rho **+0.376**, top-quartile lift **1.393** on the lidar instrument; **−0.166** on the SGMC instrument (**split decision, IR-51-04**) |

### Stage B — fine-scale detector, restricted to approved tiles (holdout: PROXY)

| Fold | 0 | 1 | 2 | 3 | mean |
|---|---|---|---|---|---|
| AUC | 0.6719 | 0.7987 | 0.7034 | 0.7331 | **0.7268** |
| sibling `oof_B`, same masks | — | — | — | — | 0.6674 |
| sibling `oof_D`, same masks | — | — | — | — | 0.6687 |

Paired matched-mass DTI against `oof_D` (identical emitter, identical folds, 8k and 32k dots):
**+0.0482 mean, 8/8 positive**. Alternatives trialled and **not** promoted: credit-density
ordering (-0.0000, 1/4 folds),
redundancy-aware expected-budget packing (+0.0002, 3/8 fold-budget rows).
Emission mass swept: density 0.005→0.1796, 0.01→0.2318, 0.02→0.2803, **0.04→0.2997**, 0.08→0.2585.

### The third instrument, and the promotion that failed

A coverage-lattice emission won a sweep against a subsample of the visible catalogue (+0.0286 mean,
4/4 folds) and **lost** the faithful off-catalogue instrument (fault systems split A/B, trained on
A, truth = B): **−0.0104 mean, 1/4 folds** (q0.20 variant: +0.0040, 2/4). It was reverted under the
pre-registered promotion rule and is recorded as IR-51-05 — a worked example of a spurious promotion
caught by holdout, which is exactly what the standing instruction "validate before spending a slot"
is for.

---

## 4. Why the 0.2778 artifact led, and whether it can be beaten (summary; full derivation on the site)

*What is verified about the artifact:* 37,654 px, all-finite float32, no nodata tag, **0 px within
200 m of the visible catalogue**, described by its own authors as UNSCORED with a modelled
projection of 0.2747, and obtained from a 0.2708-scoring model by deleting dots within 2 px of the
catalogue. The identification with the 0.2778 leaderboard row is **not cryptographic** (IR-51-02).

*Why it led.* The official metric is `DTI = T / (0.2T + 0.2F + 0.8K)` with `T = TP_w ≤ K`. Two
asymmetries decide everything: a predicted pixel sitting **on** a truth pixel costs **zero**
(FP weight `1 − k(0) = 0`), and a **missed** truth pixel costs 0.8 against 0.2 for a unit of false
mass. The marginal-inclusion theorem derived here (`src/gems51/metric.py`, unit-tested) says a dot
is worth adding iff its kernel weight to an unclaimed truth pixel exceeds `0.2·DTI` — at
DTI = 0.2778 that is **0.0556**, i.e. within **283 m**; anything further away is pure cost.
Consequences: (i) sparse dots placed where faults really are beat dense rasters; (ii) mass on the
**visible** catalogue is dead weight for a hidden set defined as "faults the catalogue does not
contain", which is why deleting the 2-px ring was free upside; (iii) unclaimed credit per dot is
only ~1–3 kernel units, so the game is a **coverage** problem at small mass, not a mass race.
Working backwards from the ancestor's own calibrated truth scale (K ≈ 12,700 px) and mass (44,090),
their live scores imply ≈32–40 % coverage of the hidden set — a *proxy-consistent* reconstruction,
labelled as inference.

*What it would take to beat it.* The ancestor's own numbers say the binding constraint is
**placement**, not mass: +17 % more matched credit at the same mass takes 0.2747 → 0.3195. This
repository's measured contributions to that constraint are (1) a belief field that is better on
4/4 folds by AUC and 8/8 paired comparisons at matched mass, and (2) a stricter off-catalogue
discipline with a better uniqueness margin (0.0322 vs the ancestor's own corpus overlap). Those are
real, reproducible improvements on the instruments available — **they are not a leaderboard score
and are not presented as one.**

---

## 5. Hypothesis ledger

Five candidates, ranked by expected DTI gain per unit cost, with falsification status:
`registry/hypotheses.json`. Headlines: **H51-1** geodetic-strain gate — refuted as a locator,
replaced by the strain-magnitude gate (**PROMOTED as a mask**); **H51-2** lidar-scarp-ensemble
detector — **PROMOTED** (+0.0482 paired at matched mass vs the best sibling field); **H51-3** the
brief's literal deficit — **FALSIFIED** and retained as the headline negative result; **H51-4**
per-sense dip / full moment tensor — **PARTIAL** (dips measured and applied; rake unavailable, so
the tensor version is NOT TESTED); **H51-5** independent-compilation gap closure (SGMC / Siler
slip tendency) — **REJECTED** (wrong sign on both instruments, and the sibling's live arm scored
~0.05).

---

## 6. Data, provenance and obtainability

* 26 files, 576,896,511 bytes, every one **sha256-pinned** in `registry/data_manifest.json` and
  restorable with `python3 scripts/fetch_data.py --group all` (fails closed on any mismatch).
* **Provenance limitation (IR-51-13, IR-51-01):** the DrivenData data page is login-walled, so the
  bytes come from **owner-published public GitHub mirrors** of the sibling repositories, not from
  the organiser. **The pins prove mirror consistency, not organiser authentication.** A reviewer
  with portal access should re-download and diff.
* `labels.tif` and `existing_faults.tif` are byte-identical in that mirror
  (sha256 `7ba308cc…`) — treated as **one** catalogue, never as two sources (IR-51-07).
* Free external data named for the untested hypotheses, with obtainability evidence in
  `registry/sources.json`: GDR-1391 paleo-geothermal (sinter/tufa/travertine), 2 m temperature
  probes, Quaternary volcanics — bytes fetched by a GitHub Actions runner; USGS ScienceBase heat
  flow (`6297d2fa…`) and Peacock & Bedrosian MT conductance (`62979746…`) — official pages verified,
  bytes fetchable by a runner; USGS Qfaults and 3DEP 1 m DEMs — public. `1m_DEM_links.csv` was
  never obtained.

---

## 7. Reproduce everything

```bash
python3 scripts/fetch_data.py --group all      # restore + verify 26 pinned files (fails closed)
python3 scripts/run_all.py --skip-data         # full pipeline, fresh evidence (~15 min)
python3 scripts/rebuild_submission.py          # rebuild the shipped file from the cached belief field
python3 scripts/run_offcat_holdout.py          # the off-catalogue A/B instrument (the decisive test)
python3 scripts/check_stage_a_convention.py    # IR-51-04 follow-up check
python3 scripts/build_site.py                  # regenerate the site from the registries + evidence
pytest tests -q                                # 15 tests incl. a brute-force metric re-implementation
```

`run_all.py` reproduces the shipped raster **byte for byte** (same sha256) from the hash-pinned
inputs — that is checked, not assumed.

---

## 8. Irregularities (full register: `registry/irregularities.json`)

Stale brief targets (IR-51-01); unverifiable artifact-to-score identification (IR-51-02); the brief's
deficit rule falsified (IR-51-03); split instrument on the adopted gate (IR-51-04); a promotion
caught by holdout and reverted (IR-51-05); label circularity trained-on-what-we-must-find
(IR-51-06); duplicated label raster (IR-51-07); per-centroid tile approximation for long traces
(IR-51-08); dip inferred per sense rather than carried per trace (IR-51-09); six unlabelled lidar
bands (IR-51-10); geodetic band units inferred (IR-51-11); miscalibrated packer self-prediction
(IR-51-12); no submission access and restricted egress in the build environment (IR-51-13).

---

## 9. Remaining work / blockers for the next session

1. **Submit and score** (blocked: no DrivenData credentials here). Highest value action available.
2. **Per-trace clipping** instead of per-centroid tile assignment (IR-51-08), then re-run the
   Stage-A gate comparison; cheap and it strengthens or kills the adopted gate.
3. **H51-4 tensor version** — needs a free rake source; none was found. Without it, the scalar
   contraction is the honest limit and is labelled as such.
4. **H51-3 thermal conjunction** (paleo-geothermal + 2 m probes + heat flow): all three sources are
   free and their obtainability is documented; the test is the same A/B instrument. This is the best
   remaining *new* idea.
5. **Organiser-authenticated byte check** of the hash-pinned mirrors (IR-51-01).
6. GitHub Pages must be enabled on this repository (`main` → `/docs`) for the site to serve;
   the site itself is complete and self-contained.

---

*License and attribution: code in this repository is provided as-is for the competition. Input
layers: USGS Quaternary Fault and Fold Database, INGENIOUS (GDR-1391, CC BY 4.0), GeoDAWN
(ScienceBase `657e1d85…`), 3DEP/lidar, Siler (2022) USGS data release, Kreemer et al. (2000),
Zeng & Shen (2016). Cite the original providers.*
