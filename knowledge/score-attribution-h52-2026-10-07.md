# Why the strongest known sibling artifact scored what it did — and what that says about beating it

Session: 2026-10-07 (H52). Repo: `GEMSDOE51`, branch `arena/4df01627-gemsdoe51`.
Audience: the project owner, who will verify every number below. Nothing here is a
leaderboard claim; every quantity is labelled **MEASURED LOCALLY** (reproducible from this
repository), **OWNER-REPORTED** (another repository's README), **USER-SUPPLIED** or
**ORGANIZER** (official competition text).

---

## 0. The premise is not auditable, and that matters

The question "why did
`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` score **0.2778**?" contains an unverified
premise. That number is **USER-SUPPLIED**, and the sibling repository that produced the file
marks it, in its own README, as **UNSCORED** (the file's model is reported there as 0.2747;
this repository recorded the discrepancy as irregularity **IR-51-22**). Two distinct
attributions are therefore available:

* the *file* was submitted and scored 0.2778 (user-supplied, unverifiable from here), or
* the *model* behind it measured 0.2747 in the owner's own local proxy (owner-reported).

Everything below is a statement about the **artifact as bytes** plus the **metric algebra**.
Those two are checkable, and they are enough to answer the useful form of the question:
*what does a score in this range consist of, and which of its terms can we actually move?*

---

## 1. What the file is (MEASURED LOCALLY, `evidence/sibling_design_audit_20261007T210250Z.json`)

| quantity | value |
|---|---|
| dots (non-zero pixels) | **37,654** |
| values | single value class, all `1.0` (binary dot raster) |
| dots within 100 m (1 px) of the published catalogue | **0.00 %** |
| dots within 200 m / 300 m / 500 m | 0.00 % / 5.77 % / 14.97 % |
| dots outside the scored footprint | 0 % |
| sha256 | recorded in the audit receipt |

Two facts follow immediately. First, the file is a **dot set at ~37.7k mass**, in a family
whose members sit between 34.5k and 46.1k dots (nine sibling files audited). Second, its
compiler deliberately kept **every** dot at least ~300 m from a published fault. That second
choice is the single most consequential thing about the file, and it is now *measured* to pay.

## 2. The metric, and what a 0.27–0.28 actually consists of

The official metric (organizer text, page 967, quoted verbatim in `src/gems51/metric.py`) is

```
DTI = TP_w / ( alpha*(TP_w + FP_w) + beta*|G| + eps ),  alpha = 0.2, beta = 0.8
```

with a triangular credit kernel `k(d) = max(1 - d/300 m, 0)` and `TP_w` summed over *truth*
pixels, taking the best nearby prediction. Two consequences are structural, not stylistic:

1. **Redundancy is nearly free to create but buys almost nothing.** A second dot inside the
   3 px kernel of a truth pixel that is already claimed adds mass and returns credit only for
   the *unclaimed* part of that kernel.
2. **Mass on published faults is bought at full price and credited at zero.** Published
   USGS/INGENIOUS pixels are excluded from the truth set (ORGANIZER FAQ), so a dot there can
   never be the nearest truth pixel for anything. Under the scoring reading that the live
   experiment in §3 identifies (reading B, implemented in `src/gems51/live_metric.py`), that
   mass is *still counted* in the false-positive term.

A useful marginal rule follows from the algebra (derived and unit-tested in
`tests/test_metric.py`): adding a dot with credit `c` and one unit of mass improves DTI iff

```
c * (1 - alpha*DTI)  >  alpha*DTI * (1 - c)      i.e.    c > ~0.055   at DTI ~ 0.27
```

So in this regime *a dot is worth adding only if it is about 5.5 % likely to earn credit*.
This is a **precision-per-dot** problem, not a detection problem. That is the honest answer to
"why did it score ~0.27": at that score level roughly **88 % of the submitted mass is either
off-target or redundant**.

The decomposition below is ours, measured on the six-block visible-catalogue instrument
(`evidence/emission_geometry.json`, arm H-D, fold 0, same mass ratio 3.47, 44,426 dots):

| term | value | interpretation |
|---|---|---|
| truth pixels `|G|` (local fold) | 12,803 | proxy truth = held-out catalogue block |
| weighted credit `TP_w` | 5,405 | 42.2 % of truth pixels claimed with partial credit |
| weighted false positive `FP_w` | 41,581 | ≈ 0.94 mass per dot |
| credit per dot | 0.1217 | the efficiency number the leaderboard really rewards |
| DTI | 0.2752 | `metric.dti_binary`, reading A |

The same instrument brackets what any file could hope for **with a hypothetical perfect dot
set**: uniformity inside the block gives 0.193; uniform placement within 300 m of the truth
gives 0.553; an oracle that lands exactly on truth gives 1.0, and at a quarter of the mass the
oracle still gives 0.546 (`data/two_stage_results.json`). The gap between 0.28 and 0.55 is
therefore **entirely field quality** — knowing *where* the faults are — not emission geometry.

## 3. The one mechanism in that family whose effect is verified, and it is worth ~+0.011

The sibling repository reports two live scores for two files that differ only in a thin band
around the published catalogue:

| file | dots | owner-reported live score |
|---|---|---|
| `GEMS28-H27-4-R1-SOLO-D2.8` | 44,090 | 0.2600 |
| `h27-4-r1-solo-d2-8-...-nan.tif` | 40,199 | 0.2708 |

Scores are **OWNER-REPORTED**. The *mechanism* is **MEASURED LOCALLY** and is exact: the kept
file is a strict subset of the larger file, the difference is 3,891 pixels, **every one of
them within 100 m of the published catalogue**, and the kept file has **zero** dots within
100 m of it. Removing mass that the scorer cannot credit raised the live score by **+0.0108**.
Under scoring reading A that removal would be score-neutral by construction, so this pair is
the strongest available evidence that the live scorer uses reading B and that
published-catalogue clearance is a **free, on-demand gain**.

Our own submission builder therefore enforces clearance as a hard rule in code (and refuses to
write a file if any dot violates it).

## 4. Can a > 0.2778 file be generated? — what we can and cannot claim

What the local evidence supports, with magnitudes:

1. **Clearance** (verified mechanism above): worth ≈ +0.011 **only if** the candidate file
   wastes mass on the catalogue. Our candidates have measured 0 %, so we bank the gain by
   construction rather than by measurement; there is nothing left to collect.
2. **Emission geometry** at matched mass: strike-coherent trace emission (STE: multi-scale
   ridge/vesselness + along-strike integration + greedy spacing) measured **+0.0022** over
   isotropic NMS on the six-fold blocked instrument (0.28534 vs 0.28317,
   `evidence/hh_blend_holdout.json`); four of six folds positive.
3. **Field composition**: the H-H/H-D blend measured **+0.006** over the base stack
   (0.28534 vs 0.27940) on the same instrument; adding more layer families (H_C, H_E, H_ALL)
   measured *worse* (0.254–0.277), so this is a local optimum in the layer space we have.
4. **Stage-1 confinement** (strain-budget deficit tiles): measured cost ≈ 0.001–0.0015, i.e.
   almost free, but it buys no local DTI either; it is a *structural* choice (the coarse prior
   must not dominate), not a scoring one.

Put together, our best locally-validated candidate is ≈ 0.285 on a proxy whose own ceiling
with a perfect dot set is 0.55 and whose truth is the *already mapped* catalogue. What that
means for the hidden label set is **not measurable from here**: the hidden faults are, by the
organizer's own statement, continuations/splays/parallel strands of mapped systems, and the
local instrument cannot reward the discovery of a genuinely new fault *style* at all. So:

* **Yes**, a file that beats 0.2778 *if* 0.2778 is the true score of a comparable artifact:
  the clearance rule alone accounts for +0.011 in the sibling's own live experiment, and our
  candidate banks it while adding the geometry gain.
* **No**, we cannot claim any number, and in particular we cannot claim the 0.3195 leaderboard
  high (user-supplied, unverified). Reaching that level requires a field substantially better
  than anything measurable here; no local instrument in this repository can certify it, and
  asserting it would be exactly the kind of hallucination the brief forbids.
* The only way to convert the *expected* improvement into knowledge is to spend one weekly
  slot on a preregistered, gated file. That is the recommendation at the end of this session.

## 5. What would falsify this analysis

* If the live scorer actually used reading A, the −0.0108 sibling delta would be inexplicable
  by the dot-removal mechanism (it would be noise), and the clearance rule would be worth 0,
  not 0.011. The pair would then need another explanation (e.g. a change in the model behind
  the two files).
* If 0.2778 is a *portal* score of the `.tif` named above while the owner's README calls it
  unscored, the attribution is wrong and IR-51-22 should be closed with the owner's
  confirmation.
* If the hidden label set contains fault *styles* absent from the visible catalogue, every
  number in §2–§4 is optimistic in an unmeasured way.
