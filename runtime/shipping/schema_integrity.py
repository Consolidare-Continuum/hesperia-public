# HESPERIA — Optional runtime integrity check: SHA256 of public_output_schema.json.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""At startup, optionally verify SHA256 of public schema to prevent accidental drift."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def verify_public_schema_sha256(expected_hex: str | None = None) -> bool:
    """
    If expected_hex is set (e.g. from HESPERIA_SCHEMA_SHA256), load public_output_schema.json,
    compute SHA256, and return True only if it matches. If expected_hex is None, return True (no check).
    """
    expected_hex = (expected_hex or os.environ.get("HESPERIA_SCHEMA_SHA256", "")).strip()
    if not expected_hex:
        return True
    base = Path(__file__).resolve().parents[2]
    for subdir in ("assets/public", "assets"):
        path = base / subdir / "public_output_schema.json"
        if path.is_file():
            raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            return actual.lower() == expected_hex.lower()
    return False
