# HESPERIA — Affect-Defense Coupling (Kernberg)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Ключевой механизм Кернберга: affect → defense activation.
Связывает A1 (affect), A3 (defenses), A4 (aggression).
Примеры: anger → splitting, shame → projection, envy → devaluation.
"""

from __future__ import annotations

from typing import Any

# Аффект (A1-релевантные маркеры / области) → типичная защита (A3 family)
AFFECT_TO_DEFENSE = {
    "anger": "A3_F1",       # splitting
    "rage": "A3_F1",
    "shame": "A3_F4",       # projection
    "envy": "A3_F2",        # idealization_devaluation (devaluation)
    "guilt": "A3_F4",
    "anxiety": "A3_F3",     # dissociation
    "fear": "A3_F4",
}

DEFENSE_NAMES = {
    "A3_F1": "splitting",
    "A3_F2": "idealization_devaluation",
    "A3_F3": "dissociation",
    "A3_F4": "projection",
    "A3_F5": "projective_identification",
    "A3_F6": "role_reversal",
}


def infer_affect_from_areas(areas: dict[str, float]) -> str:
    """По областям A1, A4 грубо вывести доминантный аффект."""
    a1 = areas.get("A1", 0.0)
    a4 = areas.get("A4", 0.0)
    if a4 >= 0.5:
        return "anger" if a4 >= 0.7 else "rage"
    if a1 >= 0.4:
        return "anxiety"
    return ""


def couple_affect_defense(
    activation: dict[str, Any],
    dominant_affect: str | None = None,
) -> dict[str, Any]:
    """
    По активации и опционально заданному аффекту вернуть ожидаемую связку affect → defense.
    Возвращает: { "affect": str, "expected_defense": str, "expected_family": str,
                  "actual_defense_scores": dict, "coupling_strength": float }.
    """
    areas = activation.get("areas") or {}
    families = activation.get("families") or {}
    affect = dominant_affect or infer_affect_from_areas(areas)
    expected_family = AFFECT_TO_DEFENSE.get(affect, "")
    expected_defense = DEFENSE_NAMES.get(expected_family, "")
    a3 = {k: v for k, v in families.items() if k.startswith("A3_")}
    actual = a3.get(expected_family, 0.0)
    coupling = min(1.0, actual * 1.2) if expected_family else 0.0
    return {
        "affect": affect,
        "expected_defense": expected_defense,
        "expected_family": expected_family,
        "actual_defense_scores": a3,
        "coupling_strength": round(coupling, 3),
    }
