from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_FILES = {
    "llm_audit": _ROOT / "llm_audit.json",
    "tfp_analysis": _ROOT / "tfp.json",
    "document_fingerprint": _ROOT / "document.json",
}


def load_profile(name: str) -> dict[str, Any]:
    p = _FILES.get(name)
    if p is None:
        raise ValueError(f"profile_unknown:{name}")
    out = json.loads(p.read_text(encoding="utf-8"))
    if str(out.get("name", "")) != name:
        raise ValueError(f"profile_name_mismatch:{name}")
    if not str(out.get("profile_version", "")).strip():
        raise ValueError(f"profile_version_missing:{name}")
    return out

