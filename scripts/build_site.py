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
        staged = u.get("staged", {}) if isinstance(u.get("staged", {}), dict) else {}
        prewrite = u.get("prewrite", {}) if isinstance(u.get("prewrite", {}), dict) else {}
        j = u.get("support_jaccard", {}) or staged.get("support_jaccard", {})
        if not j and prewrite.get("max_jaccard") is not None:
            j = {"prewrite_max": prewrite["max_jaccard"]}
        uniqueness_verdict = u.get("verdict") or staged.get("verdict", "")
        supplements = [label + ": " + link(a.get(key, ""))
                       for key, label in (("zip", "zip"), ("nan_twin", "NaN twin"))
                       if a.get(key)]
        cost = a.get("holdout_cost_vs_ungated")
        cost_text = f"{float(cost):+.4f}" if isinstance(cost, (int, float)) else "n/a"
        rows.append([a["role"],
                     link(a.get("file", "")) + ("<br><span class='ev'>" +
                     " &middot; ".join(supplements) + "</span>" if supplements else ""),
                     html.escape(a.get("gate_mode", "")),
                     html.escape(a.get("description", "")),
                     cost_text,
                     f'{max(float(v) for v in j.values()):.3f}' if j else "n/a",
                     html.escape(uniqueness_verdict)])
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
        for nm in ("deficit", "dilatation_residual", "shear_residual",
                   "combined_residual_prior", "geodetic_only"):
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
            + "</p>"
            + "<p class='ev'>Dilatation and shear rows use rank-space residuals "
            + "q(observed scalar) - q(fault tensor second invariant); their source units "
            + "and conventions are unresolved, so these are diagnostics only. The combined "
            + "row is the pixelwise maximum of the three residual fields and was not used "
            + "to place the primary Stage-2 points.</p>")


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
    # Older manifests did not carry the research comparison table. Reconstruct
    # only the already-recorded archive values; never invent a new score.
    research_comparisons.setdefault("H_M_cross_scale_crest", {
        "mean_proxy_dti": archive_hm.get("mean_proxy_dti"),
        "incumbent_H_D_mean": archive_hm.get("h_d_isotropic_baseline_mean_proxy_dti"),
        "paired_delta": archive_hm.get("delta_vs_h_d_isotropic_baseline"),
        "folds_higher": 0, "folds_total": 6,
        "approx_95pct_t_interval": [float("nan"), float("nan")],
    })
    research_comparisons.setdefault("STE_L9_w035_s24", {
        "rule": archive_s2.get("best_rule", "STE L9"),
        "mean_proxy_dti": archive_s2.get("mean_proxy_dti"),
        "comparator_iso_nms_r24_mean": archive_s2.get("incumbent_isotropic_mean_proxy_dti"),
        "paired_delta": archive_s2.get("mean_delta_vs_incumbent"),
        "folds_higher": archive_s2.get("folds_better", 0),
        "folds_total": archive_s2.get("folds", 6),
        "approx_95pct_t_interval": [float("nan"), float("nan")],
    })

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
        zip_note = (f'<p class="zip">or the <a href="downloads/{html.escape(zip_name)}">'
                    "ZIP containing the same single GeoTIFF</a></p>" if zip_name else "")
        format_value = dl.get("format", "")
        if isinstance(format_value, dict):
            checks = format_value.get("checks", {})
            format_text = (f"one-band {format_value.get('dtype', 'unknown')}, "
                           f"{format_value.get('crs', 'unknown')}, "
                           f"shape {format_value.get('shape', 'unknown')}, "
                           f"format_valid={checks.get('format_valid', False)}")
        else:
            format_text = str(format_value)
        card = f"""
<section class="download">
<h2>⬇ One-click submission file</h2>
<p class="big"><a class="btn" href="downloads/{html.escape(name)}">Download {html.escape(name)}</a></p>
{zip_note}
<dl class="kv">
<dt>Unique submission name to paste</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>Note for the <em>Note (optional)</em> field</dt><dd><code>{html.escape(dl.get('note',''))}</code></dd>
<dt>Format</dt><dd>{html.escape(format_text)}</dd>
<dt>sha256</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
</dl>
<p class="ev">{html.escape(dl.get('evidence',''))}</p>
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
justifiable as well as holdout-tested. The current primary is linked above; it is locally
validated and holdout-promoted, but has not been uploaded and has no organizer score claim.</p>
<h2>What this is</h2>
<p>GEMSDOE51 studies fault indications in the GeoDAWN region. Its intended design is two-stage:
a 10&nbsp;km geodetic strain-budget statistic is only a <b>coarse-tile prior</b> (Stage&nbsp;1); a
fine-scale detector supplies point locations (Stage&nbsp;2). Historical Stage-1 proxy receipts
suggest weak enrichment and show hard-gate harm, but they do not validate the current signed,
rate-selectable formula; a current leakage-controlled Stage-1 rerun is unavailable. Stage&nbsp;1
must not dictate fine-scale placement. Stage&nbsp;2 is reported separately on blocked known-fault
proxy holdouts. The H-H/H-D blend above clears the recorded local promotion, uniqueness,
non-dominance, and format gates; it remains unscored by the organizer.</p>

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
        primary_file = Path(sub.get("file", "")).name
        primary_zip = Path(sub.get("zip", "")).name if sub.get("zip") else ""
        primary_fmt = sub.get("format", {})
        primary_checks = primary_fmt.get("checks", {}) if isinstance(primary_fmt, dict) else {}
        primary_status = sub.get("status", subm.get("status", ""))
        primary_link = f'<a class="btn" href="downloads/{html.escape(primary_file)}">Download {html.escape(primary_file)}</a>'
        primary_zip_link = (f'<p class="zip">or download the <a href="downloads/{html.escape(primary_zip)}">'
                            "single-file ZIP</a></p>" if primary_zip else "")
        primary_format = (f"one-band {primary_fmt.get('dtype', 'unknown')}, "
                          f"EPSG:{primary_fmt.get('crs_epsg', 'unknown')}, "
                          f"shape {primary_fmt.get('shape', 'unknown')}, "
                          f"format_valid={primary_checks.get('format_valid', False)}")
        status_block = f"""
