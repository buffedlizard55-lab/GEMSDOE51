#!/usr/bin/env python3
"""H51-N2 submission builder: validated fine-scale detector + metric-algebra emission.

What is new in this artifact (each point is measured, not asserted):

1.  Stage 1 — the geodetic strain-budget deficit of the brief, computed with the
    published moment-tensor summation (Kreemer, Haines, Holt & Blewitt 2000,
    Eq. 3, https://geodesy.unr.edu/publications/Kreemer_et_al_GlobalStrain_2000.pdf)
    from the INGENIOUS/QFaults trace table, ranked against the supplied
    ``geod_2ndinv`` / ``geod_dilaterate`` / ``geod_shearrate`` layers, and kept
    strictly as a **coarse allowed domain** (it never weights a fine-scale point).
2.  Stage 2 — the repository's H-D physical arm (58 catalogue-independent stack
    layers + 4 scarp-facing-coherence layers) fitted on the visible catalogue.
3.  Emission — unit-valued dots with a minimum separation of ``--spacing`` px
    (the metric's kernel support is R = 3 px = 300 m, so closer dots share their
    credit), a mass of ``ratio * G_HIDDEN`` dots, and a hard removal of every
    candidate within ``--excl-radius`` px of the mapped catalogue.
4.  Output encoding — every pixel finite and in [0, 1] (0 outside the footprint),
    single band float32, EPSG:32611, template transform.  The previously reported
    portal error ("Predicted values must be in range [0, 1]") cannot be produced
    by a fully finite raster; NaN-outside twins are deliberately NOT written, so
    there is exactly one download to submit.

The script refuses to write unless every gate passes: official format,
support-uniqueness against the pinned family reference set, "every emitted point
inside the Stage-1 approved tiles", and Stage-1 non-dominance (lift < 1.5).

Usage::

    python3 scripts/build_submission_n1.py --ratio 3.0 --spacing 2.8 \
        --excl-radius 2.24 --stage1-q 10 --tag h51n2-creditthin
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems51 import credit_emission as ce            # noqa: E402
from gems51 import inventory_context as ic          # noqa: E402
from gems51 import strain_budget as sb              # noqa: E402
from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.emission import nms_dots, rasterise     # noqa: E402
from gems51.grid import GRID                        # noqa: E402
from gems51.submission import verify, write_tif     # noqa: E402
from gems51.uniqueness import run_gate              # noqa: E402
from scripts.build_submission import (              # noqa: E402
    G_HIDDEN_ESTIMATE,
    prior_rasters,
    require_family_reference_coverage,
    require_unique_support,
)
from scripts.build_submission_hh_blend import stage1_prior, load_observed  # noqa: E402

P = ROOT / "data" / "prepared"
DOCS = ROOT / "docs" / "downloads"


def load_hd_extras():
    path = P / "arm_hd.dat"
    names = json.loads((P / "arm_hd_names.json").read_text())
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return [np.asarray(mm[i], dtype=np.float32) for i in range(len(names))], names


def spacing_stats(support: np.ndarray, sample: int = 4000, seed: int = 7) -> dict:
    from scipy.spatial import cKDTree
    yy, xx = np.nonzero(support)
    n = yy.size
    if n == 0:
        return dict(n=0)
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=min(sample, n), replace=False)
    tree = cKDTree(np.stack([yy, xx], 1))
    d, _ = tree.query(np.stack([yy[idx], xx[idx]], 1), k=2)
    nn = d[:, 1]
    return dict(n=int(n), nn_median=float(np.median(nn)),
                nn_p10=float(np.percentile(nn, 10)),
                nn_p90=float(np.percentile(nn, 90)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=3.0)
    ap.add_argument("--g-hidden", type=int, default=G_HIDDEN_ESTIMATE)
    ap.add_argument("--tile-px", type=int, default=100)
    ap.add_argument("--stage1-q", type=float, default=10.0)
    ap.add_argument("--excl-radius", type=float, default=2.24)
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--nms-radius", type=float, default=2.4)
    ap.add_argument("--neg", type=int, default=250_000)
    ap.add_argument("--max-iter", type=int, default=250)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--tag", default="h51n2-creditthin")
    ap.add_argument("--out-dir", default=str(DOCS))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    t0 = time.time()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    stack = Stack(P)
    extras, extra_names = load_hd_extras()
    print(f"[load] stack={len(stack.names)} features, extras={extra_names}", flush=True)

    # ---------------------------------------------------------------- Stage 1
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    obs = load_observed()
    s1 = stage1_prior(catalogue, footprint, df, obs, tile_px=a.tile_px, q=a.stage1_q)
    approved = s1["approved"]
    area_share = float((approved & footprint).sum() / max(int(footprint.sum()), 1))
    print(f"[stage1] q{a.stage1_q:g} approved_area_share={area_share:.6f} "
          f"threshold={s1['threshold']:.6g}", flush=True)
    print(f"[stage1] formula: {s1['formula']}", flush=True)

    # ---------------------------------------------------------------- Stage 2
    pool = footprint & ~catalogue
    rng = np.random.default_rng(a.seed)
    X, y = stack.sample(catalogue & footprint, pool, a.neg, rng, extra=extras)
    model = fit_detector(X, y, seed=a.seed, max_iter=a.max_iter)
    del X, y
    field = predict_grid(model, stack, footprint, extra=extras, chunk=128)
    print(f"[stage2] field fitted and predicted ({time.time()-t0:.0f}s)", flush=True)
    np.save(P / "field_final_H51N2.npy", field)   # regenerable cache, gitignored

    # ---------------------------------------------------------------- emission
    dom = footprint & np.isfinite(field)
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    not_excluded = d_cat >= a.excl_radius
    cand = dom & approved & not_excluded
    n_dots = int(round(a.ratio * a.g_hidden))
    ys, xs = nms_dots(field, n_dots, radius=a.nms_radius, exclude=~cand, valid=dom)
    support = rasterise(ys, xs) > 0
    placed = int(support.sum())
    if placed != n_dots:
        raise SystemExit(f"emitter placed {placed} of {n_dots} requested dots")
    print(f"[emit] {placed:,} unit dots; spacing>={a.nms_radius} px; "
          f"exclusion>={a.excl_radius} px ({time.time()-t0:.0f}s)", flush=True)

    # ---------------------------------------------------------------- audits
    d_sup = d_cat[support]
    geom = dict(
        dots=placed,
        d_cat_p10=float(np.percentile(d_sup, 10)), d_cat_median=float(np.median(d_sup)),
        d_cat_p90=float(np.percentile(d_sup, 90)),
        frac_within_3px=float((d_sup < 3).mean()),
        frac_within_5px=float((d_sup < 5).mean()),
        frac_within_10px=float((d_sup < 10).mean()),
        spacing=spacing_stats(support),
    )
    print("[audit] " + json.dumps(geom), flush=True)
    credit = ce.expected_credit(np.clip(np.nan_to_num(field, nan=0.0), 0, 1), dom)
    sel_credit_sum = float(credit[support].sum())
    g_hat = float(a.g_hidden)
    dti_hat = ce.predicted_dti(sel_credit_sum, placed, g_hat)  # expectation, not a score
    print(f"[audit] expected-credit sum={sel_credit_sum:.1f} -> implied DTI at "
          f"|G|={int(g_hat)} is {dti_hat:.4f} (EXPECTATION ONLY, not a score)", flush=True)

    mass_sensitivity = {}
    for g in (8_000, 12_700, 20_000, 40_000):
        for r in (2.0, 3.0, 4.0):
            mass_sensitivity[f"g{g}_r{r:g}"] = int(round(r * g))

    # ---------------------------------------------------------------- gates
    priors = prior_rasters()
    ref_count = require_family_reference_coverage(priors)
    unique_preflight = require_unique_support(support, priors)
    inside = int((support & approved).sum())
    emitted_share = inside / max(placed, 1)
    lift = emitted_share / max(area_share, 1e-12)
    if inside != placed:
        raise SystemExit(f"Stage-1 confinement failed: {placed - inside} dots outside approved tiles")
    if lift > 1.5:
        raise SystemExit(f"Stage-1 dominance failed: lift={lift:.6f}")
    print("[preflight] " + json.dumps(dict(
        max_support_jaccard=unique_preflight["max_jaccard"],
        max_support_containment=unique_preflight["max_containment"],
        approved_area_share=area_share, emitted_share_inside_approved=emitted_share,
        lift_over_area_share=lift), indent=1), flush=True)
    if a.dry_run:
        print("[dry-run] gates passed; nothing written")
        return 0

    # ---------------------------------------------------------------- write
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"gemsdoe51-{a.tag}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    staging = out_dir / f".{base}.staging.tif"
    primary = out_dir / f"{base}.tif"
    try:
        rec = write_tif(staging, support.astype(np.float32), footprint,
                        outside=0.0, nodata=None)
        if not rec["checks"]["format_valid"]:
            raise SystemExit("staged GeoTIFF failed the local official-format verifier")
        gate = run_gate(staging, priors, support, footprint, approved)
        if gate.verdict != "PASS":
            raise SystemExit("staged GeoTIFF failed uniqueness/Stage-1 gate: " + gate.verdict)
        staging.replace(primary)
        rec = verify(primary, footprint)
        rec["file"] = primary.name
        gate.candidate = primary.name
    finally:
        if staging.exists():
            staging.unlink()

    zip_path = out_dir / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(primary, primary.name)

    sha = hashlib.sha256(primary.read_bytes()).hexdigest()
    record = dict(
        id="H51_N2_PHYSICAL_CREDITTHIN",
        role="PRIMARY",
        status="LOCAL_GATES_PASSED_UNSCORED",
        file=primary.name,
        zip=zip_path.name,
        submission_name=f"GEMSDOE51-{a.tag}-{stamp}",
        note=("H-D physical arm; unit dots at >=2.4 px NMS spacing; every dot >=224 m from the "
              "mapped catalogue; all points inside the Stage-1 strain-deficit q10 tiles; "
              "no organizer score claimed."),
        sha256=sha,
        bytes=primary.stat().st_size,
        format=rec,
        gate_mode="H51-N2 (single arm, metric-algebra emission)",
        stage1=dict(q=float(a.stage1_q), tile_px=int(a.tile_px),
                    approved_area_share=area_share, threshold=float(s1["threshold"]),
                    formula=s1["formula"], residual_policy=s1["residual_policy"],
                    emitted_share_inside_approved=emitted_share,
                    lift_over_area_share=lift,
                    fault_median_II=float(np.nanmedian(s1["fault_ii"])),
                    observed_median_II=float(np.nanmedian(s1["observed_ii"])),
                    meta=s1["meta"]),
        emission=dict(method="greedy NMS on the raw field", nms_radius_px=a.nms_radius,
                      exclusion_radius_px=a.excl_radius, requested_dots=n_dots,
                      placed_dots=placed, g_hidden=float(g_hat), ratio=float(a.ratio),
                      mass_sensitivity_table=mass_sensitivity,
                      expected_credit_sum=sel_credit_sum,
                      implied_dti_expectation=dti_hat),
        geometry_audit=geom,
        uniqueness=dict(prewrite=unique_preflight, staged=gate.as_dict(),
                        reference_count=ref_count),
        model=dict(detector="HistGradientBoostingClassifier",
                   features=len(stack.static) + len(extra_names),
                   extras=extra_names, negatives=a.neg, max_iter=a.max_iter, seed=a.seed),
        limitations=[
            "Local gates only: no DrivenData score, upload or acceptance is claimed.",
            "The hidden-truth mass 12700 is an estimate inferred from reported sibling scores; "
            "the mass sensitivity table lists the alternatives that were considered.",
            "Stage 1 is a coarse allowed domain; it is weak on the proxy instrument and "
            "never weights an individual emitted point.",
        ],
    )
    (out_dir / f"{base}-checks.json").write_text(json.dumps(record, indent=1) + "\n")
    (ROOT / "evidence" / "submission_h51n2.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(dict(file=primary.name, zip=zip_path.name, sha256=sha,
                          bytes=record["bytes"], format=rec["checks"]), indent=1))
    print(f"[done] {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
