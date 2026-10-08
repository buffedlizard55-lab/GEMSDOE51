"""Render the most recent experiment from immutable evidence receipts."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def _render_h53a(stage1: dict, baseline: dict):
    esc = html.escape
    s1 = stage1["summary"]["nominal"]
    base = baseline["summary"]
    tol = baseline["config"]["baseline_reproduction_tolerance"]
    folds = baseline.get("per_fold", [])
    k2x = _load(ROOT / "evidence/h53_k2x_holdout_20261008.json") or {}
    k2x_baseline = k2x.get("baseline", {})
    k2x_result = k2x.get("candidate_result", {})
    k2x_stage1 = k2x.get("stage1_holdout", {})
    k2x_frozen = k2x_baseline.get("frozen_mean_dti", float("nan"))
    k2x_mean = k2x_result.get("stage1_q10_gated_mean_dti", float("nan"))
    k2x_gap = k2x_frozen - k2x_mean
    k2x_delta = k2x_result.get("paired_mean_delta_vs_stage1_gated_hd_hh", float("nan"))
    k2x_positive = k2x_result.get("positive_folds_vs_stage1_gated_hd_hh", 0)
    k2x_drift = k2x_baseline.get("fresh_minus_frozen_mean", float("nan"))
    k2x_banner = (
        f"<p><strong>Separate earlier H53-K2x screen — research download YES; submit NO:</strong> "
        f"q10-gated mean {k2x_mean:.7f}, {k2x_gap:.7f} below the frozen best; paired delta "
        f"{k2x_delta:+.7f} ({k2x_positive}/6 folds), with baseline drift {k2x_drift:+.8f} "
        f"outside tolerance. <b>NOT PROMOTED.</b> "
        f"<a href=\"index.html#h53-k2x-research\">Download its separate research TIFF</a> · "
        f"<a href=\"downloads/h53_k2x_holdout_20261008.json\">six-fold receipt</a>. "
        f"It is not H53-A and must not be submitted.</p>"
        if k2x else
        "<p>Separate earlier H53-K2x evidence is recorded in its own receipt; it is not H53-A.</p>"
    )
    k2x_detail = (
        f"""<h3>Earlier H53-K2x screen — separate from latest H53-A; NOT PROMOTED</h3>
