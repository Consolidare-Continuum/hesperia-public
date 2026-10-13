#!/usr/bin/env bash
# Mirror operator / automation tree (e.g. /data/workflows) next to Hesperia under /data/hesperia/workflows-mirror.
# Read-only rsync; does not modify source. See docs/governance/working/GENA-HESPERIA-APOCALYPTIC-ARCHIVE-TRIAGE-2026-03-28.md
#
# Usage:
#   export WORKFLOWS_SRC=/data/workflows   # required if default missing
#   ./tools/mirror_sister_workflows_into_hesperia_data.sh
#
# Optional:
#   HESPERIA_WORKFLOWS_MIRROR_DEST=/data/hesperia/workflows-mirror
set -euo pipefail

SRC="${WORKFLOWS_SRC:-/data/workflows}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_DEST="$(dirname "$REPO_ROOT")/workflows-mirror"
DEST="${HESPERIA_WORKFLOWS_MIRROR_DEST:-$DEFAULT_DEST}"

if [[ ! -d "$SRC" ]]; then
  echo "mirror_sister_workflows: SKIP — source not a directory: $SRC" >&2
  echo "Set WORKFLOWS_SRC to the real workflows root (e.g. on LAMAITA) and re-run." >&2
  exit 0
fi

mkdir -p "$DEST"
echo "mirror_sister_workflows: $SRC -> $DEST" >&2

rsync -a --delete \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='.venv/' \
  --exclude='.venv_*/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.cache/' \
  --exclude='dist/' \
  --exclude='build/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  "$SRC/" "$DEST/"

echo "mirror_sister_workflows: DONE $DEST" >&2
