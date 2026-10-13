# HESPERIA — GTP-05 support: legal-neighbor rule N(h) for GTPA.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""
Spec §10.1 (23_SPEC__) calls for N(h) from "loopability / traversal policy (area ring
steps, family patch steps, hex index steps — frozen graph)", citing an external
`40_POLICY__Loopability_and_traversal` document. That document does not exist yet
(neither in this repo nor in the brain-export mirror) — GTP is the first implementation
to need it. This module freezes the three step kinds using the real, existing
icosahedral area adjacency (`sphere.topology.topology_loader`) for area-ring steps,
plus a simple deterministic ring rule for family and hex steps, exactly as the spec
enumerates them. Documented here as the frozen rule for `gcs_id="GCS_NU85_v0_1"`
pending a real `40_POLICY` — same spirit as spec §6.2's "one rule per gcs_id, documented".
"""

from __future__ import annotations

from dataclasses import dataclass

from sphere.topology.topology_loader import get_icosahedral_adjacency
from core.topology.invariant_catalog import AREAS as NUM_AREAS, FAMILIES_PER_AREA

HEX_PER_FAMILY = 250  # INV-HEX-PER-FAM-SEM


@dataclass(frozen=True)
class HexCell:
    """(area_id, global_id, hex_index) per spec §5.1. global_id = area_id*24 + family_index_in_area."""

    area_id: int
    global_id: int
    hex_index: int

    def __post_init__(self) -> None:
        if not (0 <= self.area_id < NUM_AREAS):
            raise ValueError(f"area_id out of range: {self.area_id!r}")
        if not (0 <= self.global_id < NUM_AREAS * FAMILIES_PER_AREA):
            raise ValueError(f"global_id out of range: {self.global_id!r}")
        if self.global_id // FAMILIES_PER_AREA != self.area_id:
            raise ValueError(
                f"global_id {self.global_id} does not belong to area_id {self.area_id}"
            )
        if not (0 <= self.hex_index < HEX_PER_FAMILY):
            raise ValueError(f"hex_index out of range: {self.hex_index!r}")

    @property
    def family_index_in_area(self) -> int:
        return self.global_id % FAMILIES_PER_AREA


def _adjacent_areas(area_id: int) -> tuple[int, ...]:
    adj = get_icosahedral_adjacency()
    row = adj[area_id]
    return tuple(int(j) for j, v in enumerate(row) if v)


def legal_neighbors(h: HexCell) -> tuple[HexCell, ...]:
    """
    N(h): area-ring steps (icosahedral adjacency, family/hex held), family-patch steps
    (family_index_in_area +-1 mod 24, area/hex held), hex-index steps (hex_index +-1 mod 250,
    area/family held). Deterministic, order-stable.
    """
    out: list[HexCell] = []
    for area2 in _adjacent_areas(h.area_id):
        out.append(HexCell(area2, area2 * FAMILIES_PER_AREA + h.family_index_in_area, h.hex_index))
    for step in (-1, 1):
        fam2 = (h.family_index_in_area + step) % FAMILIES_PER_AREA
        out.append(HexCell(h.area_id, h.area_id * FAMILIES_PER_AREA + fam2, h.hex_index))
    for step in (-1, 1):
        hex2 = (h.hex_index + step) % HEX_PER_FAMILY
        out.append(HexCell(h.area_id, h.global_id, hex2))
    return tuple(out)