<p>Stage 2: q10-gated proxy mean {k2x_mean:.7f} vs same-fold gated H-D/H-H baseline {k2x_baseline.get('stage1_q10_gated_mean_dti', float('nan')):.7f} (paired Δ {k2x_delta:+.7f}; {k2x_positive}/6 folds); {k2x_gap:.7f} below frozen best {k2x_frozen:.7f}. Fresh-baseline drift {k2x_drift:+.8f} exceeded the unchanged 1e-5 tolerance. The preregistered gate failed; no post-result tuning was performed.</p>
<p>Stage 1, measured separately: five whole-trace splits, mean approved area {k2x_stage1.get('trace_split_mean_area', float('nan')):.2%}, held-out trace recall {k2x_stage1.get('heldout_trace_recall', float('nan')):.2%}, lift {k2x_stage1.get('heldout_trace_lift', float('nan')):.4f}. Stage-2 q10 masks excluded held-out trace rows; all points were confined and Stage-1 score weight was zero. The generated TIFF passes current-inventory uniqueness and local final-byte checks; broader-family uniqueness is <b>NOT CLEARED</b>, and local checks are not portal acceptance.</p>
<p><strong>Download for research: YES. Submit: NO.</strong> <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif">H53-K2x research TIFF</a> · <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.zip">one-TIFF ZIP</a> · <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros-checks.json">local checks</a> · <a href="downloads/h53_k2x_holdout_20261008.json">six-fold receipt</a> · <a href="downloads/candidate-hypotheses-2026-10-08.md">ranked slate</a>.</p>"""
        if k2x else ""
    )
    fold_rows = "".join(
        "<tr>"
        f"<td>{r['fold']}</td>"
        f"<td>{r['dti']:.9f}</td>"
        f"<td>{r['frozen_dti']:.9f}</td>"
        f"<td>{r['delta_vs_frozen']:+.9f}</td>"
        "</tr>"
        for r in folds
    )
    split_rows = "".join(
        "<tr>"
        f"<td>{r['split']}</td>"
        f"<td>{r['held_record_count']}</td>"
        f"<td>{r['heldout_truth_pixels']:,}</td>"
        f"<td>{r['cases']['nominal']['approved_area_share']:.3%}</td>"
        f"<td>{r['cases']['nominal']['heldout_recall']:.3%}</td>"
        f"<td>{r['cases']['nominal']['recall_area_lift']:.3f}</td>"
        f"<td>{r['cases']['nominal']['matched_mass_random_controls']['uniform_in_approved']['dti']:.6f}</td>"
        f"<td>{r['cases']['nominal']['matched_mass_random_controls']['uniform_in_footprint']['dti']:.6f}</td>"
        "</tr>"
        for r in stage1.get("per_split", [])
    )
    candidate_score = "NOT RUN — BLOCKED BEFORE CANDIDATE FIT/SCORING"
    blocker = (
        f"Fresh canonical mean {base['fresh_mean_dti']:.9f} vs frozen cached-field mean "
        f"{base['frozen_mean_dti']:.9f} (Δ {base['fresh_minus_frozen_mean']:+.9f}); "
        f"required |Δ| ≤ {tol:.8f}. The reproduction gate failed. The legacy cached field files and "
        "their exact generating metadata are missing, and no cause is assigned to the fold-0 mismatch."
    )
    banner = f"""<section class="download missing">
<p class="eyebrow">LATEST EXPERIMENT · H53-A · 8 OCTOBER 2026</p>
<h2>Stage 1 measured; Stage 2 blocked before candidate scoring</h2>
<p class="warn"><strong>H53-A DOWNLOAD FOR RESEARCH: NO — NO H53-A TIFF WAS GENERATED.</strong><br>
<strong>SUBMIT TO THE COMPETITION: NO.</strong> H53-A has no candidate score, candidate raster, uniqueness result, or format result. No competition slot was used.</p>
{k2x_banner}
<p>Identifier: <code>GEMSDOE51-H53-A-20261008</code> (preregistration/research identifier only; not a portal submission name). No submission comment or filename has been issued.</p>
<dl class="kv">
<dt>Separate Stage-1 nominal result</dt><dd>5 whole-record splits; q10 approved area {s1['mean_approved_area_share']:.2%}; visible-catalogue trace-pixel recall {s1['mean_heldout_recall']:.2%}; recall/area lift {s1['mean_recall_area_lift']:.4f}.</dd>
<dt>Stage-1 matched-mass controls</dt><dd>Uniform-dot proxy DTI {s1['uniform_in_approved_mean_dti']:.6f} inside approved tiles vs {s1['uniform_in_footprint_mean_dti']:.6f} over the full footprint. One seeded random draw per split; descriptive only.</dd>
<dt>Stage-2 status</dt><dd>{candidate_score}. The baseline provenance/reproduction gate failed; see the table and receipts below.</dd>
<dt>Submission readiness</dt><dd><strong>BLOCKED_NOT_FOR_UPLOAD</strong>. Do not use the separate H53-K2x research TIFF as an H53-A substitute or competition submission.</dd>
</dl>
<p><a href="downloads/h53a_stage1_holdout_20261008.json">Stage-1 receipt</a> ·
<a href="downloads/h53a_baseline_provenance_20261008.json">baseline provenance/reproduction receipt</a> ·
<a href="downloads/hypothesis-slate-20261008.md">ranked H53 slate</a> ·
<a href="downloads/preregistration_h53.json">frozen H53 preregistration</a> ·
<a href="how-to-submit.html">submission instructions</a>.</p>
</section>"""
    detail = f"""<h2>Latest H53-A experiment: evidence and decision</h2>
{banner}
<h3>Stage 1 — coarse source-segment prior only</h3>
<p>Five deterministic whole-record splits (sorted record IDs, NumPy seed 5308) excluded held-out official records from the 10 km clipped-segment tensor. Nominal assumptions: slip-rate unit mm/year per the official attribute audit; fault-plane component; 60° normal dip; unknown-sense records omitted; literal geodetic numeric scale 1e-8/year. Sensitivities use 1e-9/year and a vertical-rate convention. The residual-rank mask approves broad tiles; it does not place fine-scale points.</p>
<p>Nominal means: approved footprint area {s1['mean_approved_area_share']:.4f}; held-out visible-catalogue pixel recall {s1['mean_heldout_recall']:.4f}; recall/area lift {s1['mean_recall_area_lift']:.4f}. Matched-mass one-draw uniform controls: in-mask proxy DTI {s1['uniform_in_approved_mean_dti']:.6f}, full-footprint proxy DTI {s1['uniform_in_footprint_mean_dti']:.6f}. The mixed split-level differences do not establish robust enrichment.</p>
<p><strong>Preregistration wording irregularity, preserved:</strong> the frozen JSON's sensitivity list redundantly names “fault-plane rate convention,” while its nominal case is already fault-plane. The receipt's executed cases are explicit: nominal 1e-8/year fault-plane; 1e-9/year fault-plane sensitivity; and 1e-8/year vertical-rate sensitivity. No fourth case is claimed; the preregistration was not edited after results.</p>
<table><thead><tr><th>Split</th><th>Held records</th><th>Held truth px</th><th>Approved area</th><th>Recall</th><th>Lift</th><th>Uniform in mask DTI</th><th>Uniform full footprint DTI</th></tr></thead><tbody>{split_rows}</tbody></table>
<h4>Frozen sensitivities (Stage 1 only)</h4>
<p>1e-9/year: area {stage1['summary']['unit_1e-9']['mean_approved_area_share']:.4f}, recall {stage1['summary']['unit_1e-9']['mean_heldout_recall']:.4f}, lift {stage1['summary']['unit_1e-9']['mean_recall_area_lift']:.4f}. Vertical-rate convention at 1e-8/year: area {stage1['summary']['vertical_rate']['mean_approved_area_share']:.4f}, recall {stage1['summary']['vertical_rate']['mean_heldout_recall']:.4f}, lift {stage1['summary']['vertical_rate']['mean_recall_area_lift']:.4f}.</p>
<h3>Baseline provenance gate — candidate Stage 2 not run</h3>
<p>{esc(blocker)}</p>
<table><thead><tr><th>Fold</th><th>Fresh canonical H-D/H-H</th><th>Frozen cached-field receipt</th><th>Fresh − frozen</th></tr></thead><tbody>{fold_rows}</tbody></table>
<p>Folds 1–5 exactly match their frozen proxy values; fold 0 differs by {base['max_abs_fold_delta']:.9f}. <code>evaluate_hh_blend.py</code> reads legacy <code>field_H_D_fold*</code>/<code>field_H_H_fold*</code> arrays that are absent from this checkout and have no persisted run metadata. <code>run_experiments.py</code> documents negative seed 1000+fold; the distinct H52 caches use 2000+fold and were not substituted. This establishes that exact historical lineage is not recoverable from preserved artifacts, not the cause of the fold-0 difference.</p>
<p><strong>Stage 2 is blocked, not a negative H53-A result.</strong> It has no measured candidate-vs-baseline DTI. The fail-closed runner refuses to train/score the candidate while reproduction fails. Do not tune the H53 features or use a competition slot on it.</p>
<h3>Hypothesis, data and limitations</h3>
<p>H53-A tests a bounded 1–8 pixel nonzero lag between detrended-elevation and isostatic-gravity edge normals, with a zero-lag control at σ=2 and 5 px. It uses the hash-pinned competition mirrors already restored; no new external source was required. Lithologic contacts, interpolation offsets, off-fault/aseismic strain, geodetic-unit interpretation, slip component and fault-dip assumptions remain plausible confounders. The visible QFaults/INGENIOUS catalogue is proxy truth; these are not hidden-label or organizer-score results.</p>
<p>External context: <a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">Kreemer et al. (2000), Eq. 3</a>; <a href="https://gdr.openei.org/submissions/1391">INGENIOUS/GDR 1391</a>; <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official task description</a>. See the <a href="downloads/official-source-review-20261007.md">source review</a> and <a href="downloads/official_attribute_audit_20261007.json">attribute audit</a>.</p>
<h3>Next step</h3>
<p>Recover an auditable H-H/H-D field lineage or create a new, preregistered benchmark before scoring another candidate. Keep the existing baseline mismatch visible; never substitute H52 seed-2000 caches for legacy fields or attribute the mismatch to an unverified cause. The portal range validation remains unresolved. No H53-A TIFF is available; the separate earlier H53-K2x TIFF is research-only.</p>
{k2x_detail}
<h3>Historical P1 result (not the latest experiment)</h3>
<p>The previous P1 odd/even screen produced a unique research-only TIFF but failed its paired gated test (mean {json.loads((ROOT / 'evidence/p1_holdout_20261007.json').read_text())['summary']['candidate_gated']:.6f}, paired delta {json.loads((ROOT / 'evidence/p1_holdout_20261007.json').read_text())['summary']['paired_delta']:+.6f}, 2/6 folds). It remains explicitly <b>NOT FOR SUBMISSION</b>; its download/checks are listed on the <a href="index.html">executive summary</a>.</p>
"""
    return banner, detail


