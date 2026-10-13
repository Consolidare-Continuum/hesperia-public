# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA deterministic dossier artifact writer.
Freezes analysis runs into canonical JSON with a stable SHA256 checksum.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

SCHEMA_VERSION = "HSD_v1.0"
CHECKSUM_KEY = "dossier_checksum"
SCHEMA_VERSION_KEY = "schema_version"


def _canonical_json(obj: Dict[str, Any]) -> str:
    """Serialize to deterministic JSON: sort_keys=True, indent=2, ensure_ascii=False."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)


DOSSIER_ID_KEY = "dossier_id"  # meta.dossier_id = first 12 chars of checksum; excluded from checksum input


def _payload_for_checksum(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Copy payload with checksum and meta.dossier_id removed for deterministic hashing."""
    out = dict(payload)
    out[CHECKSUM_KEY] = ""
    if "meta" in out and isinstance(out["meta"], dict):
        meta = dict(out["meta"])
        meta.pop(DOSSIER_ID_KEY, None)
        out["meta"] = meta
    return out


def write_dossier_json(dossier: Dict[str, Any], output_path: Path | str) -> str:
    """
    Write dossier to path with canonical JSON, dossier_checksum, and meta.dossier_id.
    Checksum is computed over payload without checksum and without meta.dossier_id.
    Public projection is applied so no internal structure leaks.
    Returns dossier_id (first 12 chars of checksum).
    """
    from core.engine.projection import project_to_public

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = project_to_public(dict(dossier), validate_schema=True)
    payload[SCHEMA_VERSION_KEY] = SCHEMA_VERSION
    payload[CHECKSUM_KEY] = ""
    if "meta" not in payload:
        payload["meta"] = {}
    payload_for_hash = _payload_for_checksum(payload)

    canonical = _canonical_json(payload_for_hash)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    dossier_id = digest[:12]
    payload[CHECKSUM_KEY] = digest
    if "meta" not in payload:
        payload["meta"] = {}
    payload["meta"][DOSSIER_ID_KEY] = dossier_id

    final_json = _canonical_json(payload)
    output_path.write_text(final_json, encoding="utf-8")
    return dossier_id
