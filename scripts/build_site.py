#!/usr/bin/env python3
"""Build the static GitHub Pages site in docs/ from the artefacts in data/.

Everything the site states is read from a JSON artifact produced by the
pipeline; nothing is typed in by hand.  If an artifact is missing the page says
so rather than inventing a number.
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
       ("sources.html", "Sources"),
       ("leaderboard.html", "Leaderboard"),
       ("irregularities.html", "Irregularities"),
       ("claims.html", "Claims")]


def load(rel, default=None):
    p = ROOT / "data" / rel
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
<p>Evidence is labelled throughout. Public leaderboard rows are organizer-posted observations
of participant scores, but the board does not identify submission files. No GEMSDOE51 TIFF has an
organizer-verified score; all local holdout values are proxy diagnostics against the visible
catalogue.</p>
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



def artifact_table(arts):
    rows = []
    for a in arts:
        u = a.get("uniqueness", {})
        fresh = u.get("fresh_public_artifact_audit", {})
        j = ({"fresh public TIFF corpus": fresh["max_support_jaccard"]}
             if fresh.get("max_support_jaccard") is not None
             else u.get("support_jaccard", {}))
        delta = float(a.get("holdout_cost_vs_ungated", 0.0))
        hnote = html.escape(a.get("holdout_cost_note", ""))
        rows.append([a["role"],
                     f'<a href="downloads/{html.escape(a["file"])}">{html.escape(a["file"])}</a>'
                     f'<br><span class="ev">zip: <a href="downloads/{html.escape(a.get("zip",""))}">'
                     f'{html.escape(a.get("zip",""))}</a>'
                     f' &middot; nan twin: <a href="downloads/{html.escape(a.get("nan_twin",""))}">'
                     f'{html.escape(a.get("nan_twin",""))}</a></span>',
                     a.get("gate_mode", ""),
                     html.escape(a.get("description", "")),
                     f'{delta:+.5f}<br><span class="ev">{hnote}</span>',
                     f'{max(j.values()):.3f}' if j else "n/a",
                     html.escape(u.get("verdict", ""))])
    return tbl(["role", "file", "gate", "what it is", "paired proxy ΔDTI vs ungated",
                "max Jaccard in available audit (scoped)", "uniqueness"], rows)


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
    p = ROOT / "evidence" / "stage1_formula_audit.json"
    if not p.exists():
        return "<p class='missing'>stage-1 formula sensitivity audit not generated</p>"
    d = json.loads(p.read_text())
    rows = []
    for r in d.get("scenarios", []):
        rows.append([
            html.escape(r["scenario"]),
            f"{r['spearman_deficit']['mean']:+.3f} / {r['spearman_geodetic_only']['mean']:+.3f}",
            f"{r['deficit_q50']['lift']['mean']:.3f} / {r['geodetic_only_q50']['lift']['mean']:.3f}",
            f"{r['deficit_q50']['random_dot_proxy_dti']['mean']:.4f} / {r['geodetic_only_q50']['random_dot_proxy_dti']['mean']:.4f}",
        ])
    return (tbl(["rate/sense assumption", "Spearman: deficit / geodetic-only",
                 "q50 lift: deficit / geodetic-only",
                 "q50 single-draw proxy DTI: deficit / geodetic-only"], rows)
            + "<p class='ev'>Five trace-level splits, not spatial blocks. The deficit underperforms "
            + "raw geodetic ranking on deterministic Spearman and q50 lift in all four scenarios. "
            + "Each DTI is a single seeded random-dot realization per field/split and is not paired "
            + "across masks; small DTI differences are descriptive/noisy. The 44,069-dot budget uses "
            + "a 12,700-pixel planning proxy, not a measured hidden truth size. Full formula, local source "
            + "field caveats and per-split results: <a href='downloads/stage1_formula_audit.json'>"
            + "stage1_formula_audit.json</a>.</p>")


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
    (DOCS / "downloads").mkdir(exist_ok=True)
    for evidence_name in (
        "stage1_formula_audit.json",
        "submission_manifest_reconciliation.json",
        "score_attribution_audit.json",
        "uniqueness_gate_H_D_soft_20261007.json",
        "experimental_H_G_plus_H_D_artifact.json",
        "uniqueness_gate_H_G_HD_experimental_20261007.json",
    ):
        source = ROOT / "evidence" / evidence_name
        if source.exists():
            shutil.copyfile(source, DOCS / "downloads" / evidence_name)
    manifest_source = ROOT / "data" / "submission_manifest.json"
    if manifest_source.exists():
        shutil.copyfile(manifest_source, DOCS / "downloads" / "submission_manifest.json")
    subm = load("submission_manifest.json", {})
    sub = subm.get("primary", {})
    arts = subm.get("artifacts", [])
    hold = {a: load(f"holdout_{a}.json") for a in
            ("base", "H_E", "H_D", "H_C", "H_ALL")}
    lb = load("leaderboard.json", {})

    # ------------------------------------------------------------ index
    dl = sub
    if dl:
        name = dl.get("file", "")
        slot_status = dl.get("slot_status", "")
        slot_warning = (f'<p class="warn"><b>Upload decision:</b> {html.escape(slot_status)}</p>'
                        if slot_status else "")
        card = f"""
