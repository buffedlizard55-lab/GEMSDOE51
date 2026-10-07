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
        return ("<p class='warn'><b>No current submission artifact is eligible or linked.</b> "
                "The previous candidates are retained outside the published download directory "
                "for audit only; the latest proposal failed uniqueness before a TIFF was written.</p>")

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
    s1stats = subm.get("stage1_stats", {})

    # The download directory is public. Keep only files explicitly named by the
    # current manifest; stale or archived submissions must not remain linkable.
    expected_downloads = set()
    for record in ([sub] if sub else []) + list(arts):
        for key in ("file", "zip", "nan_twin", "checks_file"):
            value = record.get(key)
            if value and Path(value).name == value:
                expected_downloads.add(value)
    for item in downloads.iterdir():
        if item.is_file() and item.name not in expected_downloads:
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    hold = {a: load(f"holdout_{a}.json") for a in
            ("base", "H_E", "H_D", "H_C", "H_ALL", "H_X1")}
    two = load("two_stage_results.json")

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
        card = f"""
<section class="download">
<h2>⬇ One-click submission file</h2>
<p class="big"><a class="btn" href="downloads/{html.escape(name)}">Download {html.escape(name)}</a></p>
{zip_note}
<dl class="kv">
<dt>Unique submission name to paste</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>Note for the <em>Note (optional)</em> field</dt><dd><code>{html.escape(dl.get('note',''))}</code></dd>
<dt>Format</dt><dd>{html.escape(dl.get('format',''))}</dd>
<dt>sha256</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
</dl>
<p class="ev">{html.escape(dl.get('evidence',''))}</p>
</section>"""
    else:
        d = subm.get("decision", {})
        x1 = d.get("h51_x1", {})
        soft = d.get("h_d_soft_w020", {})
        card = f"""<section class="download missing">
<h2>⬇ No eligible submission file</h2>
<p><b>No new GeoTIFF was generated, and no submission slot is recommended.</b>
The narrowed H51-X1 implementation failed its six-fold promotion test
(mean proxy DTI {x1.get('mean_proxy_dti', float('nan')):.4f}, versus
{x1.get('incumbent_h_d_mean_proxy_dti', float('nan')):.4f} for H-D). Its broader
preregistered layer family was not fully tested. The H-D soft w=0.20 proposal had only a small holdout gain and failed uniqueness
(Jaccard {soft.get('uniqueness', {}).get('max_jaccard', float('nan')):.3f};
limit 0.50). Archived TIFFs are not current recommendations and are not linked here.</p>
<p>When a genuinely distinct candidate passes the promotion, format, uniqueness, and
Stage-1 dominance checks, this card will contain the downloadable file, checksum,
unique submission name, and optional note.</p></section>"""

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
    body = card + f"""
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
a 10&nbsp;km geodetic strain-budget statistic is tested only as a <b>weak broad-tile prior</b>
(Stage&nbsp;1); a fine-scale detector supplies point locations (Stage&nbsp;2). The evidence shows
Stage&nbsp;1 is weak, and a hard gate harms Stage&nbsp;2, so the prior must not dictate the fine-scale
map. Both stages are evaluated separately on local spatial holdouts; no current artifact clears all
promotion and uniqueness checks.</p>

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
    body = """
