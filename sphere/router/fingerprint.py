"""Deterministic router fingerprint — HSR-V7-04."""

from __future__ import annotations

import hashlib
import json
from typing import Any

ROUTER_FINGERPRINT_VERSION = "v0_1"

# Canonical field order for hashing (Ethan spec §7.1).
_FINGERPRINT_PARTS = (
    "input_hash",
    "engine_trace_hash",
    "retrieval_snapshot_hash",
    "policy_snapshot_id",
    "router_version",
    "enabled_modules",
)


def fingerprint_contract_v0_1() -> dict[str, Any]:
    """Versioning contract for routed packets (Gena HSR-V7-04)."""
    return {
        "contract_id": "hesperia.router_fingerprint.v0_1",
        "algorithm": "sha256",
        "encoding": "hex",
        "canonical_json": True,
        "parts": list(_FINGERPRINT_PARTS),
        "formula": "sha256(canonical_json({parts}))",
        "router_version_prefix": "v7-router-",
    }


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hash_object(obj: Any) -> str:
    if obj is None:
        return _sha256_hex("")
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_hex(canonical)


def compute_router_fingerprint(
    *,
    input_hash: str,
    engine_trace: dict[str, Any] | None,
    retrieval_context: dict[str, Any] | None,
    policy_snapshot_id: str,
    router_version: str,
    enabled_modules: list[str] | None = None,
) -> str:
    """
    Deterministic provenance fingerprint before LLM call.

    retrieval_snapshot_hash derived from retrieval_context canonical JSON.
    """
    parts = {
        "input_hash": input_hash,
        "engine_trace_hash": _hash_object(engine_trace or {}),
        "retrieval_snapshot_hash": _hash_object(retrieval_context or {}),
        "policy_snapshot_id": policy_snapshot_id,
        "router_version": router_version,
        "enabled_modules": sorted(enabled_modules or []),
    }
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_hex(canonical)
