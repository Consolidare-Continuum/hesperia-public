# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA dossier schema validation (HSD_v1.0).
Verifies required fields exist for single-run or multiscale dossier shape.
"""

from __future__ import annotations

from typing import Any, Dict, List

REQUIRED_LAYERS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
GLOBAL_STRUCTURE_KEYS = (
    "dominant_area_distribution",
    "stable_family_core",
    "tension_axes",
    "confidence_profile",
    "document_anomaly",
)


def _check_segment_entry(entry: Any, scale_label: str, index: int) -> List[str]:
    """Validate one segment entry (has L1..L9, diagnostics). Returns list of error messages."""
    errors: List[str] = []
    if not isinstance(entry, dict):
        errors.append(f"{scale_label}[{index}]: must be object")
        return errors
    for lid in REQUIRED_LAYERS:
        key = f"L{lid}"
        if key not in entry:
            errors.append(f"{scale_label}[{index}]: missing {key}")
        elif not isinstance(entry.get(key), dict):
            errors.append(f"{scale_label}[{index}]: {key} must be object")
    if "diagnostics" not in entry:
        errors.append(f"{scale_label}[{index}]: missing diagnostics")
    elif not isinstance(entry["diagnostics"], dict):
        errors.append(f"{scale_label}[{index}]: diagnostics must be object")
    return errors


def validate_dossier_schema(dossier: Dict[str, Any]) -> bool:
    """
    Verify required fields exist for HSD_v1.0 dossier (single-run or multiscale).
    Returns True if valid. Raises ValueError with joined error messages if invalid.
    """
    if not isinstance(dossier, dict):
        raise ValueError("dossier must be a dict")

    errors: List[str] = []

    # Optional metadata (required after write)
    if "schema_version" in dossier and not isinstance(dossier["schema_version"], str):
        errors.append("schema_version must be string")
    if "dossier_checksum" in dossier and not isinstance(dossier["dossier_checksum"], str):
        errors.append("dossier_checksum must be string")
    if "dossier_checksum" in dossier and len(dossier.get("dossier_checksum", "")) != 64:
        errors.append("dossier_checksum must be 64-char hex (SHA256)")

    # Meta: when present, require engine_version and generation_timestamp (schema spec)
    if "meta" in dossier:
        if not isinstance(dossier["meta"], dict):
            errors.append("meta must be object")
        else:
            meta = dossier["meta"]
            if "engine_version" not in meta:
                errors.append("meta must contain engine_version")
            if "generation_timestamp" not in meta:
                errors.append("meta must contain generation_timestamp")
            if "run_manifest" in meta:
                if not isinstance(meta["run_manifest"], dict):
                    errors.append("meta.run_manifest must be object")
                elif "policy_mode" not in meta["run_manifest"]:
                    errors.append("meta.run_manifest must contain policy_mode")

    # Multiscale: R1, R2, R3, R4, global_structure
    if "R1" in dossier or "R2" in dossier or "global_structure" in dossier:
        for key in ("R1", "R2", "R3", "R4"):
            if key not in dossier:
                errors.append(f"multiscale dossier missing {key}")
            elif not isinstance(dossier[key], list):
                errors.append(f"{key} must be array")
            else:
                for i, entry in enumerate(dossier[key]):
                    errors.extend(_check_segment_entry(entry, key, i))
        if "global_structure" not in dossier:
            errors.append("multiscale dossier missing global_structure")
        elif not isinstance(dossier["global_structure"], dict):
            errors.append("global_structure must be object")
        else:
            gs = dossier["global_structure"]
            for k in GLOBAL_STRUCTURE_KEYS:
                if k not in gs:
                    errors.append(f"global_structure missing {k}")
    else:
        # Single-run: run, text_preview, L1..L9, diagnostics
        if "run" not in dossier:
            errors.append("single-run dossier missing run")
        if "text_preview" not in dossier:
            errors.append("single-run dossier missing text_preview")
        for lid in REQUIRED_LAYERS:
            key = f"L{lid}"
            if key not in dossier:
                errors.append(f"single-run dossier missing {key}")
            elif not isinstance(dossier.get(key), dict):
                errors.append(f"single-run {key} must be object")
        if "diagnostics" not in dossier:
            errors.append("single-run dossier missing diagnostics")
        elif not isinstance(dossier["diagnostics"], dict):
            errors.append("single-run diagnostics must be object")

    if errors:
        raise ValueError("Dossier schema validation failed: " + "; ".join(errors))
    return True
