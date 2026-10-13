#!/usr/bin/env bash
# TFP-DATA-T09: Refresh hesperia/modules/tfp/data/tfp_v1/ from assets/calibration/dicts/<pack> (no research/).
# Optional: HESPERIA_TFP_SYNC_STRICT=1 — exit non-zero if dict_a runtime face missing after sync.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${ROOT}/hesperia/modules/tfp/data"
TFPV1="${DEST}/tfp_v1"
CALIB_VER="${HESPERIA_CALIB_DICT_VERSION:-v0_6_0_clr_v052_2}"
PACK_DIR="${ROOT}/assets/calibration/dicts/${CALIB_VER}"
STRICT="${HESPERIA_TFP_SYNC_STRICT:-0}"

mkdir -p "${TFPV1}/dict_a/candidates" "${TFPV1}/dict_a/normalized" "${TFPV1}/dict_a/proposals" "${TFPV1}/dict_a/runtime" \
  "${TFPV1}/dict_b" "${TFPV1}/corpus/original/ru" "${TFPV1}/corpus/original/en" "${TFPV1}/corpus/sessions" "${TFPV1}/provenance/api/runs" "${TFPV1}/provenance/api/batch_ids" "${TFPV1}/nlp"

if [[ -d "${PACK_DIR}" ]]; then
  for name in dict_a.jsonl dict_a_candidates.jsonl dict_a_normalized.jsonl dict_b.jsonl dict_b_draft.jsonl links.jsonl metrics.json; do
    if [[ -f "${PACK_DIR}/${name}" ]]; then
      case "${name}" in
        dict_a.jsonl) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_a/runtime/dict_a.jsonl" ;;
        dict_a_candidates.jsonl) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_a/candidates/" ;;
        dict_a_normalized.jsonl) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_a/normalized/" ;;
        dict_b.jsonl) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_b/" ;;
        dict_b_draft.jsonl) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_a/proposals/" ;;
        links.jsonl|metrics.json) cp -f "${PACK_DIR}/${name}" "${TFPV1}/dict_b/" ;;
      esac
    fi
  done
  echo "Synced calibration pack ${CALIB_VER} -> ${TFPV1}"
else
  echo "SKIP: ${PACK_DIR} not present"
fi

if [[ -d "${ROOT}/assets/data/engine_dynamics_v060" ]]; then
  mkdir -p "${DEST}/dicts/engine_dynamics_v060"
  rsync -a --delete "${ROOT}/assets/data/engine_dynamics_v060/" "${DEST}/dicts/engine_dynamics_v060/"
  echo "Synced engine_dynamics_v060 -> ${DEST}/dicts/engine_dynamics_v060"
else
  echo "SKIP: engine_dynamics_v060 not present"
fi

python3 "${ROOT}/tools/gen_tfp_v1_manifest.py" --repo "${ROOT}" 2>/dev/null || true

if [[ "${STRICT}" == "1" || "${STRICT}" == "true" ]]; then
  if [[ ! -f "${TFPV1}/dict_a/runtime/dict_a.jsonl" ]]; then
    echo "FAIL: HESPERIA_TFP_SYNC_STRICT: missing ${TFPV1}/dict_a/runtime/dict_a.jsonl" >&2
    exit 1
  fi
fi

echo "DONE: sync_tfp_module_data (tfp_v1 + legacy dicts mirror); research/ not used."
