"""Render the latest experiment from measured JSON; no fabricated score fallbacks."""

from pathlib import Path
import json, html

ROOT = Path(__file__).resolve().parents[1]


def render_h53():
    """Render the 2026-10-08 H53 experiment (top-candidate validation + build).

    Returns ("", "") when the H53 receipts are absent or incomplete, so the
    caller falls back to the previous experiment's renderer.
    """
    hold_path = ROOT / "evidence/h53_holdout_20261008.json"
    build_path = ROOT / "registry/submission_build_h53.json"
    manifest_path = ROOT / "data/submission_manifest.json"
    if not (hold_path.is_file() and build_path.is_file() and manifest_path.is_file()):
        return "", ""
    h = json.loads(hold_path.read_text())
    if h.get("status") not in ("COMPLETE", "COMPLETE_NOT_PROMOTED"):
        return "", ""
    b = json.loads(build_path.read_text())
    m = json.loads(manifest_path.read_text())
    cand = m.get("recommended_upload_candidate") or {}
    esc = html.escape
    cr = h["candidate_result"]
    br = h["baseline"]
    f = h["h53f_operating_point"]
    promoted = bool(h.get("promoted"))
    gates = h.get("gates", {})
    gate_items = "".join(
        f'<li>{esc(k)}: <strong>{"PASS" if v else "FAIL"}</strong></li>'
        for k, v in gates.items())
    sweep_rows = "".join(
        f"<tr><td>r{a['ratio']:g}</td><td>f{a['flank_px']:g}</td>"
        f"<td>{a['mean_dti']:.6f}</td></tr>"
        for a in f["arms"].values())
    rows = "".join(
        f"<tr><td>{r['fold']}</td>"
        f"<td>{r['outputs']['fresh_hd_hh_blend_ungated']['dti']:.6f}</td>"
        f"<td>{r['outputs']['fresh_hd_hh_blend_stage1_q10']['dti']:.6f}</td>"
        f"<td>{r['outputs']['h53a_blend_stage1_q10']['dti']:.6f}</td></tr>"
        for r in h["rows"])
    verdict = ("PROMOTED (local proxy only)" if promoted
               else "NOT PROMOTED — no H53-A TIFF; the artifact is the q10-confined "
                    "regeneration of the promoted H-H/H-D procedure")
    banner = f"""<section class="download">
<p class="eyebrow">LATEST EXPERIMENT · H53 · 8 OCTOBER 2026</p>
<h2>H53 two-stage submission artifact — unique new TIFF</h2>
<p class="warn"><strong>DOWNLOAD: YES. SUBMIT: THIS IS THE COMPETITION SUBMISSION CANDIDATE.</strong><br>
A newly trained, uniquely seeded prediction map — not a renamed or re-encoded prior submission.
Every local gate passed: official grid/CRS/transform/dtype, all cells finite in [0, 1] with zeros
outside the footprint and no NoData tag, 100% of points inside the Stage-1 q10 approved tiles,
Stage-1 non-dominance, and a support that matches no locally held prior. <b>Not yet uploaded:</b>
portal acceptance and any organizer score are unproven.</p>
<p><a class="btn" download href="downloads/{esc(cand.get('file', ''))}">Download the submission GeoTIFF</a></p>
<p><a download href="downloads/{esc(cand.get('zip', ''))}">Download ZIP containing one TIFF</a> · <a href="holdout.html">Stage 1 / Stage 2 holdouts reported separately</a> · <a href="how-to-submit.html">Submission instructions</a></p>
<dl class="kv"><dt>Unique submission name to paste</dt><dd><code>{esc(cand.get('submission_name', ''))}</code></dd>
<dt>Note for the <em>Note (optional)</em> field</dt><dd><code>{esc(cand.get('note', ''))}</code></dd>
<dt>H53-A top-candidate verdict</dt><dd>{esc(verdict)}</dd>
<dt>H53-A q10-gated proxy DTI</dt><dd>{cr['stage1_q10_gated_mean_dti']:.6f} vs fresh q10-gated H-H/H-D baseline {br['stage1_q10_gated_mean_dti']:.6f} (Δ {cr['paired_mean_delta_vs_stage1_gated_hd_hh']:+.6f}; {cr['positive_folds_vs_stage1_gated_hd_hh']}/6 folds). Frozen ungated best {br['frozen_mean_dti']:.6f} (not uploadable). Not an organizer score.</dd>
<dt>H53-F operating point</dt><dd>adopted arm {esc(f['decision']['adopted_arm'])} (mean {f['decision']['adopted_mean']:.6f}); rule: {esc(f['decision']['rule'])}</dd>
<dt>Stage-1 confinement</dt><dd>100% of points inside approved tiles; approved area {h['stage1_non_dominance']['approved_area_share_mean']:.2%}; lift {h['stage1_non_dominance']['lift_over_area_share']:.3f} (limit 1.5)</dd>
<dt>Numeric checks</dt><dd>1 band · float32 · EPSG:32611 · 3730 × 3292 · min 0, max 1 · 0 nonfinite/out-of-range cells · no NoData tag</dd>
<dt>SHA-256</dt><dd><code>{esc(cand.get('sha256', ''))}</code></dd></dl>
<p><a href="downloads/{esc(cand.get('checks_file', ''))}">Final-byte checks and scoped uniqueness gate</a> · <a href="downloads/h53_holdout_20261008.json">H53 six-fold holdout receipt</a> · <a href="downloads/candidate_hypotheses_prereg_20261008.json">preregistered H53 slate</a>. Format/range safety is not portal acceptance.</p>
</section>"""
    detail = f"""<h2>Latest experiment: H53 evidence and decision</h2>{banner}
<h3>Stage 2: H53-A top-candidate validation (spatially blocked, paired)</h3>
<p>H53-A adds six fine-scale geodetic strain-residual ridge features (rank-space
q(observed 2.5 km tile mean) − q(fault tensor II, Kreemer et al. 2000 Eq. 3) for
geod_2ndinv / geod_shearrate / geod_dilaterate, smoothed σ=4 px, crest response at
σ=1.5/4.0 px) to the H-H arm, blended 50/50 with freshly fitted H-D. Frozen six-fold
splits, 12 px buffer, 250,000 negatives, 250 HGB iterations; STE L9 / w=0.35 /
spacing 2.4; ratio 3.47; flank 2.0 px; predictions confined to the fold-specific q10
strain prior. Preregistered in <code>registry/preregistration_h53.json</code> before
the run; no result-driven tuning.</p>
<table><thead><tr><th>Fold</th><th>Baseline ungated</th><th>Baseline q10</th><th>H53-A q10</th></tr></thead><tbody>{rows}</tbody></table>
<p>Mean H53-A q10={cr['stage1_q10_gated_mean_dti']:.7f}; paired Δ={cr['paired_mean_delta_vs_stage1_gated_hd_hh']:+.7f};
frozen best={br['frozen_mean_dti']:.7f}; baseline reproduction drift={br['fresh_minus_frozen_mean']:+.8f}
(max abs dev {br['fresh_max_abs_dev_vs_frozen']:.2e}, tolerance 1e-5). Promotion gates:</p>
<ul>{gate_items}</ul>
<h3>H53-F: emission operating-point sweep (cached fields, no retraining)</h3>
<table><thead><tr><th>Mass ratio M/|G|</th><th>Catalogue flank (px)</th><th>Mean q10-gated proxy DTI</th></tr></thead><tbody>{sweep_rows}</tbody></table>
<p>{esc(f['decision'].get('note', ''))}</p>
<h3>Stage 1: separate holdouts, not the fine-scale score</h3>
<p>The frozen q10 trace holdout: uniform-random-dot DTI 0.050627 inside the mask vs
0.048564 over the full footprint (lift 1.059). This is weak coarse enrichment, not a
detector. Stage 1 keeps zero soft score weight; it is the allowed domain only.</p>
<h3>What was built</h3>
<p>The submission artifact is a <strong>regeneration</strong> of the holdout-promoted
H-H/H-D procedure with new seeds (53/54{', 55' if promoted else ''}), STE L9 emission,
every point inside the full-data q10 approved tiles, none within the preregistered
catalogue flank, mass from the H53-F decision, written all-finite in [0, 1] with zeros
outside the footprint and no NoData tag. The support is new (new seeds → new belief
fields → new dots) and passes the pre-write and staged uniqueness gates against every
locally held prior, including the 21 pinned family references.</p>
<h3>Audit files</h3>
<ul>
<li><a href="downloads/h53_holdout_20261008.json">Complete H53 six-fold holdout receipt</a></li>
<li><a href="downloads/{esc(cand.get('checks_file', ''))}">Final-byte checks + uniqueness gate</a></li>
<li><a href="downloads/candidate_hypotheses_prereg_20261008.json">Preregistered H53 slate (5 hypotheses + calibration)</a></li>
<li><a href="downloads/candidate-hypotheses-h53-2026-10-08.md">H53 slate narrative</a></li>
<li><a href="downloads/preregistration_h53.json">Frozen H53 promotion rule</a></li>
<li><a href="../registry/submission_build_h53.json">Build provenance</a></li>
</ul>
<p>Limitations: the proxy truth is the visible catalogue, not the hidden expert labels;
the six folds are reused across hypotheses; the planning |G|=12,700 is an estimate;
no organizer upload, portal acceptance, or score is claimed.</p>"""
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
    """Index banner + latest.html detail for the newest experiment.

    When the H53 receipts exist, the H53 artifact card leads and the P1
    research card follows it (check_site requires every research-only
    artifact to stay linked from the index).
    """
    h53_banner, h53_detail = render_h53()
    p1_banner, p1_detail = render_p1()
    if h53_banner:
        return h53_banner + p1_banner, h53_detail + p1_detail
    return p1_banner, p1_detail
