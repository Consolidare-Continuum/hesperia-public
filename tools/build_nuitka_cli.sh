#!/usr/bin/env bash
# HESPERIA — Build sealed CLI with Nuitka. Standalone first, then onefile, then strip.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: from repo root, run: ./tools/build_nuitka_cli.sh
# Requires: nuitka3 (pip install nuitka), python3, strip (binutils).
#
# Deliverables:
#   S2-T3: dist/hesperia-cli/   (standalone build)
#   S2-T4: dist/hesperia-cli.bin (onefile executable)
#   S2-T5: stripped binaries

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
DIST="$REPO/dist"
STANDALONE_DIR="$DIST/hesperia-cli"
ONEFILE_BIN="$DIST/hesperia-cli.bin"
MAIN_SCRIPT="runtime/shipping/cli_main.py"

if ! command -v nuitka3 &>/dev/null; then
  echo "nuitka3 not found. Install with: pip install nuitka" >&2
  exit 1
fi

echo "=== S2-T3: Nuitka standalone (dist/hesperia-cli/) ==="
mkdir -p "$DIST"
# Nuitka standalone: creates a directory with the binary and all .so deps.
# Test standalone before onefile (recommended by Nuitka).
nuitka3 \
  --standalone \
  --output-dir="$STANDALONE_DIR" \
  --output-filename=hesperia-cli \
  --assume-yes-for-downloads \
  "$MAIN_SCRIPT"

# Standalone layout: typically STANDALONE_DIR/hesperia-cli.dist/ or STANDALONE_DIR/cli_main.dist/
# Nuitka may put binary in STANDALONE_DIR or in a .dist subdir. Prefer single dir for deliverable.
if [[ -d "$STANDALONE_DIR/cli_main.dist" ]]; then
  mv "$STANDALONE_DIR/cli_main.dist" "$STANDALONE_DIR.run" 2>/dev/null || true
  rm -rf "$STANDALONE_DIR"
  mv "$STANDALONE_DIR.run" "$STANDALONE_DIR"
fi
echo "Standalone build in $STANDALONE_DIR"

echo "=== S2-T4: Nuitka onefile (dist/hesperia-cli.bin) ==="
nuitka3 \
  --onefile \
  --output-dir="$DIST" \
  --output-filename=hesperia-cli.bin \
  --assume-yes-for-downloads \
  "$MAIN_SCRIPT"
echo "Onefile build: $ONEFILE_BIN"

echo "=== S2-T5: Strip symbols and reduce metadata ==="
# Strip standalone binary (find it in STANDALONE_DIR)
find "$STANDALONE_DIR" -type f \( -name "hesperia-cli" -o -name "cli_main" -o -name "*.bin" \) 2>/dev/null | while read -r exe; do
  [[ -x "$exe" ]] && { strip --strip-unneeded "$exe" 2>/dev/null || strip "$exe" 2>/dev/null || true; echo "Stripped: $exe"; }
done
# Strip onefile binary fully (reduce symbols and metadata)
if [[ -f "$ONEFILE_BIN" ]]; then
  strip "$ONEFILE_BIN" 2>/dev/null || true
  strip --strip-unneeded "$ONEFILE_BIN" 2>/dev/null || true
  echo "Stripped: $ONEFILE_BIN"
fi

echo "Done. Standalone: $STANDALONE_DIR | Onefile: $ONEFILE_BIN"
echo "Verify: strings $ONEFILE_BIN | grep -i hesperia  # only minimal runtime identifiers should remain"
