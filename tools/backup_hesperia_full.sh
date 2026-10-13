#!/usr/bin/env bash
# HESPERIA — Full raw backup before any cleanup. Creates mirror + working-tree snapshot.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: from repo root, run: ./tools/backup_hesperia_full.sh
# Then sync to remotes (see below or run tools/sync_backup_to_remotes.sh).
#
# Produces:
#   hesperia-backup/
#   ├── git-mirror/
#   │   └── hesperia_backup.git
#   └── snapshots/
#       └── hesperia_full_repo_snapshot_YYYYMMDD.tar.gz

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Backup root: sibling of repo (so tar does not include backup)
BACKUP_ROOT="${HESPERIA_BACKUP_ROOT:-$(dirname "$REPO_ROOT")/hesperia-backup}"
mkdir -p "$BACKUP_ROOT/git-mirror" "$BACKUP_ROOT/snapshots"

REPO_URL="$(git remote get-url origin 2>/dev/null || true)"
if [[ -z "$REPO_URL" ]]; then
  echo "No git origin. Creating mirror from local repo."
  git clone --mirror "$REPO_ROOT" "$BACKUP_ROOT/git-mirror/hesperia_backup.git"
else
  echo "Mirroring from origin: $REPO_URL"
  git clone --mirror "$REPO_URL" "$BACKUP_ROOT/git-mirror/hesperia_backup.git"
fi

SNAPSHOT_NAME="hesperia_full_repo_snapshot_$(date +%Y%m%d).tar.gz"
SNAPSHOT_PATH="$BACKUP_ROOT/snapshots/$SNAPSHOT_NAME"
echo "Creating working-tree snapshot (exact state, includes .git): $SNAPSHOT_PATH"
tar -czf "$SNAPSHOT_PATH" \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='*.pyc' \
  --exclude='.venv' \
  --exclude='.venv_v040*' \
  -C "$REPO_ROOT" .

echo "Backup complete: $BACKUP_ROOT"
echo "  git-mirror:  $BACKUP_ROOT/git-mirror/hesperia_backup.git"
echo "  snapshot:    $SNAPSHOT_PATH"
echo ""
echo "Sync to fulgusor (two copies). Run with your credentials:"
echo "  ./tools/sync_backup_to_remotes.sh"
echo "Or manually:"
echo "  rsync -avz --progress '$BACKUP_ROOT/' fulgusor:/mnt/heimdall/hesperia-backup/"
echo "  rsync -avz --progress '$BACKUP_ROOT/' fulgusor:/mnt/arc/hesperia-backup/"
