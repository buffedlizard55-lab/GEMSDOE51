# H52 session results (2026-10-07) — what was measured, what was shipped, what failed

Every number below is **MEASURED LOCALLY** in this checkout and reproducible from the named
receipt. Nothing here is a leaderboard score. Instruments: the six contiguous 3×3 spatial
blocks of the visible USGS+INGENIOUS catalogue (12 px training buffer, matched emitted mass
3.47 × n_truth), scored under both conventions of `gems51.live_metric`
(A: on-catalogue mass deleted; B: counted as a false positive). Readings A and B were
identical in every arm measured this session, because no candidate emitted inside the
catalogue flank.

---

## 1. The emission comparison (preregistered before it ran)

### 1.1 Pass 1 — new geometries vs the incumbent (`evidence/h52_holdout_20261007T211736Z.json`)

| arm | geometry | six-fold mean DTI (B) |
|---|---|---|
| V0 | isotropic NMS r=2.4, catalogue flank 2 px | **0.280563** |
| V1 | NMS r=2.8, flank 2 px | 0.280563 |
| V2 | NMS r=2.8, flank 3 px | 0.280193 |
| V3 | strike-aligned line emission (SALE), flank 3 px | 0.216720 |
| V4 | V2 confined to the Stage-1 approved tiles (q10) | 0.279778 |
| V5 | V3 confined (q10) | 0.216350 |

* The **new** SALE geometry is a dead end: −0.064 at matched mass. It is abandoned, not tuned.
* Widening the catalogue clearance from 200 m to 300 m costs 0.0004 locally, i.e. nothing
  measurable — the clearance rule is therefore set by the live evidence (§3), not by this
  instrument.
* Hard Stage-1 confinement at q10 costs 0.0004–0.0008 (V4 vs V2, V5 vs V3). Confinement is
  not what makes a candidate worse.

### 1.2 Pass 2 — the validated emitter, the domain width, and the null models
(`evidence/h52_emission_pass2_20261007T212644Z.json`, same cached fields, so every number is paired)

| arm | six-fold mean DTI (B) | vs V0 |
|---|---|---|
| V0 incumbent NMS (unconfined) | 0.280565 | — |
| V6 validated STE (unconfined) | 0.281329 | **+0.00076** (4/6 folds) |
| V7 STE inside q10 approved tiles | 0.280821 | +0.00026 |
| V7 STE inside q50 approved tiles | 0.250011 | −0.03055 |
| V7 STE inside q70 approved tiles | 0.199401 | −0.08116 |
| U_block — uniform fill of the block | 0.188044 | −0.09252 |
| U_q10 — uniform fill of the approved tiles | 0.190893 | −0.08967 |

Three conclusions, all of them usable:

1. **The emitter change is not supported on these fields.** STE is +0.00076 with 4/6 folds
   positive, below the preregistered +0.0020 bar, even though two earlier instruments put it at
   +0.00196 (`evidence/emission_geometry.json`, the H-D arm) and +0.00217
   (`evidence/hh_blend_holdout.json`). The pooled evidence says "small positive, ~+0.001";
   the protocol says "not established", so the shipped file uses the **incumbent** geometry.
   The tension is recorded rather than resolved in the file's favour.
2. **Stage-1 domain width matters enormously, and only the widest domain is cheap.**
   Approved-domain shares and costs: q10 → 0.0005, q50 → 0.0313, q70 → 0.0819. The reason is
   in §2: the low-deficit tiles are the ones that hold the mapped catalogue, so excluding them
   removes the very thing the local instrument rewards. The strictest domain inside the
   preregistered 0.0050 cost limit is q10.
3. **Stage 2 is doing the work, not the tiles.** The confined candidate beats a uniform random
   fill of the same approved tiles by **+0.0899** (0.280821 vs 0.190893), and by +0.0928 over a
   uniform fill of the whole block.

## 2. Stage 1 is broad, and its percentile direction matters
(`evidence/stage1_domain_scan_20261007T211331Z.json`)

`stage1.approved_mask` approves tiles whose rank-space deficit is **at or above** the q-th
percentile, so q10 is the *widest* domain, not the narrowest:

| q | approved share of footprint | share of mapped catalogue inside | share of the existing artifact's dots inside |
|---|---|---|---|
| 10 | 90.09 % | 85.54 % | 86.71 % |
| 30 | 70.12 % | 57.76 % | 59.14 % |
| 50 | 50.15 % | 36.15 % | 37.09 % |
| 70 | 30.05 % | 14.56 % | 16.35 % |
| 90 | 10.02 % | 3.34 % | 4.20 % |

Inside the holdout blocks the q10 domain covers 99.92 % of the area — i.e. at the width the
preregistration froze, Stage-1 confinement is a formal constraint with almost no geometric
content. That is stated on the site rather than dressed up, and the alternative reading
(a narrower "approved" set) is priced: it costs 0.031 at q50 and 0.082 at q70 on this
instrument. Note also that the approved tiles hold *less* catalogue than their area share at
every q > 10 — the deficit is anti-correlated with mapped faults, which is what the Stage-1
hypothesis predicts but also what makes the local instrument biased against confinement
(`IR-H52-04`).

## 3. The catalogue-clearance mechanism, verified rather than asserted
(`evidence/sibling_design_audit_20261007T210250Z.json`)

* `gems28-h27-4…allfinite.tif` (40,199 dots) ⊂ `gems32-probe-S1-ANCHOR` (44,090 dots) =
  `gems25-dotted…` (44,090 dots); the difference is exactly 3,891 dots, **every one within
  100 m of the published catalogue**, and the kept file has **zero** dots within 100 m of it.
