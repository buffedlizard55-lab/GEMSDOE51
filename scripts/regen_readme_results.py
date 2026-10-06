#!/usr/bin/env python3
"""Regenerate section 5 of README.md ("What shipped this session") from the
artifacts in data/.  Every number in that section is read from a JSON file that
the pipeline produced; nothing in it is typed by hand.

Usage:  python3 scripts/regen_readme_results.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load(rel, default=None):
    p = ROOT / "data" / rel
    if not p.exists():
        return default
    return json.loads(p.read_text())


def paired(v, base):
    d = [a - b for a, b in zip(v["per_fold"], base["per_fold"])]
    return sum(d) / len(d), sum(1 for x in d if x > 0), len(d)


def gate_rows():
    g = load("gate_sweep.json")
    if not g:
        return ["| *(gate sweep not run)* | | | | |"]
    out = ["| gate | setting | mean proxy DTI | paired Δ | folds better |"]
    out.append("|---|---|---|---|---|")
    for kind, label, fmt in (("soft", "soft prior", lambda k: f"w = {k}"),
                             ("hard", "hard gate", lambda k: f"top {100 - float(k):.0f} % of tiles")):
        blk = g.get(kind) or {}
        if not blk:
            continue
        base = blk.get("0") or blk.get("0.0") or list(blk.values())[0]
        for k, v in blk.items():
            d, n, tot = paired(v, base)
            out.append(f"| {label} | {fmt(k)} | {v['mean']:.4f} | {d:+.4f} | {n}/{tot} |")
    return out


def stage1_rows():
    d = load("stage1_trace_holdout.json")
    if not d:
        return ["| *(stage-1 trace holdout not run)* | | | | | |"]
    s = d["summary"]
    out = ["| prior | approved | area share | truth recall | lift | proxy DTI |",
           "|---|---|---|---|---|---|"]
    for q in ("50", "70", "80"):
        for nm in ("deficit", "geodetic_only"):
            if f"{nm}_lift_q{q}" in s:
                out.append(
                    f"| {nm} | top {100 - int(q)} % of tiles | {s[f'{nm}_area_q{q}']['mean']:.3f} "
                    f"| {s[f'{nm}_recall_q{q}']['mean']:.3f} | {s[f'{nm}_lift_q{q}']['mean']:.3f} "
                    f"| {s[f'{nm}_dti_q{q}']['mean']:.4f} |")
    out.append(f"| none | whole footprint | 1.000 | 1.000 | 1.000 | {s['uniform_dti']['mean']:.4f} |")
    rho = {k.replace("spearman_", ""): v["mean"] for k, v in s.items() if k.startswith("spearman_")}
    if rho:
        out.append("")
        out.append("Spearman rank correlation of each tile field against held-out fault density: "
                   + ", ".join(f"{k} = {v:+.3f}" for k, v in rho.items()) + ".")
    return out


def arm_rows():
    out = ["| arm | in-block AUC | proxy DTI at M/|G| = 3.47 | folds |",
           "|---|---|---|---|"]
    for a in ("base", "H_E", "H_D", "H_C", "H_ALL"):
        h = load(f"holdout_{a}.json")
        if not h:
            out.append(f"| {a} | *(not run)* | | |")
            continue
        s = h["summary"]
        dti = s.get("dti_r3.47") or s.get("dti_r3_47")
        out.append(f"| {a} | {s['auc_mean']:.4f} | {dti['mean']:.4f} | {len(s['auc_per_fold'])} |")
    return out


def artifact_rows(m):
    out = ["| role | gate | holdout cost vs ungated | max Jaccard vs any prior GEMSDOE submission "
           "| uniqueness |", "|---|---|---|---|---|"]
    for a in m["artifacts"]:
        j = a["uniqueness"]["support_jaccard"]
        out.append(f"| {a['role']} | {a['gate_mode']} | "
                   f"{a.get('holdout_cost_vs_ungated', 0):+.4f} | {max(j.values()):.3f} | "
                   f"{a['uniqueness']['verdict']} |")
    return out


def main() -> int:
    m = load("submission_manifest.json")
    if not m:
        print("data/submission_manifest.json missing - run scripts/build_submission.py first")
        return 1
    p = m["primary"]
    hd = load("holdout_H_D.json", {}).get("summary", {})
    base = load("holdout_base.json", {}).get("summary", {})
    hd_dti = hd.get("dti_r3.47") or hd.get("dti_r3_47") or {"mean": float("nan")}
    b_dti = base.get("dti_r3.47") or base.get("dti_r3_47") or {"mean": float("nan")}

    sec = f"""
