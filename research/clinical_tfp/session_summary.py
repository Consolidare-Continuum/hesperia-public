# HESPERIA — Session Summary Generator (Clinical Card)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Клиническая карта сессии после анализа:
dominant affects, active defenses, object relations pattern, transference indicators.
"""

from __future__ import annotations

from typing import Any

from research.clinical_tfp.interpretation import (
    detect_defense_pattern,
    detect_object_relation_pattern,
    classify_aggression_level,
    get_dominant_area,
    get_dominant_family,
)
from research.clinical_tfp.transference_detection import transference_summary
from research.clinical_tfp.object_representation_tracking import track_object_representations
from research.clinical_tfp.affect_defense_coupling import couple_affect_defense, infer_affect_from_areas


def build_session_summary(
    activation: dict[str, Any],
    affect_intensity: float | None = None,
    timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    По результату активации (и опционально интенсивности аффекта, таймлайну) собрать
    клиническую карту: dominant affects, active defenses, object relations pattern,
    transference indicators, object representations.
    """
    areas = activation.get("areas") or {}
    families = activation.get("families") or {}

    dominant_area = get_dominant_area(areas)
    dominant_family = get_dominant_family(families)
    defense_pattern = detect_defense_pattern(families)
    object_relation_pattern = detect_object_relation_pattern(families)
    aggression_level = classify_aggression_level(areas)

    transference = transference_summary(activation)
    object_repr = track_object_representations(activation)
    coupling = couple_affect_defense(activation)
    dominant_affect = coupling.get("affect") or infer_affect_from_areas(areas)

    transference_indicators: list[str] = []
    for direction, det in transference.items():
        d = det if isinstance(det, dict) else {}
        if d.get("negative_transference"):
            transference_indicators.append(f"negative_transference ({direction})")
        if d.get("positive_transference"):
            transference_indicators.append(f"positive_transference ({direction})")
        if d.get("projective_identification"):
            transference_indicators.append(f"projective_identification ({direction})")
        if d.get("persecutory_object"):
            transference_indicators.append(f"persecutory_object ({direction})")

    return {
        "dominant_affects": [a for a in [dominant_affect] if a],
        "aggression_level": aggression_level,
        "affect_intensity": affect_intensity,
        "active_defenses": [defense_pattern] if defense_pattern else [],
        "defense_pattern": defense_pattern,
        "object_relations_pattern": object_relation_pattern,
        "object_representations": object_repr,
        "transference_indicators": transference_indicators,
        "transference_summary": transference,
        "affect_defense_coupling": coupling,
        "dominant_area": dominant_area,
        "dominant_family": dominant_family,
        "activation_by_direction": activation.get("activation_by_direction"),
        "timeline_stages": None,  # заполняется при переданном timeline через stage_from_timeline
    }


def build_session_summary_with_timeline(
    activation: dict[str, Any],
    timeline: list[dict[str, Any]],
    affect_intensity: float | None = None,
) -> dict[str, Any]:
    """То же что build_session_summary, плюс stage из последних окон таймлайна."""
    from research.clinical_tfp.stage_detection import stage_from_timeline

    summary = build_session_summary(activation, affect_intensity=affect_intensity, timeline=timeline)
    summary["timeline_stages"] = stage_from_timeline(timeline, last_n=min(3, len(timeline)))
    return summary
