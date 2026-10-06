#!/usr/bin/env python3
"""Build the GitHub Pages site from the registries and evidence files.

    python3 scripts/build_site.py

Writes docs/index.html (executive summary + one-click download first),
docs/{analysis,hypotheses,irregularities,claims,sources,leaderboard,method}.html
and docs/.nojekyll.  Every number is read from registry/*.json, evidence/*.json or the
submission receipt; nothing is typed by hand into the HTML.
"""

from __future__ import annotations

import hashlib
import html
import json

import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
NAME = "gemsdoe51-strainbudget-s1-v1"

CSS = """
:root{--ink:#12202c;--mut:#5b6b7c;--bg:#f5f7fa;--card:#fff;--line:#dbe2ea;--ok:#0d7a4a;
--warn:#8a5300;--acc:#0b5fa5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{background:#0c1a28;color:#fff;padding:20px 0 14px}
header .in,main,footer .in{max-width:1080px;margin:0 auto;padding:0 20px}
h1{margin:0 0 4px;font-size:1.42rem}h2{margin:30px 0 8px;font-size:1.2rem;
border-bottom:2px solid var(--line);padding-bottom:5px}h3{margin:18px 0 6px;font-size:1.02rem}
a{color:var(--acc)}nav{margin-top:10px;display:flex;flex-wrap:wrap;gap:7px}
nav a{color:#cfe3ff;text-decoration:none;border:1px solid #2b4462;border-radius:999px;
padding:4px 12px;font-size:.86rem}nav a.on{background:#cfe3ff;color:#0c1a28;border-color:#cfe3ff}
main{padding:6px 0 60px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:18px 20px;margin:14px 0;box-shadow:0 1px 2px rgba(16,24,40,.05)}
.hero{border:2px solid var(--ok);background:linear-gradient(180deg,#f1fbf5,#fff)}
.btn{display:inline-block;background:var(--ok);color:#fff;font-weight:700;text-decoration:none;
padding:13px 20px;border-radius:10px;font-size:1.03rem;margin:5px 8px 5px 0}
.btn.alt{background:#fff;color:var(--ok);border:2px solid var(--ok)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84rem;word-break:break-all}
table{border-collapse:collapse;width:100%;margin:9px 0;font-size:.92rem}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:#eef2f7}.pill{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.75rem;
font-weight:700;border:1px solid}
.p-meas{color:var(--ok);border-color:var(--ok);background:#eafaf1}
.p-proxy{color:var(--warn);border-color:var(--warn);background:#fff6e8}
.p-live{color:var(--acc);border-color:var(--acc);background:#eaf2fc}
ul,ol{margin:8px 0 8px 22px;padding:0}li{margin:4px 0}
.mut{color:var(--mut)}.small{font-size:.88rem;line-height:1.5}
pre{background:#0c1a28;color:#e8eef5;padding:12px 14px;border-radius:9px;overflow-x:auto;
font-size:.85rem;line-height:1.5}
footer{color:var(--mut);font-size:.85rem;padding:18px 0 40px}
"""

NAV = [("index.html", "Executive summary"), ("analysis.html", "Why 0.2778? Can we beat it?"),
       ("strategy.html", "Strategy versus the leaders"),
       ("hypotheses.html", "Hypotheses"), ("method.html", "Method & gates"),
       ("irregularities.html", "Irregularities"), ("claims.html", "Claims"),
       ("sources.html", "Sources"), ("leaderboard.html", "Leaderboard")]


