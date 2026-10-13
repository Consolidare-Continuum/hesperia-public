#!/usr/bin/env bash
# TFP-GATE-A4: compare checksums of calibration dict files under module mirror vs assets (when mirror exists).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CALIB="${HESPERIA_CALIB_DICT_VERSION:-v0_6_0_clr_v052_2}"
SRC="$ROOT/assets/calibration/dicts/$CALIB"
DST="$ROOT/hesperia/modules/tfp/data/dicts/calibration/$CALIB"
if [[ ! -d "$SRC" ]]; then
  echo "SKIP: no $SRC"
  exit 0
fi
if [[ ! -d "$DST" ]]; then
  echo "SKIP: mirror missing (run tools/sync_tfp_module_data.sh): $DST"
  exit 0
fi
for f in dict_a.jsonl dict_b.jsonl links.jsonl metrics.json; do
  if [[ -f "$SRC/$f" && -f "$DST/$f" ]]; then
    S=$(sha256sum "$SRC/$f" | awk '{print $1}')
    D=$(sha256sum "$DST/$f" | awk '{print $1}')
    if [[ "$S" != "$D" ]]; then
      echo "FAIL: checksum mismatch $f (assets vs module mirror). Re-run sync_tfp_module_data.sh"
      exit 1
    fi
  fi
done
echo "OK: calibration mirror matches assets for $CALIB (checked dict_a, dict_b, links, metrics if present)."
