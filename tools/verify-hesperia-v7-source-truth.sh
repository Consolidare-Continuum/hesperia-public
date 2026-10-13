#!/usr/bin/env bash
# HSR-V7-A-11: Verify V7 source-of-truth on dev clone.
# Confirms: bridge code present, package pin documented, router tests pass.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0

echo "=== Hesperia V7 source-of-truth verify ==="
echo "Repo: $REPO_ROOT"
echo ""

# 1. Router bridge exists
if [ -f "$REPO_ROOT/sphere/router/thinking_map_bridge.py" ]; then
    echo "PASS  sphere/router/thinking_map_bridge.py exists"
else
    echo "FAIL  sphere/router/thinking_map_bridge.py missing"
    FAIL=1
fi

# 2. Router envelope exists
if [ -f "$REPO_ROOT/sphere/router/envelope_v0_1.py" ]; then
    echo "PASS  sphere/router/envelope_v0_1.py exists"
else
    echo "FAIL  sphere/router/envelope_v0_1.py missing"
    FAIL=1
fi

# 3. Router fingerprint exists
if [ -f "$REPO_ROOT/sphere/router/fingerprint.py" ]; then
    echo "PASS  sphere/router/fingerprint.py exists"
else
    echo "FAIL  sphere/router/fingerprint.py missing"
    FAIL=1
fi

# 4. JSON schema exists
if [ -f "$REPO_ROOT/assets/schemas/router/router_input_envelope_v0_1.schema.json" ]; then
    echo "PASS  router_input_envelope schema exists"
else
    echo "FAIL  router_input_envelope schema missing"
    FAIL=1
fi

# 5. Package pin documented
if [ -f "$REPO_ROOT/requirements/router.txt" ] && grep -q "fpf-thinking-map" "$REPO_ROOT/requirements/router.txt"; then
    PIN=$(grep "fpf-thinking-map" "$REPO_ROOT/requirements/router.txt")
    echo "PASS  fpf-thinking-map pin: $PIN"
else
    echo "FAIL  fpf-thinking-map not pinned in requirements/router.txt"
    FAIL=1
fi

# 6. VERSION.yaml reports current 0.6.5 system version
if grep -q 'system_version: "0.6.5"' "$REPO_ROOT/VERSION.yaml" 2>/dev/null; then
    echo "PASS  VERSION.yaml system version: 0.6.5"
else
    echo "FAIL  VERSION.yaml does not report 0.6.5"
    FAIL=1
fi

# 7. Router tests exist
if [ -d "$REPO_ROOT/tests/router" ]; then
    TEST_COUNT=$(find "$REPO_ROOT/tests/router" -name "test_*.py" | wc -l)
    echo "PASS  tests/router/ contains $TEST_COUNT test file(s)"
else
    echo "FAIL  tests/router/ directory missing"
    FAIL=1
fi

# 8. FPF-V7-13 calibration module (governed openai_calibrate_* path)
if [ -f "$REPO_ROOT/sphere/calibration/llm_calibration.py" ]; then
    echo "PASS  sphere/calibration/llm_calibration.py exists"
else
    echo "FAIL  sphere/calibration/llm_calibration.py missing"
    FAIL=1
fi

if [ -f "$REPO_ROOT/requirements/calibration.txt" ] && grep -q "fpf-thinking-map" "$REPO_ROOT/requirements/calibration.txt"; then
    echo "PASS  requirements/calibration.txt pins fpf-thinking-map"
else
    echo "FAIL  requirements/calibration.txt missing or unpinned"
    FAIL=1
fi

if [ -d "$REPO_ROOT/tests/calibration" ]; then
    echo "PASS  tests/calibration/ exists"
else
    echo "FAIL  tests/calibration/ missing"
    FAIL=1
fi

echo ""
if [ $FAIL -eq 0 ]; then
    echo "RESULT: ALL PASS — V7 source-of-truth verified"
else
    echo "RESULT: FAIL — source-of-truth issues found"
    exit 1
fi
