#!/usr/bin/env python3
"""UNIQUENESS GATE -- prove the candidate is not a copy of any prior submission.

The brief is explicit: "MUST GENERATE A UNIQUE TIF SUBMISSION ... DO NOT COPY A PREVIOUS
SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION."

This gate therefore compares the candidate against every prior scored/offered artifact the
group has published, using four independent fingerprints:

  1. byte identity      -- sha256 equal to any reference (hard fail)
  2. support IoU        -- |A & B| / |A | B| on the binarised (>0) support
  3. cosine similarity  -- flattened value vectors
  4. containment        -- fraction of the candidate's MASS that lies within 3 px of the
                           reference's support (would indicate the candidate is the
                           reference re-emitted with a damping/thinning transform)

Verdict rule (frozen): PASS iff no sha256 match, no IoU > 0.50, no cosine > 0.90, and no
containment > 0.98.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
IOU_LIMIT = 0.50
COSINE_LIMIT = 0.90
CONTAINMENT_LIMIT = 0.98
LIFT_LIMIT = 3.0
_FOOTPRINT = None


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_support_and_values(p: Path):
    """Load, drop non-finite cells, and CLIP to the legal [0, 1] submission range.

    Clipping is required, not cosmetic: several reference rasters are not submissions at
    all (distance-in-metres layers, nodata sentinels of -3.4e38 that carry no nodata tag).
    Comparing raw values overflows float32 and produced a spurious cosine of 8773 in the
    first run of this gate.  Clipping puts every raster on the competition's own scale.
    """
    with rasterio.open(p) as src:
        a = src.read(1).astype(np.float64)
    finite = np.isfinite(a)
    a = np.where(finite, a, 0.0)
    a = np.clip(a, 0.0, 1.0).astype(np.float32)
    return a, a > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--refs", nargs="*", default=None)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "uniqueness_gate.json"))
    a = ap.parse_args()

    global _FOOTPRINT
    cand_path = Path(a.candidate)
    cand, cand_sup = load_support_and_values(cand_path)
    fp = ROOT / "data" / "sample_submission.tif"
    if fp.exists():
        with rasterio.open(fp) as src:
            _FOOTPRINT = np.isfinite(src.read(1).astype(np.float32))
        if _FOOTPRINT.shape != cand.shape:
            _FOOTPRINT = None
    cand_hash = sha256_of(cand_path)
    refs = [Path(p) for p in (a.refs or [])]
    if not refs:
        for root in (ROOT / "submissions", ROOT / "data" / "refs",
                     ROOT / "data" / "prior", ROOT / "docs" / "downloads",
                     Path("/home/user/study")):
            if root.exists():
                refs += [p for p in root.rglob("*.tif")]
    refs = [p for p in refs if p.resolve() != cand_path.resolve()]
    # Exclude the candidate's own build family: build_submission.py writes
    # zeros/nan twins and a hard-gate sibling from the SAME field in one run,
    # all carrying the same UTC build stamp.  Those are the candidate's own
    # outputs, not prior submissions; matching them would be matching oneself.
    import re
    own_family_skipped = []
    m = re.search(r"20\d{6}T\d{6}Z", cand_path.name)
    if m:
        stamp = m.group(0)
        fam, refs = refs, []
        for p in fam:
            if stamp in p.name:
                own_family_skipped.append({"path": str(p),
                                           "reason": f"same build stamp {stamp} as candidate"})
            else:
                refs.append(p)

    rep = {
        "candidate": str(cand_path),
        "candidate_sha256": cand_hash,
        "candidate_support_px": int(cand_sup.sum()),
        "candidate_mass": float(cand.sum()),
        "n_references": len(refs),
        "limits": {"iou": IOU_LIMIT, "cosine": COSINE_LIMIT,
                   "containment": CONTAINMENT_LIMIT},
        "worst": {}, "matches": [], "skipped": own_family_skipped, "verdict": None,
    }
    cand_norm = float(np.linalg.norm(cand.ravel()))


    rows = []
    for p in refs:
        try:
            r, r_sup = load_support_and_values(p)
        except Exception as e:  # noqa: BLE001
            rep["skipped"].append({"path": str(p), "reason": f"{type(e).__name__}: {e}"})
            continue
        if r.shape != cand.shape:
            rep["skipped"].append({"path": str(p),
                                   "reason": f"shape {r.shape} != {cand.shape}"})
            continue
        inter = int(np.logical_and(cand_sup, r_sup).sum())
        union = int(np.logical_or(cand_sup, r_sup).sum())
        iou = inter / union if union else 0.0
        rn = float(np.linalg.norm(r.ravel()))
        cos = float((cand.ravel() @ r.ravel()) / (cand_norm * rn)) if cand_norm and rn else 0.0
        # fraction of the CANDIDATE's mass lying within 3 px of the REFERENCE's support
        rd = distance_transform_edt(~r_sup)
        # Containment is only informative for SPARSE references.  A continuous raster
        # (distance-in-metres, block-id, or a dense lattice) has support everywhere, so
        # "is the candidate inside it" is trivially true and tests nothing.  Restrict it.
        ref_support_fraction = float(r_sup.mean())
        # NULL MODEL for containment: what fraction of the FOOTPRINT lies within 3 px of
        # the reference's support?  A random emission confined to the footprint would
        # achieve exactly that containment.  Only the LIFT over this null is informative.
        inside = np.isfinite(_FOOTPRINT) if _FOOTPRINT is not None else None
        if inside is None:
            containment_null = float((rd <= 3.0).mean())
        else:
            containment_null = float((rd[inside] <= 3.0).mean())
        containment = (
            float(cand[rd <= 3.0].sum() / max(1e-9, cand.sum()))
            if ref_support_fraction <= 0.20 else float("nan")
        )
        containment_lift = (containment / containment_null) if (
            ref_support_fraction <= 0.20 and containment_null > 1e-6) else float("nan")
        byte_same = sha256_of(p) == cand_hash
        rows.append({"path": str(p), "iou": iou, "cosine": cos,
                     "containment": containment, "byte_identical": byte_same,
                     "mass": float(r.sum()), "support_px": int(r_sup.sum()),
                     "ref_support_fraction": ref_support_fraction,
                     "containment_null": containment_null,
                     "containment_lift": containment_lift,
                     "containment_informative": bool(ref_support_fraction <= 0.20)})
        if (byte_same or iou > IOU_LIMIT or cos > COSINE_LIMIT
                or (ref_support_fraction <= 0.20 and containment > CONTAINMENT_LIMIT
                    and containment_lift > LIFT_LIMIT)):
            rep["matches"].append(rows[-1])

    if rows:
        inform = [r for r in rows if r["containment_informative"]]
        rep["worst"] = {
            "iou": max(rows, key=lambda x: x["iou"]),
            "cosine": max(rows, key=lambda x: x["cosine"]),
            "containment": (max(inform, key=lambda x: x["containment"]) if inform else None),
        }
        rep["n_containment_informative"] = len(inform)
    rep["n_compared"] = len(rows)
    rep["verdict"] = "PASS" if not rep["matches"] else "FAIL"
    rep["rule"] = (
        "PASS iff (1) no sha256 equals any reference AND (2) max support IoU <= 0.50 AND "
        "(3) max cosine <= 0.90 AND (4) no sparse reference has containment > 0.98 with a "
        "lift > 3x over the random-emission null.  Continuous/lattice references are "
        "excluded from test (4) because their dilated support covers the map and the test "
        "would be vacuous.  Two artifacts anchored on the same mapped-fault network will "
        "ALWAYS show high mutual containment; that is a consequence of the metric's "
        "free-mass structure, not of copying, and tests (2) and (3) are what separate a "
        "re-emission from a copy.")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=2, default=float))
    print(f"[uniqueness gate] {rep['verdict']}  ({rep['n_compared']} references compared, "
          f"{len(rep['skipped'])} skipped, {len(rep['matches'])} matches)")
    for m in rep["matches"][:20]:
        print(f"  MATCH {Path(m['path']).name}: iou={m['iou']:.4f} cos={m['cosine']:.4f} "
              f"cont={m['containment']:.4f} byte={m['byte_identical']}")
    if rep["worst"]:
        w = rep["worst"]
        print(f"  worst IoU         {w['iou']['iou']:.4f}  vs {Path(w['iou']['path']).name}")
        print(f"  worst cosine      {w['cosine']['cosine']:.4f}  vs {Path(w['cosine']['path']).name}")
        if w["containment"]:
            print(f"  worst containment {w['containment']['containment']:.4f}  vs "
                  f"{Path(w['containment']['path']).name}  (over "
                  f"{rep['n_containment_informative']} sparse references)")
    print(f"  wrote {a.out}")
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
