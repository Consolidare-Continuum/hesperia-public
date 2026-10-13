# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA dossier checksum verification.
Returns True if the stored checksum matches the computed checksum of the payload.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from .dossier_writer import CHECKSUM_KEY, SCHEMA_VERSION_KEY, _canonical_json, _payload_for_checksum


def verify_dossier_checksum(file_path: Path | str) -> bool:
    """
    Verify that dossier_checksum in the file matches the SHA256 of the canonical
    JSON with the checksum field empty and meta.dossier_id excluded. Returns True if valid.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return False
    text = file_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    stored = data.get(CHECKSUM_KEY)
    if not stored or not isinstance(stored, str):
        return False
    payload = dict(data)
    payload_for_hash = _payload_for_checksum(payload)
    canonical = _canonical_json(payload_for_hash)
    computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return computed == stored


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m runtime.dossier.verify_dossier <dossier.json>", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    ok = verify_dossier_checksum(path)
    print("OK" if ok else "FAIL")
    sys.exit(0 if ok else 1)
