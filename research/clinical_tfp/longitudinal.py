# HESPERIA — LEVEL 12 Session comparison and longitudinal change
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Compare multiple sessions over time; detect structural change trajectories.
Turns HESPERIA from session analyzer into treatment process analyzer.
"""

from __future__ import annotations

import json
from typing import Any

from research.clinical_tfp.interpretation import detect_defense_pattern

# Примитивные защиты (TFP/Kernberg): высокий уровень → тенденция к снижению = улучшение
PRIMITIVE_DEFENSE_FAMILIES = frozenset({"A3_F1", "A3_F2", "A3_F3", "A3_F4", "A3_F5", "A3_F6"})


def _get_analysis(session: dict[str, Any]) -> dict[str, Any]:
    """Извлечь анализ из элемента сессии (analysis или сам объект с areas/families/concepts)."""
    if "analysis" in session:
        return session.get("analysis") or {}
    return session


def _get_areas(session: dict[str, Any]) -> dict[str, float]:
    return (_get_analysis(session) or {}).get("areas") or {}


def _get_families(session: dict[str, Any]) -> dict[str, float]:
    return (_get_analysis(session) or {}).get("families") or {}


def _get_concepts(session: dict[str, Any]) -> dict[str, float]:
    return (_get_analysis(session) or {}).get("concepts") or {}


def _get_interpretation(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("interpretation") or {}


def _session_id(session: dict[str, Any], index: int) -> str:
    return session.get("session_id") or f"S{index + 1:02d}"


def _delta(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    """Разность b - a по общим ключам; ключи только из b для направленного сравнения."""
    out: dict[str, float] = {}
    all_keys = set(a) | set(b)
    for k in all_keys:
        out[k] = b.get(k, 0.0) - a.get(k, 0.0)
    return out


def compare_session_activations(
    session_a: dict[str, Any],
    session_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Сравнить активации двух сессий. Возвращает дельты (session_b - session_a)
    по areas, families, concepts.
    """
    areas_a = _get_areas(session_a)
    areas_b = _get_areas(session_b)
    fam_a = _get_families(session_a)
    fam_b = _get_families(session_b)
    conc_a = _get_concepts(session_a)
    conc_b = _get_concepts(session_b)
    return {
        "area_deltas": _delta(areas_a, areas_b),
        "family_deltas": _delta(fam_a, fam_b),
        "concept_deltas": _delta(conc_a, conc_b),
    }


def build_longitudinal_curves(sessions: list[dict[str, Any]]) -> dict[str, list[float]]:
    """
    Построить кривые по основным областям (A2, A3, A4, A7, A10) вдоль сессий.
    """
    if not sessions:
        return {}
    curves: dict[str, list[float]] = {}
    area_ids = ("A2", "A3", "A4", "A7", "A10")
    for aid in area_ids:
        curves[aid] = []
    for s in sessions:
        areas = _get_areas(s)
        for aid in area_ids:
            curves[aid].append(areas.get(aid, 0.0))
    return curves


