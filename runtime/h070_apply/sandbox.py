# HESPERIA 0.7.0 sandbox graph snapshot.
from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from typing import Any


def _edge_key(source: str, target: str) -> str:
    return f"{source}->{target}"


def create_sandbox(
    parent_edges: dict[str, float],
    *,
    parent_sha: str,
) -> dict[str, Any]:
    """G2: immutable parent SHA + mutable sandbox edge map."""
    sid = f"sbx-{uuid.uuid4().hex[:12]}"
    return {
        "sandbox_id": sid,
        "parent_sha": parent_sha,
        "created_ts": int(time.time()),
        "edges": copy.deepcopy(parent_edges),
    }


def sandbox_diff(before: dict[str, float], after: dict[str, float]) -> list[dict[str, Any]]:
    """G3: deterministic diff hunks."""
    hunks: list[dict[str, Any]] = []
    keys = sorted(set(before) | set(after))
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            hunks.append({"edge": k, "value_before": b, "value_after": a})
    return hunks


def graph_content_hash(edges: dict[str, float]) -> str:
    payload = json.dumps(edges, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
