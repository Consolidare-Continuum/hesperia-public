# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Bind concepts to matrix coordinates (read-only lookup).
"""

from __future__ import annotations

from typing import Any, TypedDict

from hesperia.extensions.triz.models import ConceptActivation, MatrixCoordinate
from hesperia.extensions.triz.topology_metrics import areas_are_adjacent


class ConceptPlacementDict(TypedDict, total=False):
    area_id: int
    family_id: int
    hex_id: int | None


class ContradictionTopologyBinding(TypedDict):
    concept_a: str
    concept_b: str
    area_a: int | None
    family_a: int | None
    hex_a: int | None
    area_b: int | None
    family_b: int | None
    hex_b: int | None
    same_area: bool
    adjacent_areas: bool
    locality_score: float


def bind_concepts_to_coordinates(
    concept_activations: list[ConceptActivation],
) -> dict[str, MatrixCoordinate]:
    """concept_id → MatrixCoordinate (from each activation row)."""
    return {
        a.concept_id: a.coordinate
        for a in sorted(concept_activations, key=lambda x: x.concept_id)
    }


def bind_concept_to_matrix(
    concept_id: str,
    concept_to_area_family_hex: dict[str, Any],
) -> MatrixCoordinate:
    """
    Read resolved placement only. Missing concept → area_id/family_id -1, hex_id None.
    """
    raw = concept_to_area_family_hex.get(concept_id)
    if raw is None:
        return MatrixCoordinate(area_id=-1, family_id=-1, hex_id=None)
    if isinstance(raw, MatrixCoordinate):
        return raw
    if isinstance(raw, dict):
        a = raw.get("area_id", raw.get("area", -1))
        f = raw.get("family_id", raw.get("family", -1))
        h = raw.get("hex_id", raw.get("hex"))
        try:
            ai = int(a) if a is not None else -1
        except (TypeError, ValueError):
            ai = -1
        try:
            fi = int(f) if f is not None else -1
        except (TypeError, ValueError):
            fi = -1
        hi: int | None
        if h is None:
            hi = None
        else:
            try:
                hi = int(h)
            except (TypeError, ValueError):
                hi = None
        return MatrixCoordinate(area_id=ai, family_id=fi, hex_id=hi)
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        hi = None
        if len(raw) > 2 and raw[2] is not None:
            try:
                hi = int(raw[2])
            except (TypeError, ValueError):
                hi = None
        return MatrixCoordinate(
            area_id=int(raw[0]),
            family_id=int(raw[1]),
            hex_id=hi,
        )
    return MatrixCoordinate(area_id=-1, family_id=-1, hex_id=None)


def bind_contradiction_to_topology(
    contradiction: Any,
    concept_mapping: dict[str, Any],
) -> ContradictionTopologyBinding:
    """Enrich contradiction with matrix endpoints and adjacency flags."""
    from hesperia.extensions.triz.topology_metrics import contradiction_locality_score

    ca = contradiction.concept_a
    cb = contradiction.concept_b
    ma = bind_concept_to_matrix(ca, concept_mapping)
    mb = bind_concept_to_matrix(cb, concept_mapping)
    aa, ab = ma.area_id, mb.area_id
    same = aa >= 0 and ab >= 0 and aa == ab
    adj = False
    loc = 1.0
    if aa >= 0 and ab >= 0:
        adj = areas_are_adjacent(aa, ab)
        loc = contradiction_locality_score(aa, ab)
    return ContradictionTopologyBinding(
        concept_a=ca,
        concept_b=cb,
        area_a=aa if aa >= 0 else None,
        family_a=ma.family_id if ma.family_id >= 0 else None,
        hex_a=ma.hex_id,
        area_b=ab if ab >= 0 else None,
        family_b=mb.family_id if mb.family_id >= 0 else None,
        hex_b=mb.hex_id,
        same_area=same,
        adjacent_areas=adj,
        locality_score=round(loc, 6),
    )