def detect_defense_evolution(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Эволюция защит по сессиям: примитивные vs более зрелые; смена доминантной защиты.
    """
    if not sessions:
        return {
            "primitive_defenses_trend": "unknown",
            "higher_defenses_trend": "unknown",
            "dominant_defense_shift": [],
        }
    primitive_scores: list[float] = []
    dominant_list: list[str] = []
    for s in sessions:
        families = _get_families(s)
        prim = sum(families.get(fid, 0.0) for fid in PRIMITIVE_DEFENSE_FAMILIES)
        primitive_scores.append(prim)
        dominant_list.append(detect_defense_pattern(families))
    # Тренд примитивных: по убыванию суммы
    if len(primitive_scores) < 2:
        prim_trend = "stable"
    else:
        first_half = sum(primitive_scores[: len(primitive_scores) // 2]) / max(1, len(primitive_scores) // 2)
        second_half = sum(primitive_scores[len(primitive_scores) // 2 :]) / max(1, len(primitive_scores) - len(primitive_scores) // 2)
        if second_half < first_half * 0.9:
            prim_trend = "decreasing"
        elif second_half > first_half * 1.1:
            prim_trend = "increasing"
        else:
            prim_trend = "stable"
    higher_trend = "increasing" if prim_trend == "decreasing" else ("decreasing" if prim_trend == "increasing" else "stable")
    return {
        "primitive_defenses_trend": prim_trend,
        "higher_defenses_trend": higher_trend,
        "dominant_defense_shift": dominant_list,
    }


def detect_aggression_trend(sessions: list[dict[str, Any]], area_a4: str = "A4") -> dict[str, Any]:
    """Тренд A4 (агрессия) по сессиям: curve, trend, peak_session."""
    if not sessions:
        return {"trend": "unknown", "curve": [], "peak_session": ""}
    curve = [_get_areas(s).get(area_a4, 0.0) for s in sessions]
    peak_idx = max(range(len(curve)), key=lambda i: curve[i]) if curve else 0
    peak_session = _session_id(sessions[peak_idx], peak_idx)
    if len(curve) < 2:
        trend = "stable"
    else:
        if curve[-1] < curve[0] * 0.9:
            trend = "decreasing"
        elif curve[-1] > curve[0] * 1.1:
            trend = "increasing"
        else:
            trend = "stable"
    return {
        "trend": trend,
        "curve": curve,
        "peak_session": peak_session,
    }


def detect_relational_capacity_trend(
    sessions: list[dict[str, Any]],
    area_a7: str = "A7",
) -> dict[str, Any]:
    """Тренд A7 (реляционная способность) по сессиям; evidence — ключевые маркеры улучшения."""
    if not sessions:
        return {"trend": "unknown", "curve": [], "evidence": []}
    curve = [_get_areas(s).get(area_a7, 0.0) for s in sessions]
    if len(curve) < 2:
        trend = "stable"
    else:
        if curve[-1] > curve[0] * 1.1:
            trend = "increasing"
        elif curve[-1] < curve[0] * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    evidence: list[str] = []
    if trend == "increasing":
        evidence = ["gratitude", "ambivalence_tolerance", "repair_capacity"]
    return {
        "trend": trend,
        "curve": curve,
        "evidence": evidence,
    }


def estimate_structural_change(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Синтез структурного изменения по трендам: A2, A3, A4, A7, A10.
    Умеренное позитивное изменение при снижении примитивных защит и агрессии, росте A7 и интеграции.
    """
    if not sessions:
        return {
            "structural_change": "unknown",
            "confidence": 0.0,
            "supporting_factors": [],
        }
    curves = build_longitudinal_curves(sessions)
    defense_ev = detect_defense_evolution(sessions)
    agg = detect_aggression_trend(sessions)
    rel = detect_relational_capacity_trend(sessions)
    factors: list[str] = []
    score = 0.0
    if defense_ev.get("primitive_defenses_trend") == "decreasing":
        score += 0.25
        factors.append("reduced splitting")
    if agg.get("trend") == "decreasing":
        score += 0.25
        factors.append("reduced aggression")
    if rel.get("trend") == "increasing":
        score += 0.25
        factors.append("improved relational capacity")
    a2_curve = curves.get("A2", [])
    if len(a2_curve) >= 2 and a2_curve[-1] > a2_curve[0] * 1.05:
        score += 0.15
        factors.append("increased ambivalence tolerance")
    a7_curve = curves.get("A7", [])
    if len(a7_curve) >= 2 and a7_curve[-1] > a7_curve[0]:
        if "improved relational capacity" not in factors:
            factors.append("improved relational capacity")
    if score >= 0.7:
        structural = "strong_positive"
        confidence = min(0.95, score + 0.1)
    elif score >= 0.4:
        structural = "moderate_positive"
        confidence = min(0.85, score + 0.15)
    elif score >= 0.2:
        structural = "mild_positive"
        confidence = score + 0.1
    else:
        structural = "stable"
        confidence = 0.5
        if not factors:
            factors.append("insufficient trend evidence")
    return {
        "structural_change": structural,
        "confidence": round(confidence, 2),
        "supporting_factors": factors,
    }


def analyze_treatment_trajectory(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Полный анализ траектории лечения: кривые, эволюция защит, тренды агрессии и
    реляционной способности, оценка структурного изменения.
    """
    curves = build_longitudinal_curves(sessions)
    defense_evolution = detect_defense_evolution(sessions)
    aggression_trend = detect_aggression_trend(sessions)
    relational_trend = detect_relational_capacity_trend(sessions)
    structural_change = estimate_structural_change(sessions)
    return {
        "session_count": len(sessions),
        "curves": curves,
        "defense_evolution": defense_evolution,
        "aggression_trend": aggression_trend,
        "relational_capacity_trend": relational_trend,
        "structural_change": structural_change,
    }


def export_trajectory_json(result: dict[str, Any], indent: int = 2) -> str:
    """Экспорт результата analyze_treatment_trajectory в JSON."""
    return json.dumps(result, ensure_ascii=False, indent=indent)


def export_trajectory_markdown(result: dict[str, Any]) -> str:
    """Экспорт результата в Markdown для отчётов и визуализации."""
    lines = [
        "# Траектория лечения",
        "",
        f"**Количество сессий:** {result.get('session_count', 0)}",
        "",
        "## Кривые активации областей",
    ]
    for area, curve in (result.get("curves") or {}).items():
        lines.append(f"- **{area}:** `{curve}`")
    lines.extend(["", "## Эволюция защит"])
    ev = result.get("defense_evolution") or {}
    lines.append(f"- Примитивные защиты: {ev.get('primitive_defenses_trend', '—')}")
    lines.append(f"- Более зрелые защиты: {ev.get('higher_defenses_trend', '—')}")
    lines.append(f"- Смена доминантной защиты: {ev.get('dominant_defense_shift', [])}")
    lines.extend(["", "## Агрессия (A4)"])
    agg = result.get("aggression_trend") or {}
    lines.append(f"- Тренд: {agg.get('trend', '—')}")
    lines.append(f"- Пик сессии: {agg.get('peak_session', '—')}")
    lines.extend(["", "## Реляционная способность (A7)"])
    rel = result.get("relational_capacity_trend") or {}
    lines.append(f"- Тренд: {rel.get('trend', '—')}")
    lines.append(f"- Маркеры: {rel.get('evidence', [])}")
    lines.extend(["", "## Структурное изменение"])
    sc = result.get("structural_change") or {}
    lines.append(f"- Оценка: {sc.get('structural_change', '—')}")
    lines.append(f"- Уверенность: {sc.get('confidence', 0)}")
    lines.append("Поддерживающие факторы:")
    for f in sc.get("supporting_factors", []):
        lines.append(f"- {f}")
    return "\n".join(lines)
