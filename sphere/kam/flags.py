# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""HESPERIA_KAM_* feature flags — default-off; research lens only (not a KAM theorem)."""
from __future__ import annotations

import os
from pathlib import Path

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_true(key: str, *, default: str = "0") -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default.strip().lower() in _TRUTHY
    return raw.strip().lower() in _TRUTHY


def kam_enabled() -> bool:
    """Master gate. Unset/0 → no ``kam_stability`` block on inspect envelope."""
    return _env_true("HESPERIA_KAM_ENABLED", default="0")


def kam_inspect_only() -> bool:
    """Pre-0.7.0: KAM is inspect-only (default on). Never mutates graph."""
    return _env_true("HESPERIA_KAM_INSPECT_ONLY", default="1")


def kam_bounds_path() -> Path | None:
    raw = os.environ.get("HESPERIA_KAM_BOUNDS", "").strip()
    return Path(raw) if raw else None
