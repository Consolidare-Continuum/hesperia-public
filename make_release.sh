#!/usr/bin/env bash
set -e

export HESPERIA_VERSION="$(
python3 - <<'PY'
from pathlib import Path
import re
text = Path("VERSION.yaml").read_text(encoding="utf-8")
match = re.search(r'^\s*system_version:\s*"([^"]+)"', text, re.MULTILINE)
print(match.group(1) if match else "unknown")
PY
)"

echo "[1/4] Running tests"
python3 -m pytest tests/ -q --tb=no

echo "[2/4] Building shipping artifacts"
bash ./build_shipping.sh all

echo "[3/4] Validating version consistency"
python3 tools/validate_version_consistency.py

echo "[4/4] Building portable release bundle (zip)"
python3 tools/build_release_bundle.py

echo "[5/5] Verifying bundle integrity + determinism"
python3 tools/verify_release_bundle.py

echo "[OK] Release v${HESPERIA_VERSION} ready"
