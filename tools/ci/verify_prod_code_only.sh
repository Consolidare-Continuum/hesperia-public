#!/usr/bin/env bash
# Verify Hesperia prod: immaculate — no dev notes; corpus/session .md only under allowlist.
# Policy: governance/ETHAN-POLICY-HESPERIA-DEV-PROD-CONTENT.md
set -euo pipefail

ROOT="${1:-/data/hesperia/hesperia}"
MODE="${2:-repo}"
if [[ ! -d "$ROOT" ]]; then
  echo "FAIL: not a directory: $ROOT" >&2
  exit 1
fi

STAGED_ROOT=""
cleanup() {
  [[ -n "$STAGED_ROOT" && -d "$STAGED_ROOT" ]] && rm -rf "$STAGED_ROOT"
}
trap cleanup EXIT

if [[ "$MODE" == "--shipping-context" ]]; then
  STAGED_ROOT="$(mktemp -d)"
  (
    cd "$ROOT"
    tar -cf - \
      --exclude-from=.dockerignore.shipping \
      runtime core hesperia assets requirements requirements.txt Dockerfile.shipping
  ) | tar -xf - -C "$STAGED_ROOT"
  ROOT="$STAGED_ROOT"
fi

cd "$ROOT"
FAIL=0

is_allowed_md() {
  local f="${1#./}"
  case "$f" in
    README.md|LEGAL_NOTICE.md|DEV-READY-LINE-2026-05-18.md) return 0 ;;
    tests/fixtures/dict_calibration/corpus/sample.md) return 0 ;;
    hesperia/modules/tfp/data/corpus/*) return 0 ;;
    hesperia/modules/tfp/data/tfp_v1/corpus/*) return 0 ;;
    hesperia/modules/tfp/data/tfp_v1/inspector_exports/*) return 0 ;;
    hesperia/modules/tfp/data/*/corpus/*) return 0 ;;
  esac
  return 1
}

check_path() {
  [[ -e "$1" ]] || return 0
  echo "FORBIDDEN: $1"
  FAIL=1
}

for p in .cursor docs _release_tmp legacy AGENTS.md ROLLBACK-LINE-2026-05-18.md \
  task_gena_v0_6_0.md REPO_STRUCTURE_POLICY.md GENERATED_ARTIFACT_POLICY.md; do
  check_path "$p"
done

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  is_allowed_md "$f" && continue
  echo "FORBIDDEN: $f"
  FAIL=1
done < <(find . -name '*.md' ! -path './.git/*' ! -path './.pytest_cache/*' 2>/dev/null)

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  echo "FORBIDDEN: $f"
  FAIL=1
done < <(find assets/specs -name '*.md' -type f 2>/dev/null)

if [[ -f README.md ]]; then
  lines=$(wc -l <README.md 2>/dev/null || echo 0)
  if [[ "$lines" -gt 15 ]]; then
    echo "FORBIDDEN: README.md too long ($lines lines)"
    FAIL=1
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "verify-hesperia-prod-code-only: FAIL ($ROOT)"
  exit 1
fi

echo "verify-hesperia-prod-code-only: OK ($ROOT)"
exit 0
