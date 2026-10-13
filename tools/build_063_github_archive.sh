#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
VER="0.6.3"
OUT="dist/hesperia-${VER}-archive.zip"
mkdir -p dist
git archive --format=zip --prefix="hesperia-${VER}/" HEAD > "$OUT"
( cd dist && sha256sum "$(basename "$OUT")" > SHA256SUMS-hesperia-${VER}.txt )
echo "Wrote $OUT"
cat "dist/SHA256SUMS-hesperia-${VER}.txt"
