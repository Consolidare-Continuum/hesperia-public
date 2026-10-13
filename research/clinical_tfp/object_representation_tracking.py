# HESPERIA — Object Representation Tracking (TFP)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Отслеживание образов объекта: therapist representation, self representation, third objects.
Примеры: «вы хороший», «вы ужасный» → A2 object relations (therapist representation).
"""

from __future__ import annotations

from typing import Any

# A2 families: object relations
SELF_REPRESENTATION_FAMILIES = {"A2_F1"}
THERAPIST_OBJECT_FAMILIES = {"A2_F2", "A2_F3", "A2_F4", "A2_F6"}  # part_object, persecutory, bond, integrated
THIRD_OBJECT_FAMILIES = {"A2_F2", "A2_F3", "A2_F5"}  # part_object, persecutory, identity_diffusion


def _score_families(families: dict[str, float], family_set: set[str]) -> float:
    if not families:
        return 0.0
    return sum(families.get(f, 0.0) for f in family_set)


def track_object_representations(
    activation: dict[str, Any],
    activation_by_direction: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    По activation и activation_by_direction вернуть срезы по типам объектной репрезентации.

    - therapist_representation: A2 в направлении patient→therapist (образ терапевта).
    - self_representation: A2_F1 (образ себя).
    - third_objects: A2 в направлении patient→third (образ третьего объекта).

    Возвращает:
    {
      "therapist_representation": { "areas": {}, "families": {}, "score": float },
      "self_representation": { "families": {}, "score": float },
      "third_objects": { "areas": {}, "families": {}, "score": float },
    }
    """
    by_dir = activation_by_direction or activation.get("activation_by_direction") or {}
    all_families = activation.get("families") or {}

    pt = by_dir.get("patient_to_therapist") or {}
    pt_families = pt.get("families") or {}
    pthird = by_dir.get("patient_to_third") or {}
    pthird_families = pthird.get("families") or {}

    therapist_score = _score_families(pt_families, THERAPIST_OBJECT_FAMILIES) or _score_families(
        all_families, THERAPIST_OBJECT_FAMILIES
    )
    self_score = _score_families(all_families, SELF_REPRESENTATION_FAMILIES)
    third_score = _score_families(pthird_families, THIRD_OBJECT_FAMILIES) or _score_families(
        all_families, THIRD_OBJECT_FAMILIES
    )

    a2_families = {k: v for k, v in all_families.items() if k.startswith("A2_")}
    pt_a2 = {k: v for k, v in pt_families.items() if k.startswith("A2_")}
    pthird_a2 = {k: v for k, v in pthird_families.items() if k.startswith("A2_")}

    return {
        "therapist_representation": {
            "families": pt_a2 or a2_families,
            "areas": pt.get("areas") or activation.get("areas") or {},
            "score": round(therapist_score, 3),
        },
        "self_representation": {
            "families": {k: v for k, v in a2_families.items() if k in SELF_REPRESENTATION_FAMILIES},
            "score": round(self_score, 3),
        },
        "third_objects": {
            "families": pthird_a2 or a2_families,
            "areas": pthird.get("areas") or {},
            "score": round(third_score, 3),
        },
    }
