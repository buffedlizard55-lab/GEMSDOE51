"""Render the current K2-08 experiment from measured receipts.

The report intentionally keeps Stage 1, Stage 2, local format, and family
uniqueness separate. A local pass never becomes portal acceptance.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str):
    return json.loads((ROOT / path).read_text())


def render():
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
<p class="eyebrow">H53 FAMILY — LATEST EXPERIMENT: H53-A · EARLIER SEPARATE SCREEN: H53-K2x</p>
<h2>Do not conflate the two H53 experiments</h2>
<p><b>H53-A is the latest experiment within the H53 family.</b> Stage 1 was measured separately (five whole-record splits; q10 area {h53_s1.get('mean_approved_area_share', float('nan')):.2%}, trace recall {h53_s1.get('mean_heldout_recall', float('nan')):.2%}, lift {h53_s1.get('mean_recall_area_lift', float('nan')):.4f}). Stage 2 status: <b>NOT RUN — BLOCKED BEFORE CANDIDATE FIT/SCORING</b>; candidate scoring was blocked because the fresh baseline {h53_base.get('fresh_mean_dti', float('nan')):.9f} vs frozen {h53_base.get('frozen_mean_dti', float('nan')):.9f}; drift {h53_base.get('fresh_minus_frozen_mean', float('nan')):+.9f} exceeded the 1e-5 tolerance. <b>No H53-A TIFF exists and no candidate score was produced. H53-A download for research: NO. SUBMIT TO THE COMPETITION: NO.</b> See <a href="downloads/h53a_stage1_holdout_20261008.json">Stage-1 receipt</a> and <a href="downloads/h53a_baseline_provenance_20261008.json">baseline blocker</a>.</p>
<p><b>Earlier H53-K2x:</b> a distinct, completed six-fold screen, NOT PROMOTED. q10 mean {k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} vs same-fold gated baseline {k2x_base.get('stage1_q10_gated_mean_dti', float('nan')):.7f}; paired Δ {k2x_result.get('paired_mean_delta_vs_stage1_gated_hd_hh', float('nan')):+.7f}, {k2x_result.get('positive_folds_vs_stage1_gated_hd_hh', 0)}/6; {k2x_base.get('frozen_mean_dti', float('nan')) - k2x_result.get('stage1_q10_gated_mean_dti', float('nan')):.7f} below frozen best. Fresh-baseline drift {k2x_base.get('fresh_minus_frozen_mean', float('nan')):+.8f} exceeded tolerance. Its separate TIFF is <b>downloadable for research only; submit: NO</b>. <a href="downloads/gemsdoe51-h53-k2x-q10-b9c0adee61ea-zeros.tif">K2x research TIFF</a> · <a href="index.html#h53-k2x-research">full download card</a> · <a href="downloads/h53_k2x_holdout_20261008.json">six-fold receipt</a>.</p>
<p>These H53 results are separate from the later overall K2-08 experiment above. No artifact is cleared for a competition slot, and no portal acceptance or organizer score is claimed.</p>
</section>"""

    banner = f"""<section class="download missing">
<p class="eyebrow">LATEST EXPERIMENT · K2-08 · 8 OCTOBER 2026</p>
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

    detail = f"""<h2>Latest experiment: K2-08 — evidence and decision</h2>
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
