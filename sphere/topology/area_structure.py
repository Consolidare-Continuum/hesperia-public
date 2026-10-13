# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
LEVEL 1 area structure loader (TFP / Kernberg domain).
Loads spec/area_structure_tfp.yaml: 12 areas (A1–A12) with purpose and adjacency.
Used for reporting, diagnostics, and domain labels; topology graph remains in topology_loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "spec" / "area_structure_tfp.yaml"


def load_area_structure_tfp(path: str | Path | None = None) -> dict[str, Any]:
    """
    Load LEVEL 1 area structure from YAML (T1.1 areas, T1.2 purpose, T1.3 adjacency).
    Returns dict with keys: version, domain, language, public_area_count, areas (list), area_distance_matrix.
    """
    p = Path(path) if path is not None else _DEFAULT_PATH
    if not p.exists():
        raise FileNotFoundError(f"Area structure spec not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Area structure must be a YAML object, got {type(data).__name__}")
    if "areas" not in data:
        raise ValueError("Area structure must have top-level 'areas' key")
    if not isinstance(data["areas"], list):
        raise ValueError("Area structure 'areas' must be a list")
    return data


def get_operational_area_neighbors(area_index: int, path: str | Path | None = None) -> list[int]:
    """Return list of neighboring area indices (0–11) for the given area. From YAML area_neighbors."""
    data = load_area_structure_tfp(path)
    for a in data["areas"]:
        if a.get("area_index") == area_index:
            return list(a.get("area_neighbors", []))
    return []


def get_area_distance_matrix(path: str | Path | None = None) -> list[list[int]]:
    """Return 12×12 shortest-path distance matrix (full icosahedron 0–11). From YAML."""
    data = load_area_structure_tfp(path)
    matrix = data.get("area_distance_matrix")
    expected = int(data.get("public_area_count") or 12)
    if not matrix or len(matrix) != expected:
        raise ValueError(
            f"Area structure must have area_distance_matrix with {expected} rows"
        )
    return [list(row) for row in matrix]
