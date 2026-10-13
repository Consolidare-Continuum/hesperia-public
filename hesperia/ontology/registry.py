# HESPERIA — Ontology Registry (governance)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REGISTRY_PATH = Path(__file__).resolve().parent / "ontology_registry.yaml"
_CACHE: dict[str, Any] = {}


def load_ontology_registry(path: Path | str | None = None) -> dict[str, Any]:
    """Load ontology_registry.yaml: ontology_version, dictA_version, dictB_version, etc."""
    global _CACHE
    p = Path(path) if path is not None else _REGISTRY_PATH
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _CACHE.update(data)
    return dict(data)


def get_ontology_version(path: Path | str | None = None) -> str:
    """Return ontology_version (e.g. tfp_v1)."""
    if not _CACHE and path is None:
        load_ontology_registry()
    return _CACHE.get("ontology_version", "tfp_v1")


def get_dict_versions(path: Path | str | None = None) -> dict[str, str]:
    """Return dict of component -> version (dictA_version, dictB_version, ...)."""
    if not _CACHE and path is None:
        load_ontology_registry(path)
    reg = load_ontology_registry(path) if path else _CACHE
    return {
        "dictA": reg.get("dictA_version", "1.0"),
        "dictB": reg.get("dictB_version", "1.0"),
        "relations": reg.get("relations_version", "1.0"),
        "families": reg.get("families_version", "1.0"),
        "areas": reg.get("areas_version", "1.0"),
    }