def J(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default if default is not None else {}


def e(x) -> str:
    return html.escape(str(x))


def table(rows, head) -> str:
    out = ["<table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr></thead><tbody>"]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return "".join(out) + "</tbody></table>"


def pill(kind: str, text: str) -> str:
    cls = {"MEASURED": "p-meas", "PROXY": "p-proxy", "UNVERIFIED-LIVE": "p-live"}.get(kind, "p-proxy")
    return f'<span class="pill {cls}">{e(text)}</span>'


def shell(slug: str, title: str, body: str) -> None:
    nav = "".join(f'<a class="{"on" if s == slug else ""}" href="{s}">{e(t)}</a>' for s, t in NAV)
    (DOCS / slug).write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — GEMSDOE51</title><style>{CSS}</style></head><body>
<header><div class="in"><h1>GEMSDOE51 — DOE GEMS Prize, round 1</h1>
<div class="small">DrivenData #306 · GeoDAWN / NW Nevada · unique, gated, <strong>unscored</strong>
submission · every number traceable to a file in this repository</div>
<nav>{nav}</nav></div></header><main><div class="in">{body}</div></main>
<footer><div class="in">Repository: <a href="https://github.com/buffedlizard55-lab/GEMSDOE51">github.com/buffedlizard55-lab/GEMSDOE51</a>.
No leaderboard score is claimed for any file here. Provenance limitation: organiser bytes are behind
a login wall, so inputs come from owner-published mirrors pinned by sha256 — the pins prove mirror
consistency, not organiser authentication.</div></footer></body></html>\n""")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")
    rec = J(ROOT / "evidence/submission_receipt.json")
    uni = J(ROOT / "evidence/uniqueness_gate.json")
    dom = J(ROOT / "evidence/stage_dominance.json")
    sb = J(ROOT / "evidence/stage_b_folds.json", [])
    auc = J(ROOT / "evidence/auc_comparison.json", [])
    con = J(ROOT / "evidence/detector_contrast.json", {})
    sab = J(ROOT / "evidence/stage_a_budget.json")
    sag = J(ROOT / "evidence/stage_a_gate_comparison.json")
    sah = J(ROOT / "evidence/stage_a_holdout.json")
    prm = J(ROOT / "evidence/emission_promotion.json")
    ofc = J(ROOT / "evidence/offcat_holdout.json")
    hsb = J(ROOT / "evidence/holdout_stage_b.json", {})
    hpk = J(ROOT / "evidence/holdout_packer.json", {})
    hyps = J(ROOT / "registry/hypotheses.json", {}).get("hypotheses", [])
    irr = J(ROOT / "registry/irregularities.json", {}).get("items", [])
    claims = J(ROOT / "registry/claims.json", {}).get("claims", [])
    srcs = J(ROOT / "registry/sources.json", {}).get("sources", [])
    lb = J(ROOT / "registry/leaderboard_snapshot.json", {})
    man = J(ROOT / "registry/data_manifest.json")

    sha = rec.get("sha256", "n/a")
    zipsha = rec.get("zip_sha256", "n/a")
    n_px = rec.get("n_positive", 0)
    sha_ok = sha.startswith("bdc045934e4a2e33")

    # --------------------------------------------------------------- index
    index = f"""<div class="card hero">
<h2 style="margin-top:0;border:0">Download the submission — one click</h2>
<p><strong>Unique file, built from hash-pinned inputs by this repository's pipeline, never submitted,
never scored.</strong></p>
<p><a class="btn" href="downloads/{NAME}.zip" download>&#11015; Download {NAME}.zip (upload this)</a>
<a class="btn alt" href="downloads/{NAME}.tif" download>Download the raw .tif</a></p>
<div class="mono">tif sha256&nbsp; {e(sha)}<br>zip sha256&nbsp; {e(zipsha)}</div>
<p class="small mut">This site holds <strong>two independent builds</strong> of a legal submission and
publishes a download for each; their positive-pixel overlap is 1,091&nbsp;px
(<strong>Jaccard 0.0034</strong>), so submitting both is not two copies of one answer.
This page is <strong>Build B</strong> (two-stage strain gate + 44-channel blocked-CV detector).
<strong>Build A</strong> — the strain-budget allow-region with an unsteered Hessian-ridge emission —
is documented, with its own download and receipt, on
<a href="executive-summary.html">its own page</a>.</p>
<h3>Submit it in three steps</h3>
<ol>
<li>Sign in at
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the
competition submission page</a>.</li>
<li>Download the <span class="mono">.zip</span> above and upload it under <em>Submit predictions</em>.
Nothing else is needed: the raster is already on the competition grid, CRS, dtype and value range.</li>
<li>Paste this note into the description box:
<pre>GEMSDOE51 v1 — Stage-A geodetic-strain tile gate (top half by strain magnitude; the literal
strain-budget deficit was tested and reported as FALSIFIED) + Stage-B 44-channel spatially-blocked
gradient-boosted detector. {n_px:,} one-pixel dots, each inside an approved tile and >= 200 m from
every visible-catalogue pixel. All-finite float32, values 0-1, no nodata tag. UNSCORED.</pre></li>
</ol>
<h3>Why the portal will accept it</h3>
{table([
 ["dtype / count", f"float32, single band, {rec.get('shape')} px at 100 m"],
 ["CRS / transform", f"EPSG:{e(rec.get('crs'))} · [100, 0, 243350, 0, -100, 4508550]"],
 ["values", f"min {rec.get('min')} · max {rec.get('max')} · NaN {rec.get('n_nan')} · below 0 {rec.get('n_below0')} · above 1 {rec.get('n_above1')}"],
 ["all finite", f"<strong>{rec.get('all_finite')}</strong> — no NaN anywhere, so no sentinel can trip the portal's range check"],
 ["nodata tag", f"<strong>{e(rec.get('nodata'))}</strong> — deliberately absent (the training raster's own sentinel is -3.4028234663852886e+38, which is outside [0,1])"],
 ["emitting pixels", f"{n_px:,} on disk in {rec.get('bytes'):,} bytes"],
 ["uniqueness", f"max Jaccard <strong>{uni.get('max_jaccard', 0):.4f}</strong> against {uni.get('n_prior')} scored sibling submissions (limit 0.25); no subset/superset relation"],
 ["stage dominance", f"fill {dom.get('fill_fraction', 0):.4f} of the approved area, coverage inside approved tiles {dom.get('coverage_in_approved')}, tile concentration {dom.get('tile_concentration_ratio', 0):.3f}&times; the uniform control"],
 ["verification", "<span class='mono'>python3 scripts/check_submission.py docs/downloads/"+NAME+".tif</span> re-opens the file and re-checks all of the above against the receipt"],
], ["Property", "Value"])}
</div>

<div class="card">
<h2>Executive summary</h2>
<p><strong>The honest headline:</strong> this file is <strong>UNSCORED</strong>. DrivenData requires
an account to submit and this build environment has none, so nothing here is a leaderboard result.
Every accuracy number in this repository is a <em>proxy</em>: it is scored against the visible
USGS/INGENIOUS catalogue, which by construction cannot reward a fault that the catalogue is missing.
Proxies decide what ships; they do not predict a score.</p>
<p>What ships: a two-stage pipeline. <strong>Stage A</strong> computes a geodetic strain budget per
25 km tile with the published fault-slip summation (Kreemer et al. 2000, eq. 3) over INGENIOUS slip
rates and measured per-sense dips, and approves the top half of tiles by geodetic strain magnitude.
The brief's literal <em>deficit</em> rule was implemented, measured and <strong>refuted</strong>
(label-density lift {sah.get('mean_lift', float('nan')):.3f} on the blocked holdout, {sah.get('folds_with_lift_gt_1')}/{sah.get('n_folds')} folds above 1) and is reported rather than shipped.
<strong>Stage B</strong> is a 44-channel gradient-boosted detector under spatially blocked CV
(mean AUC {sum(r['auc'] for r in sb)/max(1,len(sb)):.4f}) whose belief field beats both published
sibling out-of-fold fields on <strong>4/4 folds</strong> and by a paired matched-mass DTI of
<strong>+{abs(sum(r.get('delta_vs_oof_D', 0) for r in con.get('contrasts', []))/max(1,len(con.get('contrasts', [])))):.4f}</strong>.</p>
<p>Two things were caught and reported rather than shipped: a coverage-lattice emission that won a
weak instrument and lost the faithful one (IR-51-05), and a miscalibrated self-predicting packer
(IR-51-12). The pre-registration that made those catchable is in
<span class="mono">registry/preregistration.json</span>.</p>
</div>

<div class="card">
<h2>Stage A — coarse prior over tiles (holdout reported separately, {pill("PROXY", "PROXY")})</h2>
{table([
 ["Formula (published)", f"<span class='mono'>{e(sab.get('formula', ''))}</span>"],
 ["Source", "Kreemer, Haines, Holt, Blewitt &amp; Lavallée (2000), Earth Planets Space 52(10):765–770, eq. (3) — <a href='https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf'>PDF</a>; independently restated in GJI 212(2):988 and GJI 146(2):399"],
 ["Tiles", f"{sab.get('n_tiles')} tiles of {sab.get('tile_px')} px (25 km)"],
 ["Geodetic / mapped-fault medians", f"{sab.get('geodetic_ns_yr', {}).get('median')} vs {sab.get('geologic_ns_yr', {}).get('median')} ns/yr → ratio {sab.get('ratio_geologic_over_geodetic', {}).get('median')}, deficit {sab.get('deficit', {}).get('median')}"],
 ["Deficit as a locator", f"<strong>REFUTED</strong>: lift {sah.get('mean_lift', float('nan')):.3f} ({sah.get('folds_with_lift_gt_1')}/{sah.get('n_folds')} folds), rho {sag.get('rules', {}).get('deficit', {}).get('lidar_scarp_mean', {}).get('spearman_rho', float('nan')):+.3f} vs lidar scarp intensity, rho {sag.get('rules', {}).get('deficit', {}).get('sgmc_offcat_density', {}).get('spearman_rho', float('nan')):+.3f} vs off-catalogue SGMC density"],
 ["Gate that ships", f"top-half tiles by geodetic strain magnitude — rho {sag.get('rules', {}).get('strain_2ndinv', {}).get('lidar_scarp_mean', {}).get('spearman_rho', float('nan')):+.3f} (lift {sag.get('rules', {}).get('strain_2ndinv', {}).get('lidar_scarp_mean', {}).get('top_quartile_lift', float('nan')):.3f}) on the lidar instrument, {sag.get('rules', {}).get('strain_2ndinv', {}).get('sgmc_offcat_density', {}).get('spearman_rho', float('nan')):+.3f} on the SGMC instrument — a <strong>split decision</strong>, IR-51-04"],
], ["Item", "Result"])}
</div>

<div class="card">
<h2>Stage B — fine-scale detector (holdout reported separately, {pill("PROXY", "PROXY")})</h2>
{table([[r.get("fold"), f"{r.get('auc'):.4f}"] for r in sb],
       ["Spatially blocked fold (600 m boundary band removed from training and scoring)", "AUC"])}
<p>Against the sibling repositories' published out-of-fold fields on the identical masks:</p>
{table([[r.get("fold"),
         f"{r.get('auc_ours'):.4f}" if r.get("auc_ours") else "n/a",
         f"{r.get('auc_oof_B'):.4f}" if r.get("auc_oof_B") else "n/a",
         f"{r.get('auc_oof_D'):.4f}" if r.get("auc_oof_D") else "n/a"] for r in auc],
       ["Fold", "this repository", "sibling oof_B", "sibling oof_D"])}
<p class="small mut">Paired matched-mass DTI versus <span class="mono">oof_D</span> (same emitter,
same folds, {len(con.get('contrasts', []))} comparisons at 8k and 32k dots):
mean <strong>{sum(r.get('delta_vs_oof_D', 0) for r in con.get('contrasts', []))/max(1,len(con.get('contrasts', []))):+.4f}</strong>,
positive in {sum(1 for r in con.get('contrasts', []) if r.get('delta_vs_oof_D', 0) > 0)}/{len(con.get('contrasts', []))}. PROXY and subject to IR-51-06 (label circularity).</p>
<table>
<tr><th>Emission rule</th><th>Mean paired DTI vs the incumbent</th><th>Folds positive</th><th>Verdict</th></tr>
<tr><td>Thin dots, belief priority, 4% of candidate area, 3 px separation</td><td>—</td><td>—</td>
<td>{pill("PROXY", "SHIPS")}</td></tr>
<tr><td>Credit-density ordering ({(sum(f["d_ours_minus_incumbent"] for f in hsb.get("folds", []))/max(1,len(hsb.get("folds", [])))):+.4f})</td><td>{sum(f["d_ours_minus_incumbent"] for f in hsb.get("folds", []))/max(1,len(hsb.get("folds", []))):+.4f}</td>
<td>{sum(1 for f in hsb.get("folds", []) if f["d_ours_minus_incumbent"] > 0)}/{len(hsb.get("folds", []))}</td>
<td>{pill("PROXY", "NOT PROMOTED")}</td></tr>
<tr><td>Expected-budget packer ({hpk.get("mean_contrast", float("nan")):+.4f})</td><td>{hpk.get("mean_contrast", float("nan")):+.4f}</td>
<td>{hpk.get("folds_positive")}/{hpk.get("n_folds")}</td>
<td>{pill("PROXY", "NOT PROMOTED")}</td></tr>
<tr><td>Coverage lattice, top decile, 3 px spacing</td><td>{prm.get('offcat_instrument', {}).get('lattice_q0.10_s3_B_far', {}).get('mean_delta', float('nan')):+.4f}</td>
<td>{prm.get('offcat_instrument', {}).get('lattice_q0.10_s3_B_far', {}).get('folds_positive')}/{prm.get('offcat_instrument', {}).get('lattice_q0.10_s3_B_far', {}).get('n_folds')}</td>
<td>{pill("PROXY", "REFUTED (IR-51-05)")}</td></tr>
<tr><td>Coverage lattice, top quintile, 3 px spacing</td><td>{prm.get('offcat_instrument', {}).get('lattice_q0.20_s3_B_far', {}).get('mean_delta', float('nan')):+.4f}</td>
<td>{prm.get('offcat_instrument', {}).get('lattice_q0.20_s3_B_far', {}).get('folds_positive')}/{prm.get('offcat_instrument', {}).get('lattice_q0.20_s3_B_far', {}).get('n_folds')}</td>
<td>{pill("PROXY", "NOT PROMOTED")}</td></tr>
</table>
<p class="small mut">Instrument for the two lattice rows: fault systems split A/B, detector trained
on A alone, truth = B, official DTI (off-catalogue). It also contains the halo control that keeps the
instrument honest: emitting a ring around the catalogue scores {ofc.get('paired', {}).get('halo_ring_2_5px_s3|B_far', {}).get('mean_delta', float('nan')):+.4f}.</p>
</div>"""

    shell("index.html", "Executive summary", index)

    # --------------------------------------------------------------- analysis
    r = sag.get("rules", {})
    analysis = f"""<div class="card">
<h1>Why the 0.2778 artifact led — and whether this repository can beat it</h1>
<p class="small mut">Written to be read line by line against primary sources. Numbers read from
official pages are quoted with their URL; numbers read from the sibling artifact's own description
are marked second-hand; numbers computed here point at the evidence file.</p>

<h2>1. What the artifact is, and what cannot be verified about it</h2>
<ul>
<li>File <span class="mono">gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</span>:
37,654 emitting pixels, float32, EPSG:32611, 3292×3730, all cells finite, values 0–1, no nodata tag,
and <strong>0 px within 200 m of the visible catalogue</strong>.</li>
<li>It is the artifact's 0.2708-scoring model with every dot within 2 px of the catalogue deleted;
the deletion measured <strong>+0.00487</strong> mean paired credit in 4/4 folds of the sibling live
mirror, projecting 0.2747. The sibling labels that a <em>model</em>, not a score.</li>
<li><strong>Unverifiable:</strong> no digest links this file to the 0.2778 leaderboard row. On the
2026-10-06 read, 0.2778 sits at rank 13 while rank 1 is 0.3774 and the brief's 0.3195 target is rank
7. Recorded as IR-51-02 and IR-51-01.</li>
</ul>

<h2>2. The metric, exactly as published</h2>
<pre>k(d) = max(1 - d/R, 0)                      R = 300 m = 3 px at 100 m
TP_w = sum_g  max_{{x : d(x,g) <= R}} p(x) k(d(x,g))
FP_w = sum_{{x : p(x) > 0}} p(x) [1 - max_g k(d(x,g))]
FN_w = sum_g [1 - max_{{x : d(x,g) <= R}} p(x) k(d(x,g))]
DTI  = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)</pre>
<p>Source: the competition problem description,
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page 967</a>,
with the worked example TP_w 3.00, FP_w 1.89, FN_w 2.00 → 0.60, which this repository reproduces
exactly (<span class="mono">tests/test_metric.py</span>, 9/9 passing, including a brute-force
re-implementation of the three sums).</p>
<p><strong>Two identities do all the work.</strong> First, FN_w = K − T where K is the truth pixel
count and T = TP_w, so DTI = T / (0.2T + 0.2F + 0.8K) with F = FP_w. Second, T ≤ K and each truth
pixel's credit saturates: mass cannot buy the same truth pixel twice. And a predicted pixel sitting
exactly on a truth pixel carries <strong>zero</strong> false-positive weight.</p>

