#!/usr/bin/env bash
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Phases A–D: extract → normalize → propose → anchor → links → eval → errors.
# Stops before patch/loop/freeze.
#
# Default profile — v0.5.2-style clearance (no artificial 100/240 caps):
#   - Normalize every filtered candidate row (after extract + lexical filter in pipeline).
#   - Propose from all normalized rows (--limit 0 in run_pipeline = no cap).
#   - Eval + errors over the whole corpus: every *.md, full text (eval-max-files/chars <= 0).
#
# Cheap wiring / credit test: SMOKE=1 (or BUDGET=1) restores small caps.
#
# Usage:
#   ./tools/run_dict_calibration_phases_a_d.sh
#   WORKDIR=outputs/dict_calibration/ru_clearance_run1 ./tools/run_dict_calibration_phases_a_d.sh
#   SMOKE=1 ./tools/run_dict_calibration_phases_a_d.sh
#   SKIP_LLM=1 WORKDIR=/tmp/d …   # dry-run LLM only
#
# Env (override any default):
#   CORPUS, WORKDIR, MIN_FREQ, BATCH_SIZE, MIN_SCORE
#   NORMALIZE_MAX_ROWS   set positive to cap LLM normalize rows; unset = no cap (clearance)
#   PROPOSE_LIMIT        0 = all normalized rows (clearance); positive = cap
#   MAX_CONCEPTS, CATALOG_LIMIT, PROPOSE_BATCH_SIZE
#   EVAL_MAX_FILES, EVAL_MAX_CHARS  use <=0 or empty for full corpus / full files (clearance)
#   SKIP_EXTRACT, SKIP_LLM, SMOKE, BUDGET (BUDGET aliases SMOKE)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

_load_env_key() {
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    return 0
  fi
  for f in .env.openai .env; do
    if [[ -f "$REPO_ROOT/$f" ]]; then
      # shellcheck source=/dev/null
      set -a
      source "$REPO_ROOT/$f"
      set +a
      break
    fi
  done
}

_load_env_key

CORPUS="${CORPUS:-hesperia/modules/tfp/data/tfp_v1/corpus/original/ru}"
if [[ -z "${WORKDIR:-}" ]]; then
  WORKDIR="outputs/dict_calibration/corpus_ad_$(date -u +%Y%m%d_%H%M%S)"
fi

MIN_SCORE="${MIN_SCORE:-0.52}"

SMOKE_MODE=0
if [[ -n "${SMOKE:-}" && "$SMOKE" != "0" ]] || [[ -n "${BUDGET:-}" && "$BUDGET" != "0" ]]; then
  SMOKE_MODE=1
fi

# Defaults use ${VAR-dflt} (unset only) so explicit PROPOSE_LIMIT=0 is not overwritten.
if [[ "$SMOKE_MODE" == "1" ]]; then
  MIN_FREQ="${MIN_FREQ-4}"
  BATCH_SIZE="${BATCH_SIZE-16}"
  MAX_CONCEPTS="${MAX_CONCEPTS-48}"
  CATALOG_LIMIT="${CATALOG_LIMIT-100}"
  PROPOSE_BATCH_SIZE="${PROPOSE_BATCH_SIZE-28}"
  NORMALIZE_MAX_ROWS="${NORMALIZE_MAX_ROWS-240}"
  PROPOSE_LIMIT="${PROPOSE_LIMIT-120}"
  EVAL_MAX_FILES="${EVAL_MAX_FILES-5}"
  EVAL_MAX_CHARS="${EVAL_MAX_CHARS-12000}"
else
  # v0.5.2-style clearance: all filtered candidates, full corpus eval (no 100/240 toy caps)
  MIN_FREQ="${MIN_FREQ-2}"
  BATCH_SIZE="${BATCH_SIZE-24}"
  MAX_CONCEPTS="${MAX_CONCEPTS-80}"
  CATALOG_LIMIT="${CATALOG_LIMIT-400}"
  PROPOSE_BATCH_SIZE="${PROPOSE_BATCH_SIZE-40}"
  PROPOSE_LIMIT="${PROPOSE_LIMIT-0}"
  EVAL_MAX_FILES="${EVAL_MAX_FILES-0}"
  EVAL_MAX_CHARS="${EVAL_MAX_CHARS-0}"
  # NORMALIZE_MAX_ROWS unset → no --max-llm-rows
