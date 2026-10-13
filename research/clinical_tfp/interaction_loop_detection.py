# HESPERIA — Interaction Loop Detection (TFP)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Обнаружение цикла: projection → therapist response → escalation.
Пример: patient accusation → therapist clarification → patient escalation → projective identification.
"""

from __future__ import annotations

from typing import Any

from research.clinical_tfp.intervention_classifier import classify_intervention


def _is_accusation(activation_slice: dict[str, Any]) -> bool:
    """Высокая A4 или A2_F3 (persecutory) — обвинение/агрессия в сторону терапевта."""
    areas = activation_slice.get("areas") or {}
    families = activation_slice.get("families") or {}
    a4 = areas.get("A4", 0.0)
    a2f3 = families.get("A2_F3", 0.0)
    return a4 >= 0.3 or a2f3 >= 0.3


def _is_escalation(prev: dict[str, Any], curr: dict[str, Any], area: str = "A4") -> bool:
    """Рост активации области (например A4) от предыдущего окна к текущему."""
    p = (prev.get("areas") or {}).get(area, 0.0)
    c = (curr.get("areas") or {}).get(area, 0.0)
    return c > p and (c - p) >= 0.15


def detect_interaction_loops(
    timeline: list[dict[str, Any]],
    therapist_utterances: list[tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    По таймлайну активации (и опционально репликам терапевта) найти циклы:
    patient accusation → therapist clarification → patient escalation.

    therapist_utterances: список (index_in_timeline, text) для реплик терапевта в каждом окне.
    Возвращает список { "window_index": int, "accusation": bool, "intervention_type": str, "escalation": bool }.
    """
    if not timeline or len(timeline) < 2:
        return []
    loops: list[dict[str, Any]] = []
    for i in range(1, len(timeline)):
        prev, curr = timeline[i - 1], timeline[i]
        accusation = _is_accusation(prev)
        escalation = _is_escalation(prev, curr)
        intervention_type = "unknown"
        if therapist_utterances:
            for idx, text in therapist_utterances:
                if idx == i:
                    intervention_type = classify_intervention(text)
                    break
        if accusation and escalation:
            loops.append({
                "window_index": i,
                "accusation": True,
                "intervention_type": intervention_type,
                "escalation": True,
                "projective_identification_signal": intervention_type == "clarification",
            })
    return loops
