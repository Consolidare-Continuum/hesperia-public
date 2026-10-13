# HESPERIA — Public schema validation. Fail if internal-revealing key appears before serialization.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Assertion before serialization. Walks every node in the JSON tree.

Graduated to core 2026-07-31 (was runtime/shipping/schema_guard.py) — pure computation over a
dict/list tree plus one static schema-file read, no runtime-layer dependency. It was reached by
core/engine/projection/schema_enforcer.py, which the core/engine graduation pass turned into a
"core imports runtime" RAD violation; moving the real implementation here (with the old runtime
path kept as a thin re-export shim) closes that without changing behavior for any caller.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


FORBIDDEN_KEY_SUBSTRINGS = (
    "sphere", "hex", "topology", "bridge", "side_id", "area_id", "family_id",
    "layer_", "adjacency", "propagation_path", "propagation_algorithm", "grid", "graph", "embedding",
    "vector_space", "internal_layer", "topology_index", "area11", "family240",
)

# Module/class names that must never appear in any error response
FORBIDDEN_RESPONSE_SUBSTRINGS = (
    "core.services",
    "runtime.shipping",
    "analysis_service",
)

# Ambiguous generic terms that are disallowed as standalone response keys.
# Goal: force explicit typed vocabulary (e.g. constraint_status, resistance_index).
AMBIGUOUS_EXACT_KEYS = frozenset(
    {
        "model",
        "topology",
        "geometry",
        "propagation",
        "dynamics",
        "concept",
        "mapping",
        "pipeline",
        "processing",
        "result",
        "feature",
        "parameter",
        "input",
        "signal",
        "score",
        "weight",
        "interaction",
        "inhibition",
        "distribution",
        "dominant",
        "stability",
        "loop",
        "energy",
        "normalization",
        "state",
        "dictionary",
        "error",
        "anomaly",
        "evaluation",
        "consistency",
        "drift",
        "alignment",
        "semantic",
        "analysis",
        "system",
        "module",
        "structure",
        "context",
        "segment",
    }
)

# Backward-compat keys intentionally still allowed for now.
LEGACY_COMPAT_KEYS = frozenset(
    {
        "governance",
        "loopability",
        "obstacle_score",
        "dominant_area",
        "dominant_family",
        "error",
    }
)


def _check_key(key: str) -> None:
    """Raise ValueError if key contains a forbidden substring."""
    kl = key.lower()
    if kl in AMBIGUOUS_EXACT_KEYS and kl not in LEGACY_COMPAT_KEYS:
        raise ValueError(f"public_schema_violation: ambiguous standalone key '{key}' is not allowed")
    for bad in FORBIDDEN_KEY_SUBSTRINGS:
        if bad in kl:
            raise ValueError(f"public_schema_violation: key '{key}' contains forbidden term '{bad}'")


def _walk(obj: object) -> None:
    """
    Walk every node in the JSON tree. Check every dict key; recurse into dict values and list elements.
    Ensures nested structures (comparison output, list-of-dicts, etc.) cannot bypass the guard.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_key(k)
            _walk(v)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item)


def validate_against_public_schema(output: dict | list) -> None:
    """
    Validate output before serialization. Walks every node; raises ValueError if any key
    (including nested in lists) contains a forbidden substring.
    """
    _walk(output)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_public_output_top_level_allowlist() -> frozenset[str]:
    """Keys declared under ``schemas/public/public_output_schema.json`` ``properties``."""
    path = _repo_root() / "assets" / "schemas" / "public" / "public_output_schema.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    props = data.get("properties") or {}
    return frozenset(str(k) for k in props.keys())


def validate_public_top_level_keys_allowlisted(output: dict) -> None:
    """
    **Product truth (strict):** reject unknown top-level keys on projected public dict.

    Enable with ``HESPERIA_PUBLIC_SCHEMA_STRICT_KEYS=1``. Nested ``payload`` is not recursed
    (schema allows arbitrary payload); only envelope keys are checked.
    """
    allowed = load_public_output_top_level_allowlist()
    for k in output.keys():
        if k not in allowed:
            raise ValueError(f"public_schema_violation: unknown top-level key {k!r} (not in public schema properties)")


def validate_public_schema_strict(output: dict | list) -> None:
    """Forbidden-substring walk + optional allowlisted top-level keys (env-gated)."""
    validate_against_public_schema(output)
    if os.environ.get("HESPERIA_PUBLIC_SCHEMA_STRICT_KEYS", "").strip() in ("1", "true", "yes"):
        if isinstance(output, dict):
            validate_public_top_level_keys_allowlisted(output)
