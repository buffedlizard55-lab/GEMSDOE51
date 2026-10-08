# Candidate hypotheses for H52 (session 2026-10-07)

Rules this slate obeys (from the standing brief):

* each candidate names (a) the specific layer(s) or input it uses, (b) the physical signature
  it targets, (c) why it should catch a fault **missing from** the USGS/INGENIOUS catalogue
  rather than one already in it, and (d) how it differs from everything already implemented in
  this repository;
* candidates that cannot be validated without new external data are marked **BLOCKED** and the
  specific free official source is named (and, for anything actually proposed, checked for
  obtainability);
* ranking is by **expected DTI gain ÷ implementation cost**, and every claim about a gain is
  labelled with the instrument that measured it.

Scoring context that drives the ranking (see `score-attribution-h52-2026-10-07.md`): at the
0.27 level, a dot must be ~5.5 % likely to earn credit; measured credit per emitted dot is
0.12, so **precision-per-dot is the binding constraint, not detection**. Anything that only
re-ranks pixels the model already likes cannot move the score much.

---

## 1. H52-A — Structural-inheritance prior: tip continuation and relay bridging
**Rank 1 — cost: low (implemented this session, `src/gems51/tip_model.py`); expected live gain:
unknown, plausible; measured local gain: none measurable, and §"honest measurement" explains why.**

* **(a) Layer/input:** the published catalogue raster itself (`data/labels.tif` ≡
  `existing_faults.tif`, sha256-identical). No geophysical layer is used, so the candidate is
  orthogonal to every existing arm.
* **(b) Signature:** skeleton free ends ("tips") of mapped traces; for each tip the local
  strike and curvature from a quadratic fit over the last ~14 skeleton pixels; then a
  continuation corridor (40 px = 4 km, decaying with a 1.2 km length scale) and the bridge
  between two *facing* tips of different components (relay ramp). Growth-by-linkage geometry:
  Cartwright, Trudgill & Mansfield 1995, doi:10.1016/0191-8141(95)00030-8; length/displacement
  scaling: Walsh & Watterson 1988, doi:10.1016/0191-8141(88)90110-1.
* **(c) Why it targets *new* faults:** a mapped trace's *outside* is, by construction, where a
  missing continuation or an unmapped parallel strand would be. DrivenData staff state the
  hidden set contains "continuations, splays and parallel strands" of mapped systems
  (organizer post, community thread 11536). The prior never scores a mapped pixel itself
  (corridors start 300 m beyond the tip and are removed inside the catalogue flank).
* **(d) Difference from what exists:** every other arm in this repository is a pixel-wise
  attribute classifier; this one has no geophysical input at all and is the only source of
  *new candidate locations* rather than new rankings of old locations.
* **Honest measurement (this session):** on the six-block instrument the prior, built only from
  the fold's training-visible catalogue, paints **0.024 %** of a held-out block, covering
  **15 of 12,803** truth pixels — a lift of **4.8×** over uniform placement on the pixels it
  does cover. That is statistically real (Poisson p ≈ 1e-4) but geometrically irrelevant:
  because the held-out block's own catalogue is hidden, the instrument can only evaluate
  corridors entering the block from outside, which is a tiny, boundary-dominated sample. The
  local instrument therefore **cannot** validate H52-A; the strength sweep
  (`registry/preregistration_h52_amendment3.json`) is a harm test, not a validation, and the
  submission keeps κ = 0 unless the sweep is non-negative.
* **Cheapest next test that would validate it:** leave-one-trace-out cross-validation *inside*
  the training region (hide one mapped trace + a buffer, ask whether the prior's corridor
  predicts the hidden trace). That is exactly candidate 2 below, and it is the only clean way
  to measure inheritance without the block-boundary artefact.

## 2. H52-I — Leave-one-trace-out supervision ("off-catalogue" training)
**Rank 2 — cost: medium-high; expected gain: highest ceiling of the slate, unmeasured.**

* **(a) Layers:** the existing 58-feature stack + the 35 static extras (no new data).
* **(b) Signature:** not a physical transform but a *supervision geometry*. For each training
  trace `t`, remove `t` (dilated by 1–2 px) from the positive set and remove a surrounding
  annulus band from the negative pool; the model must then learn a fault's *context*
  (its terminations, its splays) instead of memorising its pixels.
* **(c) Why it targets new faults:** the hidden set is precisely "faults whose pixels are not
  in the catalogue". Standard training on catalogue pixels teaches a model to reproduce
  catalogue pixels; leave-one-trace-out teaches it to reconstruct a trace that is *absent*,
  which is the scored task. It also converts the local instrument from "rediscover the block"
  into "reconstruct a hidden trace", which is a much closer analogue of the hidden truth.
* **(d) Difference:** it changes what the labels *mean*, not which features exist; nothing in
  this repository currently trains with held-out traces inside the training region.
* **Risk:** with 3,199 catalogue components, many are speckle; the loop must be restricted to
  components above a length threshold, and per-trace retraining is expensive (a bagged
  approximation: `K` folds of trace-held-out models, 25–50 models). Recommendation: implement
  with `K = 8` and measure on the existing six-block instrument.

