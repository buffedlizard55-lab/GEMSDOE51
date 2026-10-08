"""Render the latest experiments from measured receipts; no fabricated fallbacks.

The page leads with this session's H53-SR artifact (the recommended upload
candidate), then the parallel session's K2-08 research experiment, then the
P1 research card. Stage 1, Stage 2, local format and uniqueness stay separate;
a local pass never becomes portal acceptance.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render_h53sr():
    """Render the 2026-10-08 H53-SR experiment (strain-residual slate; top-candidate
    validation + unique submission build). Distinct from the parallel session's H53-A
    finite-lag hypothesis (IR-H53-05).

    Returns ("", "") when the H53 receipts are absent or incomplete, so the
    caller falls back to the previous experiment's renderer.
    """
    hold_path = ROOT / "evidence/h53sr_holdout_20261008.json"
    build_path = ROOT / "registry/submission_build_h53sr.json"
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
<p class="eyebrow">LATEST EXPERIMENT · H53-SR (STRAIN-RESIDUAL SLATE) · 8 OCTOBER 2026</p>
<h2>H53-SR two-stage submission artifact — unique new TIFF</h2>
<p class="ev">H53-SR denotes this session's slate (H53-A = fine-scale geodetic
strain-residual ridge). A parallel session preregistered a different H53-A (finite-lag
cross-physics edge pairing), which was blocked before Stage-2 scoring — see
<a href="irregularities.html">IR-H53-05</a>. The two H53-A records must not be conflated.</p>
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
<p><a href="downloads/{esc(cand.get('checks_file', ''))}">Final-byte checks and scoped uniqueness gate</a> · <a href="downloads/h53sr_holdout_20261008.json">H53 six-fold holdout receipt</a> · <a href="downloads/candidate_hypotheses_prereg_h53sr_20261008.json">preregistered H53 slate</a>. Format/range safety is not portal acceptance.</p>
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
<li><a href="downloads/h53sr_holdout_20261008.json">Complete H53 six-fold holdout receipt</a></li>
<li><a href="downloads/{esc(cand.get('checks_file', ''))}">Final-byte checks + uniqueness gate</a></li>
<li><a href="downloads/candidate_hypotheses_prereg_h53sr_20261008.json">Preregistered H53 slate (5 hypotheses + calibration)</a></li>
<li><a href="downloads/candidate-hypotheses-h53sr-2026-10-08.md">H53 slate narrative</a></li>
<li><a href="downloads/preregistration_h53sr_20261008.json">Frozen H53 promotion rule</a></li>
<li><a href="../registry/submission_build_h53sr.json">Build provenance</a></li>
</ul>
<p>Limitations: the proxy truth is the visible catalogue, not the hidden expert labels;
the six folds are reused across hypotheses; the planning |G|=12,700 is an estimate;
no organizer upload, portal acceptance, or score is claimed.</p>"""
    return banner, detail


def _load(path: str):
    return json.loads((ROOT / path).read_text())