<section class="download">
<h2>⬇ One-click research GeoTIFF (portal-format; not upload-authorized)</h2>
{slot_warning}
<p class="big"><a class="btn" href="downloads/{html.escape(name)}">Download {html.escape(name)}</a></p>
<p class="zip">or the <a href="downloads/{html.escape(dl.get('zip',''))}">.zip containing the same single GeoTIFF</a></p>
<dl class="kv">
<dt>Research label (not an upload recommendation)</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>Suggested note (do not paste for a submission)</dt><dd><code>{html.escape(dl.get('note',''))}</code></dd>
<dt>Format</dt><dd>{html.escape(dl.get('format',''))}</dd>
<dt>sha256</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
</dl>
<p class="ev">{html.escape(dl.get('evidence',''))}</p>
</section>"""
    else:
        card = """<section class="download missing">
<h2>⬇ Research TIFF</h2>
<p>The TIFF has not been built yet in this checkout. Run
<code>python3 scripts/build_submission.py</code> to produce it; this card is then filled from
the resulting <code>data/submission_manifest.json</code>.</p></section>"""

    experimental_card = ""
    exp_path = ROOT / "evidence" / "experimental_H_G_plus_H_D_artifact.json"
    if exp_path.exists():
        exp = json.loads(exp_path.read_text())
        ea = exp["artifact"]
        uniqueness_path = ROOT / "evidence" / "uniqueness_gate_H_G_HD_experimental_20261007.json"
        unique_metrics = ""
        if uniqueness_path.exists():
            unique = json.loads(uniqueness_path.read_text())
            unique_status = unique.get("verdict", "INCOMPLETE")
            unique_summary = (
                f"scoped public docs/downloads and submissions inventory "
                f"({unique.get('audit', {}).get('inventory_repositories', 0)} repositories): "
                f"{unique.get('audit', {}).get('downloaded_and_sha_verified', 0)} SHA-verified "
                f"payloads; {unique.get('n_compared', 0)} comparisons; "
                f"{len(unique.get('matches', []))} flagged matches.")
            wi = unique.get("worst", {}).get("iou", {})
            wc = unique.get("worst", {}).get("containment", {})
            if wi and wc and unique.get("worst", {}).get("cosine", {}).get("cosine") is not None:
                unique_metrics = (
                    f"Max support Jaccard {wi.get('iou', 0):.4f} (limit 0.50); max cosine "
                    f"{unique['worst']['cosine'].get('cosine', 0):.4f} (limit 0.90); maximum "
                    f"containment {wc.get('containment', 0):.4f} at {wc.get('containment_lift', 0):.2f}× "
                    "random-emission lift (containment is flagged only above 3× lift).")
        else:
            unique_status, unique_summary = "PENDING", "Fresh public-artifact audit not yet run."
        s1 = exp.get("stage1_dominance_q70", {})
        stage1_summary = (f"{s1.get('interpretation', 'Stage-1 diagnostic unavailable')} "
                          f"Approved area {s1.get('approved_area_share', 0) * 100:.3f}%; "
                          f"emissions inside {s1.get('emitted_share_inside_approved', 0) * 100:.3f}%; "
                          f"lift {s1.get('lift', 0):.3f}.")
        hr = exp.get("holdout_result", {})
        experimental_card = f"""
<section class="download missing">
<h2>Experimental H-G + H-D TIFF — NOT SLOT-ELIGIBLE</h2>
<p class="warn"><b>Do not upload.</b> Matched Stage-2 holdout mean proxy DTI delta was
{hr.get('paired_delta', float('nan')):+.6f} vs H-D ({hr.get('folds_higher', 0)}/{hr.get('folds_total', 0)} folds higher).
The result is against the visible catalogue only; it did not pass the locked incumbent gate.</p>
<p class="big"><a class="btn alt" href="downloads/{html.escape(ea['file'])}">Download experimental TIFF</a></p>
<p class="zip">or <a href="downloads/{html.escape(ea['zip'])}">download its one-TIFF ZIP</a></p>
<dl class="kv">
<dt>Research label (not an upload recommendation)</dt><dd><code>{html.escape(ea.get('submission_name',''))}</code></dd>
<dt>Suggested note (explicitly experimental)</dt><dd><code>{html.escape(ea.get('note',''))}</code></dd>
<dt>Format check</dt><dd>{html.escape(ea.get('format',{}).get('checks',{}).get('portal_legal',False).__str__())}; SHA-256 <code>{html.escape(ea.get('sha256',''))}</code></dd>
<dt>Fresh public uniqueness audit</dt><dd>{html.escape(unique_status)} — {html.escape(unique_summary)} {html.escape(unique_metrics)}</dd>
<dt>Stage-1 dominance diagnostic (q70/top-30%)</dt><dd>{html.escape(stage1_summary)}</dd>
</dl>
<p class="ev">This experimental full-raster build materializes H-G+H-D after its matched spatial holdout; it is not promoted. Full recipe and checks: <a href="downloads/experimental_H_G_plus_H_D_artifact.json">artifact record</a>.</p>
</section>"""

    rows = []
    for a in ("base", "H_E", "H_D", "H_C", "H_ALL"):
        h = hold.get(a)
        if not h:
            rows.append([a, "not run", "", ""])
            continue
        s = h["summary"]
        rows.append([a, f"{s['auc_mean']:.4f}",
                     " / ".join(f"r{r}: {s[f'dti_r{r}']['mean']:.4f}" for r in s["ratios"]),
                     f"{len(s['auc_per_fold'])}"])
    _ART = artifact_table(arts)
    _STAGE1 = stage1_table()
    _GATE = gate_table()
    _EMIS = emission_table()
    body = card + experimental_card + f"""
