"""Anchor loading and lookup for concept->hex projection."""

from __future__ import annotations

import json
from pathlib import Path


def load_anchor_registry(path: str | Path) -> dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Anchor registry must be a JSON object concept_id -> hex_id")
    return {str(k): str(v) for k, v in payload.items()}

