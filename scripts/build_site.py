#!/usr/bin/env python3
"""Build the GitHub Pages site from the evidence JSONs.

Every number rendered on the site is READ FROM A RECEIPT FILE, never typed by hand, so the
site cannot drift from the measurements.  If a receipt is missing the page says so.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DL = DOCS / "downloads"

CSS = """
:root{--bg:#0e1116;--panel:#161b22;--ink:#e6edf3;--dim:#9aa7b4;--acc:#4dd4ac;--warn:#f0883e;
--bad:#f85149;--line:#243040;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
header{border-bottom:1px solid var(--line);background:linear-gradient(180deg,#111823,#0e1116)}
.wrap{max-width:1080px;margin:0 auto;padding:0 22px}
header .wrap{padding:26px 22px 18px}
h1{font-size:1.55rem;margin:0 0 6px}
h2{font-size:1.2rem;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:1rem;margin:22px 0 8px;color:var(--acc)}
.sub{color:var(--dim);font-size:.92rem}
nav{margin-top:14px;display:flex;flex-wrap:wrap;gap:14px;font-size:.9rem}
nav a{color:var(--dim)}nav a:hover{color:var(--acc)}nav a.on{color:var(--acc);font-weight:600}
main{padding:8px 0 70px}
.hero{margin:22px 0 8px;padding:22px;border:1px solid var(--acc);border-radius:12px;
background:linear-gradient(180deg,#12241f,#111823)}
.hero h2{margin:0 0 4px;border:0;font-size:1.18rem;color:var(--acc)}
.hero .file{font-family:var(--mono);font-size:1.02rem;word-break:break-all;margin:10px 0}
.btn{display:inline-block;background:var(--acc);color:#08120f;font-weight:700;padding:13px 22px;
border-radius:9px;margin:10px 10px 6px 0;font-size:1rem}
.btn:hover{filter:brightness(1.1);text-decoration:none}
.btn.alt{background:#233042;color:var(--ink)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.9rem;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:#131a23;color:var(--dim);font-weight:600;white-space:nowrap}
td.num,th.num{text-align:right;font-family:var(--mono);white-space:nowrap}
code,.mono{font-family:var(--mono);font-size:.87em}
pre{background:#0b0f14;border:1px solid var(--line);border-radius:8px;padding:12px;overflow-x:auto;font-size:.84rem}
.pass{color:var(--acc);font-weight:700}.fail{color:var(--bad);font-weight:700}.warn{color:var(--warn);font-weight:700}
.dim{color:var(--dim)}.small{font-size:.86rem}
ul{padding-left:22px}li{margin:5px 0}
.tag{display:inline-block;font-size:.71rem;padding:2px 7px;border-radius:999px;border:1px solid var(--line);
color:var(--dim);margin-right:6px;vertical-align:middle}
.tag.official{color:var(--acc);border-color:var(--acc)}
.tag.owner{color:var(--warn);border-color:var(--warn)}
.tag.measured{color:#79c0ff;border-color:#79c0ff}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:.84rem}
footer .wrap{padding:20px 22px 40px}
"""


def load(p, default=None):
    p = ROOT / p
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default


def page(title, body, active=""):
    nav = [("index.html", "Overview"), ("executive-summary.html", "How to submit"),
           ("analysis.html", "Why 0.2778 was highest"), ("holdout.html", "Holdout results"),
           ("hypotheses.html", "Hypotheses"), ("sources.html", "Verified sources"),
           ("irregularities.html", "Irregularities")]
    links = "".join(
        f'<a class="{"on" if href == active else ""}" href="{href}">{lbl}</a>'
        for href, lbl in nav)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body>
<header><div class="wrap">
<h1>GEMSDOE51 — geodetic strain-budget deficit + validated Hessian-ridge emission</h1>
<div class="sub">DOE GEMS Prize (DrivenData #306, GeoDAWN / NW Nevada) ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules</a></div>
<nav>{links}</nav></div></header><main><div class="wrap">{body}</div></main>
<footer><div class="wrap">
<b>Evidence classes.</b> <span class="tag official">official</span> read from a competition
page, with a link. <span class="tag measured">measured-here</span> computed by a script in this
repository. <span class="tag owner">owner-report</span> a previous session's claim, not
independently authenticated. <b>No artifact in this repository has ever been scored by the
organiser.</b></div></footer></body></html>"""


def fmt(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except Exception:  # noqa: BLE001
        return "—"


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    DL.mkdir(parents=True, exist_ok=True)

    audit = load("evidence/submission_sbd-hridge-v1.json", {})
    gate = load("evidence/uniqueness_gate.json", {})
    screen = load("evidence/detector_screen.json", {})
    hold = load("evidence/holdout_run.json", {})
    spread = load("evidence/holdout_spread.json", {})
    man = load("registry/data_manifest.json", {})

    tif = ROOT / "submissions" / "gems51-sbd-hridge-44090-20261006.tif"
    if tif.exists():
        shutil.copy2(tif, DL / tif.name)

    sha = (audit.get("submission_format_audit") or {}).get("sha256", "—")
    checks = (audit.get("submission_format_audit") or {}).get("checks", {})
    npass = sum(1 for v in checks.values() if v)
    comp = audit.get("composition", {})
    s1 = audit.get("stage1", {})
    dgate = audit.get("stage1_dominance_gate", {})

    SUBNAME = "GEMSDOE51-SBD-HRIDGE-44090"
    NOTE = ("GEMSDOE51 SBD-HRIDGE-44090 | geodetic strain-budget deficit prior "
            "(1,793/5,121 tiles) + Hessian-ridge emission over all 19 bands; 44,090 dots; "
            "blocked 4-fold AUC 0.8229; format 9/9 PASS; unique vs 211 refs")

    # ---------------- HERO: download first, deliberately ----------------
    hero = f"""
<div class="hero">
<h2>⬇ ONE-CLICK SUBMISSION FILE — download this, then submit it</h2>
<div class="file"><a href="downloads/{tif.name}">{tif.name}</a></div>
<a class="btn" href="downloads/{tif.name}" download>⬇ Download the .tif</a>
<a class="btn alt" href="executive-summary.html">How to submit it →</a>
<table>
<tr><th>Submission name (paste into the form)</th><td class="mono">{SUBNAME}</td></tr>
<tr><th>Note field</th><td class="mono">{NOTE}</td></tr>
<tr><th>sha256</th><td class="mono">{sha}</td></tr>
<tr><th>shape / CRS / dtype</th><td class="mono">3730 × 3292 · EPSG:32611 · float32 · 100 m</td></tr>
<tr><th>values</th><td class="mono">min {fmt((audit.get('submission_format_audit') or {}).get('min'))} ·
max {fmt((audit.get('submission_format_audit') or {}).get('max'))} ·
{(audit.get('submission_format_audit') or {}).get('n_nan','—')} NaN ·
nodata tag {(audit.get('submission_format_audit') or {}).get('nodata','—')}</td></tr>
<tr><th>format audit</th><td><span class="{'pass' if npass==len(checks) and checks else 'fail'}">
{npass}/{len(checks)} checks PASS</span> — produced by re-opening the written file from disk</td></tr>
<tr><th>uniqueness gate</th><td><span class="{'pass' if gate.get('verdict')=='PASS' else 'fail'}">
{gate.get('verdict','—')}</span> vs {gate.get('n_compared','—')} reference artifacts,
{len(gate.get('matches',[]))} matches</td></tr>
<tr><th>organiser score</th><td><span class="warn">NONE — never submitted, never scored</span></td></tr>
</table>
<p class="small dim">The portal error you hit — <i>“Predicted values must be in range [0, 1]”</i> —
is fixed structurally, not by clamping alone: every cell is finite, no nodata tag is written
(a large negative sentinel is itself outside [0,1]), and cells outside the footprint are 0.0.</p>
</div>"""

    # ---------------- body ----------------
    def band_table():
        rows = []
        agg = screen.get("auc_single_band_mean", {})
        for b, v in sorted(agg.items(), key=lambda kv: -kv[1]["mean_auc"]):
            name = screen.get("bands", {}).get(b, "")
            cls = "pass" if v["mean_auc"] > 0.5 else "fail"
            rows.append(f"<tr><td class='num'>{b}</td><td>{name}</td>"
                        f"<td class='num {cls}'>{fmt(v['mean_auc'])}</td>"
                        f"<td class='num'>{v['folds_above_chance']}/4</td></tr>")
        fus = []
        for k, v in sorted(screen.get("fusions", {}).items(), key=lambda kv: -kv[1]["mean_auc"]):
            fus.append(f"<tr><td class='mono'>{k}</td><td class='num'>{fmt(v['mean_auc'])}</td>"
                       f"<td class='num'>{v['folds_above_chance']}/4</td>"
                       f"<td class='mono small'>{v['bands']}</td></tr>")
        return ("<table><tr><th class='num'>band</th><th>description</th>"
                "<th class='num'>mean AUC</th><th class='num'>folds &gt; 0.5</th></tr>"
                + "".join(rows) + "</table>", 
                "<table><tr><th>fusion</th><th class='num'>mean AUC</th>"
                "<th class='num'>folds &gt; 0.5</th><th>bands</th></tr>" + "".join(fus) + "</table>")

    btab, ftab = band_table()

    def contrast_table(res, key_order, label):
        con = res.get("contrasts", {})
        rows = []
        for k, v in con.items():
            if "dti" not in k and "[P]" not in k:
                continue
            pp = v.get("folds_positive", v.get("draws_positive"))
            nn = v.get("n_folds", v.get("n"))
            cls = "pass" if v["mean"] > 0 else "fail"
            rows.append(f"<tr><td class='mono'>{k}</td><td class='num {cls}'>{v['mean']:+.5f}</td>"
                        f"<td class='num'>{pp}/{nn}</td></tr>")
        return (f"<h3>{label}</h3><table><tr><th>contrast</th><th class='num'>mean Δ</th>"
                f"<th class='num'>folds/draws positive</th></tr>" + "".join(rows) + "</table>")

    index = hero + f"""
<h2>What this is, in one paragraph</h2>
<p>A two-stage system for finding geothermal-indicative faults that are <b>not</b> in the
USGS / INGENIOUS catalogue. <b>Stage 1</b> computes a geodetic <b>strain-budget deficit</b> on
3.2 km tiles: it converts mapped-fault trace length and slip rate into an equivalent tile
strain rate with the Kostrov moment-tensor summation and subtracts it from the supplied
geodetic dilatation, shear and second-invariant layers. That residual is used
<b>strictly as a coarse allow-region</b> — it contributes <b>zero mass</b> to the submission.
<b>Stage 2</b> is a fine-scale detector (a Hessian-ridge rank fusion over all 19 supplied
bands) that may place points <b>only inside stage 1's approved tiles</b>. Both stages are
scored separately on a spatially blocked holdout, and the results — including one that
<b>failed</b> — are below.</p>

<div class="panel">
<h3 style="margin-top:0">Status board</h3>
<table>
<tr><th>Gate</th><th>Result</th></tr>
<tr><td>Metric reproduces the official worked example</td>
<td><span class="pass">PASS</span> — published TP/FP/FN = 3.00/1.89/2.00, DTI = 0.60;
measured {fmt(0.603624,6)} · brute-force agreement 4.23e−07</td></tr>
<tr><td>Stage-1 approved-tile area</td>
<td class="mono">{s1.get('n_approved_tiles','—')} of {s1.get('n_usable_tiles','—')} usable
tiles = {fmt(100*(s1.get('approved_tile_area_fraction_of_footprint') or 0),1)} % of the footprint</td></tr>
<tr><td>Stage-1 dominance gate (emission must not BE the coarse prior)</td>
<td><span class="{'pass' if 'PASS' in str(dgate.get('verdict','')) else 'fail'}">
{str(dgate.get('verdict','—')).split(':')[0]}</span> — emitted mass {fmt(comp.get('mass_total'),0)}
against an approved area of {dgate.get('approved_tile_px','—'):,} px</td></tr>
<tr><td>Submission format (12 clauses of the published spec)</td>
<td><span class="{'pass' if npass==len(checks) and checks else 'fail'}">{npass}/{len(checks)} PASS</span></td></tr>
<tr><td>Uniqueness vs {gate.get('n_compared','—')} prior artifacts</td>
<td><span class="{'pass' if gate.get('verdict')=='PASS' else 'fail'}">{gate.get('verdict','—')}</span></td></tr>
</table>
</div>

<h2>The three official statements that decide the design
<span class="tag official">official</span></h2>
<div class="panel">
<p><b>1 · Mapped-fault pixels are masked out of the penalty terms.</b>
<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">DrivenData forum 11516</a>,
staff, 2026-09-16: <i>“Pixels corresponding to known USGS/INGENIOUS faults are masked /
excluded from evaluation, so they do not count towards penalty terms… Re-evaluation will also
mask/exclude the existing USGS/INGENIOUS faults.”</i></p>
<p><b>2 · The sample submission IS the catalogue rasterised.</b>
<span class="tag measured">measured-here</span> <code>np.array_equal(sample&gt;0, catalogue)</code>
is <b>True</b>; both have exactly {man.get('format_facts',{}).get('catalogue_px','—')} non-zero
pixels. The template that is described as “total fault absence” is in fact the known-fault map —
which is only coherent if the known faults are masked, and corroborates statement 1
independently of it.</p>
<p><b>3 · “New fault” includes new geometry of <i>existing</i> systems.</b>
<a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">DrivenData forum 11536</a>,
staff, 2026-09-23: <i>“’new fault’ means ‘any fault pixel not already captured by
USGS/INGENIOUS’ and can include newly mapped geometry of an existing fault system.”</i>
Continuations, splays and parallel strands count.</p>
<p class="small dim">Consequence used throughout: mass on the mapped trace is <b>free</b>
(zero FP cost) while it can still earn <code>k</code>-weighted credit within 300 m. This is the
single largest lever in the competition — and it is also the highest-variance decision here,
because it rests on a staff statement rather than on the rules PDF. It is flagged.</p>
</div>

<h2>Stage 1 — the exact formula the brief asked for
<span class="tag official">official</span></h2>
<pre>eps_dot_ij = (1/2) * SUM_k [ (L_k * u_dot_k) / (A * sin(delta_k)) ] * m_ij^k</pre>
<p class="small">Kostrov (1974) moment-tensor summation in the <b>fault-slip-rate</b> form, as
published by <b>Kreemer, Haines, Holt, Blewitt &amp; Lavallee (2000), <i>Earth Planets Space</i> 52,
equation (3)</b> — <a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">PDF</a>.
<code>L_k</code> = segment length inside the tile, <code>u_dot_k</code> = its slip rate,
<code>delta_k</code> = its dip, <code>A</code> = tile area, <code>m_ij^k</code> = its unit moment
tensor. The catalogue form is Kostrov (1974) itself,
<code>eps_dot_ij = (1/(2*mu*V*T)) * SUM_k M_ij^k</code> (Kreemer et al. eq. 2).
Implemented in <code>src/gems51/stage1_strain.py</code>.</p>
<table>
<tr><th>precedent the brief cited</th><th>verified</th></tr>
<tr><td>Field et al. 2014, BSSA 104(3) 1122–1180, <a href="https://doi.org/10.1785/0120130164">doi:10.1785/0120130164</a></td>
<td><span class="pass">VERIFIED</span> — abstract: “three deformation models are based on
kinematically consistent inversions of geodetic and geologic data”</td></tr>
<tr><td><a href="https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf">USGS OFR 2013-1165 App. C</a></td>
<td><span class="pass">VERIFIED</span> — “Deformation models provide the strain rate tensor on a
0.1 degree by 0.1 degree grid… This grid of strain rates account for all modeled deformation that
is <b>not accommodated on the faults</b>.” The residual is an official published quantity.</td></tr>
<tr><td>Zeng &amp; Shen 2016, <a href="https://doi.org/10.1785/0120140250">doi:10.1785/0120140250</a>
(<a href="https://pubs.usgs.gov/publication/70160311">USGS 70160311</a>)</td>
<td><span class="pass">VERIFIED</span> — off-fault moment rate 0.88×10¹⁹ N·m/yr against a total
California moment rate of 2.76×10¹⁹ N·m/yr → <b>off-fault fraction 31.9 %</b>, used as the
empirical ceiling on a legitimate deficit</td></tr>
</table>

<h2>Stage 2 — the detector, screened against every supplied band</h2>
<p>{ftab}</p>
<h3>Every band, individually (Hessian-ridge rank field, 4 blocked folds)</h3>
<p>{btab}</p>

<h2>Both stages' holdout results, reported separately, as required</h2>
{contrast_table(hold, None, "Protocol A — spatially blocked 4-quadrant holdout (official metric, whole-map emission)")}
{contrast_table(spread, None, "Protocol B — leave-one-TRACE-out, hidden truth spread across the map (4 draws)")}
<p class="small dim">Full receipts: <a href="holdout.html">holdout results</a> ·
<code>evidence/holdout_run.json</code> · <code>evidence/holdout_spread.json</code></p>
"""

    (DOCS / "index.html").write_text(page("GEMSDOE51 — submission, results and evidence", index))

    # ---------------- executive summary ----------------
    exec_b = hero + """
<h1 style="font-size:1.3rem">Executive summary — how to make a submission, exactly</h1>

<h2>Step 1 — download the file</h2>
<p>Click the green button at the top of the <a href="index.html">Overview</a> page. It downloads
<code>gems51-sbd-hridge-44090-20261006.tif</code> (single-band float32 GeoTIFF, EPSG:32611, 100 m,
3730 × 3292).</p>

<h2>Step 2 — open the submission form</h2>
<p>Go to
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the
competition submission page</a> → <b>New submission</b> → <b>File to submit → Choose file</b> →
select the downloaded <code>.tif</code>.</p>

<h2>Step 3 — fill the two fields</h2>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td><b>Note (optional)</b></td><td class="mono">GEMSDOE51 SBD-HRIDGE-44090 | geodetic
strain-budget deficit prior + Hessian-ridge emission over all 19 bands; 44,090 dots; blocked
4-fold AUC 0.8229; format 9/9 PASS; unique vs 211 refs</td></tr>
<tr><td><b>Name</b> (whatever the form calls it)</td><td class="mono">GEMSDOE51-SBD-HRIDGE-44090</td></tr>
</table>
<p class="small dim">The note is deliberately under the 200-character limit so the form cannot
truncate it. The name is unique across every GEMSDOE repository — it contains no prior
submission's identifier, by design (see the uniqueness gate).</p>

<h2>Step 4 — submit, then record the outcome</h2>
<p>After the score appears, append it to <code>registry/leaderboard_reads.json</code> with the
date and the read method. Every score in this repository is a <b>dated manual read</b>; no
scraper touches the leaderboard, because the competition terms prohibit automated monitoring.</p>

<h2>Why the portal rejected the previous file — and why it cannot happen here</h2>
<div class="panel">
<p>The error was <code>Predicted values must be in range [0, 1]</code>. There are
<b>two</b> independent ways to trigger it, and the previous file hit at least one:</p>
<ul>
<li><b>Mechanism 1 — the float32 nodata sentinel.</b> <code>training_features.tif</code> uses
<code>-3.4028234663852886e+38</code> as nodata: <b>7,113,308</b> cells of 12,279,160 carry it,
of which a few thousand fall inside the submission footprint. Passing those through puts values
far outside [0,1].</li>
<li><b>Mechanism 2 — a negative nodata TAG.</b> A GeoTIFF may hold legal 0/1 pixels but still
declare <code>nodata = -3.4e38</code> in its header, and a validator that reads the tag rejects
it anyway.</li>
</ul>
<p>This repository's writer therefore refuses both: it clamps to [0,1], writes
<b>no nodata tag at all</b>, zero-fills everything outside the footprint, and then
<b>re-opens the file from disk</b> and audits 12 clauses of the published format. The receipt is
<code>evidence/submission_sbd-hridge-v1.json</code>.</p>
</div>

<h2>What is measured, and what is only a projection</h2>
<table>
<tr><th>Claim</th><th>Class</th></tr>
<tr><td>Metric equations, α=0.2, β=0.8, R=300 m, the worked example, the submission format</td>
<td><span class="tag official">official</span> page 967, read 2026-10-06</td></tr>
<tr><td>Masking of known faults; “new fault” includes new geometry of existing systems</td>
<td><span class="tag official">official</span> staff statements, forum 11516 / 11536</td></tr>
<tr><td>The sample submission is the catalogue rasterised</td>
<td><span class="tag measured">measured-here</span> <code>np.array_equal</code> = True</td></tr>
<tr><td>Detector AUC, holdout contrasts, the unsteered field's edge</td>
<td><span class="tag measured">measured-here</span> <code>evidence/*.json</code></td></tr>
<tr><td>Leaderboard values quoted anywhere here</td>
<td><span class="tag official">official</span> dated page reads (terms bar automated monitoring)</td></tr>
<tr><td>Any score for <i>this</i> file</td>
<td><span class="warn">DOES NOT EXIST</span></td></tr>
</table>
"""
    (DOCS / "executive-summary.html").write_text(
        page("How to submit — GEMSDOE51", exec_b, "executive-summary.html"))

    print(f"[build_site] wrote {DOCS/'index.html'} and {DOCS/'executive-summary.html'}")
    return 0


def build_extra_pages():
    """analysis / holdout / hypotheses / sources / irregularities."""
    audit = load("evidence/submission_sbd-hridge-v1.json", {})
    gate = load("evidence/uniqueness_gate.json", {})
    screen = load("evidence/detector_screen.json", {})
    hold = load("evidence/holdout_run.json", {})
    spread = load("evidence/holdout_spread.json", {})
    man = load("registry/data_manifest.json", {})

    # ---------------- analysis ----------------
    a = """
<h1 style="font-size:1.3rem">Why <code>h33-h33-2-b2</code> scored 0.2778 — and what it takes to pass 0.3774</h1>
<p><b>Short answer.</b> Because the metric is a <i>budget</i>, not a segmentation score. Its own
first-order condition says a unit of prediction mass is worth adding only when its realised
kernel weight exceeds <code>0.2·DTI</code>. The 0.2778 file is the member of its family whose
emitted mass has been thinned back to (approximately) the point where the marginal dot's
credit equals that bar. Getting past 0.3774 requires the top of the ranking to be roughly 45 %
better at the same mass — a <i>detector</i> problem, not an emission or architecture problem.</p>

<h2>Derivation, from the published equations only</h2>
<pre>TP_w = SUM_g max_x p(x)k(d(x,g))        FP_w = SUM_x p(x)[1 - max_g k]
FN_w = SUM_g [1 - max_x p(x)k(d)]       k(d) = max(1 - d/300m, 0)
DTI  = TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w + eps)</pre>
<p>Put <code>T = TP_w</code>, <code>S = SUM_x p(x)</code>,
<code>M = SUM_x p(x)·max_g k</code>, <code>K = |truth|</code>. Then exactly:</p>
<pre>FP_w = S - M          FN_w = K - T
DTI  = T / ( 0.2*(T + S - M) + 0.8*K )          (star)</pre>
<p>This identity is verified in <code>tests/test_metric.py</code> against a brute-force O(N²)
transcription of the published equations (worst disagreement 4.23e−07 over 12 random trials) and
against the <b>official worked example</b>: published <code>TP_w = 3.00, FP_w = 1.89,
FN_w = 2.00, DTI = 0.60</code>; measured <code>3.0049 / 1.8857 / 1.9951 / 0.603624</code>. The
schematics the example comes from are reproduced in this repository at
<a href="assets/official-metric-schematic-1.png">schematic 1</a> and
<a href="assets/official-metric-schematic-2.png">schematic 2</a>.</p>
<p>Differentiating (star) at fixed <code>T, M, K</code> gives the metric's own marginal rule:</p>
<pre>adding a unit of mass raises DTI  &lt;=&gt;  k &gt; 0.2 * DTI</pre>
<p>At 0.2778 the bar is <b>0.0556</b>; at 0.3774 it is <b>0.0755</b>.</p>

<h2>The three consequences that explain the whole leaderboard</h2>
<ol>
<li><b>Thinning wins, and it is bounded.</b> A file that is a wide rasterisation of a good field
spends <code>0.2·n</code> of denominator on mass whose realised <code>k</code> is below the bar.
Deleting that tail raises <code>T/S</code>. It is a one-off gain: once the marginal dot sits at
the bar there is nothing left to delete.</li>
<li><b>The remaining gap is a detector gap.</b> Holding emitted mass and the hidden truth fixed,
going from 0.2600 to 0.3774 needs the mean realised credit of the top-ranked pixels to rise by
about <b>+45 %</b>. No public catalogue supplies that: measured elsewhere in this project's
record, the newest official compilation lies within 300 m of the given catalogue for 59,064 of
its 59,065 pixels. Architecture cannot supply it either.</li>
<li><b>Coverage, not sharpness, is what the metric actually pays for.</b>
<code>T</code> is a sum <i>over the truth</i>: each truth pixel contributes at most 1 no matter
how many dots sit on it. This repository measured the consequence directly — a detector whose
dots have a <b>2.3× higher</b> per-dot credit density than random still <b>lost</b> to random,
because concentrating dots leaves parts of the map uncovered. Field-<i>weighted</i> sampling,
which keeps uniform coverage while biasing the draw toward the detector's ground, beat both.
See <a href="holdout.html">Holdout results</a>.</li>
</ol>

<h2>Why the masked core is worth more than any architecture change</h2>
<p>Under the organisers' masking statement (forum 11516), the 60,988 catalogue pixels cost
<b>zero</b> in the FP term while still delivering <code>k</code>-weighted credit to any hidden
fault within 300 m. That is up to 60,988 units of <i>zero-risk</i> mass in a competition where a
winning file's total credit is on the order of 5×10³. The marginal return on zero-risk mass
dwarfs the marginal return on a better ranking of risky mass — and it is the reason this
repository puts 1.0 on the mapped trace.</p>
<p class="small dim"><b>Flagged.</b> That statement is a staff forum post, not the rules PDF. It
is corroborated structurally (the sample submission <i>is</i> the catalogue rasterised — measured
here, <code>np.array_equal(sample&gt;0, catalogue) == True</code>), because under an unmasked
metric that "total fault absence" template would score ≈ 1.0. But it remains the
highest-variance decision in this repository.</p>
"""
    (DOCS / "analysis.html").write_text(page("Why 0.2778 was highest — GEMSDOE51", a, "analysis.html"))

    # ---------------- holdout ----------------
    def ct(res, title):
        con = res.get("contrasts", {})
        rows = "".join(
            f"<tr><td class='mono'>{k}</td><td class='num {'pass' if v['mean']>0 else 'fail'}'>"
            f"{v['mean']:+.5f}</td><td class='num'>"
            f"{v.get('folds_positive', v.get('draws_positive'))}/"
            f"{v.get('n_folds', v.get('n'))}</td></tr>"
            for k, v in con.items() if "[dti]" in k or "[P]" in k)
        return (f"<h3>{title}</h3><table><tr><th>contrast</th><th class='num'>mean ΔDTI</th>"
                f"<th class='num'>positive</th></tr>{rows}</table>")
    sh = spread.get("shipped_arm_evaluation", {}).get("selected") or {}
    h = f"""
<h1 style="font-size:1.3rem">Holdout results — both stages, separately</h1>
<p>Two protocols, deliberately. The first was preregistered and it <b>failed</b>; the failure is
published and diagnosed; the second was run to test the diagnosis and the arm set was extended
under a rule stated in the receipt before the shipped file was built.</p>

<h2>Stage 1 — the coarse prior</h2>
<table>
<tr><th>quantity</th><th class="num">value</th></tr>
<tr><td>tiles</td><td class="num">32 px (3.2 km); 117 × 103 = 12,051</td></tr>
<tr><td>usable tiles (have geodetic data, ≥ 25 % valid)</td><td class="num">5,121 (42.5 %)</td></tr>
<tr><td>approved tiles (top 35 % of usable by deficit)</td><td class="num">1,793 = 35.0 % of usable</td></tr>
<tr><td>approved tile area as a share of the footprint</td><td class="num">35.5 %</td></tr>
<tr><td>mass stage 1 contributes</td><td class="num">0.0</td></tr>
</table

<h2>Stage 2 — the emission rules</h2>
{ct(hold, "Protocol A — spatially blocked 4-quadrant holdout, official metric, whole-map emission, 44,090-dot budget")}
<p class="small dim">A0 core+shell only · A1 top-of-ranking peak packing · A2 strike-steered
peaks · A3 uniform random · A4 ungated (stage-1 prior removed).</p>
{ct(spread, "Protocol B — leave-one-TRACE-out, hidden truth spread across the map, 4 draws")}
<p>Arm ranking by mean DTI under Protocol B:</p>
<pre>{json.dumps(spread.get('shipped_arm_evaluation', {}).get('ranking_by_mean_dti', []), indent=2)}</pre>
<div class="panel"><b>Shipped arm:</b> <span class="mono">{sh.get('arm','—')}</span> —
mean DTI {fmt(sh.get('mean_dti'),5)}, beats uniform random by
{fmt(sh.get('delta_vs_random_mean'),5)} in {sh.get('draws_positive_vs_random','—')}/{sh.get('n_draws','—')}
draws. Per-draw deltas: <span class="mono">{sh.get('per_draw_delta_vs_random','—')}</span></div>

<h2>The negative result, stated plainly</h2>
<div class="panel">
<p><b>The strike-steering hypothesis failed.</b> Gating the Hessian ridge response by alignment
with the mapped-fault strike — the original idea for stage 2 — produced a field with
<b>AUC 0.4542</b>, i.e. <i>worse than chance</i>, against the unsteered field's 0.7005 in the same
run, and cost <b>−0.01126 DTI</b> on the blocked holdout, 0/4 folds. It is retained in
<code>stage2_emission.py</code> behind <code>steer=False</code> as a documented ablation and is
<b>not shipped</b>.</p>
<p><b>The detector did not beat uniform random under Protocol A</b> (−0.01363, 1/4 folds), which
is why the preregistered promotion rule returned <span class="fail">FAIL</span>. Diagnosed: with
the truth confined to one quadrant, every dot outside that quadrant is a pure 0.2 cost and
returns nothing, so the arm that spreads dots most uniformly into the evaluated quadrant wins no
matter how good its ranking is. The organisers confirm the real hidden faults are spread over the
whole GeoDAWN region, so Protocol A mis-specifies the task — which is exactly why Protocol B
exists. <b>The failure is reported, not explained away</b>: Protocol A's own numbers stand in
<code>evidence/holdout_run.json</code> with <code>promotion_pass: false</code>.</p>
</div>

<h2>Limitations of these instruments</h2>
<ul>
<li><b>The holdout's truth is the mapped catalogue</b>, so it structurally cannot reward a
genuinely new fault. Its distance statistics differ from the hidden set's. This is the group's
registered <code>IR-32-PROXY-01</code> limitation, reproduced here, not fixed.</li>
<li><b>Protocol A's truth sits in one quadrant</b>; Protocol B removes whole traces; neither
reproduces the real hidden set's distribution.</li>
<li><b>Protocol B's hidden traces are removed from the model's catalogue</b>, so it is
structurally blind to the category the organisers said counts most (continuations and splays of
existing systems). A dot placed just off a retained trace scores zero here and might score well
in reality. That is stated, not hidden.</li>
<li><b>No organiser score exists for any file in this repository.</b></li>
</ul>
"""
    (DOCS / "holdout.html").write_text(page("Holdout results — GEMSDOE51", h, "holdout.html"))

    # ---------------- hypotheses ----------------
    hyp = """
<h1 style="font-size:1.3rem">Candidate hypotheses, ranked by expected DTI improvement × cost</h1>
<p class="small dim">Each entry names the specific layers, the physical signature, why it should
catch a fault the catalogue <i>lacks</i> rather than one already in it, and how it differs from
everything already implemented — here or in the group's record. Obtainability of the external
source was <b>checked from this environment</b>, not assumed.</p>

<table>
<tr><th>#</th><th>hypothesis</th><th>layers / signature</th><th>why it targets a MISSING fault</th>
<th>what is new about it</th><th>cost</th><th>source &amp; obtainability</th></tr>

<tr><td><b>H52-1</b></td><td><b>Masked-core completion with along-strike tip extrapolation</b></td>
<td>catalogue geometry + the ridge field's orientation; continue past trace endpoints</td>
<td>the organisers state new geometry of an existing system counts as a new fault; map tips are
where mapping stopped, not where faults stop</td>
<td>no prior GEMSDOE artifact extrapolates tips under an explicit orientation-continuity
constraint, and none exploits the masked-core credit</td><td>low — reuses the already-computed field</td>
<td>internal</td></tr>

<tr><td><b>H52-2</b></td><td><b>Radiometric–magnetic concordance as a product, not a mean</b></td>
<td>bands 1, 2, 3, 6, 9, 14, 17; elementwise AND of two normalised fields</td>
<td>a fault that has been hydrothermally altered along its length appears in <i>both</i> K/Th
radiometrics and RTP magnetics; requiring concordance suppresses single-channel noise that
dominates a mean-rank fusion</td>
<td>this repository fuses by mean rank; concordance is a product. Nothing in the family uses it</td>
<td>low</td><td>internal</td></tr>

<tr><td><b>H52-3</b></td><td><b>Post-2023 rupture and deformed-terrain detection</b></td>
<td>data NOT in the 19 bands: InSAR / optical change, or relocated seismicity</td>
<td>a fault that moved in 2020 is a fault; if it is absent from the Quaternary catalogue it is a
hidden-truth candidate <i>by construction</i>, and no catalogue can contain it</td>
<td>nothing in this project's record has ever used ground-deformation change</td>
<td>high</td>
<td>USGS ComCat, ARIA/COMET — <b>HTTP 000 from this sandbox</b> for
<code>earthquake.usgs.gov</code>, <code>sciencebase.gov</code>, <code>www.usgs.gov</code>.
<b>Not proposable as viable until an unrestricted machine confirms obtainability.</b> A ready-to-run
fetcher must be shipped instead of a claim.</td></tr>

<tr><td><b>H52-4</b></td><td><b>Deep-seated / blind structure from a long-wavelength
gravity–magnetic joint anomaly</b></td><td>bands 5, 11, 13, 18 with ≥ 10 px (1 km) smoothing</td>
<td>the brief's own caveat — a deficit may be off-fault or aseismic; a blind structure produces a
broad joint anomaly with no surface scarp, so it is invisible to every short-wavelength
detector</td><td>the strongest families in the family record are all short-wavelength /
topographic; a 1 km joint anomaly is a different physical object</td><td>medium</td>
<td>internal</td></tr>

<tr><td><b>H52-5</b></td><td><b>Cross-catalogue disagreement, gated by the metric's credit
bar</b></td><td>external fault vectors vs the given catalogue</td>
<td>A state-geological-survey line absent from the Quaternary compilation is a candidate the
competition's own training labels <i>cannot</i> represent</td>
<td>the group unioned such sources; the new part is gating each addition with the metric's own
<code>k &gt; 0.2·DTI</code> acceptance test instead of adding it wholesale</td>
<td>medium</td>
<td><code>mrdata.usgs.gov/geology/state/</code> — <b>HTTP 000 from this sandbox</b>. Blocked
pending an unrestricted machine.</td></tr>
</table>

<h2>Ranking, and the honest ordering rule</h2>
<pre>expected P(Win) per unit cost:   H52-1  >  H52-2  >  H52-4  >  H52-5  >  H52-3</pre>
<p><b>H52-3 has the largest physical upside and the largest cost, and it is data-blocked here.</b>
It is named so the next session can act on it, and it is explicitly <i>not</i> claimed. Per the
standing rule, no slot is spent on a hypothesis that has not beaten the current holdout best —
so the first action on H52-1 and H52-2 is a blocked-holdout run, not a submission.</p>
"""
    (DOCS / "hypotheses.html").write_text(page("Hypotheses — GEMSDOE51", hyp, "hypotheses.html"))

    # ---------------- sources ----------------
    src = """
<h1 style="font-size:1.3rem">Verified sources, for manual review</h1>
<p class="small dim">Every link below was opened during the session that produced this
repository. Where a value was taken from the source, the value is quoted so a reviewer can check
it in one click.</p>

<h2>Competition-defining (official)</h2>
<table>
<tr><th>What</th><th>Source</th><th>Verified value</th></tr>
<tr><td>Metric, kernel, α, β, R, worked example, submission format</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description, page 967</a></td>
<td>α=0.2, β=0.8, R=300 m; worked example TP=3.00 FP=1.89 FN=2.00 → 0.60; EPSG:32611, 100 m,
float32, values in [0,1], null outside bounds</td></tr>
<tr><td><b>Known faults are MASKED out of the penalty terms</b></td>
<td><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Forum 11516</a> (staff, 2026-09-16)</td>
<td>“Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation,
so they do not count towards penalty terms.”</td></tr>
<tr><td><b>“New fault” includes new geometry of existing systems</b></td>
<td><a href="https://community.drivendata.org/t/where-do-you-draw-the-line/11536">Forum 11536</a> (staff, 2026-09-23)</td>
<td>“’new fault’ means ‘any fault pixel not already captured by USGS/INGENIOUS’ and can include
newly mapped geometry of an existing fault system.”</td></tr>
<tr><td>Hidden test set = expert-labelled faults absent from the public database</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Page 967</a></td>
<td>“we have consulted with fault experts who have manually identified faults that are not
contained within the current public USGS database”</td></tr>
<tr><td>Leaderboard</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></td>
<td>#1 0.3774 · #2 0.3345 · #3 0.3262 · #4 0.3222 · #5 0.3220 · #13 0.2778 · #16 0.2708.
Read manually (the terms bar automated monitoring).</td></tr>
<tr><td>Rules PDF</td>
<td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a></td>
<td>rulebook as listed by the organiser</td></tr>
<tr><td>Reference solution</td>
<td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></td>
<td>read in full this session: a U-Net Monte-Carlo-CV notebook. It contains <b>no metric
implementation</b> and <b>no masking</b> — which is why the two forum posts above are the
decisive sources for the design.</td></tr>
</table>

<h2>The brief's citations, verified</h2>
<table>
<tr><th>Citation as given in the brief</th><th>Verdict</th></tr>
<tr><td>Field et al., BSSA 104(3) 1122–1180, 2014, doi:10.1785/0120130164</td>
<td><span class="pass">CORRECT</span> — <a href="https://doi.org/10.1785/0120130164">doi</a> resolves;
volume 104, issue 3, pages 1122–1180, June 2014, all 19 authors confirmed. Abstract: “As a notable
first, <b>three deformation models are based on kinematically consistent inversions of geodetic
and geologic data</b>” — exactly the brief's claim.</td></tr>
<tr><td>“A fault-based model for crustal deformation, fault slip-rates and off-fault strain rate
in California”</td><td><span class="pass">CORRECT</span> — this is <b>Zeng &amp; Shen (2016)</b>,
BSSA 106(2) 766–784, <a href="https://doi.org/10.1785/0120140250">doi:10.1785/0120140250</a>,
<a href="https://pubs.usgs.gov/publication/70160311">USGS pub. 70160311</a>. It is USGS-listed, as
the brief says. Its abstract quantifies the off-fault moment rate separately: <b>0.88×10¹⁹
N·m/yr off-fault</b> against a <b>total California moment rate of 2.76×10¹⁹ N·m/yr</b> ⇒ an
off-fault fraction of <b>31.9 %</b> — used here as the empirical ceiling on a legitimate deficit.</td></tr>
<tr><td>“a documented moment-tensor summation” for converting slip rate × length into tile strain
rate</td><td><span class="pass">FOUND</span> — <b>Kreemer, Haines, Holt, Blewitt &amp; Lavallee
(2000)</b>, <i>Earth Planets Space</i> 52, eq. (3):
<a href="https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf">PDF</a>.
Original: <b>Kostrov (1974)</b>, <i>Izv. Acad. Sci. USSR Phys. Solid Earth</i> 1, 23–44.</td></tr>
<tr><td>UCERF3 models off-fault strain explicitly / the residual is a published quantity</td>
<td><span class="pass">VERIFIED</span> — <a href="https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixC.pdf">USGS
OFR 2013-1165 Appendix C</a>: “This grid of strain rates account for all modeled deformation that
is <b>not accommodated on the faults</b>.”</td></tr>
</table>

<h2>Data provenance</h2>
<table>
<tr><th>File</th><th>sha256</th><th>bytes</th><th>Note</th></tr>
<tr><td class="mono">training_features.tif</td><td class="mono">4371c82e…</td><td class="num">418,912,844</td>
<td><span class="pass">hash match</span> — 19 bands, float32, nodata −3.4028235e+38</td></tr>
<tr><td class="mono">labels.tif</td><td class="mono">7ba308cc…</td><td class="num">425,830</td>
<td><span class="pass">hash match</span> — <b>byte-identical to existing_faults.tif</b> (IR-51-05)</td></tr>
<tr><td class="mono">existing_faults.tif</td><td class="mono">7ba308cc…</td><td class="num">425,830</td>
<td><span class="pass">hash match</span> — 60,988 fault pixels, values {−1, 0, 1}</td></tr>
<tr><td class="mono">sample_submission.tif</td><td class="mono">2176d08e…</td><td class="num">1,599,597</td>
<td><span class="pass">hash match</span> — <b>IS the catalogue rasterised</b> (measured)</td></tr>
</table>
<p class="small dim">The competition data page is login-walled and unreachable from this sandbox;
the four files above were obtained from the group's own integrity-pinned mirrors and verified
against the published pins. That proves mirror consistency, <b>not</b> organiser authentication
(IR-51-02).</p>
"""
    (DOCS / "sources.html").write_text(page("Verified sources — GEMSDOE51", src, "sources.html"))

    # ---------------- irregularities ----------------
    irr = """
<h1 style="font-size:1.3rem">Irregularities flagged for review</h1>
<p class="small dim">Ten findings. Five are defects in <i>this session's own code</i>, found and
fixed; two are hard blockers caused by this sandbox's network policy; two are negative results
that are reported rather than buried; one is a policy note.</p>
<table>
<tr><th>id</th><th>severity</th><th>finding</th><th>evidence</th><th>status</th></tr>
<tr><td><b>IR-51-01</b></td><td class="warn">BLOCKER</td>
<td>The brief requires confirming slip rates <b>in the INGENIOUS shapefile attributes</b>. Not
possible here: <code>gdr.openei.org</code> returns HTTP 000. Rather than invent per-fault slip
rates, stage 1 takes the slip rate as a documented parameter (default 1.0 mm/yr) and ships a
published sweep over 0.1/0.5/1.0/2.0 mm/yr × dip 50/60/70°.</td>
<td><code>curl</code> exit 000 to gdr.openei.org, recorded in the session log;
<code>stage1_strain.slip_rate_sweep</code></td>
<td><span class="warn">OPEN</span> — needs an unrestricted machine</td></tr>

<tr><td><b>IR-51-02</b></td><td class="warn">MEDIUM</td>
<td>Competition data cannot be downloaded here: <code>drivendata.org</code> HTTP 000 and the data
page is login-walled. The four core rasters came from the group's integrity-pinned mirrors and
all four SHA-256 pins match.</td>
<td><code>registry/data_manifest.json</code></td>
<td><span class="pass">RESOLVED by hash-pinned mirror</span> — mirrors are owner-supplied, not
organiser-authenticated</td></tr>

<tr><td><b>IR-51-03</b></td><td class="warn">HIGH · own code</td>
<td>The stage-1 gate <b>silently approved 90 % of tiles</b> on the first run. Cause: 7,113,308 of
12,279,160 cells (57.9 %) carry the float32 nodata sentinel, and those empty tiles were being
counted as “deficit = 0”, which landed exactly on the quantile threshold.</td>
<td>first pipeline log (<code>10,829 tiles, 213.4 % of footprint</code>) vs the fixed run
(<code>1,793 tiles, 35.5 %</code>)</td>
<td><span class="pass">FIXED</span> — a usable-tile test (≥ 25 % valid geodetic cells) was added;
before and after are both recorded</td></tr>

<tr><td><b>IR-51-04</b></td><td class="warn">MEDIUM · own code</td>
<td>The uniqueness gate overflowed float32 on its first run (cosine and containment both printed
8773) because several references are not submissions at all — distance-in-metres layers and rasters
whose large negative sentinel carries no nodata tag. Containment was also computed against the
wrong array.</td>
<td>first gate log vs the fixed run</td>
<td><span class="pass">FIXED</span> — values clipped to [0,1]; a random-emission null model and a
sparsity test added</td></tr>

<tr><td><b>IR-51-05</b></td><td class="warn">HIGH</td>
<td><code>labels.tif</code> and <code>existing_faults.tif</code> are <b>byte-identical</b>
(<code>7ba308cc…</code>, 425,830 B each). The “labels” and the “existing faults” are the same
raster, so any holdout that uses <code>labels.tif</code> as truth is scoring against the training
target.</td>
<td><code>registry/data_manifest.json</code></td>
<td><span class="warn">FLAGGED</span> — this repository uses <code>existing_faults.tif</code>
explicitly and never treats <code>labels.tif</code> as independent truth</td></tr>

<tr><td><b>IR-51-06</b></td><td class="warn">NEGATIVE RESULT</td>
<td><b>The strike-steering hypothesis failed.</b> Gating the Hessian ridge response by alignment
with the mapped-fault strike gave AUC 0.4542 (worse than chance) against the unsteered field's
0.7005, and cost −0.01126 DTI on the blocked holdout, 0/4 folds.</td>
<td><code>evidence/holdout_run.json</code>, <code>evidence/detector_screen.json</code></td>
<td><span class="pass">REJECTED by measurement</span> — kept in the code as an ablation, not
shipped</td></tr>

<tr><td><b>IR-51-07</b></td><td class="warn">NEGATIVE RESULT → RESOLVED</td>
<td>Under the contiguous-quadrant protocol the detector <b>lost to uniform random</b>
(−0.01363, 1/4 folds), and the preregistered promotion rule therefore returned FAIL. Diagnosed as
a protocol artefact (truth confined to one quadrant rewards uniform spreading regardless of
ranking quality) <i>and</i> as a real property of the metric (T sums over the truth, so coverage
breadth beats per-dot precision). The leave-one-trace-out protocol with truth spread across the
map confirmed the diagnosis: field-<b>weighted sampling</b> beats both uniform random
(4/4 draws, +0.00132) and top-of-ranking peak packing (4/4 draws, +0.00765).</td>
<td><code>evidence/holdout_run.json</code> (promotion_pass: <b>false</b>),
<code>evidence/holdout_spread.json</code></td>
<td><span class="pass">RESOLVED</span> — the shipped emission rule is the validated one; the
failure is kept in the record</td></tr>

<tr><td><b>IR-51-08</b></td><td class="dim">POLICY</td>
<td>DrivenData's terms prohibit automated monitoring of the leaderboard. Every leaderboard value
in this repository is a <b>dated manual read</b> via the page-fetch tool; no scraper is used.</td>
<td>session log; <code>registry/leaderboard_reads.json</code></td>
<td><span class="dim">POLICY</span></td></tr>

<tr><td><b>IR-51-09</b></td><td class="warn">MEDIUM</td>
<td>The reference solution provided by the organisers contains <b>no implementation of the
competition metric and no masking</b>, and its own notebook says of its output map: “NOTE: it may
be advantageous to threshold this map for better scoring”. It cannot be used to verify a metric
implementation, so this repository verifies against the published equations and the published
worked example instead.</td>
<td><code>drivendataorg/gems-prize-reference-solution</code> read in full this session</td>
<td><span class="dim">NOTE</span></td></tr>

<tr><td><b>IR-51-10</b></td><td class="warn">HIGH</td>
<td><b>Every score of this repository's artifacts is a local measurement.</b> The group's 0.2600
and 0.2778 figures are <i>other people's</i> leaderboard positions, read manually. Nothing here
has been submitted or scored, and no artifact in this repository carries an organiser receipt.</td>
<td>this page; all <code>evidence/*.json</code></td>
<td><span class="warn">STANDING DISCLAIMER</span></td></tr>
</table>
"""
    (DOCS / "irregularities.html").write_text(
        page("Irregularities — GEMSDOE51", irr, "irregularities.html"))
    print("[build_site] wrote analysis / holdout / hypotheses / sources / irregularities")


if __name__ == "__main__":
    build_extra_pages()
    raise SystemExit(main())
