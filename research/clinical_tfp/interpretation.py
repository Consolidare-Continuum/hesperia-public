# HESPERIA — LEVEL 8 Clinical interpretation layer
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Convert activation scores (areas / families / concepts) into structured clinical
interpretation consistent with TFP / Kernberg model.
"""

from __future__ import annotations

from typing import Any

# A3 Defensive Operations: family → clinical pattern name
DEFENSE_MAP = {
    "A3_F1": "splitting",
    "A3_F2": "idealization_devaluation",
    "A3_F3": "dissociation",
    "A3_F4": "projection",
    "A3_F5": "projective_identification",
    "A3_F6": "role_reversal",
}

# A2 Object Relations: family → object relation pattern
OBJECT_RELATION_MAP = {
    "A2_F1": "self_representation",
    "A2_F2": "part_object",
    "A2_F3": "persecutory_object",
    "A2_F4": "bond",
    "A2_F5": "identity_diffusion",
    "A2_F6": "integrated_object",
}


def get_dominant_area(area_scores: dict[str, float]) -> str:
    """Область с максимальной оценкой; пустая строка если словарь пуст."""
    if not area_scores:
        return ""
    return max(area_scores, key=lambda k: area_scores[k])


def get_dominant_family(family_scores: dict[str, float]) -> str:
    """Семья с максимальной оценкой; пустая строка если словарь пуст."""
    if not family_scores:
        return ""
    return max(family_scores, key=lambda k: family_scores[k])


def classify_aggression_level(area_scores: dict[str, float], area_a4: str = "A4") -> str:
    """
    Уровень агрессии по оценке области A4.
    A4 < 0.25 → low; 0.25–0.6 → moderate; > 0.6 → high.
    """
    score = (area_scores or {}).get(area_a4, 0.0)
    if score < 0.25:
        return "low"
    if score <= 0.6:
        return "moderate"
    return "high"


def detect_defense_pattern(
    family_scores: dict[str, float],
    defense_map: dict[str, str] | None = None,
) -> str:
    """
    Доминантный паттерн защиты по семьям A3. Возвращает имя из DEFENSE_MAP
    для семьи A3 с максимальной оценкой среди A3_*.
    """
    m = defense_map or DEFENSE_MAP
    a3_families = {k: v for k, v in (family_scores or {}).items() if k.startswith("A3_")}
    if not a3_families:
        return ""
    dominant = max(a3_families, key=lambda k: a3_families[k])
    return m.get(dominant, dominant)


def detect_object_relation_pattern(
    family_scores: dict[str, float],
    object_map: dict[str, str] | None = None,
) -> str:
    """
    Паттерн объектных отношений по семьям A2. Возвращает имя из OBJECT_RELATION_MAP
    для семьи A2 с максимальной оценкой среди A2_*.
    """
    m = object_map or OBJECT_RELATION_MAP
    a2_families = {k: v for k, v in (family_scores or {}).items() if k.startswith("A2_")}
    if not a2_families:
        return ""
    dominant = max(a2_families, key=lambda k: a2_families[k])
    return m.get(dominant, dominant)


def estimate_relational_capacity(area_scores: dict[str, float], area_a7: str = "A7") -> str:
    """
    Оценка реляционной способности по области A7 (Love / Relational Capacity).
    A7 > 0.6 → high; 0.3–0.6 → moderate; < 0.3 → low.
    """
    score = (area_scores or {}).get(area_a7, 0.0)
    if score > 0.6:
        return "high"
    if score >= 0.3:
        return "moderate"
    return "low"


def interpret_session(activation_result: dict[str, Any]) -> dict[str, Any]:
    """
    Преобразовать результат активации (areas, families, concepts) в структурированную
    клиническую интерпретацию в духе TFP / Kernberg.

    Вход: { "areas": {...}, "families": {...}, "concepts": {...} }
    Выход: dominant_area, dominant_family, secondary_area, defense_pattern,
           object_relation_pattern, aggression_level, relational_capacity.
    """
    areas = activation_result.get("areas") or {}
    families = activation_result.get("families") or {}

    dominant_area = get_dominant_area(areas)
    dominant_family = get_dominant_family(families)

    # Вторичная область: вторая по оценке
    secondary_area = ""
    if len(areas) >= 2:
        sorted_areas = sorted(areas, key=lambda k: areas[k], reverse=True)
        secondary_area = sorted_areas[1]

    aggression_level = classify_aggression_level(areas)
    defense_pattern = detect_defense_pattern(families)
    object_relation_pattern = detect_object_relation_pattern(families)
    relational_capacity = estimate_relational_capacity(areas)

    return {
        "dominant_area": dominant_area,
        "dominant_family": dominant_family,
        "secondary_area": secondary_area,
        "defense_pattern": defense_pattern,
        "object_relation_pattern": object_relation_pattern,
        "aggression_level": aggression_level,
        "relational_capacity": relational_capacity,
    }
