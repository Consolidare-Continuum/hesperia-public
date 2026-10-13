#!/usr/bin/env bash
# Chain dict/calibration validators for release hygiene (Ethan / Liam).
# Copyright © 2026 igareosh.com.
#
# Usage: from Hesperia repo root: ./tools/run_dict_release_gates.sh
# - Always: tools/validate_version_consistency.py
# - If sealed dict_a present: full B+CD wave (same as CI conditional)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== [1/2] Version consistency ==="
python3 tools/validate_version_consistency.py

CALIB="${HESPERIA_CALIB_DICT_VERSION:-v0_6_0_clr_v052_2}"
DICT_A="$ROOT/assets/calibration/dicts/$CALIB/dict_a.jsonl"
echo "=== [2/2] Dict B + CD wave (dict_a=$DICT_A) ==="
if [[ -f "$DICT_A" ]]; then
  bash tools/run_b_cd_wave_after_a.sh
else
  echo "[SKIP] dict_a.jsonl not in tree — wave skipped (mirror CI sealed-runtime-gate pattern)."
fi
echo "=== run_dict_release_gates: finished ==="