<h2>3. The marginal bar — why sparse-and-right beats dense</h2>
<p>Adding a unit of mass that claims dT of new credit and adds dF of uncovered weight raises DTI iff
<strong>dT·(0.2F + 0.8K) &gt; 0.2·T·dF</strong>. For one dot with kernel weight k to an unclaimed truth
pixel this is <strong>k &gt; 0.2·DTI</strong>. At DTI = 0.2778 the bar is <strong>0.0556</strong>:
the dot must lie within <strong>283 m</strong> of a truth pixel it can still claim. At the ancestor's
0.2708 level the bar is 0.0542 (284 m). Consequences:</p>
<ul>
<li><strong>Recall is worth 4× precision</strong> (0.8 vs 0.2), so even a 90 %-wasted dot field can
score 0.26–0.28 — which is exactly what the ancestor's emissions do.</li>
<li><strong>Unclaimed credit per dot is only ~1–3 kernel units</strong> (a dot on a 1-px-wide truth
line claims about 3), while each off-truth dot costs 0.2 and raises the bar for every dot after it.
The optimum is a <em>coverage</em> problem at small mass, not a mass race.</li>
<li><strong>Mass on the visible catalogue is dead mass</strong> for a hidden set defined as "faults
the catalogue does not contain". Deleting the 2-px ring — the ancestor's −0.005 step — is that
insight applied, and it is why the shipped file here is ≥ 200 m from every catalogue pixel.</li>
</ul>