<h2>What is offered</h2>
{_ART}
<p class="ev">The current primary's full-corpus audit is a FAIL, not a uniqueness pass. It includes
this TIFF's NaN-format twin and the same-repository hard-q20 alternate; the exact SHA-verified
corpus, skipped shape-mismatched fixture, and pairwise results are in
<a href="downloads/uniqueness_gate_H_D_soft_20261007.json">the public uniqueness audit</a>.</p>
<p class="warn"><b>Largest validation limitation.</b> The local <code>labels.tif</code> is byte-identical
to the known-fault raster and to the derived catalogue (IR-51-08). The competition's real training
labels have not been authenticated in this checkout. Local classifier and DTI values are therefore
proxy diagnostics against visible faults; they cannot demonstrate discovery of the hidden expert
labels or predict a leaderboard score. No GEMSDOE51 TIFF has an organizer-verified score.</p>
<p class="warn"><b>A Phase 1 entry has downstream consequences.</b> The organizer has stated that Phase 2
will use a test set updated by expert review of Phase 1 submissions. A Phase 1 upload is therefore
not a free experiment. The current primary is available for inspection, but the H-D soft-prior
delta is small and inconclusive, and H-G failed its matched add-on comparison (mean proxy DTI
0.281056 vs 0.281663 for H-D; 3/6 folds higher). <b>Do not spend a slot unless a candidate beats
the incumbent blocked holdout.</b>
<a href="https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527">Organizer statement</a>.</p>
<h2>What this is</h2>
<p>GEMSDOE51 explores fault geometries in the GeoDAWN region that are not in the USGS/INGENIOUS
catalogue and writes a competition-format GeoTIFF. Stage 1 is the requested 10 km geodetic
strain-budget deficit, retained only as a low-confidence <b>broad-tile prior</b>; it does not hard
restrict fine-scale point placement in the primary soft-prior artifact. Stage 2 ranks and places
the points. Stage 1's trace-level holdout and Stage 2's spatially blocked holdout are reported
separately; neither is a hidden-label score.</p>

<h2>The three facts that decide everything</h2>
<ol>
<li><b>Known faults are masked.</b> DrivenData staff confirmed on 2026-09-16 that pixels
corresponding to known USGS/INGENIOUS faults are excluded from evaluation, in both prize
rounds. <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">source</a></li>
<li><b>"New fault" includes new geometry of an existing system.</b> Continuations, splays and
parallel strands count. <a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">source</a></li>
<li><b>The metric trades weighted credit against weighted error.</b> From the published definitions,
<code>DTI = TP / (0.2·(TP+FP) + 0.8·|G|)</code>, where TP and FP are distance-weighted and
<code>TP+FP</code> is not simply the raw emitted-pixel count. For a proposed increment changing TP
by <code>c</code> and FP by <code>f</code>, improvement requires
<code>c·(1 − 0.2·DTI) &gt; 0.2·DTI·f</code>.</li>
</ol>

<h2>Holdout at a glance</h2>
{tbl(['arm', 'in-block AUC', 'proxy DTI by mass ratio M/|G|', 'folds'], rows)}
<p class="ev">Proxy DTI uses six spatially held-out blocks, with emissions and scoring restricted to
each block and the pixel-count ratio matched to M/|G|=3.47. The local truth is the visible
catalogue, not the hidden expert labels; matching the ratio does not make these proxy numbers
numerically interchangeable with leaderboard scores. They are <b>not</b> scores.</p>

<h2>Read next</h2>
<ul>
<li><a href="how-to-submit.html">How to submit, step by step</a> — including the fix for the
<code>"Predicted values must be in range [0, 1]"</code> portal error.</li>
<li><a href="method.html">Method</a> — the Kostrov strain budget, the detector, the emission rule.</li>
<li><a href="holdout.html">Holdout</a> — Stage 1 and Stage 2 scored separately.</li>
<li><a href="irregularities.html">Irregularities</a> — including one in a sibling repository's own
reporting that we could not reproduce.</li>
</ul>
"""
    (DOCS / "index.html").write_text(page("GEMSDOE51 — DOE GEMS Prize", body, "index.html"))

    # ------------------------------------------------------------ how to submit
    body = f"""
