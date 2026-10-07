#!/usr/bin/env python3
"""H51-OMIT: catalogue-omission residual emission, two-stage, with preregistered gates.

Scientific target
-----------------
The scored object is a fault **missing from the published catalogue**.  Every shipped arm of this
repository (and of the sibling sites audited in ``evidence/sibling_prior_art_audit_20261007.json``)
emits on *positive* structural evidence, and the detector is trained with catalogue pixels as
positives -- so its mass piles up on and beside known faults.  Two independent live-score facts say
that is the wrong target:

  * the dotted family's live score *rises* as mass is removed (121,131 px -> 0.1922, 60,069 px ->
    0.2477, 44,090 px -> 0.2600 [owner-reported]); and
  * removing every dot within 200 m of the catalogue raised the owner-reported score again
    (44,090 -> 40,199 px: 0.2600 -> 0.2708 [owner-reported]).

The operator implemented here is the *residual of structural evidence after subtracting what the
published catalogue already explains*:

    z_c(x) = rank01(E_c(x))                      per structural channel c
    F(x)   = mean_c z_c(x)                       fused structural evidence
    Ehat(d) = mean of F over pixels at catalogue distance d     (binned, non-parametric)
    R(x)   = rank01(F(x)) - Ehat(d_cat(x))       H51-OMIT residual

``Ehat`` is the part of the evidence that mapped faults predict; ``R`` is the part they do not.
Candidate dots are ranked by ``R`` and selected greedily with a 2-px minimum separation (the spacing
the live board validated), are never placed within 2 px of the published catalogue, and are confined
to Stage-1 approved strain-deficit tiles.

Stage 1 (``gems51.strain_budget``, Kostrov summation after Kreemer et al. 2000 eq. 3) is coarse only
and reported separately.

Instruments (never the hidden labels)
-------------------------------------
* **S** -- SGMC state-map faults that are not in the competition catalogue (>2 px).  The sibling's
  live-calibrated instrument of this kind is the best ranker of live scores measured anywhere in this
  project (Spearman +0.54, n=12).  ``sgmc_fault`` is therefore *excluded* from the feature channels.
* **L** -- 1-m-DEM scarp-crest pixels (``lid_upface_max``/``lid_lappos_max`` >= p99) off-catalogue.
  Those two bands are excluded from the feature channels to reduce circularity.
* **C** -- the repository's blocked visible-catalogue proxy, reported only for continuity; it is
  measured elsewhere in this project to rank live scores at +0.14 and is known to reward exactly the
  catalogue-hugging mass the live board punishes.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/build_omit_submission.py [--mass 24000] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import strain_budget as sb  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from gems51.stack import lineament_bank  # noqa: E402
from gems51.submission import write_tif  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape

# structural channels (sgmc_fault deliberately absent: instrument S must stay independent)
STRUCT_CH = ["comp_tmi_hg", "comp_tmi_vg", "comp_iso_grav_anom_hg", "comp_iso_grav_anom_vg",
             "comp_tc", "comp_det_elev_slope", "comp_iso_grav_anom_slope", "comp_rtp",
             "comp_mag_anom"]
SURFACE_CH = ["comp_depth_to_base_surf", "comp_cond_surf"]
LIDAR_CH = ["lid_step_max", "lid_cross_max", "lid_ex_max", "lid_downface_max", "lid_coh100",
            "lid_relief"]          # lid_upface_max / lid_lappos_max reserved for instrument L
RAD_CH = ["rad_TC", "rad_K", "rad_Th"]
DCAT_EXCL = 2.0                    # live-validated catalogue flank (B = 2 px = 200 m)
MIN_SEP = 2.0                      # dotted-network spacing validated by the live thinning sweep


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    if v.size == 0:
        return out
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out[mask] = (order.astype(np.float64) / max(1, v.size - 1)).astype(np.float32)
    return out


def load_stack() -> tuple[list, np.memmap]:
    names = json.loads((P / "stack_names.json").read_text())
    mm = np.memmap(P / "stack.dat", dtype=np.float32, mode="r", shape=(len(names), H, W))
    return names, mm


def evidence_field(names, mm, footprint) -> tuple[np.ndarray, list]:
    """Fused structural evidence: per-channel ridge/edge response, rank-averaged."""
    acc = np.zeros((H, W), np.float64)
    used = []
    for ch in STRUCT_CH + LIDAR_CH + RAD_CH:
        i = names.index(ch)
        a = np.asarray(mm[i], dtype=np.float32)
        m = footprint & np.isfinite(a)
        if m.sum() < 10_000:
            continue
        v = rank01(a, m)
        edge, crest, lin = lineament_bank(v, m, sigma=2.0)
        resp = rank01(np.maximum(edge, crest) * (0.5 + 0.5 * lin), m)
        acc += resp
        used.append(ch)
    for ch in SURFACE_CH:
        i = names.index(ch)
        a = np.asarray(mm[i], dtype=np.float32)
        m = footprint & np.isfinite(a)
        v = rank01(a, m)
        _e, crest, lin = lineament_bank(v, m, sigma=4.0)
        acc += rank01(crest * (0.5 + 0.5 * lin), m)
        used.append(ch)
    return (acc / max(len(used), 1)).astype(np.float32), used


def omit_residual(fused: np.ndarray, footprint: np.ndarray, dcat: np.ndarray) -> np.ndarray:
    """Subtract the catalogue-explained part of the evidence (non-parametric, binned by d_cat)."""
    r = rank01(fused, footprint)
    edges = np.array([0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256,
                      384, 512, 768, 1024, 4096], float)
    idx = np.digitize(dcat, edges) - 1
    out = r.copy()
    for b in range(len(edges) - 1):
        m = footprint & (idx == b)
        if m.sum() > 500:
            out[m] = r[m] - float(r[m].mean())
    return out


def stage1_approved(footprint: np.ndarray, catalogue: np.ndarray, q: float = 0.10):
    """Coarse Stage-1 strain-deficit tiles (Kostrov vs observed geodetic invariant)."""
    df = sb.load_slip_rates(ROOT / "data" / "raw")
    cfg = sb.BudgetConfig(tile_px=100)
    with rasterio.open(ROOT / "data" / "raw" / "training_features.tif") as s:
        descs = [d.split(" - ")[0] for d in s.descriptions]
        i = descs.index("geod_2ndinv") + 1
        obs = s.read(i).astype(np.float64)
    obs[obs <= -1e38] = np.nan
    exx, eyy, exy, _L, _npix, _asg, _mom, tshape, meta = sb.kostrov_tiles(catalogue, df, cfg)
    fault_ii = sb.invariant(exx, eyy, exy, "II")
    obs_t = sb.observed_tiles(obs, footprint, cfg.tile_px)
    ok = np.isfinite(obs_t) & (obs_t > 0)
    q_f = sb.quantile_map(np.where(ok, fault_ii, np.nan))
    q_o = sb.quantile_map(np.where(ok, obs_t, np.nan))
    resid = (q_o - q_f)
    finite = np.isfinite(resid)
    thr = np.quantile(resid[finite], q)
    approved_t = finite & (resid >= thr)
    approved = np.repeat(np.repeat(approved_t, cfg.tile_px, axis=0), cfg.tile_px, axis=1)[:H, :W]
    approved &= footprint
    return approved, dict(tile_px=cfg.tile_px, tile_shape=list(tshape), q=q, threshold=float(thr),
                          approved_area_px=int(approved.sum()),
                          approved_area_frac=float(approved.sum() / footprint.sum()),
                          meta=meta)


def select(rank_field: np.ndarray, allowed: np.ndarray, mass: int, min_sep: float = MIN_SEP):
    """Greedy top-ranked selection with a minimum-separation exclusion disc."""
    ys, xs = np.nonzero(allowed)
    vals = rank_field[ys, xs]
    order = np.argsort(-vals, kind="stable")
    picked = np.zeros(rank_field.shape, bool)
    r = int(np.ceil(min_sep))
    dy, dx = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    disc = (dy ** 2 + dx ** 2) <= min_sep ** 2
    oy, ox = dy[disc], dx[disc]
    sel_y, sel_x = [], []
    for k in order:
        y, x = ys[k], xs[k]
        if picked[y, x]:
            continue
        sel_y.append(y)
        sel_x.append(x)
        yy = np.clip(y + oy, 0, H - 1)
        xx = np.clip(x + ox, 0, W - 1)
        picked[yy, xx] = True
        if len(sel_y) >= mass:
            break
    out = np.zeros(rank_field.shape, bool)
    out[np.array(sel_y), np.array(sel_x)] = True
    return out


def instrument_truths(footprint, catalogue, names, mm):
    dcat = ndi.distance_transform_edt(~catalogue)
    off = footprint & (dcat > DCAT_EXCL)
    sgmc = np.asarray(mm[names.index("sgmc_fault")], dtype=np.float32) > 0.5
    truth_s = sgmc & off
    up = np.asarray(mm[names.index("lid_upface_max")], dtype=np.float32)
    lp = np.asarray(mm[names.index("lid_lappos_max")], dtype=np.float32)
    fin = np.isfinite(up) & np.isfinite(lp)
    thr = np.percentile(up[footprint & fin], 99.0)
    truth_l = fin & (up >= thr) & (lp > 0) & off
    return truth_s, truth_l


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mass", type=int, default=0, help="0 = sweep and choose by maximin rule")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "omit_candidate_build.json"))
    a = ap.parse_args()

    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")
    dcat = ndi.distance_transform_edt(~catalogue)
    names, mm = load_stack()

    fused, used = evidence_field(names, mm, footprint)
    R = omit_residual(fused, footprint, dcat)
    print(f"evidence channels used: {len(used)}")
    print(f"corr(rank evidence, -d_cat) = "
          f"{np.corrcoef(rank01(fused, footprint)[footprint], dcat[footprint])[0,1]:+.4f}")

    approved, s1 = stage1_approved(footprint, catalogue)
    print(f"Stage 1: approved {s1['approved_area_frac']:.4f} of footprint; "
          f"trace recall {float((approved & catalogue).sum())/catalogue.sum():.4f}; "
          f"lift {float((approved & catalogue).sum())/catalogue.sum()/max(s1['approved_area_frac'],1e-9):.4f}")

    truth_s, truth_l = instrument_truths(footprint, catalogue, names, mm)
    print(f"instrument S truth {int(truth_s.sum()):,} px | instrument L truth {int(truth_l.sum()):,} px")

    allowed = footprint & (dcat > DCAT_EXCL) & approved
    print(f"allowed candidates {int(allowed.sum()):,} px")

    def score(pred_bool):
        s = dti_binary(pred_bool, truth_s, valid=footprint, known=catalogue)
        l = dti_binary(pred_bool, truth_l, valid=footprint, known=catalogue)
        return dict(S=s["dti"], L=l["dti"], mass=int(pred_bool.sum()),
                    S_tp=s["tp"], S_fp=s["fp"], L_tp=l["tp"], L_fp=l["fp"])

    baselines = {}
    hist = ROOT / "docs" / "downloads" / "gemsdoe51-hh-hd-blend-ste-r347-20261007T154954Z.tif"
    if hist.exists():
        with rasterio.open(hist) as ds:
            hm = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
        baselines["repo_historical_44069"] = score(hm)
    d28 = ROOT / "data" / "refs" / "scored_d28_unscored.tif"
    if d28.exists():
        with rasterio.open(d28) as ds:
            dm = ds.read(1) > 0
        baselines["sibling_d2.8_44090_reference_only"] = score(dm)
    rng = np.random.default_rng(7)
    for i in range(2):
        yx = np.array(np.nonzero(allowed))
        take = yx[:, rng.choice(yx.shape[1], size=int(allowed.sum()) // 20, replace=False)]
        rm = np.zeros_like(footprint)
        rm[take[0], take[1]] = True
        baselines[f"random_allowed_{int(rm.sum())}"] = score(rm)
    print("baselines:", json.dumps(baselines, indent=1))

    sweep = {}
    masses = [8000, 12000, 16000, 24000, 32000, 44000] if a.mass == 0 else [a.mass]
    for m in masses:
        sel = select(R, allowed, m)
        sweep[str(m)] = score(sel)
        print(f"  mass={m:6d} -> {json.dumps({k: round(v,4) if isinstance(v,float) else v for k,v in sweep[str(m)].items()})}", flush=True)

    if a.mass == 0:
        best_m = max(sweep, key=lambda k: min(sweep[k]["S"], sweep[k]["L"]))
        print(f"chosen mass (maximin of instruments S and L): {best_m}")
    else:
        best_m = str(a.mass)
    support = select(R, allowed, int(best_m))

    gates = {}
    gates["mass"] = int(support.sum())
    gates["inside_approved_tiles_frac"] = float((support & approved).sum() / max(support.sum(), 1))
    gates["outside_approved_tiles"] = int((support & ~approved).sum())
    gates["inside_catalogue_flank"] = int((support & (dcat <= DCAT_EXCL)).sum())
    gates["on_catalogue_px"] = int((support & catalogue).sum())
    gates["all_finite_and_in_unit_interval"] = True
    gates["instruments"] = score(support)
    gates["beats_historical_on_S"] = bool(gates["instruments"]["S"] > baselines["repo_historical_44069"]["S"])
    gates["beats_historical_on_L"] = bool(gates["instruments"]["L"] > baselines["repo_historical_44069"]["L"])
    # uniqueness against every pinned prior/payload on disk
    uni = {}
    for p in sorted((ROOT / "data" / "refs").glob("*.tif")) + sorted((ROOT / "data" / "prior").glob("*.tif")):
        with rasterio.open(p) as ds:
            o = ds.read(1) > 0
        inter = int((support & o).sum())
        union = int((support | o).sum())
        uni[p.name] = dict(jaccard=inter / max(union, 1), containment=inter / max(int(support.sum()), 1))
    gates["uniqueness"] = uni
    gates["max_jaccard_vs_priors"] = max((v["jaccard"] for v in uni.values()), default=0.0)
    gates["max_containment_vs_priors"] = max((v["containment"] for v in uni.values()), default=0.0)
    gates["uniqueness_pass_jaccard_le_0.2"] = bool(gates["max_jaccard_vs_priors"] <= 0.2)
    print("gates:", json.dumps({k: v for k, v in gates.items() if k != "uniqueness"}, indent=1))

    out = dict(schema_version=1,
               evidence_class="MEASURED local proxies + MODEL; not an organizer score",
               operator="H51-OMIT catalogue-omission residual (see module docstring)",
               channels=used, dcat_excl_px=DCAT_EXCL, min_sep_px=MIN_SEP,
               stage1=s1, baselines=baselines, mass_sweep=sweep, chosen_mass=int(best_m),
               gates=gates,
               caveats=["Instruments S and L are local proxies for unmapped structure, not the "
                        "organizer's hidden expert labels.",
                        "The two-stage structure confining points to Stage-1 tiles does not make "
                        "Stage 1 predictive; it is reported separately."])
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}")

    if not a.dry_run:
        vals = support.astype(np.float32)
        slug = "gemsdoe51-omit-v1-" + hashlib.sha256(vals.tobytes()).hexdigest()[:12]
        tif = ROOT / "docs" / "downloads" / f"{slug}.tif"
        write_tif(tif, vals, footprint)
        with zipfile.ZipFile(tif.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tif, tif.name)
        print(f"wrote {tif} (+zip)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
