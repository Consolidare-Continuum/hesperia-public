#!/usr/bin/env bash
# After Dict A is frozen and validators green: exercise B line + CD executor + one CD-on runtime smoke.
# No OpenAI. Uses HESPERIA_CALIB_DICT_VERSION (default v0_6_0_clr_v052_2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

CALIB="${HESPERIA_CALIB_DICT_VERSION:-v0_6_0_clr_v052_2}"
CALIB_DIR="$ROOT/assets/calibration/dicts/$CALIB"
CD_JSONL="$ROOT/assets/data/engine_dynamics_v060/concept_dict/concept_dict_cd.jsonl"
LINKS_BASELINE="$CALIB_DIR/.links_line_count_baseline"
TOL="${HESPERIA_LINKS_LINE_TOLERANCE:-0}"

echo "=== Wave artifact precheck (TFP-GATE-A1) ==="
if [[ ! -d "$CALIB_DIR" ]]; then
  echo "FAIL: calibration dir missing: $CALIB_DIR"
  exit 1
fi
if [[ ! -s "$CALIB_DIR/dict_a.jsonl" ]]; then
  echo "FAIL: dict_a.jsonl missing or empty under $CALIB_DIR"
  exit 1
fi
if [[ ! -s "$CALIB_DIR/links.jsonl" ]]; then
  echo "FAIL: links.jsonl missing or empty under $CALIB_DIR"
  exit 1
fi
if [[ ! -f "$CD_JSONL" ]] || [[ ! -s "$CD_JSONL" ]]; then
  echo "FAIL: concept_dict_cd.jsonl missing or empty (expected for CD-on wave): $CD_JSONL"
  exit 1
fi
if [[ -f "$LINKS_BASELINE" ]]; then
  EXP="$(tr -d '[:space:]' < "$LINKS_BASELINE")"
  GOT="$(wc -l < "$CALIB_DIR/links.jsonl" | tr -d '[:space:]')"
  LOW=$((EXP - TOL))
  HIGH=$((EXP + TOL))
  if [[ "$GOT" -lt "$LOW" ]] || [[ "$GOT" -gt "$HIGH" ]]; then
    echo "FAIL: links.jsonl line count $GOT outside baseline $EXP ± tolerance $TOL (see $LINKS_BASELINE)"
    exit 1
  fi
  echo "OK: links.jsonl lines=$GOT (baseline $EXP ± $TOL)"
else
  echo "WARN: no $LINKS_BASELINE — skipping links count check (add file when pack is sealed)"
fi

echo "=== B pack validators (resolver / DLCR dict_b) ==="
python3 tools/validate_dict_b_dlcr.py
python3 tools/validate_tfp_ru_pack.py
python3 tools/check_dlcr_regression.py

echo "=== CD (Concept Dictionary) unit tests ==="
python3 -m pytest tests/concept_dictionary/test_cd_executor.py -q

TMP_IN="$(mktemp)"
TMP_OUT="$(mktemp)"
TMP_MAN="$(mktemp)"
cleanup() { rm -f "$TMP_IN" "$TMP_OUT" "$TMP_MAN"; }
trap cleanup EXIT
echo 'clinical language borderline splitting identity diffusion' >"$TMP_IN"

echo "=== Runtime smoke: HESPERIA_CALIB_DICT_VERSION=$CALIB HESPERIA_CD_ENABLED=1 ==="
HESPERIA_CALIB_DICT_VERSION="$CALIB" HESPERIA_CD_ENABLED=1 \
  python3 -m hesperia.run "$TMP_IN" --config assets/config/pipeline.yaml --out "$TMP_OUT" --manifest-out "$TMP_MAN"

echo "DONE: B+CD wave after green A (see docs/governance/cd_v1/MODEL_CARD_CD_PIPELINE.md: A→B→CD→C_agg→Topology)."
