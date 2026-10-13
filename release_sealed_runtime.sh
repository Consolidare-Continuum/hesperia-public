#!/usr/bin/env bash
# HESPERIA — Master command for the entire sealed runtime release flow.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: ./release_sealed_runtime.sh
# Runs: build_shipping.sh all → tools/run_release_gate.sh
# Prevents skipping the gate; simplifies documentation for evaluators.

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

export HESPERIA_VERSION="${HESPERIA_VERSION:-$(
python3 - <<'PY'
from pathlib import Path
import re
text = Path("VERSION.yaml").read_text(encoding="utf-8")
match = re.search(r'^\s*system_version:\s*"([^"]+)"', text, re.MULTILINE)
print(match.group(1) if match else "unknown")
PY
)}"

echo "=== Building sealed runtime artifacts ==="
./build_shipping.sh all

echo ""
echo "=== Running automated release gate ==="
./tools/run_release_gate.sh

echo ""
echo "SEALED RUNTIME BUILD COMPLETE"
echo "READY FOR MANUAL GATE"
echo ""
echo "Next: perform manual gate steps (clean machine, reflection audit, performance)."
echo "See docs/governance/SEALED_RUNTIME_RELEASE_PROCESS_v1.md"