<h2>Submission guide — current status first</h2>
<p class="warn"><b>There is no eligible file to upload today.</b> Do not use the archived zero-outside
files: they fail the official null/NaN-outside requirement. Do not re-upload a previous candidate:
the only new proposal that passed the numeric holdout screen failed the local uniqueness check before any TIFF was written. No weekly slot is recommended.</p>
<h3>When a candidate is cleared</h3>
<ol class="steps">
<li>Return to the <a href="index.html">executive summary</a> and download only the GeoTIFF linked in
the current eligibility card; check its SHA-256 against the receipt shown there.</li>
<li>Open the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission page</a>
(requires the participant's own login).</li>
<li>Choose the single-band <code>.tif</code> file, or the linked <code>.zip</code> containing exactly
that one GeoTIFF.</li>
<li>Paste the unique submission name and short note displayed on the executive summary. Do not
reuse names or notes from archived candidates.</li>
<li>Include the required narrative with an accurate generative-AI disclosure (template below). Read
the official rules before submitting and select one final file for both prize rounds by the deadline.</li>
</ol>

<h3>Official format checklist</h3>
<p>DrivenData specifies EPSG:32611, 100 m, matching bounds, one float32 band, values in [0,1], and
null/NaN outside the bounds. The repository writer now emits NaN outside and verifies the written
bytes. This local check does not prove acceptance by the portal. If the validator reports an error,
retain the exact rejected file and message for diagnosis; do not assume an unverified root cause.</p>

<h3>Generative-AI narrative disclosure</h3>
<p>Section 3.2 of the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">September 2026 GEMS Prize Rules</a>
requires a narrative, outside the word count, that states the extent to which generative AI was used
and how it contributed to the submission elements. Adapt this text to the actual final process and
verify every statement before submission:</p>
<pre class="note">Generative AI tools were used as research and coding assistants to analyze public-source material, generate and rank hypotheses, edit and debug code, and draft project documentation. The geospatial predictions are produced by the documented feature-engineering and machine-learning pipeline, not by a generative model. The person submitting is responsible for checking the data provenance, code, scientific claims, predictions, and all representations in this narrative. No organizer score is claimed unless returned for the submitted artifact.</pre>
<p>This is a draft disclosure, not a substitute for the entrant's own accurate narrative. Include all
actual AI use across the eventual submission materials.</p>

<h3>Leaderboard and Terms of Use</h3>
<p>This repository does not scrape, monitor, copy, or mirror leaderboard standings. DrivenData's
<a href="https://www.drivendata.org/termsofuse/">Terms of Use</a> prohibit automated monitoring/copying
and manual monitoring/copying without prior written consent. No such consent is on record.</p>
"""
    (DOCS / "how-to-submit.html").write_text(page("How to submit", body, "how-to-submit.html"))

    # ------------------------------------------------------------ method
    body = """
<h2>Method, with Stage 1 and Stage 2 kept separate</h2>
<h3>Stage 1 — geodetic strain-budget deficit (coarse prior only)</h3>
<p>Kreemer et al. (2000), Eq. 3, write the fault-slip-derived strain tensor as:</p>
<pre>eps_dot_ij = (1/2) sum_k [ L_k * u_dot_k / (A * sin(delta_k)) ] * m_ij^k
m_ij^k = n_i^k * s_j^k + n_j^k * s_i^k</pre>
<p>Here <code>L</code> is the trace-segment length, <code>u_dot</code> the slip rate,
<code>A</code> the supported tile area, <code>delta</code> dip, and <code>n</code> and
<code>s</code> the unit fault normal and slip direction. For a vertical pure strike-slip segment,
the horizontal shear coefficient is <code>L*u_dot/(2*A*sin(delta))</code>. For pure dip slip,
the horizontal projections yield <code>L*u_dot*cos(delta)/A</code>. This is the tensor formula in
<a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">Kreemer et al. (2000), Eq. 3</a>;
the exact code and unit conversions are in <code>src/gems51/strain_budget.py</code>.</p>
<p>The implementation is approximate, not a full inversion: it rasterizes local trace directions,
assigns slip rates by nearest trace centroid, simplifies slip-sense/dip categories, and lacks
per-segment rake. Partial tiles use actual footprint support area. The local slip-rate column is
provisionally interpreted as mm/yr; the NBMG <a href="https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0?f=pjson">layer schema</a>
lists numeric <code>SLIPRTNUM</code> but not its units, and the linked GDR field-definition text was
not audited locally. Absolute strain values are not source-validated. The quantile comparison is
invariant to a uniform rescaling, but not to mixed units or record-specific errors. The competition
geodetic layers have no recoverable exact invariant identity, so the Stage-1 prior is built in quantile space,
<code>Q(observed second-invariant layer) - Q(fault tensor invariant)</code>. Do not subtract raw
scalar dilation/shear from the fault tensor invariant as if their units and conventions matched.</p>
<p><b>Measured Stage-1 holdout:</b> deficit Spearman vs held-out known-fault density = 0.03916;
geodetic-only = 0.09930. Top-50% tile lift is 1.08290 for the deficit and 1.23864 for geodetic-only.
Stage 1 alone has mean randomized DTI 0.14810 versus 0.18615 uniform using the provisional
full-map mass assumption g_hidden=12,700. This is not an organizer label count. Stage 1 is a weak
prior, not a fine-scale locator. Evidence: <a href="../data/stage1_trace_holdout.json">trace holdout</a> and
<a href="../data/two_stage_results.json">separate two-stage scores</a>.</p>

<h3>Stage 2 — fine-scale detector and sparse emission</h3>
<p>The H-D incumbent combines competition geophysics with DEM-derived scarp-facing/coherence
features. A 3x3 spatial holdout removes a 1.2 km boundary band from training; each fold's Stage-2
field is scored against held-out known-fault labels at matched mass ratio <code>M/|G|=3.47</code>.
H-D mean proxy DTI is 0.2816627 and mean AUC is 0.6726183. These are measurements on the visible
known-fault proxy, not organizer scores.</p>
<p>Distance-to-catalogue is not used as a predictive shortcut because it directly encodes the
known-fault target. Emission avoids a 200 m known-fault buffer and uses non-maximum suppression at
2.4 pixels. The official metric gives a marginal-pixel credit bar near <code>0.2*DTI</code>; this
motivates sparse dots, but does not prove any individual prediction is a real fault.</p>
<p><b>Where Stage 1 enters:</b> only as a soft multiplicative score adjustment,
<code>field * (1 + w*z)</code>, over the full footprint. No hard Stage-1 tile mask is applied. A
soft <code>w=0.20</code> had a small proxy gain (+0.000483 paired mean, 4/6 folds), and the
Stage-1 top-half lift for the in-memory candidate was 0.98592. However, its support duplicated the
existing soft-0.10 candidate (Jaccard 0.86130, over the 0.50 uniqueness limit), so the writer
correctly stopped before producing any TIF.</p>
<p class="warn"><b>Leading new feature result:</b> the narrowed H51-X1 magnetic/gravity edge-normal
implementation used rank-normalized total-magnetic and isostatic-gravity bands as new-transform
inputs; the planned derivative bands remained in the common baseline stack but were not used by this
transform. It scored mean proxy DTI 0.2796713, below H-D by 0.0019913, and was positive in only 3/6
folds. It failed the frozen promotion rule. The broader preregistered layer-family hypothesis was
not fully tested. Do not describe this implementation as a win or submit it.</p>
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
<h2>Preregistered geological hypotheses</h2>
<p>Four distinct hypotheses were ranked before implementation. Each row identifies its layers,
physical signature, missing-fault rationale, novelty against this repository, expected benefit and
cost, and external-data requirements. A narrowed H51-X1 implementation has been tested; the
full preregistered layer family and all other hypotheses remain untested. The table does not convert
unmeasured ideas into scores. Local holdout labels are a known-fault proxy.</p>
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
<p>H-D is the current incumbent at 0.2816627 mean proxy DTI (AUC 0.6726183). The narrowed H51-X1
implementation (total magnetic + isostatic gravity as new-transform inputs) scores 0.2796713
(delta -0.0019913) and is positive on 3/6 folds, so it fails the frozen promotion rule. The broader
preregistered derivative-band family was not fully tested; these remain proxy results.</p>

<h3>Stage 1 — trace-held-out prior test, reported separately</h3>
<p>Five splits hold out complete trace-table rows associated with held-out catalogue pixels before
building the mapped-fault budget. The test compares tile-rank priors against held-out known-fault
density; it is not a test against hidden expert labels.</p>
{_STAGE1}

<h3>Stage 1 alone and hard-gate effect on Stage 2</h3>
<p>Stage-1-only dots are randomized in approved tiles. This standalone DTI control uses the
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
See <a href="../knowledge/preregistration-2026-10-07.md">frozen preregistration and appended outcome</a>.</p>

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
                    f'<a href="../{html.escape(candidate)}">{html.escape(text)}</a>')
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
<a href="../registry/claims.json"><code>registry/claims.json</code></a>. Proxy measurements are not
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