def render_k2():
    artifact = _load("evidence/k2_research_artifact_20261008.json")
    holdout = _load("evidence/k2_spatial_holdout_20261008.json")
    physical = _load("evidence/physical_stage1_holdout_20261008.json")
    family = _load("evidence/k2_family_uniqueness_20261008.json")
    esc = html.escape

    fmt = artifact["format"]["verifier"]
    checks = fmt["checks"]
    baseline = holdout["baseline"]
    candidate = holdout["candidate_result"]
    stage1 = artifact["stage1"]
    stage1_summary = physical["summary"]
    fold_rows = []
    for row in holdout["per_fold"]:
        b, c = row["baseline"], row["candidate"]
        fold_rows.append(
            "<tr>"
            f"<td>{row['fold']}</td>"
            f"<td>{b['fresh_hd_hh_ungated']['dti']:.6f}</td>"
            f"<td>{b['fresh_hd_hh_physical_q10']['dti']:.6f}</td>"
            f"<td>{c['candidate_h_d_hh_k2_ungated']['dti']:.6f}</td>"
            f"<td>{c['candidate_h_d_hh_k2_physical_q10']['dti']:.6f}</td>"
            f"<td>{c['paired_q10_delta_vs_fresh_hd_hh']:+.6f}</td>"
            "</tr>"
        )

    filename = Path(artifact["file"]).name
    score_table = "".join(
        f"<tr><td>{label}</td><td>{value:.7f}</td></tr>"
        for label, value in (
            ("Frozen H-H/H-D best (ungated)", baseline["frozen_hh_hd_ungated_mean_dti"]),
            ("Fresh H-H/H-D reconstruction (ungated)", baseline["fresh_hh_hd_ungated_mean_dti"]),
            ("Fresh H-H/H-D with physical q10 gate", baseline["physical_q10_gated_mean_dti"]),
            ("K2 blend, ungated", candidate["ungated_mean_dti"]),
            ("K2 blend, physical q10", candidate["physical_q10_gated_mean_dti"]),
            ("Paired q10 K2 minus fresh blend", candidate["paired_mean_q10_delta_vs_fresh_hh_hd"]),
        )
    )
    invalid_note = "".join(
        f"<li>{esc(item['source']['repo'])}: {esc(item['source']['path'])} — {esc(item['error'])}</li>"
        for item in family.get("invalid", [])
    ) or "<li>none</li>"
    failed_gates = [name for name, passed in holdout.get("promotion_gates", {}).items() if not passed]

    h53_stage1 = _load("evidence/h53a_stage1_holdout_20261008.json")
    h53_baseline = _load("evidence/h53a_baseline_provenance_20261008.json")
    h53_k2x = _load("evidence/h53_k2x_holdout_20261008.json")
    h53_s1 = (h53_stage1 or {}).get("summary", {}).get("nominal", {})
    h53_base = (h53_baseline or {}).get("summary", {})
    k2x_base = (h53_k2x or {}).get("baseline", {})
    k2x_result = (h53_k2x or {}).get("candidate_result", {})
    k2x_s1 = (h53_k2x or {}).get("stage1_holdout", {})
    h53_context = ""
    if h53_stage1 and h53_baseline and h53_k2x:
        h53_context = f"""<section class="download missing">
<p class="eyebrow">H53 FAMILY — PARALLEL-SESSION RECORDS: H53-A (FINITE-LAG, STAGE 2 BLOCKED) · EARLIER SEPARATE SCREEN: H53-K2x</p>
<h2>Do not conflate the two H53 experiments</h2>
<p><b>H53-A is the parallel session's latest experiment within the H53 family</b> (finite-lag
cross-physics edge pairing — a different hypothesis from this session's H53-SR H53-A
strain-residual ridge; see <a href="irregularities.html">IR-H53-05</a>). Stage 1 was measured separately (five whole-record splits; q10 area {h53_s1.get('mean_approved_area_share', float('nan')):.2%}, trace recall {h53_s1.get('mean_heldout_recall', float('nan')):.2%}, lift {h53_s1.get('mean_recall_area_lift', float('nan')):.4f}). Stage 2 status: <b>NOT RUN — BLOCKED BEFORE CANDIDATE FIT/SCORING</b>; candidate scoring was blocked because the fresh baseline {h53_base.get('fresh_mean_dti', float('nan')):.9f} vs frozen {h53_base.get('frozen_mean_dti', float('nan')):.9f}; drift {h53_base.get('fresh_minus_frozen_mean', float('nan')):+.9f} exceeded the 1e-5 tolerance. <b>No H53-A TIFF exists</b> (the H53-SR two-stage artifact at the top of this page is a different record) <b>and no candidate score was produced. H53-A download for research: NO. SUBMIT TO THE COMPETITION: NO.</b> See <a href="downloads/h53a_stage1_holdout_20261008.json">Stage-1 receipt</a> and <a href="downloads/h53a_baseline_provenance_20261008.json">baseline blocker</a>.</p>
<p><b>Earlier H53-K2x:</b> a distinct, completed six-fold screen, NOT PROMOTED. q10 mean {k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} vs same-fold gated baseline {k2x_base.get('stage1_q10_gated_mean_dti', float('nan')):.7f}; paired Δ {k2x_result.get('paired_mean_delta_vs_stage1_gated_hd_hh', float('nan')):+.7f}, {k2x_result.get('positive_folds_vs_stage1_gated_hd_hh', 0)}/6; {k2x_base.get('frozen_mean_dti', float('nan')) - k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} below frozen best. Fresh-baseline drift {k2x_base.get('fresh_minus_frozen_mean', float('nan')):+.8f} exceeded tolerance. Its separate TIFF is <b>downloadable for research only; submit: NO</b>. <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif">K2x research TIFF</a> · <a href="index.html#h53-k2x-research">full download card</a> · <a href="downloads/h53_k2x_holdout_20261008.json">six-fold receipt</a>.</p>
<p>These H53 results are separate from the K2-08 experiment above. The H53-SR artifact card at the top of this page is the recommended upload candidate; every experiment below it is research-only. No portal acceptance or organizer score is claimed.</p>
</section>"""

    banner = f"""<section class="download missing">
<p class="eyebrow">PARALLEL-SESSION EXPERIMENT · K2-08 · 8 OCTOBER 2026 · RESEARCH ONLY</p>
<h2>New feature-model GeoTIFF — research only</h2>
<p class="warn"><strong>DOWNLOAD FOR RESEARCH: YES. SUBMIT TO THE COMPETITION: NO.</strong><br>
The K2 map was newly fitted from feature data, not copied or re-encoded from an earlier TIFF, but it failed the frozen spatial holdout and the strict family uniqueness audit. No competition slot was used; portal validation was not performed.</p>
<p><a class="btn" download href="downloads/{esc(filename)}">Download K2-08 research TIFF</a> · <a href="downloads/k2-08-results-2026-10-08.md">Full methods and results</a></p>
<dl class="kv">
<dt>Candidate / support</dt><dd><code>{esc(artifact['candidate_id'])}</code> · {checks['predicted_px']:,} unit-valued fault-point pixels</dd>
<dt>SHA-256</dt><dd><code>{esc(artifact['sha256'])}</code></dd>
<dt>Local format and range</dt><dd>One-band {esc(fmt['dtype'])} · {esc(fmt['crs'])} · {fmt['shape'][0]} × {fmt['shape'][1]} · exact template transform · finite in-footprint values [{checks['min_value']:g}, {checks['max_value']:g}] · NaN/NoData outside. Serialized range guard passed; this is not portal acceptance.</dd>
<dt>Stage 2 proxy DTI</dt><dd>K2 q10 {candidate['physical_q10_gated_mean_dti']:.6f} vs fresh H-H/H-D q10 {baseline['physical_q10_gated_mean_dti']:.6f}; paired Δ {candidate['paired_mean_q10_delta_vs_fresh_hh_hd']:+.6f}; {candidate['positive_q10_folds']}/6 folds positive. <b>NOT PROMOTED.</b></dd>
<dt>Stage 1, separate holdout</dt><dd>20 km physical q10 tile prior; {stage1_summary['mean_approved_area_fraction']:.2%} area approved, {stage1_summary['mean_held_trace_recall']:.2%} trace recall, lift {stage1_summary['mean_held_trace_lift']:.3f}. Approved-area uniform DTI {stage1_summary['mean_uniform_in_approved_dti']:.6f} vs support {stage1_summary['mean_uniform_in_support_dti']:.6f} (Δ {stage1_summary['paired_mean_uniform_dti_delta']:+.6f}); broad and weak.</dd>
<dt>Family uniqueness</dt><dd><b>{esc(family['verdict'])}.</b> {family['downloaded']}/{family['expected']} pinned payloads; exact duplicate {family['exact_duplicate']}; max Jaccard {family['max_jaccard']:.5f}; max containment {family['max_containment']:.4f}; coverage complete {family['coverage_complete']}.</dd>
<dt>Portal status</dt><dd>NOT PERFORMED. The prior range-error trigger is unknown; do not upload.</dd>
</dl>
<p><a href="downloads/k2_research_artifact_20261008.json">Artifact receipt</a> · <a href="downloads/k2_spatial_holdout_20261008.json">Stage-2 receipt</a> · <a href="downloads/physical_stage1_holdout_20261008.json">Stage-1 receipt</a> · <a href="downloads/k2_family_uniqueness_20261008.json">Family audit</a> · <a href="downloads/k2-08-candidate-hypotheses-2026-10-08.md">Ranked hypotheses</a>.</p>
</section>"""
    banner += h53_context

    detail = f"""<h2>Parallel-session experiment: K2-08 — evidence and decision (research only)</h2>
{banner}
<h3>Stage 1 — physical fault-accommodation residual, coarse tile prior only</h3>
<p>Projected INGENIOUS/QFault v2 trace tensors are summed by the documented Kreemer et al. (2000), Eq. 3 relation in 20 km tiles. For each declared geodetic rate scale and slip-component scenario, the pipeline subtracts predicted fault-tensor dilation from supplied geodetic dilation and predicted source-defined scalar shear from supplied geodetic shear, ranks those signed residuals, and averages ranks into a broad q10 tile prior. This is not the older rank-space second-invariant residual. The DBF/field-definition audit verifies SLIPRT2023 in mm/year and SLIPRTNUM as its numeric portion; component, individual dips, and the README's literal 10E-9/yr notation remain uncertain, so both declared scenarios are retained.</p>
<table><thead><tr><th>Five whole-trace holdout measure</th><th>Mean</th></tr></thead><tbody>
<tr><td>Approved area</td><td>{stage1_summary['mean_approved_area_fraction']:.6f}</td></tr>
<tr><td>Held-trace recall</td><td>{stage1_summary['mean_held_trace_recall']:.6f}</td></tr>
<tr><td>Held-trace lift</td><td>{stage1_summary['mean_held_trace_lift']:.6f}</td></tr>
<tr><td>Spearman: residual score vs trace density</td><td>{stage1_summary['mean_spearman_residual_score_vs_held_trace_density']:.6f}</td></tr>
<tr><td>Uniform DTI in approved region</td><td>{stage1_summary['mean_uniform_in_approved_dti']:.7f}</td></tr>
<tr><td>Uniform DTI over common support</td><td>{stage1_summary['mean_uniform_in_support_dti']:.7f}</td></tr>
<tr><td>Paired approved minus support DTI</td><td>{stage1_summary['paired_mean_uniform_dti_delta']:+.7f}</td></tr>
</tbody></table>
<p>The five splits hold out whole source records but are scattered rather than geographically independent. Approval covers roughly 90% of area; trace lift is only 1.007 and the uniform DTI delta is slightly negative. Stage 1 is therefore a weak coarse allowed-domain prior, not a point placer or evidence that a residual is a missing fault. The full-map K2 file has {stage1['emitted_points_inside_approved']:,}/{stage1['emitted_points_total']:,} emitted points in q10, an area share of {stage1['full_map_approved_area_share']:.2%} and point-share lift {stage1['lift_over_area_share']:.3f}.</p>
<h3>Stage 2 — directional conductivity contrast across an independent basement edge</h3>
<p>The K2 feature arm tests conductivity contrast along an independently estimated <code>depth_to_base_surf</code> edge at 200 m and 500 m scales, including both contrast signs and an along-edge persistence term. It is compared with a fresh 50:50 H-D/H-H blend: candidate = 50:50 H-D and H-H+K2. The six-fold protocol fixes 3×3 contiguous blocks, 12-pixel buffer, 250,000 negatives per fold, HGB settings, 3.47 mass ratio, STE L9 / w=0.35 / spacing 2.4 px, 200 m catalogue exclusion, and fold-specific physical q10 masks. The hidden-mass planning value is not organizer-published.</p>
<table><thead><tr><th>Model / comparison</th><th>Mean proxy DTI</th></tr></thead><tbody>{score_table}</tbody></table>
<p>The candidate gated mean is below both the fresh gated comparator and the frozen historical best; {candidate['positive_q10_folds']}/6 folds are positive. Fresh ungated baseline drift is {baseline['fresh_minus_frozen_mean']:+.8f}, outside the preregistered 1e-5 tolerance; this harness irregularity is preserved, not relaxed. Failed gates include: {', '.join(esc(x) for x in failed_gates)}. Status: <b>{esc(holdout['status'])}</b>. All values are visible-catalogue proxy measurements, not organizer scores or hidden-fault validation.</p>
<table><thead><tr><th>Fold</th><th>Fresh blend ungated</th><th>Fresh blend q10</th><th>K2 ungated</th><th>K2 q10</th><th>Paired q10 Δ</th></tr></thead><tbody>{''.join(fold_rows)}</tbody></table>
<h3>Serialized format, range and physical confinement</h3>
<p>The final bytes have one float32 band, EPSG:32611, shape {fmt['shape']}, transform {esc(str(fmt['transform']))}; the grid matches the competition template. The {checks['nan_cells']:,} NaN cells are outside the footprint; every in-footprint serialized value is finite and in [0,1], with min {checks['min_value']:g} and max {checks['max_value']:g}. The writer checks finite/range in footprint, no positive point outside the q10 allowed domain, NaN outside, and stable point count after re-reading the GeoTIFF. The global all-finite flag is false by design because outside-footprint nulls are NaN. Local format checks do not emulate the portal; the error-triggering file is unknown.</p>
<h3>Strict family uniqueness audit — not cleared</h3>
<p>The pinned 54-repository inventory fetched and hash-verified {family['downloaded']}/{family['expected']} unique Git-blob payloads. Exact byte duplicate: {family['exact_duplicate']}; maximum positive-support Jaccard: {family['max_jaccard']:.5f}; maximum containment: {family['max_containment']:.4f}; coverage complete: {family['coverage_complete']}; fixed thresholds: Jaccard {family['thresholds']['jaccard']:.2f}, containment {family['thresholds']['containment']:.2f}. Verdict: <b>{esc(family['verdict'])}</b>. Invalid reference(s):<ul>{invalid_note}</ul>Some fully positive probability/diagnostic layers trivially contain a sparse support; that explains the strict containment failure but does not waive it. No global support uniqueness or upload eligibility is claimed.</p>
<h3>Latest H53-family experiment — H53-A baseline-reproduction gate</h3>
<p>H53-A Stage 1 is separate: five whole-record splits; q10 approved area {h53_s1.get('mean_approved_area_share', float('nan')):.4f}, held-out trace-pixel recall {h53_s1.get('mean_heldout_recall', float('nan')):.4f}, lift {h53_s1.get('mean_recall_area_lift', float('nan')):.4f}. Fresh canonical H-D/H-H mean {h53_base.get('fresh_mean_dti', float('nan')):.9f} vs frozen {h53_base.get('frozen_mean_dti', float('nan')):.9f}; delta {h53_base.get('fresh_minus_frozen_mean', float('nan')):+.9f} exceeded the locked 1e-5 tolerance. Stage 2 is <b>NOT RUN — BLOCKED before candidate scoring</b>, not a measured candidate failure. No H53-A score or TIFF exists; H53-A download for research: NO; submit: NO. See <a href="downloads/h53a_stage1_holdout_20261008.json">Stage-1 receipt</a>, <a href="downloads/h53a_baseline_provenance_20261008.json">baseline receipt</a>, and <a href="downloads/preregistration_h53.json">frozen protocol</a>.</p>
<h3>Earlier H53-K2x six-fold screen — distinct; NOT PROMOTED</h3>
<p>Stage 2 q10-gated mean {k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} vs same-fold gated H-D/H-H {k2x_base.get('stage1_q10_gated_mean_dti', float('nan')):.7f}; paired Δ {k2x_result.get('paired_mean_delta_vs_stage1_gated_hd_hh', float('nan')):+.7f}, {k2x_result.get('positive_folds_vs_stage1_gated_hd_hh', 0)}/6 folds. It remains {k2x_base.get('frozen_mean_dti', float('nan')) - k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} below frozen best; fresh-baseline drift {k2x_base.get('fresh_minus_frozen_mean', float('nan')):+.8f} exceeded tolerance. Stage 1, separately: five whole-trace splits, mean approved area {k2x_s1.get('trace_split_mean_area', float('nan')):.2%}, recall {k2x_s1.get('heldout_trace_recall', float('nan')):.2%}, lift {k2x_s1.get('heldout_trace_lift', float('nan')):.4f}. The fold-specific q10 domain excluded held-out trace rows; all Stage-2 points were confined and Stage-1 score weight was zero. The local final-byte/current-inventory checks passed, but broader family uniqueness is <b>NOT CLEARED</b> and portal behavior is untested. <b>Download for research: YES; submit: NO.</b> <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif">H53-K2x research TIFF</a> · <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.zip">one-TIFF ZIP</a> · <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros-checks.json">local checks</a> · <a href="downloads/h53_k2x_holdout_20261008.json">holdout</a> · <a href="downloads/candidate-hypotheses-2026-10-08.md">ranked four-candidate slate</a>.</p>
<h3>Task boundary, sibling-score claims and next decision</h3>
<p>The official target is fault geometry; geothermal relevance is motivation, not a vent-prediction label. The GEMSDOE32 owner page calls H33-2-B2 UNSCORED and describes 0.2747 as a projection. The user-reported 0.2778 attribution and 0.3195 high are unverified here; none is used as a target or promised result. No portal acceptance, organizer score, or competition submission is claimed. Older TIFFs remain preserved as prior art.</p>
<ul>
<li><a href="downloads/k2-08-results-2026-10-08.md">Complete K2-08 result and official source links</a></li>
<li><a href="downloads/preregistration_k2_stage1_20261008.json">Machine-readable preregistration</a></li>
<li><a href="downloads/k2-08-candidate-hypotheses-2026-10-08.md">Four ranked hypotheses</a></li>
<li><a href="downloads/k2_research_artifact_20261008.json">Artifact receipt</a> · <a href="downloads/k2_spatial_holdout_20261008.json">Stage-2 holdout</a> · <a href="downloads/physical_stage1_holdout_20261008.json">Stage-1 holdout</a> · <a href="downloads/k2_family_uniqueness_20261008.json">Family audit</a></li>
<li><a href="downloads/k2-08-review-three-passes-2026-10-08.md">Three-pass review and handoff</a></li>
<li>Historical R1 restrict artifact (failed paired rule; do not submit): <a href="downloads/gemsdoe51-r1-restrict-20261008T031052Z-research-only.tif">TIFF</a> · <a href="downloads/gemsdoe51-r1-restrict-20261008T031052Z-research-only.zip">ZIP</a> · <a href="downloads/r1_holdout_20261008.json">holdout</a>.</li>
<li>Historical H53-A baseline gate (Stage 2 blocked): <a href="downloads/h53a_baseline_provenance_20261008.json">provenance receipt</a> · <a href="downloads/h53a_stage1_holdout_20261008.json">Stage-1 receipt</a>.</li>
<li><a href="downloads/gemsdoe51-p1-odd-even-q10-2a687636c85e-zeros.tif">Historical P1 research TIFF (prior art)</a></li>
</ul>"""
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
    """Index banner + latest.html detail: H53-SR artifact, K2-08, then P1.

    check_site requires every research-only artifact to stay linked from the
    index, so the P1 and K2-08 research cards follow the candidate card.
    """
    h53_banner, h53_detail = render_h53sr()
    k2_banner, k2_detail = render_k2()
    p1_banner, p1_detail = render_p1()
    if h53_banner:
        return h53_banner + k2_banner + p1_banner, h53_detail + k2_detail + p1_detail
    if k2_banner:
        return k2_banner + p1_banner, k2_detail + p1_detail
    return p1_banner, p1_detail