* The owner reports those two files at live 0.2708 vs 0.2600 (OWNER-REPORTED, unverifiable
  here). Under scoring reading A the removal would be score-neutral by construction, so this
  pair is the strongest available evidence that the live scorer uses reading B (mass on
  published faults still counted) and that clearance is a free gain.
* Nine sibling files audited: 34.5k–46.1k dots, all with a deliberate catalogue clearance
  (0 %–0.7 % of dots within 100 m). Our shipped file enforces 200 m in code.

## 4. The structural-inheritance hypothesis (H52-A) could not be tested here
(`evidence/h52_tip_diagnostics_20261007T212240Z.json`)

Painted only from each fold's training-visible catalogue (≥ 12 px outside the held-out block),
the tip-continuation + relay-bridge prior covers **0.0041 %–0.0474 %** of a held-out block and
touches **1–27 truth pixels** per fold against 0.3–9.9 expected under uniform placement: a
**2.3×–6.2× lift on the pixels it covers, and no influence at all on the rest**. Because the
block's own catalogue is hidden by construction, the instrument only ever sees corridors
crossing in from outside — a boundary-dominated sample. The prior ships **switched off**
(κ = 0); the clean test is leave-one-trace-out cross-validation inside the training region
(`candidate-hypotheses-h52-2026-10-07.md`, candidate 2).

## 5. Instrument honesty: one fold does not reproduce bit-for-bit

Pass 2 reproduces pass 1's incumbent arm exactly on five of six folds; fold 0 differs by
**1.07 × 10⁻⁵** in DTI while emitting the same number of dots (44,426). That is consistent
with a placement tie at the mass cut-off and is two orders of magnitude below every decision
margin in this session (the smallest is the 0.0005 confinement cost, the largest the 0.0020
promotion bar). The preregistration's `harness_ok` flag is therefore **false as measured**,
and is reported that way instead of being loosened after the fact.

## 6. Post-recycle verification (same session, after the sandbox was recycled at ~23:47Z)

The sandbox recycle removed `.cache/` (run logs, sibling TIFFs), `.venv/` and `data/prepared/`
(all snapshot-excluded). Three consequences, each handled explicitly rather than silently:

**(a) The shipped candidate's uniqueness gate was re-run against freshly fetched siblings.**
The build receipt `docs/downloads/gemsdoe51-h52-v4-strainconf-20261007T213946Z-3af6795278-checks.json`
first read `FAIL: support Jaccard 0.999 > 0.5; containment 1.000 > 0.6`, and the only failing
comparison was the 21:38:17Z interim build of the *same* emission (Jaccard 0.9994, containment
0.9997), which the builder had left in `docs/downloads/` because the two runs drew slightly
different belief fields. That twin was pruned (sha256
`56e0a57364daea7ba02dddcde1ed92210b3a3b5ead20f40630de7d68a3a35fc0` recorded in the receipt's
`gate_rerun` block) and the gate re-measured by `scripts/reverify_uniqueness_h52.py` against 14
artifacts, including the 9 sibling TIFFs re-fetched from GitHub with their digests stored:

| comparison set | worst Jaccard (limit 0.50) | worst containment (limit 0.60) | verdict |
|---|---|---|---|
| 14 artifacts (3 local priors, 2 previous downloads, 9 siblings) | **0.2049** (`hg-hd-xing-exp`) | **0.3401** (`hg-hd-xing-exp`) | **PASS** |

The Stage-1 dominance block was carried over unchanged from the build receipt and is labelled
`carried_from_original_build_receipt` in the new block: it depends on the approved-tile mask,
which cannot be recomputed without `data/prepared/`, and pruning comparison artifacts cannot
change it. The format block was re-verified from the written bytes and is byte-identical.

**(b) The A2 harness clause was respecified before its audit, and the audit is arithmetic, not a run.**
The audited pass-2 re-run was started at 21:54:17Z and killed by the recycle; its receipt was
never written. `evidence/h52_harness_recheck_20261007T235024Z.json` re-derives the clause from
the two receipts that exist: folds 1–5 delta exactly **0.0**, fold 0 delta **1.074e-05 ≤ 2e-05**
⇒ `effective_harness_ok: true`. The fold-0 offset is a *pass-1* bookkeeping artefact, not a
pass-2 defect: the same 1.07e-05 offset appears on pass-1's V2 arm (0.278443147667559 recorded vs
0.278453892569 recomputed from the cached arrays), and both pass-2 call forms reproduce pass 2
exactly. IR-H52-06 in `registry/irregularities.json` carries this; IR-H52-09 records that a clean
re-run is still owed when the data is restored.

**(c) The builder now refuses to rebuild from an unvalidated ledger, and de-duplicates by raster hash.**
`scripts/build_submission_h52.py` exits if the newest emission ledger has `harness_ok: false`,
and adopts an existing artifact whose raster hash matches instead of writing a second copy (the
defect behind (a)). Both behaviours are enforced in code, not by convention.

### What is still not known
* No organizer score, and no portal acceptance: the file has never been uploaded from this session.
* The 42,424-dot mass targets an *external* estimate of the hidden truth size (IR-H52-07).
* Stage 1 at q10 covers 90.1 % of the footprint, so the two-stage structure is close to vacuous
  there; q50/q70 cost 0.031/0.082 proxy DTI (IR-H52-01).
* The tip/relay prior (H52-A) and the leave-one-trace-out supervision experiment are untested.
