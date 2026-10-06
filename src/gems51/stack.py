"""Build the analysis-ready feature stack (base layers + multi-scale lineament bank).

Design notes
------------
* Every layer is written float32 with NaN = "no data" at this pixel.  No layer is
  ever imputed with a global constant, because a constant is a value a model can
  learn to trust.
* Missing data inside a smoothing window is handled by **normalised convolution**
  (Knutsson & Westin 1993): convolve ``F*mask`` and ``mask`` separately and divide.
  This gives the local weighted least-squares estimate of the derivative instead
  of smearing zeros across data gaps.
* The lineament bank is a deliberate attempt to encode the *geometry* of a fault
  scarp -- a thin, continuous, anisotropic step -- rather than its amplitude,
  because the catalogue is biased towards high-amplitude scarps and we are
  looking for the ones it missed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems51.features import COMPETITION_BANDS, LIDAR_BANDS, RAD_BANDS  # noqa: E402
from gems51.grid import GRID  # noqa: E402

P = ROOT / "data" / "prepared"
H, W = GRID.shape

# ---------------------------------------------------------------- feature plan
COMP_NAMES = [b[0] for b in COMPETITION_BANDS]
LIDAR_USE = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
             "downface_max", "upface_max", "cross_max", "relief", "coh100"]
RAD_USE = ["K", "Th", "U", "TC"]
SGMC_USE = ["sgmc_fault"]

# (source array, index inside it, output name)
BASE_PLAN: list[tuple[str, int, str]] = []
for i, nm in enumerate(COMP_NAMES):
    BASE_PLAN.append(("comp", i, f"comp_{nm}"))
for nm in LIDAR_USE:
    BASE_PLAN.append(("lidar", LIDAR_BANDS.index(nm), f"lid_{nm}"))
for nm in RAD_USE:
    BASE_PLAN.append(("rad", RAD_BANDS.index(nm), f"rad_{nm}"))
BASE_PLAN.append(("sgmc", 0, "sgmc_fault"))

# lineament bank: (source array, index, label) x scales
LINE_FIELDS = [("comp", COMP_NAMES.index("det_elev"), "det_elev"),
               ("comp", COMP_NAMES.index("tmi"), "tmi"),
               ("comp", COMP_NAMES.index("iso_grav_anom"), "grav"),
               ("lidar", LIDAR_BANDS.index("relief"), "lid_relief")]
LINE_SCALES = [1.5, 4.0]
LINE_OPS = ["edge", "crest", "lin"]
MISC = ["d_cat", "cat_dens"]

NAMES: list[str] = ([n for _, _, n in BASE_PLAN]
                    + [f"{lab}_s{int(s*10):02d}_{op}" for _, _, lab in LINE_FIELDS
                       for s in LINE_SCALES for op in LINE_OPS]
                    + MISC)


# ---------------------------------------------------------------- utilities
def _nc_deriv(a: np.ndarray, mask: np.ndarray, sigma: float, order):
    """Normalised-convolution gaussian derivative."""
    a0 = np.where(mask, a, 0.0).astype(np.float32)
    num = ndi.gaussian_filter(a0, sigma, order=order, mode="nearest")
    den = ndi.gaussian_filter(mask.astype(np.float32), sigma, order=0, mode="nearest")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    out[den < 0.2] = np.nan
    return out.astype(np.float32)


def lineament_bank(a: np.ndarray, mask: np.ndarray, sigma: float):
    """Multi-scale geometric descriptors of a scalar field.

    Returns (edge, crest, lin):
      edge  -- |grad a| at scale sigma                       (a step is a steep place)
      crest -- max(0, -lambda_min(Hessian)) * sigma^2        (a ridge/crest is a thin high)
      lin   -- (lmax - lmin) / (|lmax| + |lmin|) in [0, 1]   (a fault is *anisotropic*:
                                                              curved across, flat along)
    """
    gx = _nc_deriv(a, mask, sigma, [0, 1])
    gy = _nc_deriv(a, mask, sigma, [1, 0])
    edge = np.hypot(gx, gy).astype(np.float32)

    fxx = _nc_deriv(a, mask, sigma, [0, 2])
    fyy = _nc_deriv(a, mask, sigma, [2, 0])
    fxy = _nc_deriv(a, mask, sigma, [1, 1])

    tr = fxx + fyy
    det = fxx * fyy - fxy * fxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    lmax = tr / 2.0 + disc
    lmin = tr / 2.0 - disc

    crest = np.maximum(0.0, -lmin) * float(sigma) ** 2
    lin = (lmax - lmin) / (np.abs(lmax) + np.abs(lmin) + 1e-9)
    lin = np.clip(lin, 0.0, 1.0).astype(np.float32)
    return edge.astype(np.float32), crest.astype(np.float32), lin


# ---------------------------------------------------------------- builder
def build(chunk: int = 256, halo: int = 24) -> Path:
    footprint = np.load(P / "footprint.npy")
    catalogue = np.load(P / "catalogue.npy")

    src = {}
    src["comp"] = np.memmap(P / "comp_rank.dat", dtype=np.float32, mode="r",
                            shape=(len(COMP_NAMES), H, W))
    src["lidar"] = np.memmap(P / "lidar_raw.dat", dtype=np.float32, mode="r",
                             shape=(len(LIDAR_BANDS), H, W))
    src["rad"] = np.memmap(P / "rad_raw.dat", dtype=np.float32, mode="r",
                           shape=(len(RAD_BANDS), H, W))
    src["sgmc"] = np.memmap(P / "sgmc_raw.dat", dtype=np.float32, mode="r", shape=(1, H, W))

    # global, scale-free context features
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    cat_dens = ndi.uniform_filter(catalogue.astype(np.float32), size=21, mode="constant")

    out_path = P / "stack.dat"
    mm = np.memmap(out_path, dtype=np.float32, mode="w+", shape=(len(NAMES), H, W))
    mm[:] = np.nan

    n_base = len(BASE_PLAN)
    for r0 in range(0, H, chunk):
        r1 = min(r0 + chunk, H)
        a0, a1 = max(0, r0 - halo), min(H, r1 + halo)
        sl = slice(a0, a1)
        cut = slice(r0 - a0, r1 - a0)
        fp_blk = footprint[sl]

        # ---- base layers -------------------------------------------------
        for k, (tag, idx, nm) in enumerate(BASE_PLAN):
            blk = np.asarray(src[tag][idx][sl], dtype=np.float32)
            mm[k, r0:r1, :] = blk[cut]

        # ---- lineament bank ----------------------------------------------
        k = n_base
        for tag, idx, lab in LINE_FIELDS:
            blk = np.asarray(src[tag][idx][sl], dtype=np.float32)
            m = np.isfinite(blk) & fp_blk
            for s in LINE_SCALES:
                edge, crest, lin = lineament_bank(blk, m, s)
                for arr in (edge, crest, lin):
                    arr[~fp_blk] = np.nan
                    mm[k, r0:r1, :] = arr[cut]
                    k += 1

        # ---- context ------------------------------------------------------
        mm[k, r0:r1, :] = np.log1p(d_cat[sl][cut])          # d_cat
        mm[k + 1, r0:r1, :] = cat_dens[sl][cut] * (21 ** 2)  # cat_dens (px of fault in 2.1 km)
        print(f"  rows {r0:5d}-{r1:5d}", flush=True)

    mm.flush()
    del mm
    (P / "stack_names.json").write_text(json.dumps(NAMES, indent=1))
    print(f"wrote {P/'stack.dat'}  features={len(NAMES)}")
    return P / "stack.dat"


if __name__ == "__main__":
    build()
