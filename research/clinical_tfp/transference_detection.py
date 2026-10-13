# HESPERIA — Transference Detection Layer (TFP)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Detect positive/negative transference, projective identification, idealization, devaluation
from phrase patterns, speaker direction (activation_by_direction), and concept clusters.
"""

from __future__ import annotations

from typing import Any

# Family clusters that signal transference type (A2 object relations, A3 defenses)
PERSECUTORY_FAMILIES = {"A2_F3"}  # persecutory object → negative transference
IDEALIZATION_FAMILIES = {"A3_F1"}  # splitting/idealization pole
DEVALUATION_FAMILIES = {"A3_F2"}   # idealization_devaluation
PROJECTIVE_ID_FAMILIES = {"A3_F5"}  # projective identification
BOND_FAMILIES = {"A2_F4"}          # bond → positive transference
INTEGRATED_OBJECT_FAMILIES = {"A2_F6"}  # integrated object → positive


def _score_families(families: dict[str, float], family_set: set[str]) -> float:
    if not families:
        return 0.0
    return sum(families.get(f, 0.0) for f in family_set)


def detect_transference(
    activation: dict[str, Any],
    direction_key: str = "patient_to_therapist",
) -> dict[str, Any]:
    """
    From activation (with activation_by_direction), detect transference types.

    Uses:
    - activation_by_direction[direction_key].families → persecutory, idealization, devaluation, projective_id
    - activation_by_direction[direction_key].areas → A4 aggression for negative
    - activation.areas A7 → positive relational capacity

    Returns:
    {
      "positive_transference": bool or score,
      "negative_transference": bool or score,
      "projective_identification": bool or score,
      "idealization": bool or score,
      "devaluation": bool or score,
      "persecutory_object": bool or score,
    }
    """
    by_dir = (activation.get("activation_by_direction") or {}).get(direction_key) or {}
    families = by_dir.get("families") or activation.get("families") or {}
    areas = by_dir.get("areas") or activation.get("areas") or {}

    persecutory = _score_families(families, PERSECUTORY_FAMILIES)
    idealization = _score_families(families, IDEALIZATION_FAMILIES)
    devaluation = _score_families(families, DEVALUATION_FAMILIES)
    projective_id = _score_families(families, PROJECTIVE_ID_FAMILIES)
    bond = _score_families(families, BOND_FAMILIES)
    integrated = _score_families(families, INTEGRATED_OBJECT_FAMILIES)
    a4 = areas.get("A4", 0.0)
    a7 = areas.get("A7", 0.0)

    # Thresholds (normalized scores ~0..1)
    thresh = 0.15
    return {
        "positive_transference": bond + integrated + a7 > thresh,
        "negative_transference": persecutory + a4 > thresh,
        "projective_identification": projective_id > thresh,
        "idealization": idealization > thresh,
        "devaluation": devaluation > thresh,
        "persecutory_object": persecutory > thresh,
        "scores": {
            "persecutory": round(persecutory, 3),
            "idealization": round(idealization, 3),
            "devaluation": round(devaluation, 3),
            "projective_identification": round(projective_id, 3),
            "bond": round(bond, 3),
            "integrated_object": round(integrated, 3),
            "A4_aggression": round(a4, 3),
            "A7_love_capacity": round(a7, 3),
        },
    }


def transference_summary(activation: dict[str, Any]) -> dict[str, Any]:
    """
    Run transference detection for patient→therapist and therapist→patient;
    return summary with labels per direction.
    """
    out: dict[str, Any] = {
        "patient_to_therapist": detect_transference(activation, "patient_to_therapist"),
        "therapist_to_patient": detect_transference(activation, "therapist_to_patient"),
        "patient_to_third": detect_transference(activation, "patient_to_third"),
    }
    return out
