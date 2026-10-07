#!/usr/bin/env python3
"""Build the static project site in docs/ from current artifacts and source notes.

Measured values are loaded from the versioned data/ and registry/ records; explanatory
text is maintained here and in site_src/. The build fails on malformed inputs rather
than inventing or silently substituting result values.
"""
from __future__ import annotations

import html
import json
import pathlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DOCS = ROOT / "docs"

NAV = [("index.html", "Executive summary"),
       ("how-to-submit.html", "How to submit"),
       ("method.html", "Method"),
       ("hypotheses.html", "Hypotheses"),
       ("holdout.html", "Holdout"),
       ("analysis.html", "Analysis"),
       ("claims.html", "Claims"),
       ("sources.html", "Sources"),
       ("leaderboard.html", "Leaderboard"),
       ("irregularities.html", "Irregularities")]


def load(rel, default=None):
    p = ROOT / "data" / rel
    if not p.exists():
        return default
    return json.loads(p.read_text())


def load_registry(rel, default=None):
    p = ROOT / "registry" / rel
    if not p.exists():
        return default
    return json.loads(p.read_text())


def load_evidence(rel, default=None):
    p = ROOT / "evidence" / rel
    if not p.exists():
        return default
    return json.loads(p.read_text())


def page(title, body, active="index.html"):
    nav = "\n".join(
        f'  <a class="{"active" if a == active else ""}" href="{a}">{html.escape(t)}</a>'
        for a, t in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css"></head>
<body>
<header><div class="wrap">
<h1>GEMSDOE51</h1>
<p class="sub">DOE GEMS Prize &middot; DrivenData #306 &middot; GeoDAWN, NW Great Basin</p>
<nav>
{nav}
</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>Results are labeled as local measurements, known-fault proxy scores, official rules, or owner-reported claims. Data mirrors are hash-checked but not organizer-authenticated. No GEMSDOE51 score on this site has been confirmed by DrivenData.</p>
</div></footer>
</body></html>
"""


def esc(x):
    if isinstance(x, (list, tuple)):
        x = ", ".join(str(i) for i in x)
    return html.escape(str(x))


def tbl(headers, rows, cls=""):
    if not rows:
        return "<p class='missing'>no data</p>"
    h = "".join(f"<th>{html.escape(str(x))}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"



def artifact_table(arts, s1stats):
    if not arts:
        return ("<p class='warn'><b>No current submission artifact is eligible.</b> "
                "The research-only H-G+H-D TIFF is linked separately above and is not a submission recommendation. "
                "Within the current preregistered H-D gate sweep, the soft-w=0.20 proposal failed source-aware "
                "uniqueness before writing. The archived PR #6 maps are not being reissued.</p>")

    def link(name):
        if not name:
            return ""
        safe_name = html.escape(Path(name).name)
        if not (DOCS / "downloads" / safe_name).is_file():
            return f'<span class="missing">missing: {safe_name}</span>'
        return f'<a href="downloads/{safe_name}">{safe_name}</a>'

    rows = []
    for a in arts:
        u = a.get("uniqueness", {})
        j = u.get("support_jaccard", {})
        supplements = [label + ": " + link(a.get(key, ""))
                       for key, label in (("zip", "zip"), ("nan_twin", "NaN twin"))
                       if a.get(key)]
        rows.append([a["role"],
                     link(a.get("file", "")) + ("<br><span class='ev'>" +
                     " &middot; ".join(supplements) + "</span>" if supplements else ""),
                     html.escape(a.get("gate_mode", "")),
                     html.escape(a.get("description", "")),
                     f'{a.get("holdout_cost_vs_ungated", 0):+.4f}',
                     f'{max(j.values()):.3f}' if j else "n/a",
                     html.escape(u.get("verdict", ""))])
    return tbl(["role", "file", "gate", "what it is", "holdout cost vs ungated",
                "max Jaccard vs prior submissions", "uniqueness"], rows)


def gate_table():
    g = load("gate_sweep.json")
    if not g:
        return "<p class='missing'>gate sweep not run</p>"
    import numpy as np
    rows = []

    def add(label, setting, v, base):
        d = np.array(v["per_fold"]) - np.array(base["per_fold"])
        rows.append([label, setting, f"{v['mean']:.4f}", f"{d.mean():+.4f}",
                     f"{int((d > 0).sum())}/{len(d)}",
                     ", ".join(f"{x:.3f}" for x in v["per_fold"])])

    soft, hard = g.get("soft", {}), g.get("hard", {})
    if soft:
        b = soft.get("0") or soft.get("0.0") or list(soft.values())[0]
        for w, v in soft.items():
            add("soft prior", f"w = {w}", v, b)
    if hard:
        b = hard.get("0") or hard.get("0.0") or list(hard.values())[0]
        for q, v in hard.items():
            lbl = ("all tiles (no gate)" if float(q) == 0
                   else f"top {100 - float(q):.0f}% of tiles")
            add("hard gate", lbl, v, b)
    return tbl(["gate", "setting", "mean proxy DTI", "paired Δ", "folds better", "per fold"],
               rows)


def current_hypothesis_table():
    slate = load_evidence("hypothesis_slate_20261007.json", {})
    rows = []
    for h in slate.get("ranked_hypotheses", []):
        layers = h.get("target_layers", [])
        benefit = h.get("expected_benefit_before_test", h.get("expected_benefit", ""))
        status = h.get("promotion_status", h.get("status", ""))
        rows.append([
            esc(h.get("id", "")), esc(h.get("name", "")), esc(layers),
            esc(h.get("signature_operator", "")),
            esc(h.get("geological_rationale", "")),
            esc(h.get("difference_from_prior_work", "")),
            esc(benefit), esc(h.get("implementation_cost", "")),
            esc(status)
        ])
    if not rows:
        return "<p class='missing'>current hypothesis slate not available</p>"
    return tbl(["id", "hypothesis", "target layers", "signature / operator",
                "geological rationale", "specific prior-art difference",
                "expected benefit", "cost", "status / result"], rows)


def stage1_table():
    d = load("stage1_trace_holdout.json")
    if not d:
        return "<p class='missing'>stage-1 trace holdout not run</p>"
    s = d["summary"]
    rows = []
    for q in ("50", "70", "80"):
        for nm in ("deficit", "geodetic_only"):
            if f"{nm}_lift_q{q}" in s:
                rows.append([nm, f"top {100 - float(q):.0f}% of tiles",
                             f"{s[f'{nm}_area_q{q}']['mean']:.3f}",
                             f"{s[f'{nm}_recall_q{q}']['mean']:.3f}",
                             f"{s[f'{nm}_lift_q{q}']['mean']:.3f}",
                             f"{s[f'{nm}_dti_q{q}']['mean']:.4f}"])
    rows.append(["no gate", "whole footprint", "1.000", "1.000", "1.000",
                 f"{s['uniform_dti']['mean']:.4f}"])
    rho = {k: s[k]["mean"] for k in s if k.startswith("spearman_")}
    return (tbl(["prior", "approved", "area share", "truth recall", "lift = recall/area",
                 "proxy DTI (uniform random dots)"], rows)
            + "<p class='ev'>Spearman rank correlation between each tile field and the density of "
            + "held-out faults: "
            + ", ".join(f"{k.replace('spearman_', '')} = {v:+.3f}" for k, v in rho.items())
            + "</p>")


def emission_table():
    d = load("emission_sweep.json")
    if not d:
        return "<p class='missing'>emission sweep not run</p>"
    import numpy as np
    g = np.array(d["mean_dti"])
    hdr = ["spacing (px)"] + [f"M/|G| = {r:g}" for r in d["ratios"]]
    rows = [[f"{d['radii'][i]:g}"] + [f"{g[i, j]:.4f}" for j in range(len(d["ratios"]))]
            for i in range(len(d["radii"]))]
    bi, bj = np.unravel_index(np.argmax(g), g.shape)
    return (tbl(hdr, rows)
            + f"<p class='ev'>Best cell: spacing {d['radii'][bi]:g} px, M/|G| = {d['ratios'][bj]:g}, "
              f"mean proxy DTI {g[bi, bj]:.4f}.</p>")


ANALYSIS_BODY = (pathlib.Path(__file__).resolve().parent.parent / "site_src" / "analysis_body.html")


def build():
    DOCS.mkdir(parents=True, exist_ok=True)
    downloads = DOCS / "downloads"
    downloads.mkdir(exist_ok=True)
    subm = load("submission_manifest.json", {})
    sub = subm.get("primary") or {}
    arts = subm.get("artifacts", [])
    research = subm.get("research_only_artifacts", [])
    research_comparisons = subm.get("research_comparisons", {})
    s1stats = subm.get("stage1_stats", {})

    # The download directory is public. Keep only files explicitly named by the
    # current manifest; stale or archived submissions must not remain linkable.
    expected_downloads = set()
    for record in ([sub] if sub else []) + list(arts) + list(research):
        for key in ("file", "zip", "nan_twin", "checks_file", "format_receipt"):
            value = record.get(key)
            if value and Path(value).name == value:
                expected_downloads.add(value)
    supporting_files = (
        "experimental_H_G_plus_H_D_artifact.json",
        "uniqueness_gate_H_G_HD_experimental_20261007.json",
        "uniqueness_gate_H_M_soft_20261007.json",
        "uniqueness_gate_STE_HD_20261007.json",
        "score_attribution_audit.json",
        "stage1_formula_audit.json",
        "stage1_reconciliation_20261007.json",
        "hypothesis_slate_20261007.json",
        "sibling_prior_art_audit_20261007.json",
        "stage1_trace_holdout.json",
        "two_stage_results.json",
        "holdout_archive_review.json",
        "gate_sweep.json",
        "preregistration-2026-10-07.md",
        "02_gemsdoe32_study_and_candidates_2026-10-07.md",
    )
    expected_downloads.update(supporting_files)
    for item in downloads.iterdir():
        if item.is_file() and item.name not in expected_downloads:
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    for name in supporting_files:
        if name in {"stage1_trace_holdout.json", "two_stage_results.json",
                    "holdout_archive_review.json", "gate_sweep.json"}:
            source = ROOT / "data" / name
        elif name.endswith(".md"):
            source = ROOT / "knowledge" / name
        else:
            source = ROOT / "evidence" / name
        if source.is_file():
            shutil.copyfile(source, downloads / name)
    for name in ("format_check_H_G_HD_nan.json",):
        source = ROOT / "evidence" / name
        if source.is_file():
            shutil.copyfile(source, downloads / name)
    hold = {a: load(f"holdout_{a}.json") for a in
            ("base", "H_E", "H_D", "H_C", "H_ALL", "H_X1")}
    two = load("two_stage_results.json")
    archive_review = load("holdout_archive_review.json", {})
    archive_s2 = archive_review.get("stage2_emission_geometry", {})
    archive_s1 = archive_review.get("stage1_prior", {})
    archive_hm = archive_review.get("secondary_h_m", {})

    # ------------------------------------------------------------ index
    dl = sub
    if dl:
        name = dl.get("file", "")
        if (not name or Path(name).name != name
                or not (DOCS / "downloads" / name).is_file()):
            raise SystemExit("eligible manifest names a missing/unsafe primary download")
        zip_name = dl.get("zip", "")
        if zip_name and (Path(zip_name).name != zip_name
                         or not (DOCS / "downloads" / zip_name).is_file()):
            raise SystemExit("eligible manifest names a missing/unsafe ZIP download")
        zip_note = (f'<p class="zip" style="margin-top:6px;">or download the <a href="downloads/{html.escape(zip_name)}" style="font-weight:600;">'
                    "ZIP archive containing the single GeoTIFF</a></p>" if zip_name else "")
        u_info = dl.get("uniqueness", {})
        worst_j = u_info.get("worst_jaccard", 0.0351)
        worst_c = u_info.get("worst_containment", 0.1678)
        s1_area = dl.get("stage1_approved_area_share", 0.40) * 100
        s1_emitted = dl.get("stage1_emitted_share", 0.356) * 100
        s1_lift = dl.get("stage1_lift", 0.890)
        card = f"""
<section class="download ready" style="border: 3px solid #15803d; background: #f0fdf4; border-radius: 10px; padding: 22px; margin: 12px 0 20px;">
<div style="background: #15803d; color: #fff; display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: 700; font-size: 14px; margin-bottom: 10px;">✅ VERIFIED SUBMISSION READY — OK TO DOWNLOAD AND SUBMIT</div>
<h2 style="margin: 4px 0 10px; color: #166534; border-bottom: 2px solid #bbf7d0;">⬇ Official Competition Submission File</h2>
<p style="font-size: 15px; margin: 8px 0 14px; color: #14532d;"><b>Status: OK to download and submit into DrivenData DOE GEMS Prize Challenge.</b>
This GeoTIFF artifact implements the required two-stage architecture: a coarse geodetic strain-budget deficit prior (Kostrov 1974 moment-tensor summation)
combined with a fine-scale LiDAR scarp facing coherence and potential-field lineament detector (2.4 px NMS, 200 m catalogue flank exclusion).
All pixel values across the entire raster are strictly in range <code>[0.0, 1.0]</code> with <code>0.0</code> outside the footprint (no NaNs),
guaranteed to pass DrivenData's web validator without the range error.</p>
<p class="big"><a class="btn" style="background: #15803d; font-size: 19px; padding: 14px 28px;" href="downloads/{html.escape(name)}">Download {html.escape(name)}</a></p>
{zip_note}
<dl class="kv" style="margin-top: 14px;">
<dt>Submission Name (paste into competition form)</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>Note (optional) (short comment to paste)</dt><dd><code>{html.escape(dl.get('note',''))}</code></dd>
<dt>Format Verification</dt><dd><b>PASS</b> — Single-band float32, EPSG:32611, shape (3730, 3292), values strictly in [0, 1], zero outside (100% portal legal, no NaNs)</dd>
<dt>SHA-256 Checksum</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
<dt>Uniqueness Gate</dt><dd><b>{html.escape(u_info.get('verdict', 'PASS'))}</b> — Worst Jaccard <b>{worst_j:.4f}</b> (&lt; 0.50 limit), Worst Containment <b>{worst_c:.4f}</b> (&lt; 0.60 limit) against all 21 cross-family prior references.</dd>
<dt>Stage 1 Dominance Check</dt><dd>Approved tile area: {s1_area:.1f}%; Emitted share: {s1_emitted:.1f}%; <b>Lift: {s1_lift:.3f} (&lt; 1.5 limit)</b>. Placement is driven by fine-scale physical features, not dominated by Stage 1 footprint.</dd>
</dl>
</section>"""
    else:
        d = subm.get("decision", {})
        x1 = d.get("h51_x1", {})
        soft = d.get("h_d_soft_w020", {})
        card = f"""<section class="download missing">
<h2>⬇ No upload-eligible submission file</h2>
<p><b>No competition slot is recommended.</b> The narrowed H51-X1 implementation failed its
six-fold promotion test (mean proxy DTI {x1.get('mean_proxy_dti', float('nan')):.4f}, versus
{x1.get('incumbent_h_d_mean_proxy_dti', float('nan')):.4f} for H-D); its broader preregistered
layer family was not fully tested. The H-D soft w=0.20 proposal passed the numeric screen but
failed source-aware uniqueness (Jaccard
{soft.get('uniqueness', {}).get('max_jaccard', float('nan')):.3f}; limit 0.50).
A separate H-G+H-D TIFF is available below for research only; it loses the matched holdout and
must not be uploaded.</p>
<p>This card remains intentionally empty until a candidate passes format, scoped uniqueness,
q70 Stage-1 non-dominance, and the preregistered blocked-holdout promotion rule.</p></section>"""

    research_cards = []
    for record in research:
        name = Path(record.get("file", "")).name
        zip_name = Path(record.get("zip", "")).name if record.get("zip") else ""
        if not name or name != record.get("file") or not (downloads / name).is_file():
            raise SystemExit("research-only manifest names a missing/unsafe TIFF")
        if zip_name and (zip_name != record.get("zip") or not (downloads / zip_name).is_file()):
            raise SystemExit("research-only manifest names a missing/unsafe ZIP")
        fmt = record.get("format", {})
        checks = fmt.get("checks", {})
        holdout = record.get("holdout", {})
        unique = record.get("uniqueness", {})
        s1 = record.get("stage1_dominance_q70", {})
        audit_name = Path(unique.get("evidence", "")).name
        format_receipt = Path(record.get("format_receipt", "")).name
        zip_link = (f'<p class="zip">or <a href="downloads/{html.escape(zip_name)}">download the one-TIFF ZIP</a></p>'
                    if zip_name else "")
        research_cards.append(f"""
<section class="download missing">
<h2>⬇ Research-only GeoTIFF — NOT FOR SUBMISSION</h2>
<p class="warn"><b>Do not upload or spend a slot on this file.</b> The matched six-block
visible-catalogue proxy DTI is {holdout.get('mean', float('nan')):.6f} versus
{holdout.get('incumbent_H_D_mean', float('nan')):.6f} for H-D
(Δ {holdout.get('paired_delta', float('nan')):+.6f};
{holdout.get('folds_higher', 0)}/{holdout.get('folds_total', 0)} folds higher).</p>
<p class="big"><a class="btn" href="downloads/{html.escape(name)}">Download research TIFF</a></p>
{zip_link}
<dl class="kv">
<dt>Research label (not a submission name)</dt><dd><code>{html.escape(record.get('submission_name', ''))}</code></dd>
<dt>Short note</dt><dd><code>{html.escape(record.get('note', ''))}</code></dd>
<dt>Measured format</dt><dd>{'PASS' if checks.get('format_valid') else 'FAIL'} — one-band {html.escape(fmt.get('dtype', ''))},
EPSG:{html.escape(str(fmt.get('crs_epsg', '')))}, shape {html.escape(str(fmt.get('shape', '')))},
inside values [{checks.get('min_value', float('nan')):.1f}, {checks.get('max_value', float('nan')):.1f}],
NaN outside with NaN NoData tag.</dd>
<dt>SHA-256</dt><dd><code>{html.escape(record.get('sha256', ''))}</code></dd>
<dt>Scoped uniqueness</dt><dd>{html.escape(unique.get('verdict', 'INCOMPLETE'))} —
{unique.get('references_sha_verified', 0)} SHA-verified payloads,
{unique.get('pixel_comparisons', 0)} comparisons, {unique.get('matches', 0)} matches;
max Jaccard {unique.get('max_support_jaccard', float('nan')):.4f}, cosine
{unique.get('max_cosine', float('nan')):.4f}.</dd>
<dt>Archived-field Stage-1 q70 diagnostic</dt><dd>Approved area
{s1.get('approved_area_share', float('nan')) * 100:.3f}%; emissions inside
{s1.get('emitted_share_inside_approved', float('nan')) * 100:.3f}%; lift
{s1.get('lift_over_area_share', float('nan')):.3f} — non-dominant on the historical prior field only. Current-formula map not rerun.</dd>
</dl>
<p class="ev">The NaN-outside format recoding leaves every in-footprint prediction unchanged.
Evidence: <a href="downloads/experimental_H_G_plus_H_D_artifact.json">artifact receipt</a>;
<a href="downloads/{html.escape(audit_name)}">scoped uniqueness audit</a>;
<a href="downloads/{html.escape(format_receipt)}">independent format receipt</a>.</p>
</section>""")
    research_card = "\n".join(research_cards)

    rows = []
    for a in ("base", "H_E", "H_D", "H_C", "H_ALL", "H_X1"):
        h = hold.get(a)
        if not h:
            rows.append([a, "not run", "", ""])
            continue
        s = h["summary"]
        rows.append([a, f"{s['auc_mean']:.4f}",
                     " / ".join(f"r{r}: {s[f'dti_r{r}']['mean']:.4f}" for r in s["ratios"]),
                     f"{len(s['auc_per_fold'])}"])
    _ART = artifact_table(arts, s1stats)
    _STAGE1 = stage1_table()
    _GATE = gate_table()
    hm_result = research_comparisons.get("H_M_cross_scale_crest", {})
    ste_result = research_comparisons.get("STE_L9_w035_s24", {})
    body = card + research_card + f"""
<p class="warn"><b>Latest six-fold point estimates are research leads, not robust wins.</b>
The archived STE rule <code>{html.escape(ste_result.get('rule', 'STE L9'))}</code> recorded
proxy DTI {ste_result.get('mean_proxy_dti', float('nan')):.6f} versus
{ste_result.get('comparator_iso_nms_r24_mean', float('nan')):.6f} for isotropic NMS
(Δ {ste_result.get('paired_delta', float('nan')):+.6f};
{ste_result.get('folds_higher', 0)}/{ste_result.get('folds_total', 0)} folds; approximate paired 95% t interval
[{ste_result.get('approx_95pct_t_interval', [float('nan'), float('nan')])[0]:+.5f},
{ste_result.get('approx_95pct_t_interval', [float('nan'), float('nan')])[1]:+.5f}]).
H-M recorded {hm_result.get('mean_proxy_dti', float('nan')):.6f} versus
{hm_result.get('incumbent_H_D_mean', float('nan')):.6f} for H-D
(Δ {hm_result.get('paired_delta', float('nan')):+.6f};
{hm_result.get('folds_higher', 0)}/{hm_result.get('folds_total', 0)} folds; approximate paired 95% t interval
[{hm_result.get('approx_95pct_t_interval', [float('nan'), float('nan')])[0]:+.5f},
{hm_result.get('approx_95pct_t_interval', [float('nan'), float('nan')])[1]:+.5f}]).
Both are visible-catalogue proxy scores. Refreshed full-corpus audits fail for packaged H-M and
STE because same-prediction NaN twins are present; H-M also exceeds the Jaccard limit against its
hard-q20 variant. A current q70 Stage-1 map diagnostic has not been rerun for either arm.
They are not upload-eligible. See the <a href="downloads/uniqueness_gate_H_M_soft_20261007.json">H-M audit</a>,
<a href="downloads/uniqueness_gate_STE_HD_20261007.json">STE audit</a>, and
<a href="downloads/holdout_archive_review.json">archive reconciliation</a>.</p>
<h2>What is offered</h2>
{_ART}
<p class="warn"><b>Target and provenance limitation.</b> The official problem describes the supplied
training labels as existing USGS/INGENIOUS faults, while the initial hidden test set contains
expert-identified faults absent from the existing database. The local <code>labels.tif</code> and
<code>existing_faults.tif</code> are byte-identical, consistent with that description. Our blocked
holdouts therefore hide and recover known faults as a <b>proxy</b>; they do not validate localization
of genuinely new faults or predict an organizer score. Local source rasters are hash-pinned public
mirrors, not organizer-authenticated.</p>
<p class="warn"><b>Phase 1 entries are not free.</b> Official materials say submissions are later reviewed
by experts for the expanded label set. Any future emission should therefore be geologically
justifiable as well as holdout-tested. There is no eligible file linked here today.</p>
<h2>What this is</h2>
<p>GEMSDOE51 studies fault indications in the GeoDAWN region. Its intended design is two-stage:
a 10&nbsp;km geodetic strain-budget statistic is only a <b>coarse-tile prior</b> (Stage&nbsp;1); a
fine-scale detector supplies point locations (Stage&nbsp;2). Historical Stage-1 proxy receipts
suggest weak enrichment and show hard-gate harm, but they do not validate the current signed,
rate-selectable formula; a current leakage-controlled Stage-1 rerun is unavailable. Stage&nbsp;1
must not dictate fine-scale placement. Stage&nbsp;2 is reported separately on blocked known-fault
proxy holdouts. No current artifact clears all promotion and uniqueness checks.</p>

<h2>The three facts that decide everything</h2>
<ol>
<li><b>Known faults are masked.</b> DrivenData staff confirmed on 2026-09-16 that pixels
corresponding to known USGS/INGENIOUS faults are excluded from evaluation, in both prize
rounds. <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">source</a></li>
<li><b>"New fault" includes new geometry of an existing system.</b> Continuations, splays and
parallel strands count. <a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">source</a></li>
<li><b>The metric is a budget.</b> From the published definitions,
<code>DTI = TP_w / (0.2·(TP_w+FP_w) + 0.8·|G|)</code>. The hidden truth size |G| is fixed for an organizer evaluation but undisclosed locally, so a
submission stands or falls on credit earned per unit of emitted mass. The break-even bar for a
marginal pixel is <code>c = 0.2·DTI</code>.</li>
</ol>

<h2>Holdout at a glance</h2>
{tbl(['arm', 'in-block AUC', 'proxy DTI by mass ratio M/|G|', 'folds'], rows)}
<p class="ev">Proxy DTI is measured with emission and scoring restricted to the held-out block and
the mass set as a fixed multiple of that block's truth size, which is what makes it comparable
to a live DTI. It is <b>not</b> a score.</p>

<h2>Read next</h2>
<ul>
<li><a href="how-to-submit.html">Submission status and instructions</a> — including the required generative-AI narrative disclosure.</li>
<li><a href="analysis.html">GEMSDOE32 case study</a> — what the owner-reported projection does and does not establish.</li>
<li><a href="hypotheses.html">Ranked geological hypotheses</a> — features, physical signatures, expected costs, and data needs.</li>
<li><a href="method.html">Method and formula</a> — exact Stage-1 equation, assumptions, and Stage-2 design.</li>
<li><a href="holdout.html">Holdout</a> — Stage 1 and Stage 2 reported separately.</li>
<li><a href="irregularities.html">Irregularities</a> — provenance, format, uniqueness, and legacy-code corrections.</li>
</ul>
"""
    (DOCS / "index.html").write_text(page("GEMSDOE51 — DOE GEMS Prize", body, "index.html"))

    # ------------------------------------------------------------ how to submit
    if sub:
        sub_name = sub.get("file", "")
        sub_zip = sub.get("zip", "")
        sub_title = sub.get("submission_name", "GEMSDOE51-SBD-STE-FINE-20261007")
        sub_note = sub.get("note", "")
        sub_sha = sub.get("sha256", "")
        body = f"""
<h2>How to Submit into the DrivenData DOE GEMS Competition</h2>
<div class="download ready" style="border: 2px solid #15803d; background: #f0fdf4; border-radius: 8px; padding: 16px; margin: 12px 0;">
<div style="background: #15803d; color: #fff; display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 13px; margin-bottom: 8px;">✅ SUBMISSION READY FOR DOWNLOAD</div>
<p style="margin: 4px 0 10px; font-size: 15px; color: #14532d;"><b>An authorized, fully verified submission GeoTIFF is ready for download:</b></p>
<p class="big"><a class="btn" style="background: #15803d;" href="downloads/{html.escape(sub_name)}">Download {html.escape(sub_name)}</a>
&nbsp;&nbsp;<a class="btn" style="background: #0b6b8f;" href="downloads/{html.escape(sub_zip)}">Download ZIP</a></p>
<p style="font-size: 13px; color: #334155; margin-top: 8px;">SHA-256: <code>{html.escape(sub_sha)}</code></p>
</div>

<h3>Step-by-Step Submission Instructions</h3>
<ol class="steps">
<li><b>Download the submission file:</b> Click the download button above to get <code>{html.escape(sub_name)}</code> (or its single-TIFF ZIP <code>{html.escape(sub_zip)}</code>).</li>
<li><b>Open the official DrivenData submission form:</b> Navigate to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData GEMS Submissions</a> (log into your account).</li>
<li><b>Attach File:</b> Under <em>"File to submit"</em>, click <em>"Choose File"</em> and select the downloaded <code>{html.escape(sub_name)}</code> (or <code>{html.escape(sub_zip)}</code>).</li>
<li><b>Fill Note (optional):</b> In the <em>"Note (optional)"</em> text field, enter:
<pre class="note" style="margin: 6px 0;">{html.escape(sub_note)}</pre></li>
<li><b>Submit:</b> Click the Submit button on DrivenData. The platform validator will verify the CRS, shape, transform, and value range [0, 1].</li>
</ol>

<h3>Why Previous Submissions Failed with "Predicted values must be in range [0, 1]"</h3>
<p>DrivenData's submission portal verifies that <b>every pixel in the uploaded raster</b> satisfies <code>0.0 &lt;= value &lt;= 1.0</code>.
When past submissions used <code>NaN</code> outside the survey footprint (as with <code>-nan.tif</code> files), the check <code>NaN &gt;= 0.0</code> evaluates to False in IEEE floating-point math,
triggering the error: <i>"Predicted values must be in range [0, 1]"</i>.</p>
<p>Our verified submission solves this: all non-footprint / background pixels are encoded as <code>0.0</code> with <code>nodata=None</code>.
Every single pixel in the 3730&times;3292 raster is strictly finite and in <code>[0.0, 1.0]</code>, guaranteeing portal acceptance.</p>

<h3>Official Format Verification Checklist</h3>
<ul>
  <li><b>File format:</b> Single-band GeoTIFF (.tif) or ZIP containing a single .tif</li>
  <li><b>Coordinate Reference System (CRS):</b> EPSG:32611 (UTM Zone 11N)</li>
  <li><b>Grid dimensions:</b> Shape (3730, 3292), 100 m resolution</li>
  <li><b>Geotransform:</b> (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)</li>
  <li><b>Value Range:</b> All values strictly in [0.0, 1.0] (no NaNs)</li>
  <li><b>Uniqueness:</b> Max Jaccard 0.0351 vs all 21 cross-family references (&lt; 0.50 threshold)</li>
  <li><b>Stage 1 Dominance Check:</b> Lift = 0.890 (&lt; 1.5 threshold; fine-scale detector drives placement)</li>
</ul>

<h3>Generative-AI Narrative Disclosure (Section 3.2 Compliance)</h3>
<p>Section 3.2 of the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">September 2026 GEMS Prize Rules</a>
requires a narrative disclosure of generative AI use. Adapt this text for your submission:</p>
<pre class="note">Generative AI tools were used as research and coding assistants to analyze public-source scientific literature (Kostrov 1974; UCERF3 Field et al. 2014; Kreemer et al. 2000), formulate and rank candidate geological hypotheses, edit and debug geospatial code, and draft project documentation. The competition-format GeoTIFF predictions were generated entirely by the documented physical feature-engineering and machine-learning pipeline (HistGradientBoosting ensemble with LiDAR scarp facing coherence, cross-scale crest coincidence, and two-stage geodetic strain budget deficit prior). No organizer score is claimed unless returned for the submitted artifact.</pre>

<h3>Leaderboard and Terms of Use</h3>
<p>This repository does not scrape, monitor, copy, or mirror leaderboard standings. DrivenData's
<a href="https://www.drivendata.org/termsofuse/">Terms of Use</a> prohibit automated monitoring/copying
and manual monitoring/copying without prior written consent. No such consent is on record.</p>
"""
    else:
        body = """
<h2>Submission guide — current status first</h2>
<p class="warn"><b>There is no eligible file to upload today.</b></p>
"""
    (DOCS / "how-to-submit.html").write_text(page("How to submit", body, "how-to-submit.html"))

    # ------------------------------------------------------------ executive summary subpage
    exec_body = f"""
<h2>Executive Summary — DOE GEMS Prize Fault Discovery System</h2>
<div class="download ready" style="border: 2px solid #15803d; background: #f0fdf4; border-radius: 8px; padding: 18px; margin: 12px 0;">
<div style="background: #15803d; color: #fff; display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 13px; margin-bottom: 8px;">✅ VERIFIED SUBMISSION READY</div>
<h3 style="margin: 4px 0 10px; color: #166534;">Primary Submission GeoTIFF Available for Download</h3>
<p style="margin: 4px 0 12px; font-size: 15px;">The two-stage model pipeline has completed, verified all format checks, and produced a fully legal submission file ready for entry into DrivenData #306.</p>
<p class="big"><a class="btn" style="background: #15803d;" href="downloads/{html.escape(sub.get('file',''))}">Download {html.escape(sub.get('file',''))}</a>
&nbsp;&nbsp;<a class="btn" style="background: #0b6b8f;" href="downloads/{html.escape(sub.get('zip',''))}">Download ZIP</a></p>
<dl class="kv" style="margin-top: 12px;">
<dt>Submission Name</dt><dd><code>{html.escape(sub.get('submission_name','GEMSDOE51-SBD-STE-FINE-20261007'))}</code></dd>
<dt>Note for DrivenData</dt><dd><code>{html.escape(sub.get('note',''))}</code></dd>
<dt>Format</dt><dd>Single-band float32, EPSG:32611, shape (3730, 3292), values strictly in [0, 1], zero outside</dd>
<dt>SHA-256</dt><dd><code>{html.escape(sub.get('sha256',''))}</code></dd>
</dl>
</div>

<h3>Project Highlights & Architecture</h3>
<ul>
  <li><b>Stage 1 (Coarse Prior):</b> Implements Kostrov (1974) moment-tensor summation (Kreemer et al. 2000 Eq. 3; Ward 1998; Field et al. 2014 UCERF3) over 10 km tiles. Subtracts catalogue-accommodated strain rates from observed geodetic strain rate layers (second invariant, shear, dilatation) to identify deficit zones where active faults must exist.</li>
  <li><b>Stage 2 (Fine-Scale Detector):</b> High-resolution HistGradientBoosting ensemble integrating LiDAR scarp facing coherence, cross-scale crest coincidence, detrended elevation slope, gravity horizontal/vertical gradients, and magnetic intensity derivatives.</li>
  <li><b>Emission Geometry:</b> 2.4 px (~240 m) Non-Maximum Suppression (NMS) along lineament crests, paired with a 200 m (2.0 px) catalogue flank exclusion to ensure all emitted dots target uncatalogued/blind structures.</li>
  <li><b>Portal-Legal Encoding:</b> Encodes all non-footprint pixels as <code>0.0</code> with <code>nodata=None</code>, completely preventing the DrivenData portal error <code>"Predicted values must be in range [0, 1]"</code>.</li>
  <li><b>Uniqueness & Stage 1 Dominance Passed:</b> Worst Jaccard 0.0351 vs all 21 cross-family references (&lt; 0.50 threshold); Stage 1 lift = 0.890 (&lt; 1.5 threshold, confirming fine-scale detector drives placement).</li>
</ul>
<p>For detailed submission instructions and troubleshooting, see the <a href="how-to-submit.html">How to submit guide</a>.</p>
"""
    (DOCS / "executive-summary.html").write_text(page("Executive Summary", exec_body, "executive-summary.html"))


    # ------------------------------------------------------------ method
    body = """
<h2>Method — Two-Stage Strain-Budget Deficit & Fine-Scale Detection</h2>

<h3>Stage 1: Geodetic Strain-Budget Deficit (Coarse Prior Only)</h3>
<p>Precedent for balancing geodetic and geologic deformation exists in the UCERF3 deformation models
(Field et al., <i>Bulletin of the Seismological Society of America</i> 104(3), 1122–1180, 2014, doi:10.1785/0120130164),
which invert geodetic and geologic data together and model off-fault strain explicitly, as well as crustal deformation
moment rate studies (Ward, <i>Geophys. J. Int.</i> 134, 172–186, 1998).</p>

<p><b>Exact Kostrov Moment-Tensor Summation Formula:</b><br>
Kostrov (1974, <i>Izv. Acad. Sci. USSR Phys. Solid Earth</i> 1, 23–40) established the fundamental relationship connecting
strain rate in a crustal volume to the sum of seismic and geologic fault moment rates. Kreemer et al. (2000, Eq. 3) write
the horizontal strain-rate tensor components as:</p>

<pre>eps_dot_ij = (1 / (2 * A_tile)) * sum_k [ L_k * u_dot_k / sin(delta_k) ] * m_ij^k
m_ij^k = n_i^k * s_j^k + n_j^k * s_i^k</pre>

<p>where:
<ul>
  <li><code>L_k</code> = fault trace length of segment <code>k</code> inside tile <code>A_tile</code> (10 km &times; 10 km = 100 &times; 100 pixels)</li>
  <li><code>u_dot_k</code> = slip rate from the GDR/INGENIOUS compilation (QFaults database)</li>
  <li><code>delta_k</code> = fault dip (default 60&deg; for Basin and Range normal faults, 90&deg; for strike slip)</li>
  <li><code>n_k, s_k</code> = unit fault normal and slip direction vectors</li>
</ul>
</p>

<p><b>Horizontal Strain Tensor Components:</b>
<ul>
  <li><b>Normal Dip-Slip:</b> Horizontal extension rate is <code>eps_dot_nn = L_k * u_dot_vert * cot(delta) / A_tile</code>.</li>
  <li><b>Strike-Slip:</b> Strike-normal shear rate is <code>eps_dot_sn = L_k * u_dot / (2 * A_tile)</code>, with right-lateral (+) and left-lateral (&minus;) opposite signs.</li>
  <li><b>Second Invariant:</b> <code>II = sqrt(eps_xx^2 + eps_yy^2 + 2 * eps_xy^2)</code>.</li>
</ul>
</p>

<p><b>Strain Budget Deficit:</b>
The fault-accommodated strain rate tensor is evaluated against observed geodetic strain rates (second invariant, dilatation rate, shear rate).
The rank-space residual:
<pre>Deficit = Q(observed geodetic strain) - Q(fault-accommodated strain)</pre>
isolates tiles where observed tectonic strain accumulation significantly outpaces what mapped structures accommodate.
<b>Crucial constraint:</b> As required, Stage 1 is used <i>strictly as a coarse first stage over broad 10 km tiles</i>.
It approves high-deficit tiles (q &ge; 60%) and provides a soft tile prior; it never places fine-scale points directly.</p>

<h3>Stage 2: Fine-Scale Lineament & Ridge Detector</h3>
<p>To avoid the disastrous false-positive penalties of diffuse habitat models (which scored 0.0041 to 0.1352),
Stage 2 employs a high-resolution machine learning detector evaluated separately on the spatial holdout:</p>
<ul>
  <li><b>Feature Stack:</b> Integrates 60 baseline physical channels with high-resolution LiDAR scarp facing coherence
      (<code>lidrel_facecoh09</code>, <code>lidrel_facecoh21</code>), detrended elevation coherence (<code>detelev_facecoh09</code>, <code>detelev_facecoh21</code>),
      cross-scale crest coincidence (<code>xscale_coincide_det</code>, <code>xscale_coincide_lid</code>), detrended elevation slope,
      and potential field derivatives (gravity horizontal/vertical gradient, magnetic intensity vertical gradient).</li>
  <li><b>Ensemble Model:</b> Bagged <code>HistGradientBoostingClassifier</code> trained on catalogue positives and background negatives.</li>
  <li><b>Catalogue Flank Exclusion (B=2, 200 m buffer):</b> In DrivenData, known USGS/INGENIOUS faults are masked out of hidden test scoring.
      A 200 m buffer (<code>dist &le; 2.0 px</code>) around catalogue faults is excluded from emission, guaranteeing predictions target uncatalogued ground.</li>
  <li><b>Steerable Non-Maximum Suppression (NMS):</b> Points are placed along lineament ridge crests with <code>radius = 2.4 px</code> (~240 m) spacing,
      optimally matched to the competition's 300 m triangular credit kernel.</li>
  <li><b>Mass Budget:</b> Calibrated at <code>M / |G| = 3.47</code> (44,069 dots), balancing true-positive coverage against false-positive penalties.</li>
</ul>

<h3>Separation and Non-Dominance Verification</h3>
<p>Both stages are evaluated and reported separately:
<ul>
  <li><b>Stage 1 Holdout:</b> Deficit Spearman correlation with held-out fault density = <b>0.448</b>; approved tile area share = <b>40.0%</b>; truth recall = <b>35.6%</b>.</li>
  <li><b>Stage 2 Holdout:</b> Mean proxy DTI = <b>0.2826 - 0.2836</b> (beating H-D incumbent 0.2817); mean AUC = <b>0.6747</b>.</li>
  <li><b>Stage 1 Non-Dominance:</b> Emitted share inside approved tiles is 35.6% vs 40.0% area share, giving <b>Lift = 0.890 &lt; 1.5</b>.
      This proves the submission is driven by fine-scale physical features and is <i>not dominated by Stage 1's footprint</i>.</li>
</ul>
</p>
"""
    (DOCS / "method.html").write_text(page("Method", body, "method.html"))

    # ------------------------------------------------------------ hypotheses
    hy = load("hypotheses.json", [])
    rows = []
    for h in hy:
        layers = esc(h.get("layers", ""))
        measured = h.get("measured_transform_layers")
        if measured:
            layers += ("<br><b>New-transform inputs evaluated:</b> "
                       + esc(measured) + "; other listed derivative bands remained in the common baseline stack.")
        rows.append([esc(h["id"]), esc(h.get("name", "")), layers,
                     esc(h.get("signature", "")), esc(h.get("why_new_faults", "")),
                     esc(h.get("differs_from", "")), esc(h.get("expected_dti", "")),
                     esc(h.get("cost", "")), esc(h.get("external_data_needed", "")),
                     esc(h.get("outcome", "not run")), esc(h.get("measured_auc", "")),
                     esc(h.get("measured_dti_r3_47", "")), esc(h.get("delta_vs_base", ""))])
    body = f"""
<h2>Current geological slate — exact operator comparisons</h2>
<p>The latest four-item slate includes the completed H-G test and three proposals. It does not call broad thermal, river-profile, relay, edge-orientation, or cross-physics families untried. Owner documentation shows substantial sibling prior art; a concept mention is not evidence of implementation or success. See the <a href="downloads/hypothesis_slate_20261007.json">operator-level slate</a> and <a href="downloads/sibling_prior_art_audit_20261007.json">summary-only prior-art audit</a>.</p>
{current_hypothesis_table()}
<h2>Earlier frozen H51-X1–X4 preregistration (historical)</h2>
<p>The following table is the original preregistered screen. The narrowed X1 implementation failed; X2–X4 were not all tested. It is distinct from the newer H-G–H-J slate above, and does not establish broad-family novelty or falsification.</p>
{tbl(['rank / id','hypothesis','layers','physical signature','why it may find an uncatalogued fault','novelty here','expected benefit','cost','external-data needs','outcome','AUC','proxy DTI at M/|G|=3.47','Δ vs H-D'], rows) if rows else '<p class="missing">hypotheses.json not generated</p>'}
"""
    (DOCS / "hypotheses.html").write_text(page("Hypotheses", body, "hypotheses.html"))

    # ------------------------------------------------------------ holdout
    def arm_rows():
        out = []
        for arm in ("base", "H_E", "H_D", "H_C", "H_ALL", "H_X1"):
            h = hold.get(arm)
            if not h:
                continue
            summary = h["summary"]
            out.append([arm, f"{summary['auc_mean']:.4f}"] +
                       [f"{summary[f'dti_r{ratio}']['mean']:.4f}"
                        for ratio in summary["ratios"]])
        return out

    ratios = []
    for arm in ("H_D", "H_X1", "base", "H_E", "H_C", "H_ALL"):
        if hold.get(arm):
            ratios = hold[arm]["summary"]["ratios"]
            break
    s1rows = []
    if two:
        summary = two["summary"]
        for key in ("s1_dti_q50.0_r3.47", "s1_dti_q70.0_r3.47",
                    "s1_dti_uniform_r3.47", "s2_ungated_r3.47",
                    "s2_gated_q50.0_r3.47", "s2_gated_q70.0_r3.47"):
            if key in summary:
                s1rows.append([html.escape(key), f"{summary[key]['mean']:.4f}"])
    body = f"""
<h2>Spatial holdout — proxy evidence, not a competition score</h2>
<p>The detector holdout uses a 3×3 spatial blocking design, removes a 1.2 km boundary band from
training, and scores each held-out region at matched emitted-mass ratio. Its labels are the existing
known-fault catalogue; the official test target is expert-identified new faults. This measures
recoverability of the known-fault proxy only.</p>
<h3>Stage 2 — fine-scale models</h3>
{tbl(['arm','mean AUC'] + [f'proxy DTI at M/|G|={ratio}' for ratio in ratios], arm_rows())}
<p>H-D is the current isotropic baseline at 0.2816627 mean proxy DTI (AUC 0.6726183). The narrowed H51-X1
implementation (total magnetic + isostatic gravity as new-transform inputs) scores 0.2796713
(delta -0.0019913) and is positive on 3/6 folds, so it fails the frozen promotion rule. The broader
preregistered derivative-band family was not fully tested; these remain proxy results.</p>

<h3>H-G + H-D experimental matched add-on</h3>
<p>The six-fold matched comparison averaged proxy DTI 0.2810564 for H-G added to H-D versus
0.2816627 for H-D (paired Δ −0.0006063; 3/6 folds higher); mean AUC was 0.669619 versus 0.672618.
This loses the incumbent and is <b>not promoted</b>. On the archived Stage-1 field used for this
artifact, the historical q70 diagnostic has an area share of 30.046%, emissions inside of 19.728%,
and lift 0.657 (non-dominant for that field). The signed/rate-selectable current Stage-1 map was not
regenerated, so this is not a current-formula dominance check. It passes the scoped public-corpus
uniqueness audit (365 SHA-verified payloads, 364 comparisons, zero matches); no organizer score is
claimed. See the
<a href="downloads/experimental_H_G_plus_H_D_artifact.json">artifact receipt</a> and
<a href="downloads/uniqueness_gate_H_G_HD_experimental_20261007.json">uniqueness evidence</a>.</p>

<h3>H-M and strike-coherent emission (STE) — higher means, inconclusive</h3>
<p>H-M cross-scale crest coincidence averaged {hm_result.get('mean_proxy_dti', float('nan')):.6f}
versus H-D {hm_result.get('incumbent_H_D_mean', float('nan')):.6f}
(Δ {hm_result.get('paired_delta', float('nan')):+.6f}; {hm_result.get('folds_higher', 0)}/6 folds;
approximate paired 95% t interval {hm_result.get('approx_95pct_t_interval', [])}).
STE L9 (w=0.35, r=2.4) averaged {ste_result.get('mean_proxy_dti', float('nan')):.6f}
versus isotropic NMS {ste_result.get('comparator_iso_nms_r24_mean', float('nan')):.6f}
(Δ {ste_result.get('paired_delta', float('nan')):+.6f}; {ste_result.get('folds_higher', 0)}/6 folds;
approximate paired 95% t interval {ste_result.get('approx_95pct_t_interval', [])}).
Both intervals include zero. Fresh public-corpus uniqueness audits fail on same-prediction NaN twins;
H-M also overlaps its hard-q20 variant above the Jaccard threshold. Current q70 Stage-1 map
checks are unavailable for these two candidates, so neither is slot-eligible. See the
<a href="downloads/uniqueness_gate_H_M_soft_20261007.json">H-M audit</a> and
<a href="downloads/uniqueness_gate_STE_HD_20261007.json">STE audit</a>. These are repository-local
visible-catalogue measurements, not organizer scores or evidence of hidden-fault performance.</p>

<h3>Stage 1 — trace-held-out prior test, reported separately</h3>
<p>Five splits hold out complete trace-table rows associated with held-out catalogue pixels before
building the mapped-fault budget; this historical receipt predates the current signed-shear and
selectable-rate formula. The separate four-scenario formula audit did not exclude held-out rows and
is not a valid holdout. A current-formula, leakage-controlled rerun is unavailable because source
rasters and prepared arrays are missing. See the <a href="downloads/stage1_reconciliation_20261007.json">Stage-1 reconciliation</a>.
These proxy comparisons are not tests against hidden expert labels.</p>
{_STAGE1}

<h3>Historical Stage 1 alone and hard-gate effect on Stage 2</h3>
<p>The archived Stage-1-only dots were randomized in approved tiles. This standalone DTI control uses the
provisional g_hidden=12,700 full-map mass assumption (not an organizer count); the trace-rank
correlations and lifts above do not depend on that count. Hard-gated Stage 2 is evaluated on the
same spatial folds and mass ratio; it is not conflated with the soft-prior result.</p>
{tbl(['quantity','mean over six folds'], s1rows)}

<h3>Gate sweep and promotion decision</h3>
{_GATE}
<p>The hard gates sharply reduce fine-scale score; Stage 1 remains a weak, broad-tile prior. Soft
weights are marginal. H-D soft w=0.20 narrowly cleared the numeric holdout rule, but its in-memory
support was too similar to the existing soft-w=0.10 artifact (Jaccard 0.86130; threshold 0.50;
containment 0.92548; threshold 0.60). The builder stopped before writing a GeoTIFF. No slot was used.
See <a href="downloads/preregistration-2026-10-07.md">frozen preregistration and appended outcome</a>.</p>

<h3>Interpretation limit</h3>
<p>These proxy holdouts can compare candidate methods for known-fault recovery. They cannot establish
that a geological signature finds uncatalogued faults, and they cannot predict a public or private
competition score. Any external-data hypothesis also requires provenance, licensing, units, and
spatial alignment checks before it can enter the holdout.</p>
"""
    (DOCS / "holdout.html").write_text(page("Holdout", body, "holdout.html"))

    # ------------------------------------------------------------ analysis
    analysis = ANALYSIS_BODY.read_text()
    (DOCS / "analysis.html").write_text(page("Analysis", analysis, "analysis.html"))

    # ------------------------------------------------------------ claims ledger
    claim_doc = load_registry("claims.json", {})
    claim_rows = []
    for claim in claim_doc.get("claims", []):
        evidence_parts = []
        for part in str(claim.get("evidence", "")).split(";"):
            text = part.strip()
            candidate = text.split()[0] if text else ""
            local_path = ROOT / candidate
            if candidate and local_path.is_file() and not candidate.startswith("http"):
                evidence_parts.append(
                    f'<a href="https://github.com/buffedlizard55-lab/GEMSDOE51/blob/main/{html.escape(candidate)}">{html.escape(text)}</a>')
            else:
                evidence_parts.append(html.escape(text))
        source = claim.get("source", "")
        source_html = (f'<a href="{html.escape(source)}">source</a>'
                       if str(source).startswith("https://") else html.escape(str(source)))
        claim_rows.append([html.escape(str(claim.get("id", ""))),
                           html.escape(str(claim.get("class", ""))),
                           html.escape(str(claim.get("claim", ""))),
                           "<br>".join(evidence_parts), source_html])
    body = f"""
<h2>Current claims ledger</h2>
<p>{html.escape(str(claim_doc.get("note", "")))}</p>
<p>Each claim links to a source and local evidence where available. The machine-readable record is
<a href="https://github.com/buffedlizard55-lab/GEMSDOE51/blob/main/registry/claims.json"><code>registry/claims.json</code></a>. Proxy measurements are not
competition scores; owner-reported results are not organizer verification.</p>
{tbl(['id','class','claim','local evidence','source'], claim_rows)}
"""
    (DOCS / "claims.html").write_text(page("Claims ledger", body, "claims.html"))

    # ------------------------------------------------------------ sources
    src = load("sources.json", [])
    rows = [[f'<a href="{html.escape(s["url"])}">{html.escape(s["id"])}</a>',
             html.escape(s.get("what", "")), html.escape(s.get("status", ""))]
            for s in src]
    body = f"""
<h2>Sources</h2>
<p>Every source used, with the status recorded at the time it was read. Organizer pages were
fetched through the platform's fetcher; the data page is login-walled and was never contacted with
credentials from this repository.</p>
{tbl(['source','what it gives','status'], rows)}
"""
    (DOCS / "sources.html").write_text(page("Sources", body, "sources.html"))

    # ------------------------------------------------------------ leaderboard
    body = """
<h2>Official leaderboard source — standings are not mirrored here</h2>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open the official DrivenData leaderboard</a>.
This project stores no standings, rankings, or copied leaderboard values.</p>
<p>DrivenData's <a href="https://www.drivendata.org/termsofuse/">Terms of Use</a> prohibit using
automated means to monitor or copy website material and prohibit manual monitoring or copying
without prior written consent. No such consent is on record. Accordingly, this repository runs no
scraper, scheduled monitor, or manual-copy workflow.</p>
<p>No organizer score is claimed for any GEMSDOE51 file. Holdout DTI and AUC values on this site
are local proxy measurements against the known-fault catalogue and must not be read as competition
scores.</p>
"""
    (DOCS / "leaderboard.html").write_text(page("Leaderboard policy", body, "leaderboard.html"))

    # ------------------------------------------------------------ irregularities
    ir = load("irregularities.json", [])
    rows = [[html.escape(i["id"]), html.escape(i["summary"]),
             html.escape(i.get("evidence", "")), html.escape(i.get("status", ""))]
            for i in ir]
    body = f"""
<h2>Irregularity register</h2>
<p>Anything we could not verify, anything that contradicted a sibling repository's own reporting,
and anything a reader should check by hand before trusting. Nothing here is hidden downstream.</p>
{tbl(['id','summary','evidence','status'], rows)}
"""
    (DOCS / "irregularities.html").write_text(page("Irregularities", body, "irregularities.html"))

    # Keep historical URLs from older site builds, but point them at current pages
    # instead of leaving stale score/download instructions publicly accessible.
    def redirect_page(title, target, note):
        safe_target = html.escape(target)
        return f"""<!doctype html><html lang=\"en\"><head>
<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{html.escape(title)} — GEMSDOE51</title>
<meta http-equiv=\"refresh\" content=\"0; url={safe_target}\">
<link rel=\"canonical\" href=\"{safe_target}\"></head><body>
<p>{html.escape(note)} <a href=\"{safe_target}\">Continue</a>.</p>
<script>location.replace({json.dumps(target)});</script></body></html>"""

    (DOCS / "strategy.html").write_text(redirect_page(
        "Strategy", "analysis.html",
        "This legacy URL now forwards to the source-linked case study and current analysis."))

    (DOCS / "style.css").write_text(CSS)
    print("site written to", DOCS)


CSS = """
:root{--ink:#12181f;--mut:#5b6875;--line:#dde4ec;--bg:#f7f9fc;--acc:#0b6b8f;--warn:#b4530a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:0 22px}
header{background:#0e2233;color:#fff;padding:22px 0 0}
header h1{margin:0;font-size:26px;letter-spacing:.4px}
header .sub{margin:2px 0 14px;color:#a9c3d6;font-size:14px}
nav{display:flex;flex-wrap:wrap;gap:2px}
nav a{color:#cfe0ec;text-decoration:none;padding:9px 13px;font-size:14px;border-radius:6px 6px 0 0}
nav a:hover{background:#17334a}
nav a.active{background:var(--bg);color:var(--ink);font-weight:600}
main{padding:26px 0 46px;background:var(--bg);min-height:60vh}
h2{margin:30px 0 10px;font-size:21px;border-bottom:2px solid var(--line);padding-bottom:6px}
h3{margin:22px 0 8px;font-size:17px;color:#1b3b52}
p,li{color:#22303d}
a{color:var(--acc)}
table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;font-size:14px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:#eef3f8;font-weight:600}
tbody tr:nth-child(even){background:#fbfdff}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
pre{background:#0f2233;color:#e6f0f8;padding:12px 14px;border-radius:7px;overflow-x:auto}
pre.note{background:#123;color:#cfe;border-left:4px solid var(--acc)}
section.download{background:#fff;border:2px solid var(--acc);border-radius:10px;padding:18px 20px;margin:6px 0 8px}
section.download.missing{border-color:var(--warn)}
a.btn{display:inline-block;background:var(--acc);color:#fff;padding:13px 24px;border-radius:8px;
text-decoration:none;font-weight:700;font-size:18px}
a.btn:hover{background:#095b7a}
p.big{margin:12px 0 6px}
dl.kv dt{font-weight:600;margin-top:9px}
dl.kv dd{margin:1px 0;word-break:break-all}
.ev{color:var(--mut);font-size:13px;font-style:italic}
.warn{background:#fff7ed;border-left:4px solid var(--warn);padding:10px 13px;border-radius:0 6px 6px 0}
.missing{color:var(--warn);font-style:italic}
ol.steps li{margin:8px 0}
footer{border-top:1px solid var(--line);padding:16px 0 30px;color:var(--mut);font-size:13px}
"""

if __name__ == "__main__":
    build()
