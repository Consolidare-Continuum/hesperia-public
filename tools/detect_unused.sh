#!/usr/bin/env bash
# HESPERIA — Detect unused or orphan files for cleanup review.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: from repo root, ./tools/detect_unused.sh
# Runs: vulture (unused Python), large files, old-script patterns.
# Does not delete; use output to decide what to move to legacy/.

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "=== 1. Unreferenced Python (vulture) ==="
if command -v vulture &>/dev/null; then
  vulture . --min-confidence 80 2>/dev/null || true
else
  echo "Install with: pip install vulture"
fi

echo ""
echo "=== 2. Largest tracked files (top 30) ==="
git ls-files | xargs du -h 2>/dev/null | sort -rh | head -30

echo ""
echo "=== 3. Old/junk script patterns (run_*, *_old, *_backup, debug_*) ==="
git ls-files -- '*.py' | while read -r f; do
  case "$f" in
    *run_*.py|*_old.py|*_backup.py|*debug_*.py) echo "$f" ;;
  esac
done

echo ""
echo "=== 4. Python files with no 'import' (often abandoned) ==="
git grep -L "import" -- '*.py' 2>/dev/null | head -20 || true

echo ""
echo "Done. Review above; move candidates to legacy/ before removing."
