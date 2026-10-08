"""Render the latest H53-A experiment from its measured, versioned receipts."""
from __future__ import annotations

from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> dict:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"Required current H53-A evidence is missing: {rel}")
    return json.loads(path.read_text(encoding="utf-8"))


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{html.escape(str(x))}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def render() -> tuple[str, str]:
    artifact = _read("evidence/h53_artifact_20261008T030347Z.json")
    stage1 = _read("evidence/h53_stage1_holdout_20261008.json")
    stage2 = _read("evidence/h53_stage2_holdout_20261008.json")
    public = _read("evidence/h53_public_uniqueness_20261008.json")
    attr = _read("evidence/official_attribute_audit_20261008.json")

    esc = html.escape
    stage1_primary = stage1["summary"]["fault_plane_1e-08"]["combined_residual_prior"]
    stage1_control = stage1["summary"]["fault_plane_1e-08"]["geodetic_only_control"]
    s2 = stage2["summary"]
    checks = artifact["format"]["checks"]
    broad = artifact["broad_family_uniqueness"]
    local = artifact["local_available_artifact_gate"]
    file = Path(artifact["file"]).name
    zip_name = Path(artifact["zip"]).name
    check_name = file.replace(".tif", "-checks.json")
    fold_rows_s1 = []
    for row in stage1["per_fold"]:
        metric = row["primary_scenario"]["metrics"]["combined_residual_prior"]
        fold_rows_s1.append([
            str(row["fold"]),
            f"{metric['approved_area_share_in_held_block']:.3f}",
            f"{metric['heldout_truth_recall']:.3f}",
            f"{metric['recall_over_area_lift']:.3f}",
            f"{metric['tile_rank_spearman']:+.3f}",
        ])
    fold_rows_s2 = []
    for row in stage2["per_fold"]:
        out = row["outputs"]
        fold_rows_s2.append([
            str(row["fold"]),
            f"{out['fresh_ungated_hh_hd']['dti']:.6f}",
            f"{out['stage1_q10_hh_hd_candidate']['dti']:.6f}",
            f"{out['same_domain_uniform_spaced']['dti']:.6f}",
            f"{row['paired_delta_candidate_minus_ungated']:+.6f}",
            f"{row['stage1']['approved_area_share_in_block']:.3f}",
            f"{row['stage1']['confinement_lift']:.3f}",
        ])

    banner = f"""<section class="download missing">
<p class="eyebrow">LATEST EXPERIMENT · H53-A · 8 OCTOBER 2026</p>
<h2>Fresh H53-A GeoTIFF — RESEARCH ONLY / DO NOT SUBMIT</h2>
<p class="warn"><strong>Download for research and audit only. Do not submit, do not spend a competition slot.</strong><br>
The full-map raster is a fresh model build, not a copied/re-encoded earlier prediction. It failed the frozen Stage-2 promotion rule and the pinned-family support-uniqueness gate. Its local format check passing does not make it eligible.</p>
<p class="big"><a class="btn" href="downloads/{esc(file)}">Download H53-A research TIFF</a></p>
<p class="zip">or <a href="downloads/{esc(zip_name)}">download the ZIP containing one GeoTIFF</a> ·
<a href="latest.html">Full results and checks</a> · <a href="how-to-submit.html">Submission guide — blocked</a></p>
<dl class="kv">
<dt>Research label (do not paste into portal)</dt><dd><code>{esc(artifact['artifact_id'])}</code></dd>
<dt>Research-only note</dt><dd><code>H53-A budget-q10 + fresh H-D/H-H; failed promotion and broad uniqueness gates; DO NOT SUBMIT.</code></dd>
<dt>Local format</dt><dd>{'PASS' if checks.get('format_valid') else 'FAIL'} — one-band float32, EPSG:32611, 3730 × 3292; finite values in [0,1], {checks.get('predicted_px', 0):,} points, zeros outside; one-file ZIP. This is not portal acceptance.</dd>
<dt>Stage 1 / Stage 2</dt><dd>Stage-1 lift {stage1_primary['recall_over_area_lift']:.3f}; Stage-2 q10 {s2['q10_constrained_mean']:.6f} vs frozen best {s2['frozen_ungated_best_mean']:.6f}; {s2['positive_paired_folds']}/6 paired folds positive.</dd>
<dt>Broad public-family gate</dt><dd><strong>FAIL</strong> — max containment {broad['max_support_containment']:.3f} &gt; {broad['thresholds']['containment']:.1f}; local gate {esc(local['verdict'])}. Not cleared as broadly unique.</dd>
<dt>SHA-256</dt><dd><code>{esc(artifact['sha256'])}</code></dd>
</dl>
<p><a href="downloads/{esc(check_name)}">Artifact receipt / final-byte checks / gate status</a>. The GeoTIFF is explicitly research-only; <b>NOT SAFE TO SUBMIT.</b></p>
</section>"""

    detail = f"""<h2>Latest experiment: H53-A — outcome and evidence</h2>
{banner}
<h3>Stage 1 — coarse residual prior, evaluated on its own</h3>
<p>Primary scenario: 10 km tiles, official clipped trace geometry and Kreemer et al. (2000), Eq. 3;
source slip rate interpreted as total fault-plane motion (assumption), normal dip 60° and strike-slip
dip 90° (assumptions), primary <code>SLIPSENSE</code>, and the registered 1e-8 unit factor. Across six
spatially held-out blocks, q10 approved {stage1_primary['approved_area_share_in_held_block']:.2%}
of area and recalled {stage1_primary['heldout_truth_recall']:.2%} of visible-catalogue truth;
recall/area lift was {stage1_primary['recall_over_area_lift']:.6f}, tile Spearman
{stage1_primary['tile_rank_spearman']:+.6f}. The geodetic-only control lift was
{stage1_control['recall_over_area_lift']:.6f}. This shows no meaningful residual enrichment on the
proxy instrument. These are Stage-1 metrics—not Stage-2 DTI and not an organizer score.</p>
{_table(['Fold', 'Approved area', 'Truth recall', 'Recall/area lift', 'Tile Spearman'], fold_rows_s1)}
<p>The registered mean mask is broad, but one block approved only
{stage1['per_fold'][2]['primary_scenario']['metrics']['combined_residual_prior']['approved_area_share_in_held_block']:.2%}
of its area (confinement lift
{1 / stage1['per_fold'][2]['primary_scenario']['metrics']['combined_residual_prior']['approved_area_share_in_held_block']:.3f}). Treat the residual as potentially off-fault/aseismic deformation, rate or geometry convention error, geodetic processing, or other model error—not proof or localization of an unmapped fault.</p>

<h3>Stage 2 — fine-scale placement, separately evaluated</h3>
<p>The unchanged H-D/H-H 50:50 blend was freshly reconstructed with the fixed STE emitter, six spatial
folds, 12-pixel training buffer and matched proxy mass. The fresh ungated mean
{ s2['fresh_ungated_mean']:.9f} differed from the frozen local best
{s2['frozen_ungated_best_mean']:.9f} by {s2['fresh_minus_frozen_mean']:+.9f}; this is outside the
frozen 1e-5 tolerance. The q10-constrained mean was {s2['q10_constrained_mean']:.9f},
{s2['q10_minus_frozen_mean']:+.9f} versus the frozen best, with {s2['positive_paired_folds']}/6
positive paired folds. It beat same-domain uniform dots by {s2['q10_minus_uniform_mean']:+.6f}, but
that control does not cure the failure to beat the frozen best. Promotion: <b>NO</b>.</p>
{_table(['Fold', 'Fresh ungated H-D/H-H', 'H53 q10 candidate', 'Same-domain uniform', 'Candidate − ungated', 'Approved area', 'Confinement lift'], fold_rows_s2)}

<h3>Stage-1 support dominance diagnostic</h3>
<p>For the full map, Stage 1 approved {artifact['build']['stage1_approved_area_share']:.2%} of the footprint and all
{artifact['build']['emitted_points']:,} points fall inside; emitted-point share / approved-area share is
{artifact['build']['stage1_lift_over_approved_area']:.3f}. Thus the global support is not strongly
concentrated beyond the broad mask by the registered lift criterion. It still inherits the q10 mask,
and the one-fold restriction noted above matters. This is not a promotion pass.</p>

<h3>Official slip-rate / geometry audit</h3>
<p>The preserved official DBF and field-definition text verify <code>SLIPRT2023</code> / <code>SLIPRTNUM</code>
in mm/year, matched across {attr['identity_checks']['rows']:,} records and
{attr['identity_checks']['sliprt2023_text_matches_segment_export']:,} segment pieces. The component
(vertical vs total fault-plane rate), per-trace dip and rake remain unresolved. The code list does not
cover observed RL/LL codes; secondary rates are not independently partitioned, so they were not added.
See <a href="downloads/official_attribute_audit_20261008.json">complete attribute audit</a> and
<a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">Kreemer et al. Eq. 3</a>.</p>

<h3>Final bytes, scoped uniqueness, and no-go decision</h3>
<p>Local checks: format {checks['format_valid']}, {checks['nan_cells']} nonfinite cells,
{checks['values_outside_0_1']} out-of-range cells, finite zeros outside, exact target grid, and a ZIP
with one TIFF. The local-artifact support gate is {esc(local['verdict'])}; the broader pinned
{public['audit']['inventory_repositories']}-repository family gate is <b>{esc(broad['verdict'])}</b>.
It SHA-verifies {public['audit']['downloaded_and_git_sha_verified']} unique Git blobs and finds no byte
duplicate, but maximum containment {broad['max_support_containment']:.3f} exceeds the
{broad['thresholds']['containment']:.1f} ceiling (maximum Jaccard {broad['max_support_jaccard']:.6f}).
Therefore H53-A is <b>not cleared as genuinely unique for the audited public family</b>. No submission
slot, portal acceptance, hidden-set improvement, organizer score, or global novelty is claimed.</p>
<ul>
<li><a href="downloads/{esc(check_name)}">Artifact receipt and local format checks</a></li>
<li><a href="downloads/h53_stage1_holdout_20261008.json">Full Stage-1 fold and sensitivity receipt</a></li>
<li><a href="downloads/h53_stage2_holdout_20261008.json">Full Stage-2 folds and promotion gate</a></li>
<li><a href="downloads/h53_public_uniqueness_20261008.json">Pinned public-family support audit</a></li>
<li><a href="downloads/candidate-hypotheses-2026-10-08.md">Ranked hypotheses, protocol and result</a></li>
</ul>

<h3>H33-2-B2 attribution and leaderboard comparison</h3>
<p>The GEMSDOE32 owner page labels H33-2-B2 UNSCORED and calls 0.2747 a modeled projection; the
user-reported 0.2778 file-to-score link is unverified. The official leaderboard was manually checked
once on 2026-10-08: the stated 0.3195 was not the current page high. A leaderboard row with the same
number would not authenticate the named H33 file. No standings snapshot is stored and there is no
automated monitor. Compare via the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official leaderboard</a>;
local holdout DTI is not comparable to organizer scores.</p>
"""
    return banner, detail