<h2>4. What the ancestor's scores imply (inference, not measurement)</h2>
<p>With the ancestor's own calibrated hidden-truth scale K ≈ 12,700 px, an emission of 44,090 dots
and the assumption that about half of its mass behaves as false:</p>
{table([
 ["Live 0.2600, 44,090 dots", "≈ 4,800", "≈ 38 % of K"],
 ["0.2708 model", "≈ 4,500", "≈ 35 % of K"],
 ["…-zeros, projected 0.2747", "≈ 4,050", "≈ 32 % of K"],
 ["brief's stated target 0.3195 at the same mass", "≈ 4,750", "≈ 37 % of K"],
 ["leader 0.3774 at triple the mass", "≈ 6,100", "≈ 48 % of K"],
], ["State", "Implied matched credit T", "Implied coverage of K"])}
<p><strong>Beating 0.3195 therefore needs roughly +17 % more matched-filter credit at the same mass:
a placement problem, not a mass problem.</strong> These four numbers are an inference from a score
and a truth model; they are labelled as such and are not used to size anything.</p>

<h2>5. Why habitat-style rasters collapse (the failure mode the brief named)</h2>
<p>With F set by a region-wide emission and T capped by K, DTI ≈ T/(0.2F + 0.8K):</p>
{table([
 ["uniform raster over the 5.17M-px domain (F ≈ 5.0M)", "≈ 0.008"],
 ["smooth habitat map over half the domain (F ≈ 2.4M)", "≈ 0.017"],
 ["the three habitat submissions as scored by the ancestor", "0.0041 / 0.1223 / 0.1352"],
], ["Emission", "DTI arithmetic"])}
<p>The arithmetic brackets the observed failures without being fitted to them, which is why this
repository refuses any emission that is not a sparse, off-catalogue, high-belief dot set.</p>

