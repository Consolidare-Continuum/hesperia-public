# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Public-safe run manifest writer. Every public run should produce a non-revealing accountability record.
Conforms to assets/public/public_audit_manifest.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Allowed keys per PUBLIC_AUDIT_POLICY (no internal layer ids, topology, or formula ids)
PUBLIC_MANIFEST_KEYS = frozenset({
    "engine_version", "public_ontology_version", "calibration_profile_id",
    "report_profile_id", "input_manifest_id", "run_timestamp", "output_checksum",
    "evidence_count", "public_metric_profile_id",
})


def write_public_audit_manifest(manifest: dict[str, Any], output_path: Path | str) -> None:
    """
    Write public audit manifest to path. Only public-safe keys are written; any other keys are stripped.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in manifest.items() if k in PUBLIC_MANIFEST_KEYS}
    if "run_timestamp" not in safe:
        from datetime import datetime, timezone
        safe["run_timestamp"] = datetime.now(tz=timezone.utc).isoformat()
    output_path.write_text(json.dumps(safe, indent=2), encoding="utf-8")
