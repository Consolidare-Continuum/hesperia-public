#!/usr/bin/env bash
set -euo pipefail

# Terminal 2: run OpenAI calibration scripts per completed bundle batch.
#
# Requires:
#   OPENAI_API_KEY (export, or repo-root .env.openai — gitignored — sourced if unset)
#   export PYTHONPATH='/home/igareosh/.local/lib/python3.10/site-packages'
# Optional:
#   export HESPERIA_OPENAI_MODEL='gpt-5.2'   (default is already gpt-5.2)
#
# Knobs (env):
#   BASE: corpus staging root (default below)
#   LIMIT: max corpus rows per script (default 200)
#   BATCH_GLOB: which batches to process (default "$BASE/batches/batch_*")
#   SKIP_DONE_OPENAI=1: skip batches that already have DONE_openai (resume without re-spending on finished batches)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${OPENAI_API_KEY:-}" && -f "$REPO_ROOT/.env.openai" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env.openai"
  set +a
fi

BASE="${BASE:-outputs/openai_calibration/noone2_cleaned}"
LIMIT="${LIMIT:-200}"
BATCH_GLOB="${BATCH_GLOB:-$BASE/batches/batch_*}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: missing OPENAI_API_KEY in env" >&2
  exit 2
fi

for broot in $BATCH_GLOB; do
  [[ -d "$broot" ]] || continue

  mkdir -p "$broot/openai" "$broot/logs"

  # Wait for bundle completion markers and key artifacts.
  until [[ -f "$broot/DONE_bundle" \
    && -f "$broot/bundle/02_session_tfp_stages.json" \
    && -f "$broot/bundle/04_dlcr_full.json" \
    && -f "$broot/bundle/05_sealed_multiscale.json" \
    && -f "$broot/bundle/06_product_analyze.json" \
    && -f "$broot/bundle/09_session_topology.json" \
    && -f "$broot/corpus.jsonl" ]]; do
    sleep 10
  done

  if [[ -n "${SKIP_DONE_OPENAI:-}" && "${SKIP_DONE_OPENAI}" != "0" && -f "$broot/DONE_openai" ]]; then
    echo "SKIP openai: $broot (DONE_openai exists; unset SKIP_DONE_OPENAI or delete marker to redo)" >&2
    continue
  fi

  # dict_a + areas in parallel
  python3 -u tools/openai_calibration/openai_calibrate_dict_a.py \
    --bundle-dir "$broot/bundle" \
    --corpus "$broot/corpus.jsonl" \
    --out "$broot/openai" \
    --limit "$LIMIT" \
    2>&1 | tee "$broot/logs/openai_dict_a.log" &
  p1=$!

  python3 -u tools/openai_calibration/openai_calibrate_areas.py \
    --bundle-dir "$broot/bundle" \
    --corpus "$broot/corpus.jsonl" \
    --out "$broot/openai" \
    --limit "$LIMIT" \
    2>&1 | tee "$broot/logs/openai_areas.log"

  wait "$p1"

  # topology after areas (reuses area_openai_segments.jsonl)
  python3 -u tools/openai_calibration/openai_calibrate_topology.py \
    --bundle-dir "$broot/bundle" \
    --corpus "$broot/corpus.jsonl" \
    --out "$broot/openai" \
    --area-segments "$broot/openai/area_openai_segments.jsonl" \
    --limit "$LIMIT" \
    2>&1 | tee "$broot/logs/openai_topology.log"

  # audit last (consumes the three OpenAI reports + bundle plane outputs)
  python3 -u tools/openai_calibration/openai_calibration_audit.py \
    --bundle-dir "$broot/bundle" \
    --openai-dir "$broot/openai" \
    --out "$broot/openai" \
    2>&1 | tee "$broot/logs/openai_audit.log"

  date > "$broot/DONE_openai"
done

echo "OK: OpenAI calibration complete under $BASE/batches"
