"""Single source of truth for engine constants."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_engine_constants() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    path = root / "assets" / "config" / "engine_constants.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_constant(path: str, default: Any) -> Any:
    node: Any = load_engine_constants()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node

