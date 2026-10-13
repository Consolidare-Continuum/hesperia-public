#!/usr/bin/env bash
# HESPERIA — Full encompassing E2E (Gena + Ethan stack + product + physics + system seal + manifest).
# Runs: run_e2e_all (dynamics env set by Python) + product surface JSON + tests.physics_validation +
#       system_seal (skips duplicate physics pytest when validation passed) → run_output_e2e_full_stack_manifest.json
# Usage: ./tools/e2e_full_deliverables.sh [OUT_DIR] ["session text..."]
# Fast iteration (no physics / seal): HESPERIA_E2E_FULL_DELIVERABLES_FAST=1 ./tools/e2e_full_deliverables.sh ...
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${1:-assets/artifacts/e2e_full_deliverables}"
shift || true
TEXT="${*:-Patient reports severe anxiety when considering work deadlines but also feels guilty resting. The team demands faster delivery while quality must not slip. Internal conflict between autonomy and compliance.}"
EXTRA=()
if [[ "${HESPERIA_E2E_FULL_DELIVERABLES_FAST:-}" == "1" ]]; then
  EXTRA+=(--skip-physics --skip-seal --no-dynamics)
fi
python3 -m runtime.pipeline.run_e2e_full_stack --out-dir "$OUT" --text "$TEXT" "${EXTRA[@]}"
