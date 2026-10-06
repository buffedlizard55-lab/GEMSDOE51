#!/usr/bin/env bash
# Place the four competition rasters into data/, then verify them.
#
# The DrivenData data page is login-walled: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
# From the sandbox this session ran in, drivendata.org returns HTTP 000, so the files were
# obtained from the group's own integrity-pinned mirrors instead (IR-51-02) and checked against
# the published SHA-256 pins by `scripts/prepare_data.py`.
#
# Run this on any machine that CAN reach DrivenData, and it will place the files where the
# pipeline expects them:
#
#   bash scripts/download_competition_data.sh
#   GEMS_DATA_DIR=data PYTHONPATH=src python3 scripts/prepare_data.py
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${GEMS_DATA_DIR:-$ROOT/data}"
mkdir -p "$DEST"

cat <<'MSG'
This script does NOT download automatically, by design: the competition data page requires
authentication and the competition terms govern redistribution. Download these four files
into the directory below, then re-run scripts/prepare_data.py to verify the SHA-256 pins.

  training_features.tif   -> 19-band float32 feature stack (EPSG:32611, 100 m, 3730x3292)
  labels.tif              -> USGS/INGENIOUS fault labels (NOTE: byte-identical to existing_faults.tif)
  existing_faults.tif     -> USGS/INGENIOUS fault labels
  sample_submission.tif   -> the sample submission (IS the catalogue rasterised; used as the grid template)

Expected SHA-256:
  training_features.tif   4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5
  labels.tif              7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
  existing_faults.tif     7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
  sample_submission.tif   2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc

Source (requires login): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
MSG
echo "destination: $DEST"
ls -la "$DEST" || true
