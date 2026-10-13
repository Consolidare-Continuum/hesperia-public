# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""HESPERIA_KSI_* feature flags — default-off; additive to sealed /analyze."""
from __future__ import annotations

import os
from pathlib import Path

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_true(key: str, *, default: str = "0") -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default.strip().lower() in _TRUTHY
    return raw.strip().lower() in _TRUTHY


def ksi_enabled() -> bool:
    """Master gate. Unset/0 → sealed analyze unchanged (no ``ksi`` block)."""
    return _env_true("HESPERIA_KSI_ENABLED", default="0")


def phi_trace_enabled() -> bool:
    return _env_true("HESPERIA_KSI_PHI_TRACE", default="0")


def ksi_phi_trace_enabled() -> bool:
    """Alias for :func:`phi_trace_enabled` (H62 naming)."""
    return phi_trace_enabled()


def ksi_sandbox_fixtures_enabled() -> bool:
    """True when ``HESPERIA_KSI_SANDBOX_FIXTURES`` is non-empty."""
    return bool(os.environ.get("HESPERIA_KSI_SANDBOX_FIXTURES", "").strip())


def teacher_inspect_only() -> bool:
    """Until 0.7.0 apply gates: teacher packet is inspect-only (default on)."""
    return _env_true("HESPERIA_KSI_TEACHER_INSPECT_ONLY", default="1")


def teacher_packet_enabled() -> bool:
    """Include ``teacher_packet`` under ``ksi`` when master gate is on (default on)."""
    return _env_true("HESPERIA_KSI_TEACHER_PACKET", default="1")


def ksi_config_path() -> Path | None:
    raw = os.environ.get("HESPERIA_KSI_CONFIG", "").strip()
    return Path(raw) if raw else None


def tau_override() -> float | None:
    raw = os.environ.get("HESPERIA_KSI_TAU", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def tau_bridge_override() -> float | None:
    raw = os.environ.get("HESPERIA_KSI_TAU_BRIDGE", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def tau_teacher_override() -> float | None:
    raw = os.environ.get("HESPERIA_KSI_TAU_TEACHER", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
