# Why the best prior submission scored what it did, and what beating it requires

Evidence class: **measured**, except where marked. Nothing here is organizer-verified.

## 1. The arithmetic of the metric, first

From the published definitions `FN = |G| − TP`, so

```
DTI = TP / (TP + 0.2·FP + 0.8·FN) = TP / (0.2·(TP + FP) + 0.8·|G|)
```

`|G|`, the hidden truth size, is fixed. A submission is therefore decided by
**credit earned per unit of emitted mass**. Two corollaries, both proved
numerically in `tests/test_metric.py`:

* redundancy is expensive — for each truth pixel the scorer takes the *maximum*
  over nearby predictions, so two dots 1 px apart earn the credit of one and cost
  the mass of two;
* there is a break-even bar: a marginal pixel of value `p` earning expected
  kernel credit `c` raises the score iff `c > 0.2·DTI`, i.e. `c > 0.056` at
  DTI = 0.28.

## 2. A free natural experiment sitting in the group's own artifacts

`gemsdoe32-h33-h33-2-b2` (0.2778) is exactly the 0.2600 anchor with 6,436 dots
deleted. Measured here: the deleted set is precisely the emitted pixels at
Euclidean distance 1–2 px from a catalogued fault pixel (min 1.000, max 2.000,
mean 1.286), and the retained set all lie at distance ≥ 2.236 px.

Writing `K = 0.8·|G|`:

```
TP(44 090) = 0.2600 · (0.2·44 090 + K) = 2 292.68 + 0.2600 K
TP(37 654) = 0.2778 · (0.2·37 654 + K) = 2 092.06 + 0.2778 K
ΔTP        =   200.62 − 0.0178 K
```

`ΔTP ≥ 0` bounds the hidden truth at **|G| ≤ 14 090 px**. With the group's own
generative truth model (12 691 px, from GEMSDOE25 H28) → `K = 10 153` and
**ΔTP ≈ 20**.

So the 6 436 deleted dots earned **0.003 credit each**, against **0.139** for the
dots that were kept. A factor of 45. **Predicting within 200 m of the catalogue
is worth essentially nothing**, which is consistent with the organizer's
confirmation that known fault pixels are masked out of the scoring entirely.

Two independent routes give the same |G|: the group's generative model gives
12 691 px, and 44 090 / 3.47 (the mass ratio our holdout prefers) gives 12 708 px.
We adopt **|G| ≈ 12 700** and record that the bound is loose (2 700 – 14 100).

## 3. What the leader is actually doing better

At `|G| = 12 700`, inverting the same identity:

| submission | public DTI | emitted mass M | implied TP | credit per dot |
|---|---:|---:|---:|---:|
| 0.2600 anchor | 0.2600 | 44 090 | 4 736 | 0.107 |
| 0.2778 (group best) | 0.2778 | 37 654 | 4 915 | 0.131 |
| nchuzhoy | 0.3262 | ~40 000? | ~5 770 | ~0.144 |
| leader | 0.3774 | ~44 000? | ~7 160 | ~0.163 |

(M for the two non-group rows is not published; the implied TP assumes the same
mass as the group's files, so those two rows are **estimates**, not measurements.)

The kernel is `k = 1 − d/3`. A credit of 0.131 corresponds to a mean distance of
**2.6 px = 260 m** between an emitted dot and the nearest hidden fault pixel; the
leader's 0.163 corresponds to **2.0 px = 200 m**.

**That is the whole game.** It is a localisation problem, not a coverage problem.
The winner is not the model that flags the most ground — it is the model whose
dots sit closest to faults the catalogue does not have.

An isolated dot landing exactly on a straight trace earns about
`1 + 2(0.667) + 2(0.333) ≈ 3.0` credit, so a mean of 0.131 means only about 4 %
of the group's dots land *on* a hidden trace; the rest sit in the 1–3 px halo or
in open ground.

## 4. Why the group's dotted/thinned design worked, and where it runs out

Thinning a thick probability surface down to isolated dots at ~2.4 px spacing
removes mass that was already covered by a neighbouring dot, which raises credit
per unit mass — exactly the objective the metric rewards. That is why
0.1922 (continuous field) → 0.2477 → 0.2600 → 0.2778 as the emission got
sparser and better spaced.

It runs out when the dots start landing off the traces. At that point no amount
of re-spacing helps; only a better field does. Our holdout in-block AUC is 0.667
and our proxy DTI at matched mass is 0.279 — i.e. our detector is, on this
instrument, about as good as the one that produced 0.2778. Beating 0.3774
requires a materially better field, not a better emission rule.

## 5. What would move it

Ranked by expected effect on credit-per-dot:

1. **Train the shipped model on the whole catalogue.** Every holdout fold trains
   on 8/9 of it; the shipped model trains on 9/9. Cheap, certain, small.
2. **Beat the 0.667 in-block AUC.** The single layers top out near AUC 0.63
   in-block; the model already combines them. The remaining gap is the
   difference between "looks like a mapped fault" and "is a fault" —
   the catalogue is amplitude-biased, so the geometric/persistence features
   (H-D) and the buried-structure features (H-E) are the right direction, but
   measured here they did not move it (see `holdout.html`).
3. **Emission spacing.** Our sweep finds the mass ratio `M/|G| ≈ 3.5` optimal and
   the curve flat between 2 and 5, so this is worth a few thousandths, not
   hundredths.
4. **External data.** The 1 m 3DEP DEM is the obvious unlock — a fault mapper
   reads sub-pixel scarp geometry that a 100 m aggregate destroys. It is *not
   reachable from this sandbox* (measured: HTTP 000 to
   elevation.nationalmap.gov and prd-tnm.s3.amazonaws.com), so it cannot be
   validated here and is not proposed as viable without a machine with
   unrestricted egress.

## 6. Honest expectation

Our instrument says 0.279 ± 0.02 at the live mass ratio, which brackets the
group's own best of 0.2778 and sits well below the current leader of 0.3774.
A submission built by this pipeline should be expected to land **in the high
0.2s**, not at the top of the board, unless Stage 2's field improves
substantially. That expectation is stated before the score is known and is the
number we will compare against.
