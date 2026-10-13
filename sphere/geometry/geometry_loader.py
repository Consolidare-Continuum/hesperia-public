# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural geometry loader. Loads family and area geometry specs; builds canonical index.
No business logic—data loading and indexing only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ALLOWED_BOUNDARY_CLASSES = frozenset({"internal", "edge", "corner", "bridge"})
ALLOWED_BOUNDARY_TYPES = frozenset({"closed", "open", "bridge", "terminal"})
ALLOWED_GEOMETRY_ROLES = frozenset({"standard", "hub", "peripheral", "connector"})


def load_family_geometry(path: str | Path) -> dict[str, Any]:
    """
    Load family geometry spec from YAML. Returns dict with 'version' and 'families' (list).
    Does not validate; use boundary_validator for that.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Family geometry spec not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Family geometry must be a YAML object, got {type(data).__name__}")
    if "families" not in data:
        raise ValueError("Family geometry must have top-level 'families' key")
    if not isinstance(data["families"], list):
        raise ValueError("Family geometry 'families' must be a list")
    return data


def load_area_geometry(path: str | Path) -> dict[str, Any]:
    """
    Load area geometry spec from YAML. Returns dict with 'version' and 'areas' (list).
    Does not validate; use boundary_validator for that.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Area geometry spec not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Area geometry must be a YAML object, got {type(data).__name__}")
    if "areas" not in data:
        raise ValueError("Area geometry must have top-level 'areas' key")
    if not isinstance(data["areas"], list):
        raise ValueError("Area geometry 'areas' must be a list")
    return data


def build_geometry_index(
    family_geometry: dict[str, Any],
    area_geometry: dict[str, Any],
) -> dict[str, Any]:
    """
    Build canonical index from loaded family and area geometry.
    Returns:
      families_by_index: { family_index: family_record }
      areas_by_index: { area_index: area_record }
      families_by_area: { area_id: [family_indices] }
      boundary_families: [ family_indices with boundary_class in (edge, corner, bridge) ]
      bridge_families: [ family_indices with boundary_class == 'bridge' ]
    """
    families = list(family_geometry.get("families") or [])
    areas = list(area_geometry.get("areas") or [])

    families_by_index: dict[int, dict[str, Any]] = {}
    for f in families:
        if not isinstance(f, dict):
            continue
        idx = f.get("family_index")
        if idx is None:
            continue
        families_by_index[int(idx)] = dict(f)

    areas_by_index: dict[int, dict[str, Any]] = {}
    for a in areas:
        if not isinstance(a, dict):
            continue
        idx = a.get("area_index")
        if idx is None:
            continue
        areas_by_index[int(idx)] = dict(a)

    families_by_area: dict[int, list[int]] = {}
    for area_rec in areas_by_index.values():
        aid = int(area_rec.get("area_index", -1))
        members = area_rec.get("family_members") or area_rec.get("family_range")
        if members is None:
            continue
        if isinstance(members, list):
            families_by_area[aid] = [int(x) for x in members]
        else:
            # family_range as [start, end] inclusive
            r = members if isinstance(members, (list, tuple)) else []
            if len(r) >= 2:
                families_by_area[aid] = list(range(int(r[0]), int(r[1]) + 1))

    boundary_families: list[int] = []
    bridge_families: list[int] = []
    for idx, rec in families_by_index.items():
        bc = rec.get("boundary_class") or "internal"
        if bc in ("edge", "corner", "bridge"):
            boundary_families.append(idx)
        if bc == "bridge":
            bridge_families.append(idx)

    return {
        "families_by_index": families_by_index,
        "areas_by_index": areas_by_index,
        "families_by_area": families_by_area,
        "boundary_families": boundary_families,
        "bridge_families": bridge_families,
    }
