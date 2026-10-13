#!/usr/bin/env bash
# Build static dist for output_views/hex_matrix_viewer (Vite).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/output_views/hex_matrix_viewer"
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found" >&2
  exit 1
fi
npm ci
npm run build
echo "OK: dist → $ROOT/output_views/hex_matrix_viewer/dist"
