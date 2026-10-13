#!/usr/bin/env bash
# HESPERIA — Sync local hesperia-backup to two remotes: fulgusor /mnt/heimdall and /mnt/arc.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: ./tools/sync_backup_to_remotes.sh
# Credentials: yours (sudo no pass). Run from repo root.
# Requires: hesperia-backup/ already created by backup_hesperia_full.sh.

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${HESPERIA_BACKUP_ROOT:-$(dirname "$REPO_ROOT")/hesperia-backup}"
REMOTE="${HESPERIA_BACKUP_REMOTE:-fulgusor}"

if [[ ! -d "$BACKUP_ROOT" ]]; then
  echo "Run ./tools/backup_hesperia_full.sh first." >&2
  exit 1
fi

echo "Syncing $BACKUP_ROOT to $REMOTE (heimdall and arc)..."
rsync -avz --progress "$BACKUP_ROOT/" "$REMOTE:/mnt/heimdall/hesperia-backup/"
rsync -avz --progress "$BACKUP_ROOT/" "$REMOTE:/mnt/arc/hesperia-backup/"
echo "Done. Two copies: $REMOTE:/mnt/heimdall/hesperia-backup/ and $REMOTE:/mnt/arc/hesperia-backup/"
