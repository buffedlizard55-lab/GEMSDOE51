#!/usr/bin/env bash
# Fetch the family-submission reference set for the uniqueness gate.
#
# Why: the brief requires a UNIQUE submission, and the gate
# (scripts/run_uniqueness_gate.py) proves it by comparing the candidate against
# every prior family artifact it can hold.  The previous session ran the gate on
# the owner's workstation against 211 references under /home/user/study; this
# sandbox does not have them, so we rebuild the reference set from the family's
# own public GitHub mirrors (GEMSDOE24 and GEMSDOE32 docs/downloads +
# inputs/calibration), pinned here by repo@ref:path.
#
# Regenerable -> gitignored (see .gitignore); the gate's OUTPUT stays in git.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/refs

fetch() { # repo ref path dest
  local repo="$1" ref="$2" path="$3" dest="$4"
  if [[ -f "$dest" ]]; then echo "cached  $dest"; return 0; fi
  echo "fetch   $repo:$path"
  gh api "repos/$repo/contents/$path?ref=$ref" -H "Accept: application/vnd.github.raw" > "$dest.tmp"
  mv "$dest.tmp" "$dest"
}

G24=buffedlizard55-lab/GEMSDOE24
R24=07345ea0604953d7efb858d9cfbc21e20c7aca0b
G32=buffedlizard55-lab/GEMSDOE32
R32=b983924b57781edd29b8e249c4923bf33d9902f6

# ---- GEMSDOE24: earlier families + calibration artifacts -------------------
fetch $G24 $R24 "inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif"                 data/refs/gemsdoe9-2314b599.tif
fetch $G24 $R24 "inputs/calibration/gemsdoe-ens12-adopted-7f00890a.tif"                 data/refs/gemsdoe-ens12-7f00890a.tif
fetch $G24 $R24 "inputs/calibration/8GEMSDOE_Hedge-v2_submission.tif"                   data/refs/8gemsdoe-hedge-v2.tif
fetch $G24 $R24 "inputs/calibration/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif" data/refs/gems10-h28-dotted-ridge.tif
fetch $G24 $R24 "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"  data/refs/13gems-r13-lattice-nan.tif
fetch $G24 $R24 "inputs/calibration/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif" data/refs/gems10-h25-ctx-ridge.tif
fetch $G24 $R24 "inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif" data/refs/gems19-h19-5-powerlaw-allfinite.tif
fetch $G24 $R24 "inputs/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-allfinite.tif" data/refs/gems19-h19-4-thermalpop-allfinite.tif
fetch $G24 $R24 "inputs/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif" data/refs/gems16-h16-1-baseline-nan.tif
fetch $G24 $R24 "docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-allfinite.tif" data/refs/gems24-dotted-d2-8-allfinite.tif
fetch $G24 $R24 "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif" data/refs/gems24-dotted-d1-5-allfinite.tif

# ---- GEMSDOE32: the 0.2778 family and its ablations -------------------------
fetch $G32 $R32 "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif" data/refs/gems25-dotted-d2-8-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif" data/refs/gemsdoe32-h33-2-b2-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h33-h33-2b2-plus-h33-1-20261004T220000Z-31588dc7-zeros.tif" data/refs/gemsdoe32-h33-2b2-plus-h33-1-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-d28-ref02600-repro-44090-20261004T183200Z-426073b6-zeros.tif" data/refs/gemsdoe32-d28-ref02600-repro-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h32a-dip-projected-step-46090-20261004T183200Z-838fcd84-zeros.tif" data/refs/gemsdoe32-h32a-dipstep-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h32b-transtensional-swarm-45890-20261004T183200Z-27b7c9e6-zeros.tif" data/refs/gemsdoe32-h32b-swarm-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h32c-mt-claycap-breach-45890-20261004T183200Z-a5963d0a-zeros.tif" data/refs/gemsdoe32-h32c-claycap-zeros.tif
fetch $G32 $R32 "docs/downloads/gemsdoe32-h32d-submodular-multipysics-46090-20261004T183200Z-4de30601-zeros.tif" data/refs/gemsdoe32-h32d-submodular-zeros.tif
fetch $G32 $R32 "docs/downloads/gems32-bayesopt-dilation-scarp-d28-20261004-zeros.tif" data/refs/gems32-bayesopt-dilation-zeros.tif
fetch $G32 $R32 "docs/downloads/gems32-probe-S1-ANCHOR-identical-to-live-02600.tif" data/refs/gems32-probe-S1-anchor.tif

echo "OK: $(ls data/refs | wc -l) references in data/refs/"
