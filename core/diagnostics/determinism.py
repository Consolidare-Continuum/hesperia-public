"""Deterministic serialization and hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.dynamics.numeric import quantize


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        return quantize(obj)
    return obj


def canonical_json(obj: Any) -> str:
    normalized = _normalize(obj)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_hash(output: Any) -> str:
    payload = canonical_json(output).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

