"""Two conventions for what happens to a prediction that lands on a *published*
(USGS/INGENIOUS) fault pixel — and why the conservative one governs our design.

The official metric is published as

    DTI = TP_w / ( TP_w + a*FP_w + b*FN_w + eps ),   a = 0.2, b = 0.8
with a triangular credit kernel k(d) = max(1 - d/300 m, 0) and a FAQ statement
that known USGS/INGENIOUS fault pixels are "excluded from evaluation"
(DrivenData staff, chrisk-dd, 2026-09-16):
https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516

That statement admits two readings, and they differ in what a competitor should do:

Reading A ("mass removed"):  the published-fault pixels are removed from the
    scored domain for *both* truth and prediction mass.  Then a dot on a
    published fault is simply deleted and costs nothing.  ``gems51.metric``
    implements this reading (``p = np.where(active, pred, 0.0)``).

Reading B ("zero credit, still counted"):  the published-fault pixels are
    removed from the *truth* set only.  A submitted unit of mass there can never
    earn credit (there is no truth pixel within the kernel to credit it) but it
    is still counted in the prediction-mass / false-positive term, at the full
    triangular penalty (1 - max_g k) = 1 when no hidden truth pixel is nearby.

These differ by up to ``a`` per unit of on-catalogue mass, and reading B makes
on-catalogue dots actively harmful to the score.

**Which reading is the live one?**  The sibling GEMSDOE32 repository records a
two-file live experiment that isolates exactly this mechanism
(retrieved 2026-10-07 from
https://github.com/buffedlizard55-lab/GEMSDOE32, README "Round 4"):

  * ``h27-4-r1-solo-d2-8-...-nan.tif``  — 40,199 dots — owner-reported live 0.2708
  * ``GEMS28-H27-4-R1-SOLO-D2.8``       — 44,090 dots — owner-reported live 0.2600

The published ``existing_faults.tif`` is byte-identical to ``labels.tif``
(sha256 ``7ba308ccdc44...``), so the only difference between those two files is
the removal of the 3,891 dots lying within 100 m of the published catalogue.
Removing them *raised* the live score by +0.0108.  Under reading A that removal
is score-neutral by construction.  It is therefore reading B that the live
scorer uses, and the same repository measures the consequence directly as a 47 %
drop of its calibrated proxy when a single dot is placed on a mapped fault
(``IR-32-INSTR-01``, README "New this session").

Both facts are *owner reports about a live score*, not organizer documentation.
They are used here as design evidence of the stated strength and are labelled as
such — the local numbers in this repository are computed under both readings so
that the consequence of the ambiguity is always visible.

This module implements reading B.  ``dti_binary_live`` is a drop-in companion to
``gems51.metric.dti_binary`` and shares its convention for everything else:
``valid`` = the scored footprint, ``known`` = published catalogue (truth-excluded),
``truth`` = the hidden/new fault set.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

from .metric import ALPHA, BETA, EPS, RADIUS_PX, kernel


def dti_binary_live(pred_bool: np.ndarray, truth: np.ndarray,
                    valid: np.ndarray | None = None, known: np.ndarray | None = None,
                    alpha: float = ALPHA, beta: float = BETA,
                    radius: float = RADIUS_PX) -> dict:
    """DTI under reading B: prediction mass on published faults is counted as FP.

    ``pred_bool``  predicted pixels (bool); mass 1.0 per True.
    ``truth``      hidden/new fault pixels (bool).
    ``valid``      scored footprint (bool); outside it nothing is counted.
    ``known``      published USGS/INGENIOUS fault pixels (bool).

    Difference from ``metric.dti_binary``: there, ``p = pb & active`` with
    ``active = valid & ~known`` (reading A, on-catalogue mass deleted).  Here
    ``p = pb & valid`` (reading B, on-catalogue mass kept and penalised).

    Returns the same keys as ``metric.dti_binary`` plus ``fp_on_known`` and
    ``mass_on_known`` so the penalty is auditable.
    """
    pb = np.asarray(pred_bool, bool)
    truth = np.asarray(truth, bool)
    valid_ = np.ones(pb.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pb.shape, bool) if known is None else np.asarray(known, bool)
    if pb.shape != truth.shape or valid_.shape != pb.shape or known_.shape != pb.shape:
        raise ValueError("pred, truth, valid and known must share one shape")

    p = pb & valid_                      # reading B: no removal at known pixels
    g = truth & valid_ & ~known_         # truth excludes the published catalogue
    n = int(g.sum())
    mass_on_known = float((pb & valid_ & known_).sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0,
                    coverage=0.0, mass=float(p.sum()), fp_on_known=float(mass_on_known),
                    mass_on_known=mass_on_known)
    if not p.any():
        return dict(tp=0.0, fp=0.0, fn=float(n), n_truth=n, dti=0.0, coverage=0.0,
                    mass=0.0, fp_on_known=0.0, mass_on_known=0.0)

    dp = distance_transform_edt(~p)
    tp = float(kernel(dp[g], radius).sum())
    fn = float(n) - tp
    dg = distance_transform_edt(~g)
    fp = float((1.0 - kernel(dg[p], radius)).sum())
    fp_on_known = float((1.0 - kernel(dg[p & known_], radius)).sum()) if mass_on_known else 0.0
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n,
                dti=float(tp / (tp + alpha * fp + beta * fn + EPS)),
                coverage=tp / n, mass=float(p.sum()),
                fp_on_known=fp_on_known, mass_on_known=mass_on_known)


def on_catalogue_mass(pred_bool: np.ndarray, known: np.ndarray,
                      valid: np.ndarray | None = None) -> dict:
    """How much submitted mass sits on published-fault pixels (a design gate)."""
    pb = np.asarray(pred_bool, bool)
    kn = np.asarray(known, bool)
    vd = np.ones(pb.shape, bool) if valid is None else np.asarray(valid, bool)
    total = int((pb & vd).sum())
    on = int((pb & vd & kn).sum())
    return dict(predicted_px=total, on_catalogue_px=on,
                on_catalogue_fraction=(on / total) if total else 0.0)