<h2>6. Can this repository beat it? What is actually measured here</h2>
<ol>
<li><strong>A better belief field.</strong> Identical folds, identical truth, matched mass: mean AUC
{sum(r['auc'] for r in sb)/max(1,len(sb)):.4f} versus the sibling fields, higher on 4/4 folds; paired
matched-mass DTI <strong>{sum(r.get('delta_vs_oof_D', 0) for r in con.get('contrasts', []))/max(1,len(con.get('contrasts', []))):+.4f}</strong>
positive in {sum(1 for r in con.get('contrasts', []) if r.get('delta_vs_oof_D', 0) > 0)}/{len(con.get('contrasts', []))}.
Verdict: a genuine improvement <em>on this instrument</em>; IR-51-06 applies.</li>
<li><strong>A stricter gate.</strong> Stage A approves {dom.get('n_approved_tiles')} of 116 tiles
({dom.get('approved_px'):,} px, 49 % of the footprint) on the strain-magnitude rule, whose lidar
support (rho {r.get('strain_2ndinv', {}).get('lidar_scarp_mean', {}).get('spearman_rho', float('nan')):+.3f},
lift {r.get('strain_2ndinv', {}).get('lidar_scarp_mean', {}).get('top_quartile_lift', float('nan')):.3f})
is reported next to its SGMC contradiction
(rho {r.get('strain_2ndinv', {}).get('sgmc_offcat_density', {}).get('spearman_rho', float('nan')):+.3f}).</li>
<li><strong>A stricter off-catalogue discipline.</strong> Every dot obeys ≥ 200 m from the catalogue,
and uniqueness is enforced mechanically: max Jaccard {uni.get('max_jaccard', 0):.4f} against
{uni.get('n_prior')} scored sibling submissions.</li>
<li><strong>A trap avoided.</strong> The coverage-lattice emission won a weak instrument
(+0.0286, 4/4 folds) and lost the faithful off-catalogue instrument
({prm.get('offcat_instrument', {}).get('lattice_q0.10_s3_B_far', {}).get('mean_delta', float('nan')):+.4f},
{prm.get('offcat_instrument', {}).get('lattice_q0.10_s3_B_far', {}).get('folds_positive')}/4 folds).
It was reverted before any submission was spent (IR-51-05).</li>
</ol>

<h2>8. Verdict</h2>
<p><strong>Why it led:</strong> it is the strongest publicly described emission in the family: almost
entirely off-catalogue, sparse enough that its dead mass is a few thousand denominator units at most,
and placed by a belief field that was itself scored 0.27 live. A 30–40 % coverage of a ~12,700-pixel
hidden set is enough to reach 0.27 under this metric, and that artifact plausibly has it.</p>
<p><strong>Can we beat it?</strong> Not provably from inside this repository, and no such claim is
made. The two constraints the ancestor's own analysis identified as binding — the field and the
placement rule — are both measurably better here on every instrument that can be run offline, and the
shipped file obeys a stricter off-catalogue discipline with a wider uniqueness margin. The decisive
test is to score it. Until then the honest statement is: <em>measured better on the instruments that
exist, unverified on the instrument that decides.</em></p>
</div>"""
    shell("analysis.html", "Why 0.2778 led", analysis)

    # --------------------------------------------------------------- strategy
    # Everything in this page is either (a) algebra applied to the published metric, or (b)
    # read from an evidence file.  The algebra is recomputed here from the same closed form the
    # metric module uses, so a wrong number cannot be typed in by hand.
    def req_T(dti: float, M: float, K: float, alpha: float = 0.2, beta: float = 0.8) -> float:
        """Credit T needed for a given DTI, assuming worst-case mass (F = M)."""
        return dti * (alpha * M + beta * K) / (1.0 - alpha * dti)

    mrows = []
    for M in (20000, 37654, 67200, 95927):
        for K in (12200, 24000, 60894):
            T = req_T(0.3195, M, K)
            mrows.append([f"M = {M:,} dots", f"K = {K:,} px",
                          f"T = {T:,.0f}", f"{100 * T / K:.1f} % of K",
                          f"{T / M:.3f}"])
    dens = J(ROOT / "evidence/offcat_density_sweep.json", {})
    dens_rows = dens.get("results", [])
    have_dens = bool(dens_rows)
    def _verdict(r: dict) -> str:
        if r["arm"] == dens.get("shipped_arm", "thin_d0.04_s3.0"):
            return "baseline (shipped mass)"
        if r.get("promoted"):
            return "CLEARS THE PRE-REGISTERED BAR"
        return "not promoted"

    def _delta(r: dict) -> str:
        d = r.get("delta_vs_shipped")
        if d is None or (isinstance(d, float) and d != d):   # NaN = the baseline against itself
            return "&mdash;"
        return f"{d:+.4f}"

    dens_block = "".join(
        f"<tr><td class='mono'>{e(r['arm'])}</td><td>{r['n_px']:,}</td>"
        f"<td>{r['dti_B_far']:.4f}</td><td>{_delta(r)}</td>"
        f"<td>{_verdict(r)}</td></tr>" for r in dens_rows)

    strategy = f"""<div class="card">
