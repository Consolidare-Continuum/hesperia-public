#!/usr/bin/env bash
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
# Wrapper: repo root on PYTHONPATH, then tools/run_dict_calibration_clearance.py
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
export PYTHONPATH="${REPO}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 tools/run_dict_calibration_clearance.py "$@"
