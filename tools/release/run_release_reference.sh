#!/usr/bin/env bash
# HESPERIA — Task 6: canonical release reference command (repo root).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage:
#   ./tools/release/run_release_reference.sh
#   HESPERIA_RELEASE_BUILD_TIMESTAMP=2026-03-19T12:00:00Z ./tools/release/run_release_reference.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export HESPERIA_RELEASE_BUILD_TIMESTAMP="${HESPERIA_RELEASE_BUILD_TIMESTAMP:-}"
exec python3 tools/release/build_release_audit_v0_5_0.py "$@"
