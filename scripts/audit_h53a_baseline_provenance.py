#!/usr/bin/env python3
"""Fresh-fit H-D/H-H baseline audit; H53 candidate scoring is not performed here.

The audit follows run_experiments.py's canonical 1000+fold negative-sampling
seed and compares a freshly rebuilt H-D/H-H 50/50 STE blend with the frozen
cached-field receipt. It stops the H53 Stage-2 path if the locked tolerance is
not met. Cached h52_field_* files are never consumed.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gems51.detector import Stack, fit_detector, predict_grid  # noqa: E402
from gems51.grid import GRID  # noqa: E402
from gems51.holdout import make_folds  # noqa: E402
from gems51.metric import dti_binary  # noqa: E402
from scripts.evaluate_hh_blend import ste_emit  # noqa: E402

P = ROOT / "data" / "prepared"
FROZEN = ROOT / "evidence" / "hh_blend_holdout.json"
OUT = ROOT / "evidence" / "h53a_baseline_provenance_20261008.json"
FIELD_DIR = P / "h53a_baseline_fields"
FROZEN_MEAN = 0.285340602656319
REPRO_TOLERANCE = 1e-5
NEGATIVES = 250_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_arm(path: Path, names_path: Path, required_prefixes):
    names = json.loads(names_path.read_text())
    if not names or len(names) != len(set(names)):
        raise ValueError(f"invalid or duplicate feature names in {names_path}")
    absent = [prefix for prefix in required_prefixes
              if not any(name.startswith(prefix) for name in names)]
    if absent:
        raise ValueError(f"{path.name} does not contain required feature groups {absent}")
    mm = np.memmap(path, dtype=np.float32, mode="r", shape=(len(names), *GRID.shape))
    return names, mm


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite baseline audit receipt {OUT}")
    if not FROZEN.is_file():
        raise SystemExit(f"frozen baseline receipt missing: {FROZEN}")
    hd_path, hd_names_path = P / "arm_hd.dat", P / "arm_hd_names.json"
    hh_path, hh_names_path = P / "arm_hh.dat", P / "arm_hh_names.json"
    for path in (hd_path, hd_names_path, hh_path, hh_names_path):
        if not path.is_file():
            raise SystemExit(f"rebuild the preregistered static arm first: missing {path}")
    if FIELD_DIR.exists():
        raise SystemExit(f"refusing to reuse unreceipted field directory: {FIELD_DIR}")

    hd_names, hd_mm = load_arm(hd_path, hd_names_path, ("lidrel_facecoh", "detelev_facecoh"))
    hh_names, hh_mm = load_arm(hh_path, hh_names_path,
                               ("lidrel_facecoh", "detelev_facecoh", "hh_endpoint", "hh_bridge"))
    if not set(hd_names).issubset(set(hh_names)):
        raise SystemExit("H-H arm must contain the exact H-D face-coherence feature names")

    frozen = json.loads(FROZEN.read_text())
    frozen_ste = frozen["summary"]["ste"]
    frozen_by_fold = [float(v) for v in frozen_ste["per_fold"]]
    if len(frozen_by_fold) != 6 or not np.isclose(float(frozen_ste["mean"]), FROZEN_MEAN,
                                                   rtol=0.0, atol=1e-14):
        raise SystemExit("frozen baseline receipt does not match its pinned six-fold mean")
    footprint = np.load(P / "footprint.npy").astype(bool)
    catalogue = np.load(P / "catalogue.npy").astype(bool)
    folds = make_folds(footprint, catalogue, buffer_px=12, n_rows=3, n_cols=3, min_truth=500)
    if len(folds) != 6:
        raise SystemExit(f"expected the frozen six folds; found {len(folds)}")

    FIELD_DIR.mkdir(parents=True)
    receipt = dict(
        schema_version=1,
        id="GEMSDOE51-H53-A-BASELINE-PROVENANCE-20261008",
        status="IN_PROGRESS",
        scope="Baseline-only provenance and reproduction audit. No H53 candidate fields are fitted or compared.",
        frozen_receipt="evidence/hh_blend_holdout.json",
        frozen_receipt_sha256=sha256_file(FROZEN),
        frozen_field_paths="data/prepared/field_H_D_fold*.npy and field_H_H_fold*.npy (not present in this checkout)",
        canonical_protocol_source="scripts/run_experiments.py: default_rng(1000 + fold.index), fit_detector(seed=fold.index,max_iter=250), 250000 negatives",
        distinct_noncanonical_protocol="scripts/run_h52_holdout.py: h52_field_* caches use default_rng(2000 + fold.index); never substituted in this audit",
        fresh_field_cache_directory=str(FIELD_DIR.relative_to(ROOT)),
        config=dict(
            folds=6,
            buffer_px=12,
            negatives_per_fold=NEGATIVES,
            negative_rng_seed="1000 + fold.index",
            model_seed="fold.index",
            max_iter=250,
            blend="0.5 * H-D + 0.5 * H-H",
            emission="same evaluate_hh_blend.ste_emit implementation; STE L9, w=0.35, spacing=2.4 px",
            mass_ratio=3.47,
            exclusion_px=2.0,
            baseline_reproduction_tolerance=REPRO_TOLERANCE,
            frozen_mean=FROZEN_MEAN,
            frozen_per_fold=frozen_by_fold,
        ),
        data_and_feature_provenance=dict(
            prepared_manifest_sha256=sha256_file(P / "prepared_manifest.json"),
            base_stack_names_sha256=sha256_file(P / "stack_names.json"),
            hd_names=hd_names,
            hd_names_sha256=sha256_file(hd_names_path),
            hd_arm_memmap_sha256=sha256_file(hd_path),
            hh_names=hh_names,
            hh_names_sha256=sha256_file(hh_names_path),
            hh_arm_memmap_sha256=sha256_file(hh_path),
            official_training_raster_sha256=json.loads(
                (ROOT / "registry" / "data_manifest.json").read_text()
            )["files"][0]["sha256"],
            source_note="Input mirrors are integrity-pinned, but their login-walled competition provenance is owner-supplied, not organizer-authenticated.",
        ),
        versions=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            scipy=scipy.__version__,
            scikit_learn=sklearn.__version__,
        ),
        per_fold=[],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")

    stack = Stack(P)
    t0 = time.time()
    for fold in folds:
        extras_by_arm = {"HD": [hd_mm[i] for i in range(len(hd_names))],
                         "HH": [hh_mm[i] for i in range(len(hh_names))]}
        fields = {}
        for arm, extras in extras_by_arm.items():
            rng = np.random.default_rng(1000 + fold.index)
            X, y = stack.sample(fold.train_pos, fold.train_neg_pool,
                                NEGATIVES, rng, extra=extras)
            model = fit_detector(X, y, seed=fold.index, max_iter=250)
            del X, y
            field = predict_grid(model, stack, footprint, extra=extras)
            dest = FIELD_DIR / f"{arm}_fold{fold.index}.npy"
            np.save(dest, field)
            fields[arm] = field
            del model

        # This arithmetic blend and STE emitter match the frozen evaluation
        # entry point. The 2 px exclusion only constrains points at emission;
        # training features and source folds are unchanged.
        blend = (0.5 * fields["HD"] + 0.5 * fields["HH"]).astype(np.float32)
        del fields
        in_block = fold.block & footprint
        exclude = ndi.distance_transform_edt(~fold.known) <= 2.0
        allowed = in_block & ~exclude & np.isfinite(blend)
        n_target = int(round(3.47 * fold.n_truth))
        ys, xs = ste_emit(blend, allowed, n_target)
        prediction = np.zeros(GRID.shape, dtype=bool)
        prediction[ys, xs] = True
        score = dti_binary(prediction, fold.truth,
                           valid=footprint & fold.block, known=fold.known)
        value = float(score["dti"])
        receipt["per_fold"].append(dict(
            fold=int(fold.index),
            n_truth=int(fold.n_truth),
            n_target=n_target,
            dti=value,
            frozen_dti=frozen_by_fold[fold.index],
            delta_vs_frozen=float(value - frozen_by_fold[fold.index]),
            tp=float(score["tp"]),
            fp=float(score["fp"]),
            emitted=int(prediction.sum()),
            hd_field_sha256=sha256_file(FIELD_DIR / f"HD_fold{fold.index}.npy"),
            hh_field_sha256=sha256_file(FIELD_DIR / f"HH_fold{fold.index}.npy"),
        ))
        OUT.write_text(json.dumps(receipt, indent=1) + "\n")
        print(
            f"fold {fold.index}: fresh={value:.9f} frozen={frozen_by_fold[fold.index]:.9f} "
            f"delta={value - frozen_by_fold[fold.index]:+.9f} ({time.time() - t0:.0f}s)",
            flush=True,
        )
        del blend, prediction, ys, xs

    fresh = np.asarray([row["dti"] for row in receipt["per_fold"]], dtype=np.float64)
    delta = float(fresh.mean() - FROZEN_MEAN)
    receipt["summary"] = dict(
        fresh_mean_dti=float(fresh.mean()),
        frozen_mean_dti=FROZEN_MEAN,
        fresh_minus_frozen_mean=delta,
        max_abs_fold_delta=float(max(abs(r["delta_vs_frozen"]) for r in receipt["per_fold"])),
        mean_reproduction_tolerance=REPRO_TOLERANCE,
        reproduced=bool(abs(delta) <= REPRO_TOLERANCE),
        candidate_stage2_authorized=bool(abs(delta) <= REPRO_TOLERANCE),
    )
    receipt["status"] = ("BASELINE_REPRODUCED_STAGE2_MAY_PROCEED" if abs(delta) <= REPRO_TOLERANCE
                          else "BASELINE_REPRODUCTION_FAILED_STAGE2_BLOCKED")
    receipt["elapsed_seconds"] = float(time.time() - t0)
    receipt["limitations"] = [
        "A fresh fit can test the canonical protocol, but it cannot recover missing legacy field bytes or prove which command generated them.",
        "Any fresh-versus-frozen discrepancy is reported without assigning cause.",
        "The metric is a local visible-catalogue proxy, not a DrivenData score.",
    ]
    OUT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt["summary"], indent=1))
    print(f"status: {receipt['status']}; wrote {OUT}")
    return 0 if receipt["summary"]["reproduced"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
