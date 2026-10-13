# HESPERIA — canonical concept registry loader.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REGISTRY_PATH = Path(__file__).resolve().parent / "concepts_registry.yaml"
_DEFAULT_CACHE: dict[str, Any] | None = None


def load_concepts_registry(path: Path | str | None = None) -> dict[str, Any]:
    """Load governed concept registry (versioned n_concept, id format)."""
    global _DEFAULT_CACHE
    p = Path(path) if path is not None else _REGISTRY_PATH
    if p == _REGISTRY_PATH and _DEFAULT_CACHE is not None:
        return dict(_DEFAULT_CACHE)
    if not p.is_file():
        raise FileNotFoundError(f"concepts_registry missing: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("concepts_registry must be a mapping")
    nc = int(data.get("n_concept", 0))
    if nc < 1:
        raise ValueError("n_concept must be >= 1")
    if p == _REGISTRY_PATH:
        _DEFAULT_CACHE = dict(data)
    return dict(data)


def concepts_registry_version(path: Path | str | None = None) -> str:
    return str(load_concepts_registry(path).get("registry_version", "unknown"))


def n_concept_canon(path: Path | str | None = None) -> int:
    return int(load_concepts_registry(path)["n_concept"])


def concept_id_for_index(index: int, *, registry_path: Path | str | None = None) -> str:
    reg = load_concepts_registry(registry_path)
    fmt = str(reg.get("concept_id_format", "HESP-C{index:04d}"))
    if "{index:04d}" in fmt:
        return fmt.format(index=int(index))
    if "{index}" in fmt:
        return fmt.format(index=int(index))
    raise ValueError("concept_id_format must contain {index:04d} or {index}")


def concept_record(index: int, path: Path | str | None = None) -> dict[str, Any]:
    """Single concept row: concept_id, concept_index, linked_family, metadata."""
    reg = load_concepts_registry(path)
    nc = int(reg["n_concept"])
    i = int(index)
    if not (0 <= i < nc):
        raise ValueError(f"concept_index {i} out of range [0, {nc})")
    ident = reg.get("identity_mapping") or {}
    if ident.get("linked_family_equals_concept_index"):
        lf = i
    else:
        raise NotImplementedError("Only identity linked_family is implemented in v0.5 registry")
    return {
        "concept_id": concept_id_for_index(i, registry_path=path),
        "concept_index": i,
        "linked_family": lf,
        "metadata": {
            "registry_version": reg.get("registry_version"),
            "schema_id": reg.get("schema_id"),
        },
    }


__all__ = [
    "load_concepts_registry",
    "concepts_registry_version",
    "n_concept_canon",
    "concept_id_for_index",
    "concept_record",
]
