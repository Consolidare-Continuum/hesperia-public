# HESPERIA — Semantic→GCS lookup J_sem→gcs + spacing_factor (24_SPEC §4.4, §6 / METRIC-26).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

from functools import lru_cache
from typing import Any

from core.topology.invariant_catalog import AREAS, FAMILIES_PER_AREA, TOTAL_FAMILIES

SEMANTIC_HEX_COUNT = 72000
HEXES_PER_FAMILY_SEMANTIC = 250
GCS_HEX_SLOT_250 = 250
GCS_HEX_SLOT_251 = 251
PENTAGON_POLE_COUNT = 12
EXTRA_HEX_PER_PENTAGON_POLE = 20


def _family_gcs_slot_count(family_index: int) -> int:
    """anchor_map_v1 rule: family_index_in_area % 6 == 0 → 250; else 251."""
    family_index_in_area = family_index % FAMILIES_PER_AREA
    return GCS_HEX_SLOT_250 if family_index_in_area % 6 == 0 else GCS_HEX_SLOT_251


def spacing_factor(family_index: int) -> float:
    """Local conformal factor for gcs_surface distance (24_SPEC §4.4).

    spacing_factor = slot_count / gcs_mean_hex_per_family
    where gcs_mean_hex_per_family = 72240 / 288 ≈ 250.8333...
    """
    slot_count = _family_gcs_slot_count(family_index)
    gcs_mean = 72240.0 / TOTAL_FAMILIES
    return slot_count / gcs_mean


@lru_cache(maxsize=1)
def _build_j_sem_to_gcs() -> dict[str, Any]:
    """Build the sparse J_sem→gcs assignment map.

    Each semantic hex (0..71999) maps to a GCS slot within its family.
    Families with 251 slots have geodesic_extra_index=250 for the extra slot.
    """
    mapping: list[int] = []
    gcs_offset = 0

    for fam in range(TOTAL_FAMILIES):
        slot_count = _family_gcs_slot_count(fam)
        for local_hex in range(HEXES_PER_FAMILY_SEMANTIC):
            mapping.append(gcs_offset + local_hex)
        gcs_offset += slot_count

    return {
        "semantic_hex_count": SEMANTIC_HEX_COUNT,
        "geodesic_hex_count": gcs_offset,
        "mapping": mapping,
    }


def sem_to_gcs(semantic_hex_index: int) -> int:
    """Map a semantic hex index (0..71999) to its GCS slot index."""
    j = _build_j_sem_to_gcs()
    m = j["mapping"]
    if not 0 <= semantic_hex_index < len(m):
        raise IndexError(f"semantic_hex_index {semantic_hex_index} out of range [0, {len(m)})")
    return m[semantic_hex_index]


def family_of_semantic_hex(semantic_hex_index: int) -> int:
    return semantic_hex_index // HEXES_PER_FAMILY_SEMANTIC


def gcs_extra_indices() -> list[int]:
    """Return GCS slot indices that are geodesic_extra_index (slot 250 in 251-slot families)."""
    extras: list[int] = []
    gcs_offset = 0
    for fam in range(TOTAL_FAMILIES):
        slot_count = _family_gcs_slot_count(fam)
        if slot_count == GCS_HEX_SLOT_251:
            extras.append(gcs_offset + GCS_HEX_SLOT_250)
        gcs_offset += slot_count
    return extras
