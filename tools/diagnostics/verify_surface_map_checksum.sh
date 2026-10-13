#!/usr/bin/env bash

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GENERATED_PATH="${1:-${ROOT_DIR}/legacy/assets/data/v040/surface_map_v040.json}"
EXPECTED_FILE="${2:-${ROOT_DIR}/legacy/assets/data/v040/surface_map_v040.json.sha256}"

if [[ ! -f "${GENERATED_PATH}" ]]; then
  echo "missing generated artifact: ${GENERATED_PATH}" >&2
  exit 1
fi

if [[ ! -f "${EXPECTED_FILE}" ]]; then
  echo "missing expected checksum file: ${EXPECTED_FILE}" >&2
  exit 1
fi

expected_hash="$(awk '{print $1}' "${EXPECTED_FILE}")"
actual_hash="$(sha256sum "${GENERATED_PATH}" | awk '{print $1}')"

if [[ "${expected_hash}" == "UNSET" ]]; then
  echo "Expected checksum is UNSET — run canonicalize to set it." >&2
  exit 1
fi

if [[ "${expected_hash}" != "${actual_hash}" ]]; then
  echo "surface_map hash changed — update expected checksum" >&2
  echo "expected=${expected_hash}" >&2
  echo "actual=${actual_hash}" >&2
  exit 1
fi

echo "surface_map checksum verified: ${actual_hash}"
