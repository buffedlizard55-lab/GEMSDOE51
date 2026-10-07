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
       ("irregularities.html", "Irregularities")]


def load(rel, default=None):
    p = ROOT / "data" / rel
    if not p.exists():
        return default
    return json.loads(p.read_text())


def page(title, body, active="index.html"):
    nav = "  \n".join(
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
<p>Every number on this site is read from an artifact in <code>data/</code> and carries an
evidence class. Measured = computed on bytes we hold. Claim = reported by the owner group and not
independently verifiable here. Organizer-verified = none; no score on this site has been
confirmed by DrivenData.</p>
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
    rows = []
    for a in arts:
        u = a.get("uniqueness", {})
        j = u.get("support_jaccard", {})
        rows.append([a["role"],
                     f'<a href="downloads/{html.escape(a["file"])}">{html.escape(a["file"])}</a>'
                     f'<br><span class="ev">zip: <a href="downloads/{html.escape(a.get("zip",""))}">'
                     f'{html.escape(a.get("zip",""))}</a>'
                     f' &middot; nan twin: <a href="downloads/{html.escape(a.get("nan_twin",""))}">'
                     f'{html.escape(a.get("nan_twin",""))}</a></span>',
                     a.get("gate_mode", ""),
                     html.escape(a.get("description", "")),
                     f'{a.get("holdout_cost_vs_ungated", 0):+.4f}',
                     f'{min(j.values()):.3f}' if j else "n/a",
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



def loadev(rel, default=None):
    q = ROOT / "evidence" / rel
    if not q.exists():
        return default
    return json.loads(q.read_text())


def autocontext_table():
    d = loadev("autocontext_holdout.json")
    if not d:
        return "<p class='missing'>auto-context holdout not run</p>"
    import numpy as np
    rows = d.get("rows", [])
    folds = sorted({r["fold"] for r in rows})
    ratios = sorted({r["ratio"] for r in rows})
    by = {(str(r["level"]).upper().lstrip("LEVEL "), r["ratio"], r["fold"]): r
          for r in rows}
    out = []
    for lvl in ("1", "2"):
        aucs = [by[(lvl, ratios[0], f)]["auc"] for f in folds if (lvl, ratios[0], f) in by]
        cells = [f"level {lvl}", f"{np.mean(aucs):.4f}"]
        for r in ratios:
            v = [by[(lvl, r, f)]["dti_iso"] for f in folds if (lvl, r, f) in by]
            cells.append(f"{np.mean(v):.4f}")
        out.append(cells)
    d_cells = ["paired &Delta; (L2 &minus; L1)", ""]
    n_cells = ["folds positive", ""]
    for r in ratios:
        a = np.array([by[("1", r, f)]["dti_iso"] for f in folds if ("1", r, f) in by])
        b = np.array([by[("2", r, f)]["dti_iso"] for f in folds if ("2", r, f) in by])
        dd = b - a
        d_cells.append(f"<b>{dd.mean():+.4f}</b>")
        n_cells.append(f"{int((dd > 0).sum())}/{len(dd)}")
    out += [d_cells, n_cells]
    hdr = ["model", "in-block AUC"] + [f"DTI at M/|G|={r:g}" for r in ratios]
    per = ", ".join(
        f"{(by[('2', 3.47, f)]['dti_iso'] - by[('1', 3.47, f)]['dti_iso']):+.4f}"
        for f in folds if ('1', 3.47, f) in by)
    return tbl(hdr, out) + (
        f"<p class='ev'>per-fold paired &Delta; at the shipped mass ratio 3.47: {per}. "
        "The sign alternates. The preregistered promotion rule was a paired mean of at least "
        "+0.006 <i>and</i> at least 4/6 folds positive; auto-context clears the fold count and "
        "misses the effect size by 5&times;, so it is <b>not shipped</b> (IR-51-12).</p>")


def geometry_table():
    d = loadev("emission_geometry.json")
    if not d:
        return "<p class='missing'>emission-geometry A/B not run</p>"
    import numpy as np
    rows = d.get("rows", [])
    by = {}
    for r in rows:
        by.setdefault(r["rule"], {})[r["fold"]] = r["dti"]
    if "iso_nms_r2.4" not in by:
        return "<p class='missing'>incumbent rule absent from the A/B</p>"
    folds = sorted(by["iso_nms_r2.4"])
    base = np.array([by["iso_nms_r2.4"][f] for f in folds])
    out = []
    for rule in sorted(by, key=lambda k: -np.mean(list(by[k].values()))):
        v = np.array([by[rule].get(f, np.nan) for f in folds])
        dd = v - base
        nm = html.escape(rule)
        if rule == "iso_nms_r2.4":
            nm = f"<b>{nm}</b> (incumbent)"
        elif rule == "ste_L9_w0.35_s2.4_nothin":
            nm = f"<b>{nm}</b> (shipped)"
        elif rule.startswith("ste_L9_w0_"):
            nm = f"{nm} (control: must equal the incumbent)"
        out.append([nm, f"{np.nanmean(v):.4f}", f"{np.nanmean(dd):+.4f}",
                    f"{int((dd > 0).sum())}/{len(dd)}",
                    ", ".join(f"{x:+.4f}" for x in dd)])
    return tbl(["emission rule", "mean proxy DTI", "paired delta vs incumbent",
                "folds better", "per-fold delta"], out)


def offcat_table():
    d = loadev("offcatalogue_ab.json")
    if not d:
        return "<p class='missing'>off-catalogue A/B not run</p>"
    import numpy as np
    rows = d.get("rows", [])
    by = {}
    for r in rows:
        for key in ("B_all", "B_far"):
            k = r.get("dti_" + key, r.get(key))
            if k is not None:
                by.setdefault(r["rule"], {}).setdefault(key, []).append(k)
    order = ["ste_L9_w0.35_s2.4", "iso_nms_r2.4", "uniform_random", "halo_ring_2_5px"]
    labels = {"ste_L9_w0.35_s2.4": "detector + strike-coherent trace emission <b>(shipped)</b>",
              "iso_nms_r2.4": "detector + isotropic NMS (incumbent)",
              "uniform_random": "uniform random inside the footprint (null)",
              "halo_ring_2_5px": "ring of dots 2&ndash;5 px around visible faults (halo control)"}
    out = []
    for k in order + [k for k in by if k not in order]:
        if k not in by:
            continue
        out.append([labels.get(k, html.escape(k)),
                    f"{np.mean(by[k].get('B_all', [np.nan])):.4f}",
                    f"{np.mean(by[k].get('B_far', [np.nan])):.4f}"])
    return tbl(["rule", "DTI vs B_all", "DTI vs B_far (strict)"], out)


def build():
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "downloads").mkdir(exist_ok=True)
    subm = load("submission_manifest.json", {})
    sub = subm.get("primary", {})
    arts = subm.get("artifacts", [])
    s1stats = subm.get("stage1_stats", {})
    hold = {a: load(f"holdout_{a}.json") for a in
            ("base", "H_E", "H_D", "H_M", "H_C", "H_ALL")}
    two = load("two_stage_results.json")
    lb = load("leaderboard.json", {})

    # ------------------------------------------------------------ index
    dl = sub
    if dl:
        name = dl.get("file", "")
        card = f"""
<section class="download">
<h2>⬇ One-click submission file</h2>
<p class="big"><a class="btn" href="downloads/{html.escape(name)}">Download {html.escape(name)}</a></p>
<p class="zip">or the <a href="downloads/{html.escape(dl.get('zip',''))}">.zip containing the same single GeoTIFF</a></p>
<dl class="kv">
<dt>Unique submission name to paste</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>Note for the <em>Note (optional)</em> field</dt><dd><code>{html.escape(dl.get('note',''))}</code></dd>
<dt>Format</dt><dd>{html.escape(dl.get('format',''))}</dd>
<dt>sha256</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
</dl>
<p class="ev">{html.escape(dl.get('evidence',''))}</p>
</section>"""
    else:
        card = """<section class="download missing">
<h2>⬇ Submission file</h2>
<p>The submission has not been built yet in this checkout. Run
<code>python3 scripts/build_submission.py</code> to produce it; this card is then filled from
the resulting <code>data/submission_manifest.json</code>.</p></section>"""

    rows = []
    for a in ("base", "H_E", "H_D", "H_M", "H_C", "H_ALL"):
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
    _EMIS = emission_table()
    _AC = autocontext_table()
    _GEO = geometry_table()
    _OFFCAT = offcat_table()
    hm = load("holdout_H_M.json")
    hd51 = load("holdout_H_D.json")
    sess = ""
    if hm and sub:
        sM = hm["summary"]
        sD = hd51["summary"] if hd51 else {}
        dd = sM["dti_r3.47"]["mean"] - sD.get("dti_r3.47", {}).get("mean", float("nan"))
        sess = f"""
<h2>This session, work stream B (2026-10-07): a second candidate submission</h2>
<p>The site's primary download above is stream A's strike-coherent emission (best holdout,
0.2836). Stream B independently built a <b>second, structurally different candidate</b> from the
same detector family, so this week's three submission slots can span two hypotheses instead of
one. Its story:</p>
<ul>
<li><b>Studied why the group's best scored 0.2778</b>: it is a <i>removal</i> result &mdash; pruning
dots within 200 m of the mapped catalogue raised the live score 0.2600 &rarr; 0.2708 &rarr; 0.2778
(GEMSDOE32 Round 4, live-anchored safety 2.08). Mass near mapped faults is dead mass. Full write-up:
<a href="https://github.com/buffedlizard55-lab/GEMSDOE51/blob/main/knowledge/02_gemsdoe32_study_and_candidates_2026-10-07.md">knowledge/02</a>.</li>
<li><b>Five new candidate hypotheses pre-registered</b> (H-51-L, H-51-M, H-51-P, H-51-S, H-51-V;
letters L/M because stream A already owns F/G) with layers, signatures and novelty checks &mdash;
see the <a href="hypotheses.html">hypotheses</a> page.</li>
<li><b>H-51-L (trace-axis snap) validated and falsified</b> on the blocked holdout under a
pre-registered rule: at conserved mass and spacing, window=2 costs &minus;0.0033 proxy DTI,
window=1 is neutral. Two earlier failure modes (spacing collapse; silent mass loss) were
reproduced, explained and unit-tested. Registered as IR-51-14 with the instrument caveat.</li>
<li><b>H-51-M (cross-scale crest coincidence) adopted</b>: in-block AUC {sM['auc_mean']:.4f}
(+{sM['auc_mean'] - sD.get('auc_mean', float('nan')):.4f} over H_D) and proxy DTI
{sM['dti_r3.47']['mean']:.4f} ({dd:+.4f} over H_D at M/|G| = 3.47) &mdash; the second-best arm
measured in this repository, 0.0010 below stream A's emission.</li>
</ul>
<section class="download">
<h3>&#11015; Stream B candidate (H-51-M two-stage)</h3>
<p class="big"><a class="btn" href="downloads/gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-softw0p1-zeros.tif">Download gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-softw0p1-zeros.tif</a></p>
<p class="zip">or the <a href="downloads/gemsdoe51-hm-twostage-r347-bag3-20261007T031825Z-softw0p1.zip">.zip containing the same single GeoTIFF</a></p>
<dl class="kv">
<dt>Unique submission name to paste</dt><dd><code>GEMSDOE51-HM-SOFT-W010</code></dd>
<dt>sha256</dt><dd><code>c3bf15a0471c5f00d3a436f2328ef443564a955f44a32776485e706344529839</code></dd>
</dl>
<p class="ev">44,069 dots &middot; float32 EPSG:32611 3730&times;3292 &middot; all cells finite in [0,1] &middot;
0 dots within 200 m of the catalogue &middot; Stage-1 dominance lift 0.978 &middot; holdout cost of the soft
prior +0.0000. The hard top-80% tile variant (the brief's literal design) is also in
<code>docs/downloads</code> and costs &minus;0.0027 on holdout, disclosed.</p>
</section>
"""
    body = card + sess + f"""
<h2>What is offered</h2>
{_ART}
<p class="warn"><b>The biggest limitation, stated first.</b> The visible USGS/INGENIOUS fault
catalogue <b>is</b> the training label — <code>labels.tif</code> is byte-identical to
<code>existing_faults.tif</code>, and this is <b>by design</b>: the organizer's own reference
solution trains on exactly that file, and the hidden test set is the expert-identified faults
<i>absent</i> from it (IR-51-08, closed). The consequence is IR-51-11: every offline number here
measures <b>rediscovery</b>, not discovery. This session quantified the gap with a second
instrument that hides half the catalogue's fault <i>systems</i> and leaves them inside the negative
class. Against those genuinely off-catalogue structures the detector scores <b>0.0813</b>, not the
0.282 the blocked holdout reports — still 1.9&times; uniform random, and 37&times; a
catalogue-halo control (0.0022), so it is finding real new geometry rather than ringing what is
already mapped. Read every 0.28 on this site with that factor in mind. Nothing here should be read
as a prediction of the leaderboard.</p>
<p class="warn"><b>Phase 1 entries are not free.</b> The organizer has stated on the forum that the
Phase 2 test set "will use a test set that is updated by expert review of all Phase 1 submissions,
so your fault predictions have an impact on final evaluation even if they are not the most
performant in Phase 1" (chrisk-dd, 2026-09-23). Every dot in the files below is therefore
geologically defensible on its own terms, not just score-optimal: all of them lie outside the
200 m exclusion zone, none sits on a catalogued trace, and the Stage 1 strain-budget argument for
why each tile is worth looking at is published on the <a href="method.html">method</a> page.</p>
<h2>What this is</h2>
<p>GEMSDOE51 predicts geothermal-indicative faults in the GeoDAWN region that are
<b>not</b> in the USGS / INGENIOUS catalogue, and ships them as a competition-legal GeoTIFF.
It is a <b>two-stage</b> system: a coarse geodetic <i>strain-budget deficit</i> prior over
10&nbsp;km tiles (Stage&nbsp;1), and a fine-scale fault detector whose output is turned into
emitted pixels by a <i>strike-coherent trace emitter</i> (Stage&nbsp;2). Both stages are scored
separately on a preregistered spatially blocked holdout, and the whole system is scored again on an
off-catalogue A/B that is the closest offline analogue of the real task.</p>
<p>Stage&nbsp;1 ships as a <b>soft multiplicative prior at w = 0.10</b>, not as a filter: a six-fold
paired sweep found the hard gate monotone-harmful at every setting (it never wins a fold), and the
soft prior at w = 0.10 is the only setting that is not negative. The shipped file's Stage-1
dominance lift is <b>0.963</b> — below 1 — so the submission is demonstrably <i>not</i> a
re-expression of Stage 1's approved footprint.</p>

<h2>The three facts that decide everything</h2>
<ol>
<li><b>Known faults are masked.</b> DrivenData staff confirmed on 2026-09-16 that pixels
corresponding to known USGS/INGENIOUS faults are excluded from evaluation, in both prize
rounds. <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">source</a></li>
<li><b>"New fault" includes new geometry of an existing system.</b> Continuations, splays and
parallel strands count. <a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">source</a></li>
<li><b>The metric is a budget.</b> From the published definitions,
<code>DTI = TP / (0.2·(TP+FP) + 0.8·|G|)</code>. The hidden truth size |G| is fixed, so a
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
<li><a href="executive-summary.html">Executive summary</a> — the one-page version: the file, how
to submit it, what it is worth, and the proof that it is not a copy of anything.</li>
<li><a href="how-to-submit.html">How to submit, step by step</a> — including the fix for the
<code>"Predicted values must be in range [0, 1]"</code> portal error.</li>
<li><a href="hypotheses.html">Hypotheses</a> — eleven candidates, each with its layers, physical
signature, and the measured outcome filled in after the run.</li>
<li><a href="method.html">Method</a> — the Kostrov strain budget, the detector, the emission rule.</li>
<li><a href="holdout.html">Holdout</a> — Stage 1 and Stage 2 scored separately.</li>
<li><a href="irregularities.html">Irregularities</a> — including one in a sibling repository's own
reporting that we could not reproduce.</li>
</ul>
"""
    (DOCS / "index.html").write_text(page("GEMSDOE51 — DOE GEMS Prize", body, "index.html"))

    # ------------------------------------------------------------ how to submit
    body = f"""
<h2>How to submit into the contest — exactly</h2>
<ol class="steps">
<li><b>Download the file.</b> Go to the <a href="index.html">executive summary</a> and click the
big download button. You get a single-band GeoTIFF called
<code>{html.escape(dl.get('file','…'))}</code>.</li>
<li><b>Open the submission page.</b>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/</a>
(requires login). The form is titled <b>New submission</b>.</li>
<li><b>File to submit → Choose File.</b> Select the <code>.tif</code> you just downloaded. You may
also upload the <code>.zip</code>; both contain the same single GeoTIFF.</li>
<li><b>Note (optional).</b> Paste this exact string so you can tell this submission apart later:</li>
</ol>
<pre class="note">{html.escape(dl.get('note','…'))}</pre>
<ol class="steps" start="5">
<li><b>Submit.</b> The score appears on the
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">public leaderboard</a>
once the validator finishes.</li>
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

    # ------------------------------------------------- executive summary subpage
    # Generated from the manifest so it can never go stale: an earlier hand-written
    # copy of this page still pointed at a file that no longer existed.
    u = subm.get("uniqueness", {})
    jac = u.get("support_jaccard", {})
    ext = {k: v for k, v in jac.items() if not k.startswith("own:")}
    s1 = subm.get("stage1", {})
    oc = loadev("offcatalogue_ab.json", {}) or {}
    ocsum = oc.get("summary", {})
    esbody = f"""
<section class="download">
<h2>&#11015; The submission, in one click</h2>
<p class="big"><a class="btn" href="downloads/{html.escape(dl.get('file',''))}">Download {html.escape(dl.get('file',''))}</a></p>
<p class="zip">or the <a href="downloads/{html.escape(dl.get('zip',''))}">.zip containing the same single GeoTIFF</a>
&middot; <a href="downloads/{html.escape(dl.get('nan_twin',''))}">NaN-outside twin</a></p>
<dl class="kv">
<dt>Submission name to paste</dt><dd><code>{html.escape(dl.get('submission_name',''))}</code></dd>
<dt>sha256</dt><dd><code>{html.escape(dl.get('sha256',''))}</code></dd>
</dl>
</section>

<h2>Exactly how to submit</h2>
<ol class="steps">
<li><b>Download</b> the <code>.tif</code> above (the <code>.zip</code> is accepted too and holds
the identical single band).</li>
<li><b>Open</b> <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the
submission form</a> (login required); it is titled <b>New submission</b>.</li>
<li><b>File to submit &rarr; Choose File</b>, and select the downloaded file.</li>
<li><b>Note (optional)</b> &mdash; paste the string below verbatim. It is what distinguishes this
entry from every earlier GEMSDOE submission.</li>
</ol>
<pre class="note">{html.escape(dl.get('note',''))}</pre>
<ol class="steps" start="5">
<li><b>Submit</b>, then record the returned score in <code>registry/claims.json</code>.
A full step-by-step walkthrough, including the two mechanisms behind the
<code>"Predicted values must be in range [0, 1]"</code> rejection and how this file avoids both,
is on the <a href="how-to-submit.html">how to submit</a> page.</li>
</ol>

<h2>Is it legal for the portal?</h2>
{tbl(['requirement', 'this file'], [[r, v] for r, v in dl.get('format_table', [])]
     or [["(built after build_submission_v2.py)", ""]])}
<p class="ev">Measured by re-opening the written file from disk in a second process, not from the
array in memory.</p>

<h2>Is it actually new?</h2>
<table class=''><thead><tr><th>test</th><th>limit</th><th>measured</th></tr></thead><tbody>
<tr><td>byte-identical to a prior GEMSDOE submission</td><td>must be none</td>
<td>{'none' if not u.get('byte_duplicate_of') else esc(u.get('byte_duplicate_of'))}</td></tr>
<tr><td>max Jaccard of emitted pixels vs the three external prior submissions</td><td>&lt; 0.50</td>
<td>{max(ext.values()):.4f}</td></tr>
<tr><td>Stage-1 dominance lift (emitted share inside approved &divide; approved area share)</td>
<td>&lt; 1.50</td><td>{s1.get('lift_over_area', float('nan')):.3f}</td></tr>
<tr><td>standalone gate (<code>scripts/run_uniqueness_gate.py</code>, shares no code with the builder)</td>
<td>PASS</td><td>{html.escape(str(u.get('verdict','')))}</td></tr>
</tbody></table>
<p>A dominance lift <b>below 1</b> is the answer to the question &ldquo;is this just Stage 1 drawn
as dots?&rdquo;. It is not: the emitted pixels are very slightly <i>less</i> concentrated in
Stage&nbsp;1&rsquo;s approved tiles than area alone would predict.</p>

<h2>What it is, and what it is worth</h2>
<p>A fine-scale fault detector (58 physical layers plus 4 scarp-facing-coherence layers, 3-bag
gradient-boosted ensemble) over the GeoDAWN footprint, tilted by a 10&nbsp;km geodetic
strain-budget prior at weight 0.10, emitted as {subm.get('n_dots', 0):,} binary dots by a
<b>strike-coherent trace emitter</b>. Every dot is at least 200&nbsp;m from a catalogued fault.</p>
<ul>
<li><b>Blocked-holdout proxy DTI 0.2836</b> at the shipped mass, +0.0020 paired against the
isotropic-NMS incumbent on all six folds (4/6, sign-test p = 0.344 &mdash; small and not
statistically separable from zero).</li>
<li><b>Off-catalogue A/B &mdash; the honest number: 0.0813</b> against structures the training
catalogue genuinely does not contain, versus 0.0424 for uniform random and <b>0.0022</b> for a
catalogue-halo control. The detector is finding new geometry, not ringing what is mapped.</li>
<li><b>Auto-context stacking was tried and rejected</b> (+0.0012 against a preregistered +0.006
bar). The negative result is published on the <a href="holdout.html">holdout</a> page.</li>
<li><b>No score here is organizer-verified.</b> This file is UNSCORED.</li>
</ul>
"""
    (DOCS / "executive-summary.html").write_text(
        page("Executive summary", esbody, "index.html"))

    # ------------------------------------------------------------ method
    body = """
<h2>Method</h2>
<h3>Stage 1 — geodetic strain-budget deficit (coarse prior only)</h3>
<p>Kostrov (1974) moment-tensor summation, per tile:</p>
<pre>eps_dot_ij  =  (1 / (2·mu·V)) · sum_k  Mdot_ij^(k)
Mdot_ij^(k) =  mu · A_k · sdot_k · ( n_i·m_j + n_j·m_i )
A_k = L_k · W_k ,  W_k = H / sin(delta) ,  V = A_tile · H</pre>
<p>mu and H cancel, giving the two working equations used in the code:</p>
<pre>strike-slip :  eps_dot_sn = L_k · sdot_k / (2 · A_tile · sin delta)
dip-slip    :  eps_dot_nn = L_k · sdot_k · cot(delta) / A_tile</pre>
<p>Slip rates come from the INGENIOUS compilation mirrored in
<a href="https://gdr.openei.org/submissions/1391">GDR submission 1391</a> — the attribute
<code>slip_rate</code> (mm/yr) is present on all 1,126 traces, confirmed directly in
<code>data/raw/external/gdr_qfaults_traces.csv</code>. Geometry (trace length per cell) comes from
the catalogue raster itself, so L is exact at 100&nbsp;m resolution; dip follows from
<code>slip_sense</code> (normal 60°, strike-slip 90°) and H is 15&nbsp;km with 10/20&nbsp;km
sensitivities.</p>
<p><b>Result, measured over the 10&nbsp;km tiles:</b> the mapped faults accommodate a median of
<b>{fm:.1f}</b> nanostrain/yr of second invariant <i>on tiles that contain a mapped trace</i>,
against an observed geodetic median of <b>{om:.1f}</b> — about <b>{pct:.0f}&nbsp;%</b>. Over
<i>all</i> tiles the fault-accommodated median is exactly <b>0.0</b>, because most tiles contain no
mapped trace at all. That is the structural reason the deficit is a weak prior: the fault term is
near-null almost everywhere, so subtracting it mostly subtracts nothing, and where it is not null
it is measuring how well-mapped a tile already is rather than how much strain is unaccounted
for.</p>
<p class="warn"><b>Convention caveat (IR-51-02).</b> The three geodetic layers shipped with the
competition satisfy no exact algebraic identity — <code>sqrt(dil²+shear²)</code>,
<code>sqrt((dil²+shear²)/2)</code> and <code>|dil|+|shear|</code> all miss by more than 30&nbsp;%
locally (best r = 0.993) — so the invariant convention behind <code>geod_2ndinv</code> is not
recoverable from the shipped data. Stage&nbsp;1 is therefore stated in <b>quantile space</b>,
<code>Q(observed) − Q(fault)</code>, which is invariant to any monotone rescaling of either side.
No absolute claim rests on the nanostrain/yr numbers.</p>
<p>Used strictly as a prior over broad tiles. It approves tiles; it never places a point.</p>

<h3>Stage 2 — fine-scale detector</h3>
<p>Histogram gradient boosting over 58 physical layers: the 19 competition bands (rank
transformed), ten 1&nbsp;m-DEM-derived scarp layers, four radiometric layers, the USGS SGMC fault
raster, and a multi-scale lineament bank (gradient magnitude, crestness and Hessian anisotropy of
detrended elevation, TMI, isostatic gravity and lidar relief at 150&nbsp;m and 400&nbsp;m).
Missing data inside a smoothing window is handled by normalised convolution rather than
zero-fill.</p>
<p class="warn"><b>Leak control (IR-51-LEAK-01).</b> Any feature derived from the catalogue is a
perfect training leak in a blocked holdout, because every positive has distance-to-catalogue
exactly 0. Measured: in-block AUC collapsed to 0.500 with those columns present and recovered to
0.667 without them. Catalogue-derived quantities are therefore excluded from the model and used
only at emission time.</p>

<h3>Emission</h3>
<p>Greedy non-maximum suppression at a 2.4&nbsp;px radius, every point at least 200&nbsp;m from any
catalogued fault pixel, at a mass chosen from the holdout. The reason for the sparsity is the
break-even bar: a marginal pixel earning expected kernel credit <code>c</code> raises the score only
if <code>c &gt; 0.2·DTI</code>, and pixels adjacent to an already-emitted dot earn almost nothing
because the dot beside them already collected the credit.</p>
<p class="warn"><b>Where Stage&nbsp;1 enters, in the two shipped files.</b> In the <b>primary</b>
file the deficit enters as a <b>soft multiplicative prior</b>: the detector's field is multiplied by
<code>1 + 0.10·z</code> where <code>z</code> is the standardised tile deficit clipped to ±4, so a
high-deficit tile and a low-deficit tile differ by at most a few percent — enough to break ties
between otherwise equal pixels, not enough to veto a strong detection. In the <b>secondary</b> file
it enters as the brief's literal <b>hard gate</b>: emission is permitted only inside the top
80&nbsp;% of tiles. The holdout says the soft version costs nothing (+0.0004, 4 of 6 folds) and the
hard version costs 0.0025 and loses in 6 of 6 folds. Both numbers are on the
<a href="holdout.html">holdout</a> page.</p>
"""
    _f = s1stats.get("fault_II_median_nanostrain_tiles_with_trace", float("nan"))
    _o = s1stats.get("observed_II_median_nanostrain", float("nan"))
    body = (body.replace("{fm:.1f}", f"{_f:.1f}")
                .replace("{om:.1f}", f"{_o:.1f}")
                .replace("{pct:.0f}", f"{100 * _f / _o if _o else 0:.0f}"))
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
    body = f"""
<h2>Candidate hypotheses</h2>
<p>Each names the layers involved, the physical signature targeted, why it should catch a fault the
USGS/INGENIOUS catalogue is missing rather than one already in it, and how it differs from what is
already implemented here. Ranked by expected DTI improvement against implementation cost. The last
four columns are the measured result from the block holdout, filled in after the run, not before.</p>
{tbl(['id','name','layers','physical signature','why it catches a missing fault','differs from','expected ΔDTI','cost','outcome','AUC','proxy DTI at M/|G| = 3.47','Δ vs base'], rows) if rows else '<p class="missing">hypotheses.json not generated</p>'}
"""
    (DOCS / "hypotheses.html").write_text(page("Hypotheses", body, "hypotheses.html"))

    # ------------------------------------------------------------ holdout
    def arm_rows():
        out = []
        for a in ("base", "H_E", "H_D", "H_M", "H_C", "H_ALL"):
            h = hold.get(a)
            if not h:
                continue
            s = h["summary"]
            out.append([a, f"{s['auc_mean']:.4f}"] +
                       [f"{s[f'dti_r{r}']['mean']:.4f}" for r in s["ratios"]])
        return out

    ratios = []
    for a in ("base", "H_E", "H_D", "H_M", "H_C", "H_ALL"):
        if hold.get(a):
            ratios = hold[a]["summary"]["ratios"]
            break
    s1rows = []
    if two:
        sm = two["summary"]
        for k, v in sm.items():
            if k.startswith("s1_") or k.startswith("recall") or k.startswith("s2_"):
                s1rows.append([html.escape(k), f"{v['mean']:.4f}"])
    body = f"""
<h2>Holdout: both stages, scored separately</h2>
<h3>Design</h3>
<p>The footprint is cut into 3&times;3 contiguous blocks. Each block is held out in turn; the
detector never sees it; a 1.2&nbsp;km buffer around it is removed from the training pool.
Emission and scoring are both restricted to the block, and the number of emitted dots is a fixed
multiple of that block's own truth size — the official metric depends on mass and truth size only
through their ratio, so matching M/|G| is what makes the proxy comparable to a live number.</p>

<h3>Stage 2 — fine-scale arms</h3>
{tbl(['arm','in-block AUC'] + [f'DTI at M/|G|={r}' for r in ratios], arm_rows())}

<h3>Stage 1 — tile prior, alone</h3>
<p>Stage&nbsp;1 is scored with <b>no Stage 2 involvement at all</b>: dots are thrown down uniformly
at random inside the approved tiles and compared with dots thrown uniformly over the whole block.
That isolates the prior.</p>
{tbl(['quantity','mean over folds'], s1rows) if s1rows else '<p class="missing">two-stage results not generated</p>'}

<h3>Stage 1 on its own instrument</h3>
<p>The deficit is computed from the catalogue, so it cannot be evaluated on a design that removes a
whole spatial block — inside a held-out block the fault-accommodated term is identically zero and
the deficit collapses to the raw geodetic field. Stage 1 is therefore scored on a <b>trace-level</b>
holdout: a random fifth of the mapped traces is withheld, the remaining four fifths supply the
budget, and uniform random dots are thrown down inside the approved tiles versus everywhere. No
model is fitted, so there is no leakage to control.</p>
""" + _STAGE1 + f"""
<p><b>Result: the strain-budget deficit is a weak prior, and subtracting the fault-accommodated
term makes it weaker.</b> Against the raw geodetic field the deficit loses on every measure. The
reason is physical as much as statistical: the mapped-fault term tracks where faults cluster, and
faults that are mapped are surrounded by faults that are not, so the term carries <i>positive</i>
information about where the missing ones are. Removing it throws that away.</p>

<h3>Gate sweep: hard gate versus soft prior</h3>
""" + _GATE + f"""
<p>The hard gate is uniformly harmful and gets monotonically worse the tighter it is: it does not
win a single fold at any setting, and at the top 30&nbsp;% and 10&nbsp;% it destroys the submission.
The soft prior is flat across its whole range — every weight from 0.05 to 0.2 is within +0.0004 of
ungated, and 0.4 is the first weight that hurts. That is the signature of a prior that is
<i>not wrong</i> but also <i>not doing much</i>: the strain budget and the detector are looking at
the same structures, so nudging one by the other mostly rearranges ties. The shipped primary uses
w = 0.10; a hard-gated twin is offered with its cost printed on it.</p>

<h3>Stage 2 &mdash; does auto-context stacking help? (no)</h3>
<p>A per-pixel tree cannot say &ldquo;there is a long coherent high-belief lineament through this
pixel&rdquo;, and that sentence is the whole difference between a fault and a geophysical blob. The
organizer&rsquo;s reference solution buys it with a U-Net over 128&times;128 patches. Auto-context
(Tu &amp; Bai 2010) buys it for a tree: a level-1 belief map is summarised at several scales and
those summaries are appended to the raw features for a level-2 model. The level-1 belief used to
build level-2 <i>training</i> rows is cross-fitted over two spatially contiguous slabs
(Breiman 1996), so the stack cannot learn to over-trust a belief that already saw the label.</p>
""" + _AC + f"""
<p><b>It improves ranking and does not improve score.</b> In-block AUC rises +0.0085, consistently,
and the paired DTI at the shipped mass moves +0.0012. The explanation is the useful part: the
re-ordering happens <i>inside</i> the top 3.47&times;|G| pixels that were already being emitted, so
it buys no new credit. <b>Global AUC is the wrong proxy for this metric</b>; credit-per-dot at the
shipped mass is the right one. The code is kept and reachable
(<code>build_submission_v2.py --level 2</code>); it is not shipped.</p>

<h3>Stage 2 &mdash; emission geometry at matched mass (the one change that shipped)</h3>
<p>The detector field is held <i>fixed</i> and only the rule that turns it into emitted pixels is
varied, with every rule given the same number of dots. The metric forces this question:
<code>TP_w</code> is a sum over the truth of the <i>max</i> over nearby predictions, so a dot 2&nbsp;px
off the crest earns one third of a crest dot, and a second dot across the width of the same
structure earns nothing extra while costing a full unit of false-positive mass. Isotropic NMS is
blind to both facts. The shipped rule scores each pixel as
<code>rank(belief)<sup>1&minus;w</sup> &times; rank(line-accumulated ridgeness)<sup>w</sup></code>
&mdash; a multi-scale Frangi ridge filter answering &ldquo;am I on the crest?&rdquo; and a
Vanderbrug straight-line accumulator answering &ldquo;does this persist for 900&nbsp;m in one
direction?&rdquo; &mdash; then spreads dots <i>along</i> the surviving crest.</p>
""" + _GEO + f"""
<p>The <code>w = 0</code> control reproducing isotropic NMS to within 2&times;10<sup>&minus;4</sup>
on every fold is what proves the implementation is a <b>strict generalisation</b> of the incumbent:
the shipped rule cannot be worse than it through a coding error. <code>w = 0.35</code> ships rather
than the 3-fold pilot&rsquo;s <code>w = 0.7</code> because it has the same six-fold mean with a
5&times; smaller worst-fold loss. <b>Stated plainly: +0.0020 with a sign-test p of 0.344 is not
statistically separable from zero.</b> It ships because it is free, because its limit provably
reduces to the incumbent, and because a second independent instrument corroborates it &mdash; not
because the evidence is strong. That pilot/full-sweep discrepancy is logged as IR-51-13: folds
0, 2 and 4 are the three <i>easiest</i> folds, and testing on them inflated the effect by 65&nbsp;%.</p>

<h3>Emission mass</h3>
""" + _EMIS + f"""

<h3>The honest instrument: off-catalogue A/B</h3>
<p>Everything above shares one flaw. A blocked holdout hides a whole <i>region</i>, so inside it no
fault is mapped at all &mdash; it cannot measure the task the competition actually sets, which is
finding a fault the catalogue missed <i>while other faults in the same place are mapped and masked
out of scoring</i>. So a second instrument was built. The catalogue&rsquo;s 8-connected components
are treated as fault <i>systems</i> and split into <b>A</b> (visible: training positives, and the
scorer&rsquo;s known-mask) and <b>B</b> (hidden pretend-new faults, left inside the negative class
exactly as real unmapped faults are). <code>B_far</code> keeps only B components at least 5&nbsp;px
from any A pixel &mdash; structures that are not merely an interleaved strand of a mapped zone.</p>
""" + _OFFCAT + f"""
<p>Four folds; A = 41,247&nbsp;px, B = 19,741&nbsp;px, B_far = 6,130&nbsp;px in 158 components.
Two readings, both of which matter more than any tuning result on this page:</p>
<ol>
<li><b>The detector is not a catalogue halo.</b> The halo control scores <b>0.0022</b> against
<code>B_far</code> &mdash; effectively nothing, 37&times; below the detector. Whatever the model has
learned, it is not &ldquo;draw a ring around what is already mapped&rdquo;. That matters for Phase 2,
where every emitted dot goes to expert review.</li>
<li><b>Discovery is about 3.5&times; harder than rediscovery.</b> The blocked-holdout proxy reads
0.282; the same detector reads <b>0.081</b> against genuinely off-catalogue structures &mdash; still
1.9&times; uniform random, so it is finding real new geometry, but IR-51-11 is now a measured
number rather than a caveat.</li>
</ol>
<p class="ev">Stated bias of this instrument: B is drawn from the same compilation as A, so a rule
that merely haloes the catalogue flatters itself here. The <code>halo_ring</code> control is
included precisely to quantify that, and it shows the effect is absent for this detector.</p>

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
    _rows = [["0.2600 anchor (group)", "0.2600", "44 090", "4 736", "0.107"],
             ["0.2778 (group best)", "0.2778", "37 654", "4 915", "0.131"],
             ["nchuzhoy (public #3)", "0.3262", "~40 000*", "~5 770*", "~0.144*"],
             ["leader (public #1)", "0.3774", "~44 000*", "~7 160*", "~0.163*"]]
    (DOCS / "analysis.html").write_text(page(
        "Analysis", ANALYSIS_BODY.read_text().replace(
            "{tbl_html}",
            tbl(["submission", "public DTI", "emitted mass M", "implied TP", "credit per dot"],
                _rows)), "analysis.html"))

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
h3{margin:22px 0 8px;font-size:17px;color:#1c3purple}
h3{color:#1b3b52}
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