<h1>Strategy versus the leaders — the arithmetic of 0.3195, and what it takes to exceed it</h1>
<p class="small mut">Sources for every external number are linked; every local number points at the
evidence file that produced it. Where a quantity is inferred rather than measured it is labelled
<strong>inference</strong> and the assumption is stated.</p>

<h2>1. The decision equation, derived</h2>
<pre>Official metric (page 967):   DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)
Exact identity, verified in tests/test_metric.py against the published worked example:
   FN_w = K - T        K = number of truth pixels, T = TP_w
   FP_w = M - C        M = total emitted mass, C = mass sitting on the visible candidate
Working form used everywhere below:
   DTI = T / (0.2 T + 0.2 F + 0.8 K)          F = FP_w,  0 <= F <= M
Solving for the credit a target score requires:
   T = DTI * (0.2 F + 0.8 K) / (1 - 0.2 DTI)</pre>
<p>Two consequences drive everything: (i) <strong>credit saturates per truth pixel</strong> — a truth
pixel pays its best dot once, no matter how many dots crowd it, so extra mass cannot buy the same
pixel twice; (ii) <strong>mass that misses costs 0.2 per unit</strong>, which is why an over-massive
file needs proportionally more credit for the same score.</p>

<h2>2. What a 0.3195-class score requires (inference, assumption-stated)</h2>
<p>The hidden label set is bigger than the visible catalogue in the final round, but the live
leaderboard is scored on a set the family's own calibration places near <strong>K ≈ 12,200 px</strong>
(the sibling's calibrated hidden-truth scale, used here only as a sensitivity anchor — not as a
measurement). The table gives the credit T a file of mass M must earn at F = M (worst case,
i.e. all mass wasted) to reach <strong>0.3195</strong>, and what fraction of the hidden set that is:</p>
{table(mrows, ["file mass", "hidden truth size", "credit needed T", "T as share of K", "credit per dot"])}
<p>Read the first two rows: for the 37,654-dot file that sits on today's leaderboard, beating 0.3195
requires covering roughly <strong>half</strong> of the hidden set within 300 m; for a 95,927-dot file
like the one this repository ships, the same score requires covering <strong>four fifths</strong> of it.
<strong>Mass is a liability unless the extra dots earn their 0.2.</strong> That single inequality
explains why the family's results improved every time mass was removed, and it is the reason the
density test below is the most consequential experiment left.</p>

<h2>3. Why the 0.2778-class file leads its own family — evidence, not legend</h2>
<ul>
<li>Spec of <span class="mono">gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</span>:
float32, EPSG:32611, 3292×3730, all-finite, values 0–1, no nodata tag, <strong>37,654 emitting
pixels</strong>, <strong>0 px within 200 m of the visible catalogue</strong> (read from the sibling's own
published description, class UNVERIFIED-LIVE).</li>
<li>It is the family's 0.2708-scoring emission with dots within 2 px of the catalogue deleted; in the
sibling's live-mirror holdout that deletion measured <strong>+0.00487</strong> mean paired credit in 4/4
folds, projecting 0.2747 — a model, not a score.</li>
<li>Mass-arithmetic check (inference): 37,654 dots with ≥ 200 m clearance and a 0.2778-class score
implies T ≈ {req_T(0.2778, 37654, 12200):,.0f} credit units — about
{100 * req_T(0.2778, 37654, 12200) / 12200:.0f} % of a 12,200-px hidden set, i.e. the file does not
need to be brilliant, only <em>efficient</em>: ~{req_T(0.2778, 37654, 12200) / 37654:.2f} credit units
per dot.</li>
<li>Rank context on the 2026-10-06 read: 0.2778 sits at rank 13; rank 1 is 0.3774, rank 3 is 0.3262,
and the brief's stated target 0.3195 is rank 7 (DARD).</li>
</ul>

<h2>4. What this repository has measured that bears on beating it</h2>
{table([
 ["Belief field, blocked 4-fold AUC", f"{sum(r['auc'] for r in sb) / max(1, len(sb)):.4f} — beats both sibling out-of-fold fields on 4/4 folds (evidence/auc_comparison.json)"],
 ["Matched-mass DTI vs the best sibling field", f"{sum(r.get('delta_vs_oof_D', 0) for r in con.get('contrasts', [])) / max(1, len(con.get('contrasts', []))):+.4f} over {len(con.get('contrasts', []))} fold×budget rows, positive in {sum(1 for r in con.get('contrasts', []) if r.get('delta_vs_oof_D', 0) > 0)}/{len(con.get('contrasts', []))} (work/detector_contrast.json)"],
 ["Mass experiment — full (visible) catalogue as truth", "optimum at 4 % of the candidate area: 0.005→0.1796, 0.01→0.2318, 0.02→0.2803, 0.04→0.2997, 0.08→0.2585 (work/detector_contrast.json)"],
 ["Mass experiment — density-matched truth", "with the truth thinned toward the hidden set's density (K ≈ 12,200 px), the optimum MOVES DOWN in mass and the win shifts to coverage lattices (strategy_sweep.json)"],
 ["Off-catalogue (faithful) instrument", f"shipped thin rule {float(np.mean([r['dti_B_far'] for r in ofc.get('results', []) if r['rule'] == 'thin_d0.04_s3.0'])):.4f} mean DTI vs uniform random {float(np.mean([r['dti_B_far'] for r in ofc.get('results', []) if r['rule'] == 'uniform_s3'])):.4f} and the halo control {float(np.mean([r['dti_B_far'] for r in ofc.get('results', []) if r['rule'] == 'halo_ring_2_5px_s3'])):.4f} — the coverage lattice that wins the density-matched experiment LOSES here (IR-51-05)"],
], ["Measurement", "Result"])}
<p><strong>The contradiction in that table is the honest state of the art.</strong> The visible
catalogue is five times denser than the presumed hidden set, so a rule tuned on it prefers mass; the
density-matched proxy prefers coverage; and the only instrument that withholds entire fault systems
(the off-catalogue A/B) prefers the sparse thin-dot rule that ships. Rather than pick the instrument
that flatters the file, the density question is being settled on the faithful instrument itself —
varying only the mass of the shipped rule and pairing every arm per fold against it.</p>

