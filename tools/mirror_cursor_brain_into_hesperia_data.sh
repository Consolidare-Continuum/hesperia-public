#!/usr/bin/env bash
# Mirror Cursor brain repo (default /data/workspaces/cursor) next to Hesperia under
# /data/hesperia/cursor-brain-mirror/. Read-only rsync; does not modify source.
# See operational/assignments/GRACE-HESPERIA-DATA-ROOT-COMPLETE-2026-03-28.md (cursor repo).
#
# Usage:
#   export CURSOR_BRAIN_SRC=/data/workspaces/cursor   # default if unset
#   ./tools/mirror_cursor_brain_into_hesperia_data.sh
#
# Optional:
#   HESPERIA_CURSOR_BRAIN_MIRROR_DEST=/data/hesperia/cursor-brain-mirror
set -euo pipefail

SRC="${CURSOR_BRAIN_SRC:-/data/workspaces/cursor}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_DEST="$(dirname "$REPO_ROOT")/cursor-brain-mirror"
DEST="${HESPERIA_CURSOR_BRAIN_MIRROR_DEST:-$DEFAULT_DEST}"

if [[ ! -d "$SRC" ]]; then
  echo "mirror_cursor_brain: SKIP — source not a directory: $SRC" >&2
  echo "Set CURSOR_BRAIN_SRC to the Cursor repo root and re-run." >&2
  exit 0
fi

mkdir -p "$DEST"
echo "mirror_cursor_brain: $SRC -> $DEST" >&2

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

echo "mirror_cursor_brain: DONE $DEST" >&2
