#!/usr/bin/env bash
# TFP-GATE-A0: deterministic env + version/calibration pin before wave or pytest release slice.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONHASHSEED=0
export PYTHONPATH=.
python3 tools/validate_version_consistency.py
echo "OK: TFP env precheck (PYTHONHASHSEED=0, version + calibration pack pin)."