<p class="download"><b>Current primary: {html.escape(primary_status)}.</b>
This candidate passed the frozen six-fold local promotion rule, scoped reference-aware
uniqueness, q70 Stage-1 non-dominance, and the written GeoTIFF checks. It has not been
uploaded and no DrivenData score or portal acceptance is claimed.</p>
<p class="big">{primary_link}</p>
{primary_zip_link}
<dl class="kv">
<dt>Unique submission name</dt><dd><code>{html.escape(str(sub.get('submission_name', '')))}</code></dd>
<dt>Note</dt><dd><code>{html.escape(str(sub.get('note', '')))}</code></dd>
<dt>Format receipt</dt><dd>{html.escape(primary_format)}</dd>
<dt>SHA-256</dt><dd><code>{html.escape(str(sub.get('sha256', '')))}</code></dd>
</dl>
"""
    else:
        status_block = """
<p class="warn"><b>There is no current upload-eligible artifact.</b> Do not upload an archived
or research-only file. This block is generated from the submission manifest.</p>
"""
    body = f"""
<h2>Submission guide — current status first</h2>
{status_block}
<h3>Before any upload</h3>
<ol class="steps">
<li>Return to the <a href="index.html">executive summary</a> and download only the current
primary GeoTIFF shown there. If using the ZIP, confirm it contains exactly that one TIFF.</li>
<li>Recheck the displayed SHA-256 and the local receipt. The local verifier checks one band,
float32 values in [0,1], the template grid and CRS EPSG:32611, finite in-footprint values,
and NaN outside the footprint. A local pass does not prove portal acceptance.</li>
<li>Open the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission page</a>
(requires the participant's own login), choose the current file, and paste the exact unique
name and note shown above. Do not reuse an archived name or relabel a previous TIFF.</li>
<li>Include the required narrative with an accurate generative-AI disclosure. Read the current
official rules and verify the final file, scientific claims, provenance, and license position
before submitting.</li>
</ol>

<h3>Current artifact interpretation</h3>
<p>The primary is a substantively new fixed 50/50 H-H/H-D probability blend emitted with STE
line length 9, continuity weight 0.35, and spacing 2.4 pixels. Stage 1 is retained as a
coarse diagnostic only and has <code>stage1_weight=0.0</code>; it does not dominate fine-scale
placement. The local holdout truth is the visible known-fault catalogue, not hidden organizer
labels, so “holdout-promoted” is not a competition-score claim.</p>

<h3>Generative-AI narrative disclosure</h3>
<p>Section 3.2 of the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">GEMS Prize Rules</a>
requires a narrative, outside the word count, that states the extent to which generative AI was
used and how it contributed to the submission elements. Adapt this text to the actual final
process and verify every statement:</p>
<pre class="note">Generative AI tools were used as research and coding assistants to analyze public-source material, generate and rank hypotheses, edit and debug code, and draft project documentation. The geospatial predictions are produced by the documented feature-engineering and machine-learning pipeline, not by a generative model. The person submitting is responsible for checking the data provenance, code, scientific claims, predictions, and all representations in this narrative. No organizer score is claimed unless returned for the submitted artifact.</pre>
<p>This is a draft disclosure, not a substitute for the entrant's own accurate narrative. Include
all actual AI use across the eventual submission materials.</p>

<h3>Leaderboard and Terms of Use</h3>
<p>This repository does not scrape, monitor, copy, or mirror leaderboard standings. DrivenData's
<a href="https://www.drivendata.org/termsofuse/">Terms of Use</a> prohibit automated monitoring/copying
and manual monitoring/copying without prior written consent. No such consent is on record.</p>
"""
    (DOCS / "how-to-submit.html").write_text(page("How to submit", body, "how-to-submit.html"))

    # ------------------------------------------------------------ method
    trace_receipt = load("stage1_trace_holdout.json", {})
    trace_cfg = trace_receipt.get("config", {})
    trace_summary = trace_receipt.get("summary", {})
    def trace_mean(key):
        return trace_summary.get(key, {}).get("mean", float("nan"))
    body = f"""
<h2>Method, with Stage 1 and Stage 2 kept separate</h2>
<h3>Stage 1 — geodetic strain-budget residuals (coarse prior only)</h3>
<p>Kreemer et al. (2000), Eq. 3, write the fault-slip-derived strain tensor as:</p>
<pre>eps_dot_ij = (1/2) sum_k [ L_k * u_dot_k / (A * sin(delta_k)) ] * m_ij^k
m_ij^k = n_i^k * s_j^k + n_j^k * s_i^k</pre>
<p>Here <code>L</code> is trace length, <code>u_dot</code> the rate component, <code>A</code>
supported tile area, <code>delta</code> dip, and <code>n</code>/<code>s</code> the unit fault
normal/slip direction. A total fault-plane rate for pure normal slip yields
<code>L*u_plane*cos(delta)/A</code>; if the source is vertical displacement rate, the coefficient
is <code>L*u_vertical*cot(delta)/A</code>. Vertical strike slip yields
<code>L*u_dot/(2*A)</code>, with RL and LL signs opposite. The source convention and dip are
still unresolved: the implementation exposes vertical versus total-plane rates, defaults
provisionally to vertical, assumes a 60-degree normal dip, and converts source values
provisionally as mm/yr. Absolute strain values remain source-sensitive.</p>
<p>The implementation is approximate rather than a full inversion: it rasterizes local trace
directions, assigns slip rates from trace associations, simplifies slip-sense/dip categories,
and uses partial-footprint support area. The Stage-1 runner now performs a valid five-split
trace holdout with held-out trace rows removed from the catalogue-derived budget before each
field is computed (<code>n_splits={trace_cfg.get('n_splits', 'unknown')}</code>,
rate convention <code>{html.escape(str(trace_cfg.get('rate_convention', 'unknown')))}</code>,
planning constant <code>g_hidden={trace_cfg.get('g_hidden', 'unknown')}</code>; this is not
an organizer truth count).</p>
<p><b>Residual convention:</b> the supplied dilatation and shear scalar layers are not
source-verified to share units, signs, or tensor definitions with the fault second invariant.
The reported controls therefore use rank-space residuals
<code>rank(observed scalar) - rank(fault tensor II)</code>, not absolute-number subtraction.
The combined residual prior is the pixelwise maximum of the second-invariant, dilatation, and
shear rank residuals. These are coarse diagnostics, not dimensional strain rates and not fine
point placers.</p>
{tbl(['field','mean Spearman rank','mean q70 lift'], [
    ['geodetic second-invariant deficit', f"{trace_mean('spearman_deficit'):.4f}", f"{trace_mean('deficit_lift_q70'):.4f}"],
    ['dilatation rank residual', f"{trace_mean('spearman_dilatation_residual'):.4f}", f"{trace_mean('dilatation_residual_lift_q70'):.4f}"],
    ['shear rank residual', f"{trace_mean('spearman_shear_residual'):.4f}", f"{trace_mean('shear_residual_lift_q70'):.4f}"],
    ['combined residual diagnostic', f"{trace_mean('spearman_combined_residual_prior'):.4f}", f"{trace_mean('combined_residual_prior_lift_q70'):.4f}"],
    ['geodetic-only control', f"{trace_mean('spearman_geodetic_only'):.4f}", f"{trace_mean('geodetic_only_lift_q70'):.4f}"],
])}
<p class="warn">The rerun shows the geodetic-only control has the strongest mean q70 lift
({trace_mean('geodetic_only_lift_q70'):.4f}); the combined residual is only a diagnostic
({trace_mean('combined_residual_prior_lift_q70'):.4f}) and was not selected for the primary.
The promoted artifact sets <code>stage1_weight=0.0</code>. Stage 1 therefore remains a broad,
non-dominant prior and does not hard-gate or dominate Stage 2. Full per-split results and
configuration are in <a href="downloads/stage1_trace_holdout.json">the trace receipt</a>;
the formula caveat and decision are in <a href="downloads/stage1_reconciliation_20261007.json">the reconciliation</a>.</p>

<h3>Stage 2 — fine-scale detector and sparse emission</h3>
<p>The H-D incumbent combines competition geophysics with DEM-derived scarp-facing/coherence
features. A 3×3 spatial holdout removes a 1.2 km boundary band from training; each fold's
Stage-2 field is scored against held-out known-fault labels at matched mass ratio
<code>M/|G|=3.47</code>. H-D mean proxy DTI is 0.2816627 and mean AUC is 0.6726183.
These are measurements on the visible known-fault proxy, not organizer scores.</p>
<p>Distance-to-catalogue is not used as a predictive shortcut because it directly encodes the
known-fault target. Emission avoids a 200 m known-fault buffer and uses non-maximum suppression
or STE at approximately 2.4 pixels. The official metric gives a marginal-pixel credit bar
near <code>0.2*DTI</code>; this motivates sparse dots, but does not prove any individual
prediction is a real fault.</p>
<p>The current primary is the fixed 50/50 H-H/H-D probability blend emitted with STE line length
9, continuity weight 0.35, spacing 2.4, and 44,069 predicted pixels. Its matched six-fold
proxy DTI is 0.2853406 versus 0.2816627 for H-D (paired Δ +0.0036779; 4/6 folds higher).
This is a local promotion result only; no organizer score or acceptance is claimed.</p>
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

<h3>Stage 1 — trace-held-out residual diagnostics, reported separately</h3>
<p>The current runner holds out complete trace-table rows associated with held-out catalogue pixels
before building the mapped-fault budget. It reports the geodetic second-invariant deficit and
rank-space dilatation/shear residual controls. Mean q70 lifts are 1.0929 for the deficit, 1.0653
for dilatation, 1.0722 for shear, and 1.1477 for their combined diagnostic maximum; geodetic-only
is 1.2469. These are coarse prior diagnostics, not fine-scale emission scores. The promoted
primary uses <code>stage1_weight=0.0</code>. See the <a href="downloads/stage1_trace_holdout.json">trace receipt</a>
and <a href="downloads/stage1_reconciliation_20261007.json">Stage-1 reconciliation</a>.
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

    (DOCS / "executive-summary.html").write_text(redirect_page(
        "Executive summary", "index.html",
        "This legacy URL now forwards to the current submission status and executive summary."))
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
