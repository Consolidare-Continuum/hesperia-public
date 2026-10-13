# HESPERIA — License token check. Redistribution friction, not absolute security.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Startup gate: env var or license file, optional expiry, optional reviewer token.
Skip if HESPERIA_LICENSE_SKIP=1 (e.g. dev). Optional machine binding (S4-T2) kept light.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


def check_license() -> bool:
    """
    Return True if license is valid or check is skipped. False otherwise.
    - HESPERIA_LICENSE_SKIP=1 → skip (return True)
    - HESPERIA_LICENSE_REQUIRED=1 → require token and optional expiry
    - HESPERIA_LICENSE_TOKEN=... or HESPERIA_LICENSE_FILE=path → token
    - HESPERIA_LICENSE_EXPIRY=YYYY-MM-DD or expiry= in file → past date → False
    If neither SKIP nor REQUIRED is set, allow (no friction for eval).
    """
    if os.environ.get("HESPERIA_LICENSE_SKIP", "").strip() == "1":
        return True
    if os.environ.get("HESPERIA_LICENSE_REQUIRED", "").strip() != "1":
        return True

    token = os.environ.get("HESPERIA_LICENSE_TOKEN", "").strip()
    license_file = os.environ.get("HESPERIA_LICENSE_FILE", "").strip()

    if license_file:
        path = Path(license_file)
        if path.is_file():
            raw = path.read_text(encoding="utf-8").strip()
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("token="):
                    token = token or line.split("=", 1)[1].strip()
                if line.startswith("expiry="):
                    expiry_str = line.split("=", 1)[1].strip()
                    if not _check_expiry(expiry_str):
                        return False
        else:
            return False

    if not token:
        return False

    expiry_env = os.environ.get("HESPERIA_LICENSE_EXPIRY", "").strip()
    if expiry_env and not _check_expiry(expiry_env):
        return False

    return True


def _check_expiry(expiry_str: str) -> bool:
    """Return True if expiry is in the future or unparseable (allow)."""
    try:
        # YYYY-MM-DD
        when = datetime.strptime(expiry_str.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return when >= datetime.now(timezone.utc)
    except Exception:
        return True


def optional_machine_binding_enabled() -> bool:
    """S4-T2: Optional host fingerprint. Only if HESPERIA_MACHINE_BINDING=1. Keep light."""
    return os.environ.get("HESPERIA_MACHINE_BINDING", "").strip() == "1"


def check_machine_binding_if_enabled() -> bool:
    """If machine binding is enabled, check a simple host id (e.g. from license file). Else True."""
    if not optional_machine_binding_enabled():
        return True
    # Light check: optional machine_id in license file or env; no heavy fingerprinting
    mid = os.environ.get("HESPERIA_MACHINE_ID", "").strip()
    return bool(mid)