fi

DRY_ARGS=()
if [[ -n "${SKIP_LLM:-}" && "$SKIP_LLM" != "0" ]]; then
  DRY_ARGS=(--dry-run)
fi

echo "== dict calibration A–D (clearance default unless SMOKE/BUDGET) ==" >&2
echo "repo    $REPO_ROOT" >&2
echo "corpus  $CORPUS" >&2
echo "workdir $WORKDIR" >&2
echo "smoke/budget=${SMOKE:-0}/${BUDGET:-0}  skip_llm=${SKIP_LLM:-0}  skip_extract=${SKIP_EXTRACT:-0}" >&2
if [[ -z "${NORMALIZE_MAX_ROWS:-}" ]]; then
  echo "normalize: no --max-llm-rows (all filtered candidates → API)" >&2
else
  echo "normalize: cap --max-llm-rows=$NORMALIZE_MAX_ROWS" >&2
fi
echo "propose: limit=$PROPOSE_LIMIT (0=all)  eval: files=$EVAL_MAX_FILES chars=$EVAL_MAX_CHARS (<=0=full)" >&2

if [[ -z "${OPENAI_API_KEY:-}" && ( ${#DRY_ARGS[@]} -eq 0 ) ]]; then
  echo "WARN: OPENAI_API_KEY unset; normalize/propose will fail unless SKIP_LLM=1" >&2
fi

mkdir -p "$WORKDIR"

PY=(python3 tools/dict_calibration/run_pipeline.py)

if [[ -z "${SKIP_EXTRACT:-}" || "$SKIP_EXTRACT" == "0" ]]; then
  echo ">> A extract" >&2
  "${PY[@]}" extract --corpus "$CORPUS" --out "$WORKDIR" --min-freq "$MIN_FREQ"
else
  echo ">> A extract SKIPPED" >&2
  if [[ ! -f "$WORKDIR/dict_a_candidates.jsonl" ]]; then
    echo "ERROR: SKIP_EXTRACT set but missing $WORKDIR/dict_a_candidates.jsonl" >&2
    exit 2
  fi
fi

echo ">> B normalize" >&2
NORM_CMD=("${PY[@]}" normalize --workdir "$WORKDIR" --batch-size "$BATCH_SIZE")
if [[ -n "${NORMALIZE_MAX_ROWS:-}" && "$NORMALIZE_MAX_ROWS" -gt 0 ]]; then
  NORM_CMD+=(--max-llm-rows "$NORMALIZE_MAX_ROWS")
fi
NORM_CMD+=("${DRY_ARGS[@]}")
"${NORM_CMD[@]}"

echo ">> B propose" >&2
"${PY[@]}" propose --workdir "$WORKDIR" --limit "$PROPOSE_LIMIT" \
  --max-concepts "$MAX_CONCEPTS" --catalog-limit "$CATALOG_LIMIT" \
  --propose-batch-size "$PROPOSE_BATCH_SIZE" "${DRY_ARGS[@]}"

echo ">> C anchor" >&2
"${PY[@]}" anchor --workdir "$WORKDIR" --min-score "$MIN_SCORE"

echo ">> C links" >&2
"${PY[@]}" links --workdir "$WORKDIR"

echo ">> D eval" >&2
"${PY[@]}" eval --workdir "$WORKDIR" --corpus "$CORPUS" \
  --eval-max-files "$EVAL_MAX_FILES" --eval-max-chars "$EVAL_MAX_CHARS"

echo ">> D errors" >&2
"${PY[@]}" errors --workdir "$WORKDIR" --corpus "$CORPUS" \
  --eval-max-files "$EVAL_MAX_FILES" --eval-max-chars "$EVAL_MAX_CHARS"

echo "OK: phases A–D complete → $WORKDIR" >&2
