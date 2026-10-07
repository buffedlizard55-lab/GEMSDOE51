#!/usr/bin/env python3
"""Rebuild the shipped submission from the cached production belief field using the promoted
coverage-lattice emission rule, without retraining.

    python3 scripts/rebuild_submission.py [--quantile 0.90] [--spacing 3]

It writes the same artefacts as scripts/run_all.py step 6-7 (tif, zip, checks, receipt, gates,
audit) so the two paths are interchangeable.  run_all.py calls submission.build_emission with the
same defaults, so a fresh end-to-end run reproduces this file byte for byte.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems51 import emission, grid, metric, submission  # noqa: E402

NAME = "gemsdoe51-strainbudget-s1-v1"
NOTE = ("GEMSDOE51 | S1 geodetic-strain tile gate + S2 blocked-CV 44-ch detector, coverage-lattice "
        "emission over top-decile belief inside approved tiles; Stage-A deficit tested and reported "
        "as falsified; UNSCORED")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quantile", type=float, default=0.90)
    ap.add_argument("--spacing", type=int, default=3)
    args = ap.parse_args()

    belief = np.load(ROOT / "work" / "belief_field_full.npy")
    approved = submission.approved_mask_from_stage_a(0.5)
    np.save(ROOT / "work" / "approved_mask.npy", approved)
    mask, info = submission.build_emission(belief, approved, quantile=args.quantile,
                                          spacing=args.spacing)
    cand = submission.candidate_mask(approved)
    np.save(ROOT / "work" / "candidate_mask.npy", cand)
    np.save(ROOT / "work" / "emission_mask.npy", mask)

    audit = metric.credit_audit(mask)
    (ROOT / "evidence" / "emission_audit.json").write_text(json.dumps(dict(
        **{k: v for k, v in info.items() if k != "n_emitted"},
        n_emitted=audit.n_emitted, total_mass=audit.total_mass,
        redundancy_fraction=audit.redundancy_fraction,
        mean_self_kernel=audit.mean_self_kernel,
        approved_px=int(approved.sum())), indent=1) + "\n")

    receipt = submission.write_submission(emission.to_values(mask), NAME, NOTE)
    (ROOT / "evidence" / "submission_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    (ROOT / "evidence" / "uniqueness_gate.json").write_text(
        json.dumps(submission.uniqueness_gate(mask), indent=1) + "\n")
    (ROOT / "evidence" / "stage_dominance.json").write_text(
        json.dumps(submission.stage_dominance_check(mask, approved, cand), indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("name", "n_positive", "min", "max", "n_nan",
                                              "sha256", "all_finite", "in_0_1", "bytes")}, indent=1))
    print("emission info:", json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
