"""Immutable context snapshots between phases."""

from __future__ import annotations

import copy
import json
from types import MappingProxyType
from typing import Any


def freeze_context(ctx: dict[str, Any]) -> dict[str, Any]:
    frozen = copy.deepcopy(dict(ctx))
    frozen["modules"] = MappingProxyType(frozen.get("modules", {}))
    return frozen


def hash_context(ctx: dict[str, Any]) -> str:
    payload = json.dumps(ctx, sort_keys=True, ensure_ascii=True, default=str)
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

