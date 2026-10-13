#!/usr/bin/env bash
# TFP-DATA-T04: One-shot (idempotent) migration: research/_noone_local + calibration pack → hesperia/modules/tfp/data/tfp_v1/
# Read-only on research/. Logs: tfp_v1/MIGRATION_LOG.jsonl
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${ROOT}/hesperia/modules/tfp/data/tfp_v1"
LOG="${DEST}/MIGRATION_LOG.jsonl"
PACK="${HESPERIA_CALIB_DICT_VERSION:-v0_6_0_clr_v052_2}"
PACK_DIR="${ROOT}/assets/calibration/dicts/${PACK}"

log_line() {
  export OP="$1" SRC="$2" DST="$3" DET="${4:-}"
  python3 - <<'PY' >>"${LOG}"
import json, os, datetime
print(json.dumps({
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "op": os.environ["OP"],
    "src": os.environ["SRC"],
    "dst": os.environ["DST"],
    "detail": os.environ.get("DET", ""),
}, ensure_ascii=False))
PY
}

sha_file() {
  local f="$1"
  if [[ -f "$f" ]]; then sha256sum "$f" | awk '{print $1}'; else echo ""; fi
}

mkdir -p "${DEST}/corpus/original/ru" "${DEST}/corpus/original/en" "${DEST}/corpus/sessions" "${DEST}/corpus/normalized" \
  "${DEST}/dict_a/candidates" "${DEST}/dict_a/normalized" "${DEST}/dict_a/proposals" "${DEST}/dict_a/runtime" \
  "${DEST}/dict_b" "${DEST}/provenance/api/runs" "${DEST}/provenance/api/batch_ids" "${DEST}/nlp"
: >"${LOG}"

if [[ -d "${ROOT}/research/_noone_local/2_cleaned" ]]; then
  rsync -a "${ROOT}/research/_noone_local/2_cleaned/" "${DEST}/corpus/original/ru/"
  log_line rsync "${ROOT}/research/_noone_local/2_cleaned" "${DEST}/corpus/original/ru" "ru corpus"
else
  log_line skip_missing "${ROOT}/research/_noone_local/2_cleaned" "${DEST}/corpus/original/ru" "no source"
fi

if [[ -d "${ROOT}/research/_noone_local/english_2_cleaned" ]]; then
  rsync -a "${ROOT}/research/_noone_local/english_2_cleaned/" "${DEST}/corpus/original/en/"
  log_line rsync "${ROOT}/research/_noone_local/english_2_cleaned" "${DEST}/corpus/original/en" "en corpus"
else
  log_line skip_missing "${ROOT}/research/_noone_local/english_2_cleaned" "${DEST}/corpus/original/en" "no source"
fi

if [[ -d "${ROOT}/research/_noone_local/sessions" ]]; then
  rsync -a "${ROOT}/research/_noone_local/sessions/" "${DEST}/corpus/sessions/"
  log_line rsync "${ROOT}/research/_noone_local/sessions" "${DEST}/corpus/sessions" "session md corpus"
else
  log_line skip_missing "${ROOT}/research/_noone_local/sessions" "${DEST}/corpus/sessions" "no source"
fi

if [[ -d "${PACK_DIR}" ]]; then
  for name in dict_a.jsonl dict_a_candidates.jsonl dict_a_normalized.jsonl dict_b.jsonl dict_b_draft.jsonl links.jsonl metrics.json; do
    if [[ -f "${PACK_DIR}/${name}" ]]; then
      case "${name}" in
        dict_a.jsonl) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_a/runtime/dict_a.jsonl" ;;
        dict_a_candidates.jsonl) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_a/candidates/" ;;
        dict_a_normalized.jsonl) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_a/normalized/" ;;
        dict_b.jsonl) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_b/" ;;
        dict_b_draft.jsonl) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_a/proposals/" ;;
        links.jsonl|metrics.json) cp -f "${PACK_DIR}/${name}" "${DEST}/dict_b/" ;;
      esac
      h="$(sha_file "${PACK_DIR}/${name}")"
      log_line copy_file "${PACK_DIR}/${name}" "${DEST}" "${name} sha256=${h}"
    fi
  done
else
  log_line skip_missing "${PACK_DIR}" "${DEST}/dict_a" "calibration pack absent"
fi

python3 "${ROOT}/tools/gen_tfp_v1_manifest.py" --repo "${ROOT}"
log_line manifest "${ROOT}/tools/gen_tfp_v1_manifest.py" "${DEST}/MANIFEST.yaml" "regenerated"

echo "DONE migrate_research_tfp_to_module_tfp_v1: ${DEST} (log ${LOG})"