def render_p1():
    path = ROOT / "evidence/p1_artifact_20261007.json"
    if not path.exists():
        return "", ""
    a = json.loads(path.read_text())
    h = json.loads((ROOT / "evidence/p1_holdout_20261007.json").read_text())
    v = json.loads((ROOT / "evidence/official_vector_budget_20261007.json").read_text())
    esc = html.escape
    s = h["summary"]
    c = a["format"]["checks"]
    g = a["uniqueness"]
    st = a["stage1"]
    family_path = ROOT / "evidence/p1_family_audit_20261007.json"
    family_result = json.loads(family_path.read_text()) if family_path.exists() else {}
    family_notice = (
        "Broader family gate: "
        + family_result.get("verdict", "PENDING")
        + "; exact duplicate: "
        + str(family_result.get("exact_duplicate", "not checked"))
    )
    banner = f"""<section class="download missing">
<p class="eyebrow">LATEST EXPERIMENT · P1 · 7 OCTOBER 2026</p>
<h2>New, independently generated TIFF</h2>
<p class="warn"><strong>DOWNLOAD FOR RESEARCH: YES. SUBMIT TO THE COMPETITION: NO.</strong><br>
This is a newly trained prediction map, not a renamed or re-encoded prior submission. It has not cleared every promotion gate. No competition slot was used.</p>
<p><a class="btn" download href="downloads/{esc(a['file'])}">Download new research TIFF</a></p>
<p><a download href="downloads/{esc(a['zip'])}">Download ZIP containing one TIFF</a> · <a href="latest.html">Results, checks &amp; decision</a> · <a href="how-to-submit.html">Submission instructions</a></p>
<dl class="kv"><dt>Unique identifier</dt><dd><code>{esc(a['submission_name'])}</code></dd>
<dt>Short comment (research only)</dt><dd><code>{esc(a['note'])}</code></dd>
<dt>Numeric checks</dt><dd>{a['format']['count']} band · float32 · EPSG:32611 · 3730 × 3292 · min {c['min_value']:g}, max {c['max_value']:g} · {c['global_invalid_cells']} nonfinite/out-of-range cells · no NoData tag.</dd>
<dt>Stage2 proxy DTI</dt><dd>{s['candidate_gated']:.6f} vs paired gated baseline {s['baseline_gated']:.6f}; {s['positive_folds']}/6 folds improved. Not an organizer score.</dd>
<dt>Stage1 confinement</dt><dd>{st['emitted_pixels_inside_approved']:,}/{st['emitted_pixels_total']:,} points inside approved tiles; approved area {st['approved_area_share_of_footprint']:.2%}; lift {st['lift_over_area_share']:.3f}.</dd>
<dt>Uniqueness scope</dt><dd>{esc(family_notice)}. Dense probability maps can fully contain a sparse support without being the same prediction. No universal novelty claim.</dd>
<dt>SHA-256</dt><dd><code>{esc(a['sha256'])}</code></dd></dl>
<p><a href="downloads/{esc(a['checks_file'])}">Final-byte checks and scoped uniqueness gate</a>. Format/range safety is not portal acceptance. <strong>NOT FOR SUBMISSION.</strong></p>
</section>"""
    rows = "".join(
        f"<tr><td>{r['fold']}</td><td>{r['scores']['baseline_ungated']['dti']:.6f}</td><td>{r['scores']['baseline_gated']['dti']:.6f}</td><td>{r['scores']['candidate_gated']['dti']:.6f}</td></tr>"
        for r in h["rows"]
    )
    gates = "".join(
        f'<li>{esc(k)}: <strong>{"PASS" if val else "FAIL"}</strong></li>'
        for k, val in h["gates"].items()
    )
    vh = v["holdout"]
    detail = f"""<h2>Latest experiment: evidence and decision</h2>{banner}
<h3>Stage2: spatially blocked fine-scale detector</h3>
<p>P1 decomposes detrended-elevation normal profiles into antisymmetric step and symmetric ridge/valley signals at ±200m and ±500m. Three features extend H-H, blended50/50 with freshly fitted H-D. No earlier submission is an input. Fixed six-fold splits, 1.2km buffer,250,000 negative samples and250 HGB iterations; STE L9/w0.35/spacing2.4, ratio3.47. Predictions confined to the frozen fold-specific q10 strain prior.</p>
<table><thead><tr><th>Fold</th><th>Baseline ungated</th><th>Baseline q10</th><th>P1 q10</th></tr></thead><tbody>{rows}</tbody></table>
<p>Mean P1={s['candidate_gated']:.7f}; paired Δ={s['paired_delta']:+.7f}. Frozen best={s['frozen_best']:.7f}; reproduced baseline drift={s['baseline_drift']:+.8f}. Promotion rules were not relaxed after results.</p><ul>{gates}</ul>
<h3>Stage1: separate holdouts, not the fine-scale score</h3>
<p>The frozen legacy q10 trace holdout: DTI0.050627 vs uniform0.048564; approved area90.06%, recall95.39%. This is weak coarse enrichment, not a detector.</p>
<p>The new <strong>official-vector</strong> five-split trace audit has mean approved area {vh['mean_area']:.2%}, trace recall {vh['mean_recall']:.2%}, and lift {vh['mean_lift']:.4f}. It uses actual clipped segment lengths rather than centroid rate assignment. This separate source-corrected audit is <em>not</em> silently substituted into P1's frozen legacy gate. It requires its own paired Stage2 test before production use.</p>
<p>Actual artifact gate ablation: {a['stage1_ablation']['fraction_gated_points_also_ungated']:.2%} of gated points also occur in the same detector's ungated output; support Jaccard {a['stage1_ablation']['gated_vs_ungated_support_jaccard']:.4f}. Within approved tiles, only {st['approved_pixel_occupancy']:.2%} of cells receive a point. Broadness/lift is an operational check, not proof of causal independence.</p>
<h3>Source corrections and limitations</h3>
<p>Official DBF confirms mm/year and matches all1,126 mirrored records. Source shear is min(|e1|,|e2|) for opposite-signed principal strains, else0. Actual-vector tensor summation and scalar residuals are now implemented with explicit dip/component/unit scenarios. Off-fault and aseismic strain or erroneous catalogue rates can cause a deficit. The task predicts faults, not vents.</p>
<p>All-finite zero-outside encoding removes NaNs and out-of-range sentinels from this file. The published null/NaN-outside language and portal behavior remain unverified together; the historical error-triggering file is unknown. Do not treat a local check as a successful portal submission.</p>
<p>Neither the user-reported0.2778 attribution nor the stated0.3195 leaderboard high establishes an achievable score here. GEMSDOE32's own primary page still says UNSCORED. Reused catalogue folds cannot certify hidden-fault or leaderboard performance.</p>
<h3>Audit files and next experiment</h3>
<ul>
<li><a href="downloads/p1_final_verification_20261007.json">Independent final-byte, ZIP and tile-confinement verification</a></li>
<li><a href="downloads/p1_holdout_20261007.json">Complete P1 holdout</a></li>
<li><a href="downloads/official_vector_budget_20261007.json">Vector-budget equation, residuals and five-split Stage1 holdout</a></li>
<li><a href="downloads/official_attribute_audit_20261007.json">Official DBF match receipt</a></li>
<li><a href="downloads/official-source-review-20261007.md">Source ledger, exact equations and scientific corrections</a></li>
<li><a href="downloads/next-candidates-20261007.md">Four ranked hypotheses and preregistered rules</a></li>
<li><a href="../registry/official/receipt.json">Official archive hashes and field inventory</a></li>
</ul>
<p>Next: resolve frozen-baseline drift, verify outside-footprint semantics with the organizer, introduce an untouched spatial/trace-family lockbox, and test the official-vector mask with a new fine-scale candidate. Preserve this negative experiment. Do not tune P1 until it passes the same reused folds.</p>"""
    family = ROOT / "evidence/p1_family_audit_20261007.json"
    if family.exists():
        f = json.loads(family.read_text())
        if "verdict" in f:
            detail += f"<h3>Broader family audit</h3><p>{f['downloaded']}/{f['expected']} inventory payloads restored; verdict {esc(f['verdict'])}; exact duplicate={f['exact_duplicate']}; maximum support Jaccard={f['max_jaccard']:.4f}, containment={f['max_containment']:.4f}. Scoped to the committed inventory, not a universal novelty proof. <a href='downloads/p1_family_audit_20261007.json'>Full comparisons</a>.</p>"
    return banner, detail


def render():
    manifest = _load(ROOT / "data/submission_manifest.json") or {}
    latest = manifest.get("latest_experiment", {}) or {}
    if latest.get("hypothesis_id") == "H53-A":
        h53_stage1 = _load(ROOT / "evidence/h53a_stage1_holdout_20261008.json")
        h53_baseline = _load(ROOT / "evidence/h53a_baseline_provenance_20261008.json")
        if (not h53_stage1 or not h53_baseline
                or h53_stage1.get("status") != "COMPLETE_STAGE1_ONLY"
                or h53_baseline.get("status") != "BASELINE_REPRODUCTION_FAILED_STAGE2_BLOCKED"):
            missing = """<section class="download missing">
<p class="warn"><strong>H53-A is the latest registered experiment, but its expected frozen receipts are missing or inconsistent.</strong></p>
<p>No H53-A prediction TIFF, candidate score, submission name, or upload authorization is available. A separate earlier H53-K2x TIFF exists for research only; do not treat it as H53-A or fall back to it as the latest result.</p>
<p>Restore the versioned H53 Stage-1 and baseline provenance receipts before rebuilding this page.</p>
</section>"""
            return missing, missing
        return _render_h53a(h53_stage1, h53_baseline)
    return render_p1()