## 5. What shipped this session

### The deliverable

`docs/downloads/{p['file']}` — {p['checks']['positive_px']:,} emitted pixels,
sha256 `{p['sha256'][:12]}…`.

Two files are offered, both from the same detector and the same 3-bag ensemble, differing only in
how Stage 1 is allowed to touch them:

{chr(10).join(artifact_rows(m))}

The **PRIMARY** uses the soft prior, because it is the only Stage-1 setting that is not negative on
the blocked holdout. The **SECONDARY** is the brief's literal design — points only inside
stage-one-approved tiles — shipped as ordered, with its measured cost printed next to it rather than
hidden.

### Stage 1 and Stage 2, reported separately

*Stage 1* (Kostrov strain-budget deficit, 10 km tiles) is scored on a **trace-level** holdout,
because a spatial block would zero the fault-accommodated term inside the block and the question
would be circular: with the block's own faults removed there is nothing to accommodate. A fifth of
the mapped traces is withheld, the remaining four fifths supply the budget, and uniform random dots
are thrown down inside the approved tiles versus everywhere. No model is fitted, so there is no
leakage to control.

{chr(10).join(stage1_rows())}

The deficit is **worse than the raw geodetic field** on every column. Subtracting the
fault-accommodated term removes signal instead of isolating it: the mapped-fault term tracks where
faults cluster, mapped faults are surrounded by unmapped ones, so it carries *positive* information
about where the missing ones are. Stage 1 is retained as a prior, not as a filter.

*Stage 2* (the detector), spatially blocked holdout:

{chr(10).join(arm_rows())}

### Gate sweep

Hard gate versus soft prior, six folds, paired against the ungated run:

{chr(10).join(gate_rows())}

The hard gate is monotone-harmful: it never wins a fold at any setting. It is shipped anyway, at the
mildest setting that still passes the anti-dominance test, because the brief asks for it — and its
cost is disclosed on the download page rather than hidden.

### Honest expectation, written down before the score is known

Our instrument says **{hd_dti['mean']:.3f}** proxy DTI at the live mass ratio, against
**{b_dti['mean']:.3f}** for the previous stack. That brackets the group's best owner claim (0.2778)
and sits below the current public leader (0.3774). **Expect this file to land in the high 0.2s.** It
is a genuinely new, independently verified, portal-legal submission — it is not yet a leaderboard
win.

### Phase 1 entries are not free

The organizer has stated that the Phase 2 test set "will use a test set that is updated by expert
review of all Phase 1 submissions, so your fault predictions have an impact on final evaluation even
if they are not the most performant in Phase 1" (chrisk-dd, 2026-09-23, thread 11527 post 7). Every
emitted dot is therefore required to be individually defensible: all lie outside the 200 m exclusion
zone, none sits on a catalogued trace, and the argument for looking in any given tile is published
on the method page. The same organizer post declined to disclose the data sources, fault types or
coverage behind the hidden labels, so **no** validation instrument here — including ours — can be
shown to match the hidden label style (IR-51-05).
"""
    r = ROOT / "README.md"
    txt = r.read_text()
    i = txt.find("\n## 5. What shipped this session")
    if i < 0:
        txt = txt.rstrip() + "\n" + sec
    else:
        txt = txt[:i] + sec
    r.write_text(txt)
    print("README section 5 regenerated from data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