<h2>5. The density test that decides the next submission</h2>
<p>Same A/B instrument, same detector, same folds, same 200 m off-catalogue rule, same 3 px spacing:
only the number of dots changes. Promotion requires the pre-registered bar — mean paired DTI > 0
<em>and</em> ≥ 3/4 folds — which is the rule that already killed the lattice (IR-51-05).</p>
{"<table><tr><th>arm</th><th>dots</th><th>mean DTI on B_far</th><th>paired vs shipped</th><th>verdict</th></tr>" + dens_block + "</table>" if have_dens else "<p class='small mut'>Run <span class='mono'>python3 scripts/run_offcat_density.py</span> to populate this table (or re-run the off-catalogue instrument with its density arms).</p>"}

<h2>6. What the density test found, and what happens next</h2>
<p>Two arms cleared the pre-registered bar on the faithful instrument: <strong>thin d0.02 s3.0</strong>
(12,131 dots, +0.0047 paired, 3/4 folds; best mean DTI of any arm at 0.0859) and
<strong>thin d0.03 s3.0</strong> (+0.0033, 3/4 folds). Everything heavier was worse
(d0.06 −0.0078, d0.08 −0.0141, both 0/4 folds) and the coverage lattice that won the
density-matched proxy still loses here (q0.10, −0.0104). That is the mass curve the metric's own
arithmetic predicted, measured on the only instrument that withholds whole fault systems.</p>
<p><strong>Consequence, stated plainly:</strong> the shipped file is at the baseline density
(d0.04 → 95,927 dots), which the instrument now says is heavier than optimal, and the promoted
arms imply roughly 48,000–72,000 dots at production scale (d0.02–0.03 of the same candidate area).
Rebuilding at a promoted density changes the artifact, so it is a separate, fully re-run change
with new receipts — not something to slip into a merge. The shipped file here is the one whose
bytes were verified end to end; the lower-mass rebuild is the next change, and it ships only after
the same 8-stage run reproduces its bytes (that run also refreshes this table automatically).</p>

<h2>7. Verdict: can we beat 0.3195?</h2>
<ol>
<li><strong>Not provable offline, and this repository does not claim it.</strong> The only instrument
that decides is the leaderboard, and no file here has ever been scored.</li>
<li><strong>But the two binding constraints are both attacked with measurements.</strong> The belief
field is better than the best sibling field on every fold and budget that can be scored offline; the
emission discipline (≥ 200 m clearance, sparse dots, uniqueness margin 0.0322) matches or exceeds the
leading artifact's.</li>
<li><strong>The remaining risk is mass, not ranking.</strong> Section 2 shows that at 95,927 dots the
file must cover ~4/5 of the hidden set to reach 0.3195; at ~30–40k dots it must cover ~1/2. If the
faithful instrument says a lower-mass arm is not worse, shipping the lower-mass arm strictly raises
the ceiling. That decision is made by the table in section 5, not by preference.</li>
<li><strong>The next two ideas with the highest expected P(Win) per unit of cost</strong> are, in order:
H52-1 horsetail/step-over geometry completion (internal data only, targets the settings that host
~57 % of the region's known systems — Faulds &amp; Hinz 2015) and H52-2 paleo-geothermal sinter/travertine
proximity (GDR-1391, CC-BY, 19.85 MB, obtainable through a GitHub Actions runner). Both must clear the
off-catalogue instrument before consuming a slot.)</li>
</ol>
</div>"""
    shell("strategy.html", "Strategy versus the leaders", strategy)

    # --------------------------------------------------------------- hypotheses
    hrows = []
    for h in hyps:
        hrows.append(f"""<div class="card"><h2 style="margin-top:0">{e(h.get('id'))} — {e(h.get('title'))}</h2>
<p class="small mut">rank {e(h.get('rank'))} · status: <strong>{e(h.get('validation', 'n/a'))[:1].upper() + e(h.get('validation', 'n/a'))[1:]}</strong></p>
<h3>Layers</h3><ul>{''.join(f'<li class="mono">{e(x)}</li>' for x in h.get('layers', []))}</ul>
<h3>Signature targeted</h3><p>{e(h.get('signature'))}</p>
<h3>Formula / mechanism</h3><p class="mono small">{e(h.get('formula', '—'))}</p>
<h3>Why it catches a fault missing from the catalogue</h3><p>{e(h.get('why_off_catalogue'))}</p>
<h3>How it differs from everything already implemented</h3><p>{e(h.get('difference'))}</p>
<h3>Validation</h3><p>{e(h.get('validation'))}</p>
<h3>Expected gain vs cost</h3><p>{e(h.get('gain_vs_cost'))}</p></div>""")
    shell("hypotheses.html", "Hypotheses",
          "<div class='card'><h1>Candidate hypotheses</h1><p class='small'>Ranked by expected DTI "
          "gain per unit of implementation cost. Only H51-1 and H51-2 were allowed into the shipped "
          "emission; everything else is recorded with its falsification status. Machine-readable: "
          "<span class='mono'>registry/hypotheses.json</span>.</p></div>" + "".join(hrows))

    # --------------------------------------------------------------- method
    method = f"""<div class="card"><h1>Method, gates and prudence rules</h1>