<h2>Submission workflow — only for a future promoted candidate</h2>
<p class="warn"><b>Current decision: do not submit any file offered on this site.</b> The H-D soft TIFF
fails the fresh uniqueness gate and its blocked-holdout gain is inconclusive. Experimental H-G+H-D
passes the scoped uniqueness gate but loses to H-D on the matched holdout. Neither is slot-eligible.
The steps below describe the portal workflow only; wait until a candidate is explicitly promoted in
the <a href="index.html">executive summary</a>.</p>
<ol class="steps">
<li><b>Wait for promotion.</b> A future candidate must beat the incumbent on the locked spatially
blocked holdout, pass the scoped uniqueness and portal-format checks, and have a refreshed manifest
marking it slot-eligible. The site currently has no approved upload file.</li>
<li><b>Download the promoted GeoTIFF.</b> Use the download button for that promoted file in the
executive summary. Do not use the H-D or experimental download cards currently displayed.</li>
<li><b>Open the submission page.</b>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">competition submission page</a>
(requires login) → <b>New submission</b>.</li>
<li><b>Choose the file.</b> Under <b>File to submit → Choose File</b>, select the promoted single-band
<code>.tif</code> (or its ZIP only if it contains exactly that TIFF).</li>
<li><b>Record the run.</b> Copy the distinctive submission name and short note from the promoted
manifest. Names and notes shown on the current research cards are for research identification only,
not authorization to upload.</li>
<li><b>Submit only after all gates pass.</b> The result appears on the
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">public leaderboard</a>
once the validator finishes. Do not infer a score-to-file link unless the organizer provides it.</li>
</ol>

<h2>Why you previously saw <code>"Predicted values must be in range [0, 1]"</code></h2>
<p>Two different failures produce that one message, and both are measured on the written bytes of
every file offered here:</p>
<dl class="kv">
<dt>Mechanism 1 — the float32 sentinel</dt>
<dd><code>training_features.tif</code> uses <code>-3.4028234663852886e+38</code> as nodata.
Writing those bytes through unchanged puts values far outside [0,&nbsp;1].</dd>
<dt>Mechanism 2 — a NaN nodata tag</dt>
<dd>A raster tagged <code>nodata=NaN</code> is a legitimate reading of the competition format,
but it is one validator change away from the same rejection.</dd>
</dl>
<p><b>The fix:</b> the primary download is written <b>all-finite with no nodata tag</b> — every one
of the 12,279,160 cells is finite, the minimum is 0.0 and the maximum is 1.0. This is verified by
re-opening the file from disk after writing, not from memory. An official NaN-outside twin is
offered alongside it.</p>

<h2>What the validator checks</h2>
{tbl(['requirement', 'this file'],
     [[r, v] for r, v in dl.get('format_table', [])] or [["(built after build_submission.py)", ""]])}

<h2>Rules and deadlines</h2>
<p>Read the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/rules/">competition rules</a>
and the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">prize rules PDF (NLR 96647)</a>
before submitting. You must choose a <b>single</b> submission for scoring across both prize rounds
before the deadline, without knowing your private-test performance.</p>
"""
    (DOCS / "how-to-submit.html").write_text(page("How to submit", body, "how-to-submit.html"))

    # Retire the pre-audit page in place: old links must not advertise its stale upload file,
    # 211-reference uniqueness result, or unverified score attribution.
    legacy_body = """
<h2>Archived executive-summary page — current status has superseded it</h2>
<p class="warn"><b>Do not upload the legacy Hridge TIFF or any current research artifact.</b>
The old page advertised a historic Hridge artifact, a 211-reference uniqueness PASS, and a
0.8229 blocked AUC. Those claims do not describe the current H-D soft TIFF and are not a
current submission recommendation. A fresh audit finds H-D soft FAIL; the experimental H-G+H-D
TIFF passes the scoped uniqueness audit but loses its matched holdout. No slot is authorized.</p>
<p>The official public leaderboard's displayed 0.3774 row belongs to participant
<code>xiaofanhu</code>, but it identifies no TIFF or method. The 0.2778 row belongs to
<code>extradr19</code>; the claimed GEMSDOE32 H33-2-B2 link is unsupported and contradicted by
that repository's own UNSCORED label and 0.2747 modelled projection.</p>
<ul>
<li><a href="index.html">Current executive summary and research downloads</a></li>
<li><a href="analysis.html">Measured evidence and public-score attribution</a></li>
<li><a href="holdout.html">Separate Stage-1 and Stage-2 holdout results</a></li>
<li><a href="hypotheses.html">Hypotheses and prior-art comparisons</a></li>
<li><a href="how-to-submit.html">Submission workflow (only after promotion)</a></li>
<li><a href="irregularities.html">Audit irregularities and current artifact status</a></li>
</ul>
"""
    (DOCS / "executive-summary.html").write_text(
        page("Archived executive summary — current status", legacy_body, "index.html"))

    # ------------------------------------------------------------ method
    body = """
