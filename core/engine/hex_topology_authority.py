# HESPERIA — canonical hex topology (governed manifest + deterministic adjacency).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.topology.invariant_catalog import HEXES_PER_FAMILY, TOTAL_FAMILIES, TOTAL_HEXES

_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "assets" / "topology" / "hex_topology_v1.json"


@lru_cache(maxsize=1)
def load_hex_topology_manifest(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else _MANIFEST_PATH
    if not p.is_file():
        raise FileNotFoundError(f"hex topology manifest missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def validate_topology_invariants() -> None:
    """Assert manifest matches frozen invariant catalog."""
    m = load_hex_topology_manifest()
    hm = m.get("hex_model") or {}
    if int(hm.get("total_hexes", 0)) != int(TOTAL_HEXES):
        raise RuntimeError("hex_topology_v1.json total_hexes mismatch vs invariant_catalog")
    if int(hm.get("n_families", 0)) != int(TOTAL_FAMILIES):
        raise RuntimeError("hex_topology_v1.json n_families mismatch")
    if int(hm.get("hexes_per_family", 0)) != int(HEXES_PER_FAMILY):
        raise RuntimeError("hex_topology_v1.json hexes_per_family mismatch")


def global_hex_id(family_id: int, local_hex_index: int) -> int:
    """Canonical linear hex index u ∈ [0, TOTAL_HEXES)."""
    if not (0 <= family_id < TOTAL_FAMILIES):
        raise ValueError(f"family_id {family_id} out of range")
    if not (0 <= local_hex_index < HEXES_PER_FAMILY):
        raise ValueError(f"local_hex_index {local_hex_index} out of range")
    return int(family_id * HEXES_PER_FAMILY + local_hex_index)


def split_global_hex_id(u: int) -> tuple[int, int]:
    if not (0 <= u < TOTAL_HEXES):
        raise ValueError(f"global hex u={u} out of range")
    return u // HEXES_PER_FAMILY, u % HEXES_PER_FAMILY


def neighbor_global_hex_ids(u: int) -> tuple[int, int]:
    """
    Fixed undirected ring neighbors on the family-local cycle (no dynamic discovery).
    Returns (left_neighbor_u, right_neighbor_u) in global linear indexing.
    """
    fam, loc = split_global_hex_id(u)
    left_loc = (loc - 1) % HEXES_PER_FAMILY
    right_loc = (loc + 1) % HEXES_PER_FAMILY
    return global_hex_id(fam, left_loc), global_hex_id(fam, right_loc)


__all__ = [
    "load_hex_topology_manifest",
    "validate_topology_invariants",
    "global_hex_id",
    "split_global_hex_id",
    "neighbor_global_hex_ids",
]
