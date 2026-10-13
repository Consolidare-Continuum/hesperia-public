# HESPERIA — Model Explainability Layer
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
activation_trace: объяснение каждой активации цепочкой marker → concept → family → area.
"""

from __future__ import annotations

from typing import Any


def build_activation_trace(
    markers: list[tuple[str, float]],
    concept_to_area_family: dict[str, tuple[str, str]],
) -> list[dict[str, Any]]:
    """
    По списку маркеров (concept_id, weight) и маппингу concept→(area, family) построить
    цепочки marker → concept → family → area. Каждый маркер даёт одну запись (concept_id уже
    результат сопоставления marker→concept в пайплайне; здесь marker = concept_id для упрощения,
    либо передавать (marker_str, concept_id, weight) если доступно).
    """
    trace: list[dict[str, Any]] = []
    for cid, weight in markers:
        area_family = concept_to_area_family.get(cid)
        if not area_family:
            continue
        area, family = area_family
        family_id = f"{area}_{family}"
        trace.append({
            "marker": cid,  # или marker_str если передавать из детектора
            "concept_id": cid,
            "family_id": family_id,
            "area_id": area,
            "weight": round(float(weight), 4),
        })
    return trace


def build_activation_trace_with_markers(
    marker_to_concepts: list[tuple[str, str, float]],
    concept_to_area_family: dict[str, tuple[str, str]],
) -> list[dict[str, Any]]:
    """
    Полная цепочка: (marker_str, concept_id, weight) → concept → family → area.
    marker_to_concepts: список (marker_lexeme, concept_id, weight).
    """
    trace: list[dict[str, Any]] = []
    for marker_str, cid, weight in marker_to_concepts:
        area_family = concept_to_area_family.get(cid)
        if not area_family:
            continue
        area, family = area_family
        family_id = f"{area}_{family}"
        trace.append({
            "marker": marker_str,
            "concept_id": cid,
            "family_id": family_id,
            "area_id": area,
            "weight": round(float(weight), 4),
        })
    return trace


def trace_to_readable(trace: list[dict[str, Any]], max_entries: int = 20) -> list[str]:
    """Преобразовать trace в читаемые строки для отчёта."""
    lines = []
    for i, t in enumerate(trace):
        if i >= max_entries:
            lines.append("...")
            break
        lines.append(
            f"{t.get('marker', '')} → {t.get('concept_id', '')} → "
            f"{t.get('family_id', '')} → {t.get('area_id', '')} (w={t.get('weight', 0)})"
        )
    return lines
