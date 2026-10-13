# HESPERIA — LEVEL 2 family structure loader (TFP domain).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Load families_master.txt and families_structure_tfp.yaml.
Registry (T2.1) and structure: scope, observability, adjacency (T2.2–T2.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_SPEC_DIR = Path(__file__).resolve().parents[2] / "spec"
_MASTER_PATH = _SPEC_DIR / "families_master.txt"
_STRUCTURE_PATH = _SPEC_DIR / "families_structure_tfp.yaml"

OBSERVABILITY_LEVELS = frozenset({"высокий", "умеренный", "латентный"})


def load_families_master(path: str | Path | None = None) -> list[dict[str, str]]:
    """
    Load families_master.txt (T2.1). Returns list of dicts with area_id, family_id, family_name, family_definition.
    """
    p = Path(path) if path is not None else _MASTER_PATH
    if not p.exists():
        raise FileNotFoundError(f"Families master not found: {p}")
    text = p.read_text(encoding="utf-8")
    entries = []
    block: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if block:
                entries.append(block)
                block = {}
            continue
        if "\t" in line:
            key, val = line.split("\t", 1)
            block[key] = val
    if block:
        entries.append(block)
    return entries


def load_families_structure_tfp(path: str | Path | None = None) -> dict[str, Any]:
    """
    Load families_structure_tfp.yaml (T2.2 scope, T2.3 observability, T2.4 adjacency).
    Returns dict with version, domain, families (list of family dicts).
    """
    p = Path(path) if path is not None else _STRUCTURE_PATH
    if not p.exists():
        raise FileNotFoundError(f"Families structure not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "families" not in data:
        raise ValueError("Families structure must have top-level 'families' list")
    return data


def get_family_by_id(family_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    """Return structure entry for family_id or None."""
    data = load_families_structure_tfp(path)
    for f in data["families"]:
        if f.get("family_id") == family_id:
            return f
    return None
