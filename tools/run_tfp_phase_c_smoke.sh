#!/usr/bin/env bash
# TFP-GATE-C-SMOKE + TFP-ENF-04/05: precheck, wave, metrics gate, pytest slice, wall-clock cap.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONHASHSEED=0
export PYTHONPATH=.
START_TIME=$SECONDS
bash tools/run_tfp_env_precheck.sh
bash tools/run_b_cd_wave_after_a.sh
python3 tools/check_metrics_gate.py
python3 -m pytest tests/test_tfp_module_main_run.py tests/test_env_determinism.py \
  tests/test_tfp_concept_invariants_enf.py tests/test_tfp_cd_delta_enf.py tests/test_tfp_unmapped_gate_enf.py \
  tests/test_tfp_rel_realism_enf.py \
  -q --tb=short
elapsed=$((SECONDS - START_TIME))
max=${HESPERIA_PHASE_C_SMOKE_MAX_SEC:-120}
if (( elapsed > max )); then
  echo "FAIL: phase C wall time ${elapsed}s > max ${max}s" >&2
  exit 1
fi
ratio_max=${HESPERIA_PHASE_C_LATENCY_RATIO_MAX:-18}
baseline_file="$ROOT/tools/tfp_phase_c_latency_baseline_seconds.txt"
if [[ -f "$baseline_file" ]]; then
  read -r baseline <"$baseline_file" || true
  baseline="${baseline%%#*}"
  baseline=$(echo "$baseline" | tr -d '\r\n[:space:]')
  if [[ "$baseline" =~ ^[0-9]+$ ]] && (( baseline > 0 )); then
    limit=$(( baseline * ratio_max ))
    if (( elapsed > limit )); then
      echo "FAIL: phase C latency ratio ${elapsed}s > baseline(${baseline})*R(${ratio_max})=${limit}s" >&2
      exit 1
    fi
  fi
fi
echo "OK: TFP phase C smoke (${elapsed}s <= ${max}s, ratio vs baseline OK): precheck + wave + metrics + REL/ENF pytest."