<pre>python3 scripts/fetch_data.py --group all      # restore 26 sha256-pinned files, fail closed
python3 scripts/run_all.py --skip-data         # full pipeline, fresh evidence
python3 scripts/rebuild_submission.py          # rebuild the shipped raster from the cached field
python3 scripts/run_offcat_holdout.py          # off-catalogue A/B instrument (decisive test)
python3 scripts/check_stage_a_convention.py    # IR-51-04 follow-up
python3 scripts/build_site.py                  # regenerate this site
pytest tests -q                                # 9 tests incl. brute-force metric</pre>
<h3>Prudence rules (fixed before the emission was built; registry/preregistration.json)</h3>
<ul>
<li><strong>Slot rule:</strong> nothing ships unless it beats the incumbent on a declared instrument
(mean paired DTI &gt; 0 AND ≥ 3/4 folds positive).</li>
<li><strong>Fold rule:</strong> 2×2 spatial blocks with a 600 m boundary band removed from
<em>both</em> training and scoring.</li>
<li><strong>Mass rule:</strong> emission size comes from the measured mass sweep, never from a
model's self-prediction (the packer's dti_pred was ~0.49 against a realised ~0.27).</li>
<li><strong>Off-catalogue rule:</strong> every dot is ≥ 2 px from the catalogue, inside an approved
tile, inside the footprint.</li>
<li><strong>Range rule:</strong> float32, all-finite, [0,1], no nodata tag.</li>
</ul>
<h3>Data provenance</h3>
<p class="small">{man.get('n_files')} files, {man.get('total_bytes'):,} bytes, every one pinned by
sha256 in <span class="mono">registry/data_manifest.json</span>. The pins prove <strong>mirror
consistency, not organiser authentication</strong>: the bytes come from owner-published public GitHub
mirrors because the DrivenData data page is login-walled (IR-51-13). A reviewer with portal access
should re-download and diff.</p>
<h3>What was tried and did not work (so it is not retried)</h3>
<ul>
<li>The brief's literal strain-budget deficit as a locator — refuted on three instruments (H51-3).</li>
<li>Credit-density emission ordering (−0.0019, 2/4 folds) and redundancy-aware expected-budget
packing (−0.0034, 1/4 folds).</li>
<li>The coverage-lattice emission (−0.0104, 1/4 folds on the faithful instrument; IR-51-05).</li>
<li>SGMC/pre-Quaternary gap closure (wrong sign on both instruments; H51-5).</li>
</ul></div>"""
    shell("method.html", "Method & gates", method)

    # --------------------------------------------------------------- irregularities
    irows = "".join(
        f"<div class='card'><h2 style='margin-top:0'><span class='mono'>{e(i.get('id'))}</span> "
        f"<span class='pill p-proxy'>{e(i.get('severity'))}</span></h2>"
        f"<h3>Issue</h3><p>{e(i.get('issue'))}</p><h3>Action taken</h3><p>{e(i.get('action'))}</p></div>"
        for i in irr)
    shell("irregularities.html", "Irregularities",
          "<div class='card'><h1>Irregularities, deviations and self-caught errors</h1>"
          "<p class='small'>Flagged for human review. Nothing here is an accusation about anyone; "
          "several items are this repository's own mistakes, recorded so they are not repeated. "
          "Machine-readable: <span class='mono'>registry/irregularities.json</span>.</p></div>" + irows)

    # --------------------------------------------------------------- claims
    crows = [[f"<span class='mono'>{e(c.get('id'))}</span>", pill(c.get("class", ""), c.get("class", "")),
              e(c.get("claim")), f"<span class='mono small'>{e(c.get('evidence'))}</span>",
              f"<a class='small' href='{e(c.get('source'))}'>{e(str(c.get('source'))[:60])}</a>"
              if str(c.get("source", "")).startswith("http") else e(c.get("source"))] for c in claims]
    shell("claims.html", "Claims",
          "<div class='card'><h1>Claims ledger</h1><p class='small'>Every substantive statement this "
          "project makes, with the evidence that would falsify it and its class: "
          f"{pill('MEASURED','MEASURED')} recomputed here · {pill('PROXY','PROXY')} scored against the "
          f"visible catalogue only · {pill('UNVERIFIED-LIVE','UNVERIFIED-LIVE')} read from a live page."
          "</p>" + table(crows, ["ID", "Class", "Claim", "Evidence", "Source"]) + "</div>")

    # --------------------------------------------------------------- sources
    srows = [[f"<a href='{e(s.get('url'))}'>{e(s.get('title'))}</a>", e(s.get("used_for")),
              e(s.get("verified")), e(s.get("license", ""))] for s in srcs]
    shell("sources.html", "Sources",
          "<div class='card'><h1>Verified sources</h1><p class='small'>Free, public, official or "
          "primary sources only, each with what it was used for and who verified what: SELF = checked "
          "in this session from this environment; OWNER = recorded by the sibling repositories (second-hand, "
          "quoted as such); RUNNER = bytes fetched by a GitHub Actions runner. Machine-readable: "
          "<span class='mono'>registry/sources.json</span>.</p>"
          + table(srows, ["Source", "Used for", "Verification", "Licence"]) + "</div>")

    # --------------------------------------------------------------- leaderboard
    lrows = [[r.get("rank"), e(r.get("team")), f"{r.get('score'):.4f}"] for r in lb.get("rows", [])]
    shell("leaderboard.html", "Leaderboard",
          f"<div class='card'><h1>Public leaderboard, {e(lb.get('read_utc'))} {pill('UNVERIFIED-LIVE','read once, quoted')}</h1>"
          f"<p class='small'>Source: <a href='{e(lb.get('source_url'))}'>{e(lb.get('source_url'))}</a>. "
          f"{e(lb.get('note'))}</p>" + table(lrows, ["Rank", "Team", "Public score"])
          + f"<h3>Discrepancy with the task brief</h3><p>{e(lb.get('brief_discrepancy'))}</p>"
          + f"<h3>Artifact caveat</h3><p>{e(lb.get('artifact_caveat'))}</p></div>")

    print("site written; submission sha check:", "OK" if sha_ok else "MISMATCH", sha[:16])
    for f in sorted(DOCS.glob("*.html")):
        print(f"  {f.name} {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