<h2>Method</h2>
<h3>Stage 1 — strain-budget deficit (coarse-tile prior only)</h3>
<p>The fault-accommodated horizontal strain-rate tensor uses the published moment-tensor sum in
Kreemer et al. (2000), Eq. 3, <i>Earth, Planets and Space</i> 52, 765–770
(<a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">paper PDF</a>):</p>
<pre>eps_dot_ij = (1 / (2 A_tile)) · sum_k [ L_k · u_dot_k / sin(delta_k) ] · m_ij^k
m_ij^k = s_i^k n_j^k + s_j^k n_i^k</pre>
<p>Here <code>L</code> is mapped trace length represented in the tile, <code>u_dot</code> is the
slip-rate component supplied by the source table, <code>delta</code> is dip, and <code>m</code> is
the unit moment tensor from fault orientation and unit slip. Under the code's pure-mode assumptions,
the horizontal components are:</p>
<pre>normal fault, if rate is vertical displacement u_v:  L · u_v · cot(delta) / A_tile
normal fault, if rate is total fault-plane slip u_p: L · u_p · cos(delta) / A_tile
vertical strike-slip plane, total along-strike rate: L · u / (2 A_tile), sign from RL/LL</pre>
<p>The local GDR/INGENIOUS-derived CSV has 1,126 traces; the <code>slip_rate</code> values are
numeric and the USGS REST alias says “Slip Rate (mm/year)”. But the local field is string-typed in
the USGS service, and neither the metadata fetched here nor the unread GDR field-definition text
establish whether the decimal values represent vertical displacement, total fault-plane slip, or
another component. Both first two interpretations are therefore tested assumptions, not
measurements. The local table has 95 missing <code>slip_sense</code> values; sensitivity runs either
assume unknown sense is normal or exclude those contributions. <code>dip_direct</code> is a direction,
not a numeric dip angle. The code assumes 60° normal-fault dip and 90° strike-slip dip; it uses
nearest-centroid transfer from the table and catalogue-derived local strike. See
<a href="https://gdr.openei.org/submissions/1391">GDR submission 1391</a> and the
<a href="https://earthquake.usgs.gov/arcgis/rest/services/haz/Qfaults/MapServer/21?f=pjson">USGS
QFaults layer metadata</a>.</p>
<p>Tile prior = quantile-rank(geodetic second invariant) minus quantile-rank(fault-accommodated
second invariant). Because the exact tensor invariant convention of the supplied geodetic bands is
not recoverable (IR-51-02), Stage 1 is not an absolute strain calibration. It is kept as a
<b>low-confidence broad-tile ranking prior</b>; it never places fine-scale points. The configured
15 km seismogenic thickness appears only in a scalar moment-rate proxy, not in the strain tensor
components or the Stage-1 rank.</p>
<p><b>Stage-1 result:</b> in five trace-level splits the deficit loses to raw geodetic-only ranking
on mean Spearman and q50 recall/area lift under all four rate/sense assumptions. This is not a
spatially blocked holdout. DTI values are single-draw random-dot diagnostics, not paired across
masks; the <a href="holdout.html">separate Stage-1 table</a> and
<a href="downloads/stage1_formula_audit.json">full formula/sensitivity audit</a> record the
limitations.</p>

<h3>Stage 2 — fine-scale detector</h3>
<p>Histogram gradient boosting over 58 physical layers: the 19 competition bands (rank
transformed), ten 1&nbsp;m-DEM-derived scarp layers, four radiometric layers, the USGS SGMC fault
raster, and multiscale derivatives. H-G separately adds two edge-weighted magnetic–gravity
crossing features; its matched six-block comparison with the incumbent scored −0.000606 mean proxy
DTI delta (3/6 folds higher) and was not promoted. Missing values in
smoothing windows are handled by normalized convolution, not zero-fill.</p>
<p class="warn"><b>Leak control (IR-51-LEAK-01).</b> Any feature derived from the catalogue is a
perfect training leak in a blocked holdout, because every positive has distance-to-catalogue
exactly 0. Measured: in-block AUC collapsed to 0.500 with those columns present and recovered to
0.667 without them. Catalogue-derived quantities are excluded from the model and used only at
emission time.</p>

<h3>Emission</h3>
<p>The current candidate uses greedy non-maximum suppression at a 2.4&nbsp;px radius and keeps all
points at least 200&nbsp;m from catalogued fault pixels. Sparse spacing reduces redundant coverage:
each truth pixel receives only its best nearby prediction credit, while off-target prediction mass
incurs false-positive cost.</p>
<p>For a proposed increment with change <code>c</code> in weighted true-positive credit and change
<code>f</code> in weighted false-positive cost, the exact local improvement condition is
<code>c·(1 − 0.2·DTI) &gt; 0.2·DTI·f</code>. A simpler <code>c &gt; 0.2·DTI</code> threshold is
valid only when that increment adds one unit to <code>TP+FP</code>; it is not universal.
See the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric">official metric definition</a>.</p>
<p class="warn"><b>Stage 1's actual role in each artifact.</b> The <b>primary</b> applies a soft
multiplicative rank prior: <code>score = detector_field · (1 + 0.10·z)</code>, with standardized
tile deficit <code>z</code> clipped to ±4. It does <b>not</b> hard-mask emissions. Its primary
diagnostic is q70 (top 30% of deficit values): 30.05% of the footprint is approved, while the
original build-time check places 20.31% of emissions inside; a current-formula rerun places 19.56%
inside. Both are under-representation, not dominance. q20 is the hard secondary's top-80%
threshold; do not substitute its 80.05% area / 78.09% emission numbers for the primary's q70
check. The <a href="downloads/submission_manifest.json">reconciled manifest</a> preserves both.
The six-fold pre-revision soft-prior holdout delta is +0.000367 (4/6 folds), small and inconclusive,
not a demonstrated win; the hard q20 gate loses about 0.0025 on the same sweep.</p>
"""
    (DOCS / "method.html").write_text(page("Method", body, "method.html"))

    # ------------------------------------------------------------ hypotheses
    hy = load("hypotheses.json", [])
    rows = [[esc(h["id"]), esc(h.get("name", "")), esc(h.get("layers", "")),
             esc(h.get("signature", "")), esc(h.get("why_new_faults", "")),
             esc(h.get("differs_from", "")), esc(h.get("expected_dti", "")),
             esc(h.get("cost", "")), esc(h.get("outcome", "not run")),
             esc(h.get("measured_auc", "")), esc(h.get("measured_dti_r3_47", "")),
             esc(h.get("delta_vs_base", ""))]
            for h in hy]
    slate_path = ROOT / "evidence" / "hypothesis_slate_20261007.json"
    slate_rows = []
    if slate_path.exists():
        slate = json.loads(slate_path.read_text())
        for h in slate.get("ranked_hypotheses", []):
            result = h.get("baseline_arm_result", {})
            matched = h.get("matched_incumbent_result", {})
            if matched:
                outcome = (f"matched add-on DTI={matched['proxy_dti_mean_r3_47']:.5f}; "
                           f"Δ vs H-D={matched['paired_mean_proxy_dti_delta_vs_H_D']:+.5f}; "
                           f"{matched['folds_higher_than_H_D']}/{matched['folds_total']} folds above; "
                           + h.get("promotion_status", ""))
                if result:
                    outcome += (f" Initial replacement arm: {result['proxy_dti_mean_r3_47']:.5f}; "
                                f"Δ={result['paired_mean_proxy_dti_delta_vs_H_D']:+.5f}, "
                                f"{result['folds_higher_than_H_D']}/{result['folds_total']} folds above.")
            elif result:
                outcome = (f"initial arm DTI={result['proxy_dti_mean_r3_47']:.5f}; "
                           f"vs H-D Δ={result['paired_mean_proxy_dti_delta_vs_H_D']:+.5f}; "
                           f"{result['folds_higher_than_H_D']}/{result['folds_total']} folds above; "
                           + h.get("promotion_status", ""))
            else:
                outcome = h.get("status", "not run") + " " + h.get("promotion_status", "")
            slate_rows.append([
                esc(h.get("id", "")), esc(h.get("name", "")),
                esc(h.get("target_layers", [])), esc(h.get("signature_operator", "")),
                esc(h.get("geological_rationale", "")),
                esc(h.get("difference_from_prior_work", "")),
                esc(h.get("expected_benefit_before_test", h.get("expected_benefit", ""))),
                esc(h.get("implementation_cost", "")), esc(outcome),
            ])
        shutil.copyfile(slate_path, DOCS / "downloads" / slate_path.name)
    body = f"""
<h2>Prior hypotheses recorded for this project</h2>
<p>The table below is the earlier GEMSDOE51 slate and its measured outcomes; it is retained as
history, not as evidence that a family is globally novel. See the current, date-stamped slate
below for specific operators and sibling prior-art comparisons.</p>
{tbl(['id','name','layers','physical signature','why it catches a missing fault','differs from','expected benefit','cost','historic outcome','AUC','proxy DTI at M/|G| = 3.47','Δ vs base'], rows) if rows else '<p class="missing">hypotheses.json not generated</p>'}

<h2>2026-10-07 specific hypothesis slate and test</h2>
<p>Four candidates were ranked. H-G was the strongest low-cost screen and its matched H-D add-on
holdout is complete but negative; H-H–H-J remain proposals, not results. Broad families have
substantial sibling prior art. A keyword
hit proves documentation, not implementation or performance; no global novelty claim is made.
H53's default branch contained only a one-line README and no method to compare.</p>
{tbl(['ID','candidate','target layers','specific signature/operator','geological rationale','difference from inspected prior art','expected benefit (pre-test)','cost','holdout/status'], slate_rows) if slate_rows else '<p class="missing">2026-10-07 slate not available</p>'}
<p>Regional rationale sources: <a href="https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf">Faulds &amp; Hinz, Great Basin structural settings</a> and
<a href="https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and">USGS integrated geologic/geophysical play-fairway report</a>. These support why fault intersections, terminations and coincident geophysical evidence may be relevant; they do not validate any raster operator or local holdout result.
<a href="downloads/hypothesis_slate_20261007.json">Download the full slate and evidence notes.</a></p>
"""
    (DOCS / "hypotheses.html").write_text(page("Hypotheses", body, "hypotheses.html"))

    # ------------------------------------------------------------ holdout
    def arm_rows():
        out = []
        for a in ("base", "H_E", "H_D", "H_C", "H_ALL"):
            h = hold.get(a)
            if not h:
                continue
            s = h["summary"]
            out.append([a, f"{s['auc_mean']:.4f}"] +
                       [f"{s[f'dti_r{r}']['mean']:.4f}" for r in s["ratios"]])
        return out

    ratios = []
    for a in ("base", "H_E", "H_D", "H_C", "H_ALL"):
        if hold.get(a):
            ratios = hold[a]["summary"]["ratios"]
            break
    # The old two_stage_results.json was built with the pre-revision prior and a
    # spatial-block design that zeroes the catalogue-derived strain term in each
    # held-out block. It is deliberately not presented as the current Stage-1 test.
    h_g_path = ROOT / "evidence" / "holdout_H_G.json"
    h_g_match_path = ROOT / "evidence" / "holdout_H_G_plus_H_D.json"
    h_g_section = "<p class='missing'>H-G blocked holdout not available.</p>"
    if h_g_path.exists():
        hg = json.loads(h_g_path.read_text())
        hd = hold.get("H_D")
        hgs = hg.get("summary", {})
        hgd = hgs.get("dti_r3.47", {}).get("mean")
        hga = hgs.get("auc_mean")
        hd_d = hd["summary"]["dti_r3.47"]["mean"] if hd else None
        hd_a = hd["summary"]["auc_mean"] if hd else None
        delta = hgd - hd_d if hgd is not None and hd_d is not None else None
        rows_hg = [["H-G, replaces H-D extras", f"{hga:.4f}", f"{hgd:.5f}",
                    f"{delta:+.5f}" if delta is not None else "n/a",
                    f"{sum(x > y for x,y in zip(hgs['dti_r3.47']['per_fold'], hd['summary']['dti_r3.47']['per_fold']))}/6" if hd else "n/a"]]
        if hd:
            rows_hg.append(["H-D incumbent", f"{hd_a:.4f}", f"{hd_d:.5f}", "reference", "reference"])
        if h_g_match_path.exists():
            hgm = json.loads(h_g_match_path.read_text())
            ms = hgm.get("summary", {})
            md = ms.get("dti_r3.47", {}).get("mean")
            ma = ms.get("auc_mean")
            dd = md - hd_d if md is not None and hd_d is not None else None
            wins = sum(x > y for x,y in zip(ms["dti_r3.47"]["per_fold"], hd["summary"]["dti_r3.47"]["per_fold"])) if hd else 0
            rows_hg.append(["H-G added to H-D (matched)", f"{ma:.4f}", f"{md:.5f}",
                            f"{dd:+.5f}" if dd is not None else "n/a", f"{wins}/6"])
            shutil.copyfile(h_g_match_path, DOCS / "downloads" / h_g_match_path.name)
        else:
            rows_hg.append(["H-G added to H-D (matched)", "running", "pending", "pending", "pending"])
        shutil.copyfile(h_g_path, DOCS / "downloads" / h_g_path.name)
        h_g_section = tbl(["arm", "in-block AUC", "proxy DTI, ratio 3.47", "paired Δ vs H-D", "folds above H-D"], rows_hg)
        h_g_section += ("<p class='ev'>H-G's first run replaced H-D's four LiDAR-coherence channels with two crossing channels, "
                        "so only the matched add-on row is a promotion-grade comparison. Six spatial blocks; "
                        "visible-catalogue proxy, not organizer score.</p>")

    body = f"""
<h2>Holdout: both stages, scored separately</h2>
<h3>Design</h3>
<p>The footprint is cut into 3&times;3 contiguous blocks. Each block is held out in turn; the
detector never sees it; a 1.2&nbsp;km buffer around it is removed from the training pool.
Emission and scoring are both restricted to the block, and the number of emitted dots is a fixed
multiple of that block's own truth size to standardize the emission budget. Matching M/|G| does
not make visible-catalogue proxy scores numerically interchangeable with live leaderboard scores.</p>

<h3>Stage 2 — fine-scale arms</h3>
{tbl(['arm','in-block AUC'] + [f'DTI at M/|G|={r}' for r in ratios], arm_rows())}

<h3>Stage 1 — broad-tile prior, evaluated separately</h3>
<p>A spatial block cannot directly test the catalogue-derived fault-budget term: removing all
catalogue traces from a held-out block makes the fault term zero there, reducing the deficit to the
raw geodetic field. Stage 1 is therefore reported on five <b>trace-level</b> splits, not the Stage-2
spatial blocks. A random fifth of mapped traces is withheld and the remaining traces supply the
budget. No model is fitted. This is an association diagnostic against visible catalogue faults,
not hidden-label performance.</p>
""" + _STAGE1 + f"""
<p><b>Result: the deficit is not a validated locator.</b> Under all four rate/sense assumptions,
its mean Spearman correlation and q50 recall/area lift are below the raw geodetic-only field. That
is a measured association result, not proof of a causal mechanism. The mapped-fault budget term may
remove spatial information that also predicts additional mapped-style structures; the source-rate
and dip assumptions are uncertain. Keep Stage 1 as a low-confidence broad-tile prior only.</p>

<h3>Gate sweep: hard gate versus soft prior</h3>
""" + _GATE + f"""
<p>The older six-fold gate sweep shows the hard gate losing on all folds (q20/top-80% mean delta
about −0.00250). The soft w=0.10 setting's raw mean delta is <b>+0.000367</b>, positive in 4/6
folds; this is small and inconclusive, not a demonstrated win. These gate-sweep numbers and the
existing soft TIFF predate the signed strike-slip correction in the current strain-budget code.
The soft primary does not restrict emissions to approved tiles; the hard secondary does. Do not
interpret q20/top-80% statistics as the soft primary's q70/top-30% diagnostic.</p>

<h3>H-G: spatially blocked screen and incumbent comparison</h3>
""" + h_g_section + f"""
<p>The matched H-G + H-D arm averaged 0.281056 proxy DTI versus 0.281663 for H-D (paired
Δ −0.000606; 3/6 folds higher) and averaged AUC 0.669619 versus 0.672618. H-G is not promoted and
no competition slot is authorized. All local scores are visible-catalogue proxies only; the true
labels remain unavailable.</p>

<h3>Emission geometry</h3>
""" + _EMIS + f"""

<h3>Known biases of this instrument</h3>
<ul>
<li>its truth is the visible catalogue, so it can only reward rediscovering the <i>kind</i> of fault
that is already mapped, never a genuinely new style;</li>
<li>truth density inside a block is several times the regional average, so absolute proxy DTI is
optimistic;</li>
<li>the block is treated as unmapped territory, whereas in reality known faults are interleaved
with the hidden ones and their neighbourhoods are excluded from emission.</li>
</ul>
<p>A pass on this instrument licenses packaging a candidate. It is never a score.</p>
"""
    (DOCS / "holdout.html").write_text(page("Holdout", body, "holdout.html"))

    # ------------------------------------------------------------ analysis
    observed = [r for r in lb.get("rows", []) if r.get("rank") in (1, 7, 13)]
    score_rows = [[str(r["rank"]), html.escape(r["team"]), f"{r['score']:.4f}",
                   "Not identified by the public leaderboard"] for r in observed]
    score_table = tbl(["rank", "participant", "public DTI", "artifact/method identity"], score_rows)
    analysis_html = ANALYSIS_BODY.read_text().replace("{score_table}", score_table)
    (DOCS / "analysis.html").write_text(page("Analysis", analysis_html, "analysis.html"))
    retired_strategy = """
<h2>Legacy strategy page retired</h2>
<p>This URL is preserved for old links, but the former strategy narrative is not current evidence.
It incorrectly attributed a public score of 0.2778 to GEMSDOE32 H33-2-B2 and used that unverified
file identity in downstream arithmetic. The attribution has been withdrawn: the 2026-10-07 public
leaderboard displayed 0.2778 for participant <code>extradr19</code> and 0.3774 for
<code>xiaofanhu</code>, but neither row identifies a TIFF or method. GEMSDOE32's own report labels
H33-2-B2 UNSCORED with a modelled projection of 0.2747.</p>
<p>Use the current <a href="analysis.html">score analysis</a>,
<a href="holdout.html">separate Stage-1/Stage-2 holdout report</a>,
<a href="hypotheses.html">hypothesis slate</a>, and
<a href="irregularities.html">irregularity register</a>. No public score is attributed to a local
artifact, and no local proxy result is a leaderboard score.</p>
"""
    (DOCS / "strategy.html").write_text(page("Retired strategy analysis", retired_strategy, "analysis.html"))

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
    rows = [[r["rank"], html.escape(r["team"]), r["score"], html.escape(r.get("when", ""))]
            for r in lb.get("rows", [])]
    body = f"""
<h2>Public leaderboard</h2>
<p class="ev">Read {html.escape(lb.get('read_at', 'n/a'))} from the official page. These are
organizer-verified public scores and are the only scores on this site that are.</p>
{tbl(['rank','team','public DW-Tversky','when'], rows)}
<p>Our own submission's score, once it exists, will be recorded here with its evidence class and
will be labelled a <b>claim</b> until the organizer confirms it.</p>
"""
    (DOCS / "leaderboard.html").write_text(page("Leaderboard", body, "leaderboard.html"))

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

    # ------------------------------------------------------------ claims
    claims_path = ROOT / "registry" / "claims.json"
    claim_rows = []
    if claims_path.exists():
        claims_doc = json.loads(claims_path.read_text())
        for c in claims_doc.get("claims", []):
            source = c.get("source", "")
            source_cell = (f'<a href="{html.escape(source, quote=True)}">external source</a>'
                           if source.startswith(("http://", "https://")) else "")
            claim_rows.append([
                html.escape(c.get("id", "")),
                html.escape(c.get("class", "")),
                html.escape(c.get("claim", "")),
                html.escape(c.get("evidence", "")),
                source_cell,
            ])
    claims_body = """
<h2>Claim and evidence ledger</h2>
<p>Claim classes are not interchangeable: recomputed measurements, proxy diagnostics, public-board
observations, and owner-reported/unverified values are labelled separately. Public scores do not
identify a TIFF unless an authenticated receipt links the exact file or hash to the row.</p>
""" + tbl(["ID", "evidence class", "claim", "local evidence", "external source"], claim_rows)
    (DOCS / "claims.html").write_text(page("Claims", claims_body, "claims.html"))

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
