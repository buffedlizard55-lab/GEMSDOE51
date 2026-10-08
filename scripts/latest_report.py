"""Render the latest experiment from measured JSON; no fabricated score fallbacks."""

from pathlib import Path
import json, html

ROOT = Path(__file__).resolve().parents[1]


def _render_h53_k2x():
    artifact = json.loads((ROOT / "evidence/h53_k2x_artifact_20261008.json").read_text())
    hold = json.loads((ROOT / "evidence/h53_k2x_holdout_20261008.json").read_text())
    esc = html.escape
    fmt = artifact["format"]
    checks = fmt["checks"]
    result = hold["candidate_result"]
    baseline = hold["baseline"]
    stage1 = hold["stage1_holdout"]
    domain = stage1["spatial_fold_q10_domain"]
    stage1_ref = json.loads((ROOT / "evidence/official_vector_budget_20261007.json").read_text())["holdout"]
    uniq = artifact["uniqueness"]
    current = artifact["current_inventory_uniqueness"]
    family = artifact["family_inventory_uniqueness"]
    fold_rows = []
    for row in hold["rows"]:
        out = row["outputs"]
        base_u = out["fresh_hd_hh_blend_ungated"]["dti"]
        cand_u = out["h53_k2x_blend_ungated"]["dti"]
        base_q = out["fresh_hd_hh_blend_stage1_q10"]["dti"]
        cand_q = out["h53_k2x_blend_stage1_q10"]["dti"]
        fold_rows.append(
            f"<tr><td>{row['fold']}</td><td>{base_u:.6f}</td><td>{cand_u:.6f}</td>"
            f"<td>{base_q:.6f}</td><td>{cand_q:.6f}</td><td>{cand_q-base_q:+.6f}</td></tr>"
        )
    area_rows = []
    for i, (area, lift) in enumerate(zip(domain["approved_area_share_by_fold"],
                                         domain["implied_lift_by_fold"])):
        area_rows.append(f"<tr><td>{i}</td><td>{area:.4%}</td><td>{lift:.4f}</td></tr>")
    submission_name = esc(artifact["submission_name"])
    note = esc(artifact["note"])
    filename = esc(artifact["file"])
    zipname = esc(artifact["zip"])
    checksname = esc(artifact["checks_file"])
    sha = esc(artifact["sha256"])
    gated_mean = result["stage1_q10_gated_mean_dti"]
    baseline_gated = baseline["stage1_q10_gated_mean_dti"]
    delta = result["paired_mean_delta_vs_stage1_gated_hd_hh"]
    frozen = baseline["frozen_mean_dti"]
    gap_below_frozen = frozen - gated_mean
    banner = f"""<section class="download missing">
<p class="eyebrow">LATEST EXPERIMENT · H53-K2x · 8 OCTOBER 2026</p>
<h2>New, independently generated research TIFF</h2>
<p class="warn"><strong>DOWNLOAD FOR RESEARCH: YES. SUBMIT TO THE COMPETITION: NO.</strong><br>
The preregistered candidate failed its frozen promotion rule. The artifact is a fresh model output, not a renamed prior raster. No competition slot was used; no organizer score or portal acceptance is claimed.</p>
<p><a class="btn" download href="downloads/{filename}">Download H53-K2x research TIFF</a></p>
<p><a download href="downloads/{zipname}">Download one-TIFF ZIP</a> · <a href="latest.html">Results and checks</a> · <a href="how-to-submit.html">How to submit (currently blocked)</a></p>
<dl class="kv"><dt>Unique label (research only)</dt><dd><code>{submission_name}</code></dd>
<dt>Short comment</dt><dd><code>{note}</code></dd>
<dt>Local final-byte checks</dt><dd>one float32 band · EPSG:32611 · {fmt['shape'][1]} × {fmt['shape'][0]} · min {checks['min_value']:g}, max {checks['max_value']:g} · {checks['global_invalid_cells']} nonfinite/out-of-range cells · zeros outside · no NoData tag. These local checks do not establish portal acceptance.</dd>
<dt>Stage-2 q10 proxy</dt><dd>{gated_mean:.6f} vs same-fold gated H-D/H-H baseline {baseline_gated:.6f}; Δ {delta:+.6f}, {result['positive_folds_vs_stage1_gated_hd_hh']}/6 folds. Frozen best {frozen:.6f}; candidate is {gap_below_frozen:.6f} below it. Fresh baseline drift {baseline['fresh_minus_frozen_mean']:+.8f} exceeded 1e-5; <b>NOT PROMOTED</b>.</dd>
<dt>Stage-1 domain</dt><dd>q10 approves {artifact['stage1']['approved_area_share']:.2%} of the footprint; {artifact['stage1']['points_inside_approved']:,}/{artifact['stage1']['emitted_points']:,} points lie inside. This is a broad hard domain, not Stage-2 score credit.</dd>
<dt>Uniqueness</dt><dd>Current local inventory {esc(current['verdict'])} ({current['comparisons']} comparisons); committed-family gate {esc(family['verdict'])}, not a global proof. Exact family duplicate={family['exact_duplicate']}; full receipt linked below.</dd>
<dt>SHA-256</dt><dd><code>{sha}</code></dd></dl>
<p><a href="downloads/{checksname}">Checks and artifact receipt</a>. <strong>NOT FOR SUBMISSION.</strong></p>
</section>"""
    detail = f"""<h2>Latest experiment: H53-K2x structure-conditioned conductive-ribbon anisotropy</h2>
{banner}
<h3>Stage 2 — preregistered six-fold spatial holdout</h3>
<p>The target remains fault pixels absent from the supplied catalogue, not geothermal-vent probability. H53-K2x adds one fixed, label-free feature from the rank-prepared conductivity surface, basement depth, gravity anomaly, and total magnetic intensity. At σ=2 and 5 px it estimates an unoriented independent structural edge axis, projects conductivity-gradient energy into edge-normal and edge-parallel components, weights the positive cross-edge contrast by structural-edge coherence, normalizes the two scales, and takes their pixelwise minimum. No feature threshold or scale was tuned after seeing results. The exact definition is frozen in the <a href="downloads/candidate_hypotheses_prereg_20261008.json">preregistration</a>.</p>
<p>Protocol: six contiguous 3×3 spatial folds; 12 px training buffer; 250,000 negatives; fixed fold seeds; HGB 250 iterations; 3.47 matched point-mass ratio; 50/50 fresh H-D plus H-H+K2x; STE scales 1/2/3.5 px, L9, continuity 0.35, spacing 2.4 px. The metric is a visible-known-catalogue proxy, not hidden organizer truth.</p>
<table><thead><tr><th>Fold</th><th>Baseline ungated</th><th>K2x ungated</th><th>Baseline q10</th><th>K2x q10</th><th>Paired q10 Δ</th></tr></thead><tbody>{''.join(fold_rows)}</tbody></table>
<p>Fresh ungated baseline mean {baseline['fresh_ungated_mean_dti']:.7f} vs frozen {frozen:.7f}; drift {baseline['fresh_minus_frozen_mean']:+.8f} exceeds the preregistered ±0.00001 tolerance. K2x q10 mean {gated_mean:.7f}, same-fold q10 baseline {baseline_gated:.7f}, paired Δ {delta:+.7f}, {result['positive_folds_vs_stage1_gated_hd_hh']}/6 folds higher. K2x is {gap_below_frozen:.7f} below the frozen local best, so it fails promotion independently of baseline reproducibility. <b>No tuning, slot, or organizer score.</b></p>
<h3>Stage 1 — separate trace holdout and broad-domain audit</h3>
<p>The source-corrected official-vector five-whole-trace holdout approved mean area {stage1_ref['mean_area']:.2%}, with held-out trace recall {stage1_ref['mean_recall']:.2%} and lift {stage1_ref['mean_lift']:.4f}. This is weak broad enrichment only; it is not a fine-scale DTI and is not combined with Stage 2. Its budget retains the recorded slip-unit ambiguity, assumed dips/components, and residual alternatives.</p>
<p>For Stage 2 the q10 mask was recomputed in each spatial fold with held-out trace rows removed. Every fold-specific mask approved more than two-thirds of the footprint; every baseline and candidate point was inside the approved mask. Stage-1 score weight was zero.</p>
<table><thead><tr><th>Fold</th><th>q10 approved area</th><th>Implied lift if all points are confined</th></tr></thead><tbody>{''.join(area_rows)}</tbody></table>
<p>Mean fold-wise area {domain['mean_approved_area_share']:.2%}; implied mean lift {domain['mean_implied_lift_if_all_stage2_points_are_confined']:.4f}. The separate full-map research TIFF has {artifact['stage1']['points_inside_approved']:,}/{artifact['stage1']['emitted_points']:,} points confined and reports its own gate/ungated support overlap in the artifact receipt.</p>
<h3>Input semantics and science limitations</h3>
<p>The local band 17 descriptor says “Conductivity surface — electrical conductivity of subsurface,” but supplies no verified units, depth sensitivity, inversion/source or calibration. Its owner-pinned mirror is hash-verified, not organizer-authenticated. The feature is therefore rank-space only and makes no S/m, depth, fluid, alteration, or geothermal-temperature claim. See the <a href="downloads/h53_k2x_input_audit_20261008.json">input/source audit</a>. Electrical conductivity is non-unique; the cited fault-zone conductor studies are site-specific, and some active faults lack an observed conductor.</p>
<h3>Artifact, local checks, and uniqueness</h3>
<p>The fresh research TIFF contains {checks['predicted_px']:,} binary points; float32; one band; EPSG:32611; exact template transform and shape; all cells finite in [0,1]; zeros outside footprint; no NoData tag. This is a local check only. The official problem page describes null/NaN outside the data bounds; the all-finite zero convention was chosen for local range safety and has <b>not</b> been validated by the portal. <a href="downloads/{checksname}">Final-byte receipt</a> · <a href="downloads/h53_k2x_current_uniqueness_20261008.json">current local inventory</a> · <a href="downloads/h53_k2x_family_uniqueness_20261008.json">54-repository family inventory</a>.</p>
<p>Current local uniqueness passes 8 comparisons (max Jaccard {current['max_support_jaccard']:.4f}, containment {current['max_support_containment']:.4f}). The broader family audit restored 365/365 payloads but is <b>NOT CLEARED</b>: one toy TIFF has a different grid, and several same-grid dense maps fully contain this sparse support (max containment 1.0). No exact duplicate was found; no universal novelty claim is made.</p>
<h3>Source links checked</h3>
<ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official task, feature inventory, metric, and format description</a></li>
<li><a href="https://gdr.openei.org/submissions/1391">GDR 1391 INGENIOUS compilation record</a></li>
<li><a href="https://www.sciencebase.gov/catalog/item/62979746d34ec53d276c113b">USGS Great Basin depth-integrated MT conductance release</a> — distinct from the undocumented source of cond_surf</li>
<li><a href="https://pubs.usgs.gov/publication/70204785">USGS Great Basin MT + structural/geochemical case studies</a> — context, not validation of this operator</li></ul>
<p>Receipts: <a href="downloads/h53_k2x_holdout_20261008.json">six-fold Stage-2 / separate Stage-1 holdout</a>, <a href="downloads/h53_k2x_feature_build_20261008.json">feature build</a>, <a href="downloads/h53_k2x_pretest_lock_20261008.json">pretest freeze</a>, <a href="downloads/candidate-hypotheses-2026-10-08.md">ranked hypothesis slate and outcome</a>, and <a href="downloads/review-three-passes-20261008.md">three-pass review/recheck</a>. No upload, slot use, portal acceptance, hidden score, or vent-prediction claim is made.</p>"""
    return banner, detail


def render():
    if (ROOT / "evidence/h53_k2x_artifact_20261008.json").exists():
        return _render_h53_k2x()
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
