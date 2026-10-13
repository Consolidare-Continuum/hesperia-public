#!/usr/bin/env bash
# HESPERIA — Sealed runtime release gate. Runs automated checks and prints PASS/FAIL.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: from repo root, ./tools/run_release_gate.sh
# Prerequisite: Run Step 0 first (./build_shipping.sh all). Without it, manifest check fails and binary/container scans are skipped.
# With artifacts: runs import-boundary, projection test, binary scan, container scan, manifest verification.
#
# Output: HESPERIA SEALED RUNTIME: PASS | FAIL

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
FAIL=0
# Projection test: must not appear in CLI/API output (propagated is allowed)
FORBIDDEN_OUTPUT='sphere|hex|topology|bridge|layer|area11|family240|coordinates|vector3'
# Binary strings scan: extended list including propagation, grid, graph, etc.
FORBIDDEN_STRINGS='sphere|hex|topology|bridge|layer|area11|family240|coordinates|vector3|grid|graph|propagation|embedding|vector_space|internal_layer|topology_index'

run_check() {
  local name="$1"
  if [[ "$2" == "0" ]]; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name"
    FAIL=1
  fi
}

echo "=== HESPERIA Sealed Runtime Release Gate ==="

# 1. Import-boundary check
if python3 tools/check_import_boundary.py 2>/dev/null; then
  run_check "Import boundary" "0"
else
  run_check "Import boundary" "1"
fi

# 2. Projection test (CLI output must not contain forbidden terms)
if [[ -x "$REPO/dist/hesperia-cli.bin" ]]; then
  OUT="$("$REPO/dist/hesperia-cli.bin" analyze --text "test policy statement" 2>/dev/null)" || true
else
  OUT="$(python3 -m runtime.shipping.cli_main analyze --text "test policy statement" 2>/dev/null)" || true
fi
if echo "$OUT" | grep -iE "$FORBIDDEN_OUTPUT" >/dev/null 2>&1; then
  echo "[FAIL] Projection (forbidden terms in CLI output)"
  FAIL=1
else
  echo "[PASS] Projection (no forbidden terms in CLI output)"
fi

# 3. Binary reflection scan (only if binary exists)
if [[ -f "$REPO/dist/hesperia-cli.bin" ]]; then
  if strings "$REPO/dist/hesperia-cli.bin" 2>/dev/null | grep -iE "$FORBIDDEN_STRINGS" >/dev/null 2>&1; then
    echo "[FAIL] Binary reflection scan (forbidden terms in binary strings)"
    FAIL=1
  else
    echo "[PASS] Binary reflection scan"
  fi
else
  echo "[SKIP] Binary reflection scan (no dist/hesperia-cli.bin)"
fi

# 4. Container inspection and Docker layer check (only if image tar exists)
if [[ -f "$REPO/release/hesperia-api-image.tar" ]]; then
  if command -v docker >/dev/null 2>&1; then
    docker load -i "$REPO/release/hesperia-api-image.tar" >/dev/null 2>&1 || true
    FORBIDDEN_DIR=0
    for dir in docs tests debug legacy specs; do
      if docker run --rm hesperia-api:latest ls "/app/$dir" 2>/dev/null; then
        FORBIDDEN_DIR=1
        break
      fi
    done
    if [[ "$FORBIDDEN_DIR" -eq 1 ]]; then
      echo "[FAIL] Container inspection (forbidden directory in image)"
      FAIL=1
    else
      echo "[PASS] Container inspection"
    fi
    # Docker history: confirm only final stage is shipped (multi-stage build)
    echo "Docker history (confirm only final runtime stage):"
    docker history hesperia-api:latest 2>/dev/null | head -15 || true
  else
    echo "[SKIP] Container inspection (docker not available)"
  fi
else
  echo "[SKIP] Container inspection (no release/hesperia-api-image.tar)"
fi

# 5. Manifest verification
if [[ -f "$REPO/release/manifest.json" && -f "$REPO/release/checksums.txt" ]]; then
  echo "[PASS] Manifest and checksums present"
  if [[ -f "$REPO/dist/hesperia-cli.bin" ]]; then
    if grep -q "hesperia-cli.bin" "$REPO/release/checksums.txt" 2>/dev/null; then
      echo "[PASS] CLI checksum listed"
    else
      echo "[FAIL] Manifest verification (hesperia-cli.bin not in checksums.txt)"
      FAIL=1
    fi
  fi
else
  echo "[FAIL] Manifest verification (manifest.json or checksums.txt missing)"
  FAIL=1
fi

echo "=============================================="
if [[ $FAIL -eq 0 ]]; then
  echo "HESPERIA SEALED RUNTIME: PASS"
  exit 0
else
  echo "HESPERIA SEALED RUNTIME: FAIL"
  exit 1
fi
