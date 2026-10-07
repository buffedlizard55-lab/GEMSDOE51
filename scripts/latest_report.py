"""Render the latest experiment from measured JSON; no fabricated score fallbacks."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[1]


def render():
    path=ROOT/'evidence/p1_artifact_20261007.json'
    if not path.exists():return '', ''
    a=json.loads(path.read_text());h=json.loads((ROOT/'evidence/p1_holdout_20261007.json').read_text())
    v=json.loads((ROOT/'evidence/official_vector_budget_20261007.json').read_text())
    esc=html.escape;s=h['summary'];c=a['format']['checks'];g=a['uniqueness'];st=a['stage1']
    banner=f'''<section class="download missing">
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
<dt>SHA-256</dt><dd><code>{esc(a['sha256'])}</code></dd></dl>
<p><a href="downloads/{esc(a['checks_file'])}">Final-byte checks and scoped uniqueness gate</a>. Format/range safety is not portal acceptance. <strong>NOT FOR SUBMISSION.</strong></p>
</section>'''
    rows=''.join(f"<tr><td>{r['fold']}</td><td>{r['scores']['baseline_ungated']['dti']:.6f}</td><td>{r['scores']['baseline_gated']['dti']:.6f}</td><td>{r['scores']['candidate_gated']['dti']:.6f}</td></tr>" for r in h['rows'])
    gates=''.join(f'<li>{esc(k)}: <strong>{"PASS" if val else "FAIL"}</strong></li>' for k,val in h['gates'].items())
    vh=v['holdout']
    detail=f'''<h2>Latest experiment: evidence and decision</h2>{banner}
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
<li><a href="downloads/p1_holdout_20261007.json">Complete P1 holdout</a></li>
<li><a href="downloads/official_vector_budget_20261007.json">Vector-budget equation, residuals and five-split Stage1 holdout</a></li>
<li><a href="downloads/official_attribute_audit_20261007.json">Official DBF match receipt</a></li>
<li><a href="downloads/official-source-review-20261007.md">Source ledger, exact equations and scientific corrections</a></li>
<li><a href="downloads/next-candidates-20261007.md">Four ranked hypotheses and preregistered rules</a></li>
<li><a href="../registry/official/receipt.json">Official archive hashes and field inventory</a></li>
</ul>
<p>Next: resolve frozen-baseline drift, verify outside-footprint semantics with the organizer, introduce an untouched spatial/trace-family lockbox, and test the official-vector mask with a new fine-scale candidate. Preserve this negative experiment. Do not tune P1 until it passes the same reused folds.</p>'''
    family=ROOT/'evidence/p1_family_audit_20261007.json'
    if family.exists():
        f=json.loads(family.read_text())
        if 'verdict' in f:
            detail+=f"<h3>Broader family audit</h3><p>{f['downloaded']}/{f['expected']} inventory payloads restored; verdict {esc(f['verdict'])}; exact duplicate={f['exact_duplicate']}; maximum support Jaccard={f['max_jaccard']:.4f}, containment={f['max_containment']:.4f}. Scoped to the committed inventory, not a universal novelty proof. <a href='downloads/p1_family_audit_20261007.json'>Full comparisons</a>.</p>"
    return banner,detail