## 3. H52-K — Long-chord Radon/Hough voting on the belief field
**Rank 3 — cost: low-medium; expected gain: small-positive (geometry), measurable locally.**

* **(a) Layers:** the belief field produced by the current stack (no new data).
* **(b) Signature:** straight-line coherence over **3–10 km** chords (30–100 px), i.e. the
  scale of a Basin-and-Range fault trace, versus the 0.9 km integration length of the current
  STE emitter (Vanderbrug 1976 line detection; the Radon family in general).
* **(c) Why it targets new faults:** the pixel classifier's evidence for a *long* trace is
  spread thin where the trace is only partly expressed (buried segment, alluvium cover); a
  long-chord accumulator can integrate that weak evidence along strike, whereas a 9 px
  accumulator cannot. Long coherent alignments are also the hardest thing for noise to fake.
* **(d) Difference:** STE integrates 9 px / 12 orientations; this would integrate 30–100 px
  with an explicit straightness criterion, and would emit *along* the chord (a "string of
  dots") exactly where the field is weakest but the chord evidence is strongest.
* **Measurable:** yes, directly on the six-block instrument at matched mass (cheap; one new
  emitter, no retraining). If it does not beat STE by the preregistered bar, it is dropped.

## 4. H52-D — Geodetic principal-strain-axis alignment of candidate traces
**Rank 4 — BLOCKED: needs an external input whose availability was not verified in this session.**

* **(a) Layers:** the competition's geodetic scalars are already in the stack
  (`comp_geod_2ndinv`, `comp_geod_shearrate`, `comp_geod_dilaterate`), but a *tensor
  orientation* cannot be recovered from three scalars; it needs the underlying GNSS velocity
  field or a published strain-rate tensor grid.
* **(b) Signature:** a candidate fault should strike along the local principal-shortening
  azimuth (Andersonian reasoning for dip-slip faulting in an extensional province).
* **(c) Why it targets new faults:** it is a *directional* filter that suppresses candidates
  whose strike is incompatible with the regionally measured strain field, i.e. it reduces the
  false-positive term rather than adding detections — the term that dominates the metric.
* **(d) Difference:** this repository currently uses the geodetic layers only through the
  Stage-1 *deficit magnitude* (a coarse tile mask). Using the *orientation* is new.
* **BLOCKED:** the named candidate sources are the Nevada Geodetic Laboratory velocity field
  (http://geodesy.unr.edu/, MAGNET/GPS networks) and the USGS/UNAVCO GNSS velocity products.
  **Neither was fetched or verified in this session**, and the competition's rules on external
  data have not been re-read for this session. Do not implement until (i) the source is
  downloaded and hash-recorded, and (ii) the rules question is answered from the official
  competition text.

## 5. H52-B — Published-catalogue clearance (already banked, listed for completeness)
**Rank 5 — cost: zero (implemented); gain: +0.0108 in the only live experiment that isolates it.**

* **(a) Layer/input:** the published catalogue mask.
* **(b) Signature:** nothing is emitted within 100–200 m of a published fault pixel.
* **(c) Why:** published pixels are excluded from the truth set (organizer FAQ), so mass there
  can never earn credit while still counting against the score (reading B). The sibling's own
  live pair isolates the effect: removing 3,891 dots within 100 m raised the live score from
  0.2600 to 0.2708 (owner-reported scores; the *support relation* is verified locally in
  `evidence/sibling_design_audit_*.json`).
* **(d) Difference:** it is a placement rule, not a detector.

## 6. Rejected this session (with the measurement that rejects them)
* **Deeper blends / more layer families** (H_C, H_E, H_ALL): measured 0.2544–0.2770 vs 0.2853
  for the H-H/H-D blend on the six-block instrument → rejected.
* **Strike-aligned line emission as implemented in V3/V5** (coherence-axis SALE): −0.058 proxy
  DTI at matched mass (pass 1, fold 0: 0.2207 vs 0.2790) → rejected, not tuned.
* **Position snapping of dots onto trace crests** (H-51-L): 0/6 folds improved, mean ΔDTI
  −4.1e-05 → rejected.
* **Habitat/emission-style spatial statements**: 0.0041 / 0.1223 / 0.1352 in the owner's
  records → the class of approach to avoid.
* **Stage-1 deficit as a hard gate *of the field* (old construction)**: gated 0.182 vs ungated
  0.2816 → the gate must only ever be applied at *emission* time (which is what H52 does) and
  its cost must be measured, as it now is (≈0.001–0.0015).

---

## Ranking table

| rank | candidate | cost | expected local gain | expected live gain | new external data |
|---|---|---|---|---|---|
| 1 | H52-A tip/relay prior | low (done) | not measurable (harm test only) | hypothesis-level | none |
| 2 | H52-I leave-one-trace-out supervision | med-high | testable, unknown | potentially largest | none |
| 3 | H52-K long-chord Radon emission | low-med | testable, small | small-positive | none |
| 4 | H52-D geodetic axis alignment | medium | testable *if* data obtained | reduces FP | **BLOCKED (unverified)** |
| 5 | H52-B catalogue clearance | zero (done) | 0 (already enforced) | +0.011 (sibling live pair) | none |
