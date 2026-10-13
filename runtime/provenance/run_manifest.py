# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA run manifest.
Records execution parameters for full reproducibility inside the dossier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _serialize_value(v: Any) -> Any:
    """Make value JSON-serializable (Path -> str, etc.)."""
    if v is None:
        return None
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _serialize_value(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_serialize_value(x) for x in v]
    return str(v)


def build_run_manifest(
    args: Any,
    defaults: Dict[str, Any],
    profile_id: str | None,
    profile: Dict[str, Any] | None,
    assets_root: Path | str | None,
) -> Dict[str, Any]:
    """
    Build run manifest for embedding in dossier meta.
    Captures policy_mode, profile_id, assets_root, defaults_used, and cli_arguments.
    """
    policy_mode = getattr(args, "policy_mode", None) or (defaults.get("interpretation_policy_mode") if defaults else None) or "STRUCTURE_PLUS_CONTEXT"
    assets_str = str(assets_root) if assets_root else None
    defaults_used = _serialize_value(defaults) if isinstance(defaults, dict) else {}

    cli_arguments: Dict[str, Any] = {}
    if args is not None:
        for key in ("text", "out", "profile", "policy_mode", "write_dossier", "validate_dossier"):
            if hasattr(args, key):
                val = getattr(args, key)
                cli_arguments[key] = _serialize_value(val)

    return {
        "policy_mode": policy_mode,
        "profile_id": profile_id or "",
        "assets_root": assets_str,
        "defaults_used": defaults_used,
        "cli_arguments": cli_arguments,
    }
