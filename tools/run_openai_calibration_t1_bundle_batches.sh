#!/usr/bin/env bash
set -euo pipefail

# Terminal 1: build per-batch TFP bundles from the staged corpus.
#
# Prereq: staged corpus exists:
#   outputs/openai_calibration/noone2_cleaned/sessions.json
#   outputs/openai_calibration/noone2_cleaned/corpus.jsonl
#
# Usage (recommended):
#   export PYTHONPATH='/home/igareosh/.local/lib/python3.10/site-packages'
#   export HESPERIA_OPENAI_MODEL='gpt-5.2'
#   bash tools/run_openai_calibration_t1_bundle_batches.sh
#
# Knobs (env):
#   BASE: corpus staging root (default below)
#   DOCS_PER_BATCH: how many docs per batch (default 3)
#   BATCH_COUNT: how many batches to run in this invocation (default 5)
#   START_BATCH: first batch index 1..N (default 1). Use e.g. START_BATCH=4 to resume after batch_003.
#     Example resume: START_BATCH=4 BATCH_COUNT=2  → batch_004 and batch_005 only.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE="${BASE:-outputs/openai_calibration/noone2_cleaned}"
BATCH_ROOT="${BATCH_ROOT:-$BASE/batches}"
DOCS_PER_BATCH="${DOCS_PER_BATCH:-3}"
BATCH_COUNT="${BATCH_COUNT:-5}"
START_BATCH="${START_BATCH:-1}"
END_BATCH=$((START_BATCH + BATCH_COUNT - 1))

mkdir -p "$BATCH_ROOT"

if [[ ! -f "$BASE/sessions.json" || ! -f "$BASE/corpus.jsonl" ]]; then
  echo "ERROR: staged corpus missing under $BASE" >&2
  echo "Expected: $BASE/sessions.json and $BASE/corpus.jsonl" >&2
  exit 2
fi

if [[ "$START_BATCH" -lt 1 ]]; then
  echo "ERROR: START_BATCH must be >= 1 (got $START_BATCH)" >&2
  exit 2
fi

for b in $(seq "$START_BATCH" "$END_BATCH"); do
  batch="$(printf "batch_%03d" "$b")"
  start=$(( (b - 1) * DOCS_PER_BATCH + 1 ))
  broot="$BATCH_ROOT/$batch"

  mkdir -p "$broot" "$broot/logs" "$broot/bundle"

  # Build per-batch sessions.json + corpus.jsonl
  python3 - "$BASE" "$broot" "$start" "$DOCS_PER_BATCH" <<'PY'
import json, sys
from pathlib import Path

base = Path(sys.argv[1])
broot = Path(sys.argv[2])
start = int(sys.argv[3])
count = int(sys.argv[4])

sessions_all = json.loads((base / "sessions.json").read_text(encoding="utf-8"))["sessions"]
chunk = sessions_all[start - 1 : start - 1 + count]
keep = {s["session_id"] for s in chunk}

(broot / "sessions.json").write_text(
    json.dumps({"sessions": chunk}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
with (base / "corpus.jsonl").open("r", encoding="utf-8") as src, (broot / "corpus.jsonl").open(
    "w", encoding="utf-8"
) as dst:
    for line in src:
        row = json.loads(line)
        if row.get("session_id") in keep:
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")

(broot / "meta.json").write_text(
    json.dumps({"start": start, "count": count, "session_ids": sorted(keep)}, ensure_ascii=False, indent=2)
    + "\n",
    encoding="utf-8",
)
print(f"prepared {broot}")
PY

  # Full cross-check bundle (needed for openai_calibration_audit.py): emits 00/02/04/05/06/09
  # Notes:
  # - --skip-structural keeps runtime sane on batches.
  # - --with-topology keeps topology artifacts for OpenAI topology calibration.
  python3 -u -m runtime.pipeline.run_tfp_file_pipeline \
    --input "$broot/sessions.json" \
    --out-dir "$broot/bundle" \
    --skip-structural \
    --with-topology \
    --skip-triz-activation \
    2>&1 | tee "$broot/logs/bundle.log"

  date > "$broot/DONE_bundle"
done

echo "OK: bundles complete under $BATCH_ROOT"
