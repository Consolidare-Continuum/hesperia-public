#!/usr/bin/env bash
# 0.6.3 archive E2E — no prod dicts/corpus required.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
export HESPERIA_DICT_CALIB_OFFLINE=1
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
PY="${PY:-$REPO/.venv/bin/python}"
[[ -x "$PY" ]] || PY=python3
FAIL=0
echo "=== Hesperia 0.6.3 archive E2E gate ==="
if "$PY" -m pytest tests/test_archive_063_e2e_gate.py tests/test_engine_api_v1.py \
    tests/test_e2e_flows.py::test_e2e_analyze_sentence_output_exists -q --tb=short; then
  echo "[PASS] pytest archive subset"
else
  echo "[FAIL] pytest archive subset"
  FAIL=1
fi
if "$PY" -m tools.system_seal.run_system_seal; then
  echo "[PASS] system_seal"
else
  echo "[FAIL] system_seal"
  FAIL=1
fi
if grep -q '"version": "0.6.3"' release/v0.6.3/system_seal.json 2>/dev/null; then
  echo "[PASS] seal version 0.6.3"
else
  echo "[FAIL] seal version mismatch"
  FAIL=1
fi
# Archive must not list prod dict dirs as required
for forbidden in assets/calibration/dicts/v0_6_0_clr_v052_2; do
  if [[ -d "$forbidden" ]] && ! grep -q "$forbidden" release/v0.6.3/packaging_exclude.txt; then
    echo "[WARN] prod dict present on disk but excluded from archive manifest"
  fi
done
echo "=============================================="
if [[ $FAIL -eq 0 ]]; then
  echo "HESPERIA 0.6.3 ARCHIVE E2E: PASS"
  exit 0
fi
echo "HESPERIA 0.6.3 ARCHIVE E2E: FAIL"
exit 1
