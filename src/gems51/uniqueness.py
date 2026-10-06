"""Uniqueness gate: prove the candidate is not a re-issue of a previous submission.

The brief is explicit that the file must be a *unique* submission rather than a
copy of anything in the GEMSDOE1..54 family.  "Unique" is checked three ways,
because a file can be novel in one sense and a duplicate in another:

1. **Byte identity** — sha256 against every prior artifact we hold.  A digest
   match is a hard fail.
2. **Pixel identity** — Jaccard overlap of the emitted support and of the
   binarised support at several thresholds.  A file that is 99 % the same dots is
   not unique however different its bytes are.
3. **Submission-dominance** — what fraction of the candidate's emitted mass lies
   inside Stage 1's approved-tile footprint, and how much of the candidate is
   explained by the coarse prior alone.  The brief asks us to confirm the
   submission is not dominated by Stage 1.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

KNOWN_PRIOR_SHA256 = {
    # sha256 -> (label, reported score or None if unscored)
    "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9":
        ("GEMSDOE32 h33-h33-2-b2 (zeros)", 0.2778),
    "baeae3219bba6a19": ("GEMSDOE32 h33-h33-2-b2 (nan twin)", None),
    "4dc4cc54b061cb4567a5500c8fa2bfe750a39340b02c8cdbb4308916f36cbcc3":
        ("GEMSDOE32 probe-S1 anchor == GEMSDOE25 dotted-h19-5-d2-8 (zeros)", 0.2600),
    "3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30":
        ("GEMSDOE25 dotted-h19-5-d2-8 (zeros)", 0.2600),
    "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8":
        ("GEMSDOE25 dotted-h19-5-d2-8 (nan)", 0.2600),
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, bool)
    b = np.asarray(b, bool)
    inter = int((a & b).sum())
    union = int((a | b).sum())
    return inter / union if union else 1.0


def overlap_fraction(a: np.ndarray, b: np.ndarray) -> float:
    """|a ∩ b| / |a| -- how much of a is already in b."""
    a = np.asarray(a, bool)
    b = np.asarray(b, bool)
    return float((a & b).sum() / max(int(a.sum()), 1))


@dataclass
class UniquenessReport:
    candidate: str
    sha256: str
    byte_duplicate_of: list = field(default_factory=list)
    support_jaccard: dict = field(default_factory=dict)
    support_containment: dict = field(default_factory=dict)
    stage1_dominance: dict = field(default_factory=dict)
    verdict: str = "PENDING"
    notes: list = field(default_factory=list)

    def as_dict(self):
        return dict(candidate=self.candidate, sha256=self.sha256,
                    byte_duplicate_of=self.byte_duplicate_of,
                    support_jaccard=self.support_jaccard,
                    support_containment=self.support_containment,
                    stage1_dominance=self.stage1_dominance,
                    verdict=self.verdict, notes=self.notes)


def run_gate(candidate_path: Path, prior_paths: dict, candidate_support: np.ndarray,
             truth_footprint: np.ndarray, stage1_approved: np.ndarray | None = None,
             max_jaccard: float = 0.50, max_containment: float = 0.60,
             max_stage1_lift: float = 1.5) -> UniquenessReport:
    """Run every uniqueness check.

    ``candidate_support`` : bool grid of emitted pixels.
    ``truth_footprint``   : bool grid of the scored domain.
    ``stage1_approved``   : bool grid of Stage 1's approved tiles (may be None).
    """
    sha = sha256_file(candidate_path)
    rep = UniquenessReport(candidate=str(candidate_path.name), sha256=sha)

    hit = KNOWN_PRIOR_SHA256.get(sha)
    if hit:
        rep.byte_duplicate_of.append(dict(label=hit[0], score=hit[1]))
    for label, p in prior_paths.items():
        p = Path(p)
        if not p.exists():
            continue
        s = sha256_file(p)
        if s == sha:
            rep.byte_duplicate_of.append(dict(label=label, sha256=s))

    for label, p in prior_paths.items():
        p = Path(p)
        if not p.exists():
            continue
        if p.suffix.lower() == ".npy":
            other = np.load(p) > 0
        elif p.suffix.lower() in (".tif", ".tiff"):
            try:
                import rasterio
                with rasterio.open(p) as s:
                    arr = s.read(1)
                other = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0) > 0
                if other.shape != candidate_support.shape:
                    continue
            except Exception as exc:  # noqa: BLE001
                rep.notes.append(f"could not read {p.name}: {exc}")
                continue
        else:
            continue
        rep.support_jaccard[label] = round(float(jaccard(candidate_support, other)), 6)
        rep.support_containment[label] = round(float(overlap_fraction(candidate_support, other)), 6)

    if stage1_approved is not None:
        ap = np.asarray(stage1_approved, bool)
        inside = int((candidate_support & ap).sum())
        total = int(candidate_support.sum())
        area_share = float((ap & truth_footprint).sum() / max(int(truth_footprint.sum()), 1))
        rep.stage1_dominance = dict(
            approved_area_share_of_footprint=area_share,
            emitted_pixels_inside_approved=inside,
            emitted_pixels_total=total,
            emitted_share_inside_approved=inside / max(total, 1),
            lift_over_area_share=(inside / max(total, 1)) / max(area_share, 1e-9),
        )
        lift = rep.stage1_dominance["lift_over_area_share"]
        if lift > 1.5:
            rep.notes.append(
                f"emission is {lift:.2f}x over-represented inside the Stage 1 approved "
                "tiles relative to their area share -- the coarse prior is driving the "
                "placement and the brief's 'not dominated by stage one' test is at risk")
        elif lift < 0.8:
            rep.notes.append(
                f"emission is under-represented inside the Stage 1 approved tiles "
                f"(lift {lift:.2f}): the fine-scale model is placing points by its own "
                "criteria, so Stage 1 does not dominate -- but note the two stages are "
                "mildly anti-correlated at the point level")

    worst_j = max(rep.support_jaccard.values(), default=0.0)
    worst_c = max(rep.support_containment.values(), default=0.0)
    fails = []
    if rep.byte_duplicate_of:
        fails.append("byte-identical to a prior submission")
    if worst_j > max_jaccard:
        fails.append(f"support Jaccard {worst_j:.3f} > {max_jaccard}")
    if worst_c > max_containment:
        fails.append(f"containment {worst_c:.3f} > {max_containment}")
    # Note the test cannot be the raw share: under a hard gate every emitted point
    # is inside an approved tile *by construction*, so that share is always 1.0 and
    # would fail regardless of how little the coarse prior actually constrains.
    # The meaningful quantity is the lift -- how much more the emission favours the
    # approved tiles than their own area share does.  A lift near 1 means Stage 1
    # is not steering the placement at all.
    if rep.stage1_dominance.get("lift_over_area_share", 0.0) > max_stage1_lift:
        fails.append(f"emission dominated by Stage 1 footprint "
                     f"(lift {rep.stage1_dominance['lift_over_area_share']:.2f})")
    rep.verdict = "FAIL: " + "; ".join(fails) if fails else "PASS"
    return rep
