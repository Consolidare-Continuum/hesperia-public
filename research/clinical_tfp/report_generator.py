# HESPERIA — LEVEL 11 Clinical report generator
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Transform analysis, interpretation, and session topology into a structured
clinical report suitable for therapist review. All narrative text in Russian.
"""

from __future__ import annotations

import json
from typing import Any

from research.clinical_tfp.interpretation import (
    detect_defense_pattern,
    detect_object_relation_pattern,
    classify_aggression_level,
    DEFENSE_MAP,
    OBJECT_RELATION_MAP,
)

# Области: id → русское название для отчёта
AREA_NAMES_RU = {
    "A1": "влечения и аффекты",
    "A2": "объектные отношения",
    "A3": "защитные операции",
    "A4": "агрессия",
    "A5": "перверсии",
    "A6": "нарциссизм",
    "A7": "любовь / реляционная способность",
    "A8": "структурный диагноз",
    "A9": "терапевтическая техника",
    "A10": "процесс лечения",
    "A11": "интеграция / сублимация",
    "A12": "взаимное признание / анти-грандиозность",
}

# Защиты: ключ DEFENSE_MAP → русское описание
DEFENSE_NAMES_RU = {
    "splitting": "расщепление",
    "idealization_devaluation": "идеализация и обесценивание",
    "dissociation": "диссоциация",
    "projection": "проекция",
    "projective_identification": "проективная идентификация",
    "role_reversal": "реверс ролей",
}

# Объектные отношения: ключ OBJECT_RELATION_MAP → русское описание
OBJECT_NAMES_RU = {
    "self_representation": "репрезентация себя",
    "part_object": "парциальный объект",
    "persecutory_object": "преследующий объект",
    "bond": "связь с объектом",
    "identity_diffusion": "диффузия идентичности",
    "integrated_object": "интегрированный объект",
}


def generate_session_summary(
    analysis_result: dict[str, Any],
    interpretation: dict[str, Any],
) -> str:
    """
    Краткое резюме сессии: доминантная область и ведущий механизм (семья/защита).
    """
    areas = (analysis_result or {}).get("areas") or {}
    dom_area = (interpretation or {}).get("dominant_area") or ""
    dom_family = (interpretation or {}).get("dominant_family") or ""
    defense = (interpretation or {}).get("defense_pattern") or ""

    if not dom_area:
        return "Доминантная динамика по сессии не выделена."

    area_name = AREA_NAMES_RU.get(dom_area, dom_area)
    parts = [f"Основная динамика сессии связана с областью {area_name}."]
    if defense:
        defense_ru = DEFENSE_NAMES_RU.get(defense, defense)
        parts.append(f"Ведущий механизм — {defense_ru}.")
    elif dom_family:
        parts.append(f"Ведущая семья активации: {dom_family}.")
    return " ".join(parts)


def describe_defense_patterns(analysis_result: dict[str, Any]) -> str:
    """
    Описание защитных паттернов по семьям A3.
    """
    families = (analysis_result or {}).get("families") or {}
    a3 = {k: v for k, v in families.items() if k.startswith("A3_") and v and v > 0}
    if not a3:
        return "Явные защитные паттерны в речи не выделены."

    # Сортируем по убыванию, берём до 3 ведущих
    sorted_fams = sorted(a3.items(), key=lambda x: -x[1])[:3]
    names: list[str] = []
    for fid, _ in sorted_fams:
        pattern = DEFENSE_MAP.get(fid, fid)
        names.append(DEFENSE_NAMES_RU.get(pattern, pattern))
    if len(names) == 1:
        return f"В речи пациента проявляются признаки {names[0]}."
    return "В речи пациента проявляются признаки " + " и ".join(names) + "."


def describe_object_relations(analysis_result: dict[str, Any]) -> str:
    """
    Описание объектных отношений по семьям A2.
    """
    families = (analysis_result or {}).get("families") or {}
    pattern = detect_object_relation_pattern(families)
    if not pattern:
        return "Объектно-реляционный паттерн по данным сессии не выделен."

    pattern_ru = OBJECT_NAMES_RU.get(pattern, pattern)
    return f"Пациент склонен воспринимать терапевта как {pattern_ru}."


def describe_aggression_profile(
    analysis_result: dict[str, Any],
    session_topology: dict[str, Any],
) -> str:
    """
    Профиль агрессии: уровень A4 и динамика по сегментам (кривая).
    """
    areas = (analysis_result or {}).get("areas") or {}
    curve = (session_topology or {}).get("aggression_curve") or []
    level = classify_aggression_level(areas)

    level_ru = {"low": "низкий", "moderate": "умеренный", "high": "высокий"}.get(
        level, level
    )
    level_genitive = {"low": "низкого", "moderate": "умеренного", "high": "высокого"}.get(
        level, level_ru
    )
    if not curve:
        return f"Уровень активации агрессии в сессии: {level_ru}."

    # Проверка монотонного роста
    rising = len(curve) >= 2 and all(curve[i] <= curve[i + 1] for i in range(len(curve) - 1))
    if rising and len(curve) >= 2:
        return (
            f"В ходе сессии наблюдается нарастание агрессии, "
            f"достигающее {level_genitive} уровня к концу сессии."
        )
    if len(curve) >= 2 and curve[-1] > (curve[0] or 0):
        return f"Агрессия усиливается к концу сессии. Итоговый уровень: {level_ru}."
    return f"Уровень агрессии в сессии: {level_ru}."


def describe_session_trajectory(session_topology: dict[str, Any]) -> str:
    """
    Траектория сессии по переходам областей (state_sequence или transitions).
    """
    topo = session_topology or {}
    state_sequence = topo.get("state_sequence") or []
    transitions = topo.get("transitions") or []

    if state_sequence:
        # Убираем пустые, склеиваем стрелками
        seq = [s for s in state_sequence if s]
        if seq:
            return " → ".join(seq)
    if transitions:
        parts = [t[0] for t in transitions]
        if transitions:
            last = transitions[-1][-1]
            if last and (not parts or parts[-1] != last):
                parts.append(last)
            return " → ".join(parts) if parts else ""
    return "Траектория по сегментам не построена."


def detect_clinical_flags(
    analysis_result: dict[str, Any],
    interpretation: dict[str, Any],
) -> list[str]:
    """
    Сигналы внимания для терапевта: высокий уровень агрессии, диффузия идентичности,
    эскалация проективной идентификации, риск отыгрывания и т.д.
    """
    flags: list[str] = []
    areas = (analysis_result or {}).get("areas") or {}
    families = (analysis_result or {}).get("families") or {}
    agg = (interpretation or {}).get("aggression_level") or ""
    defense = (interpretation or {}).get("defense_pattern") or ""
    obj_rel = (interpretation or {}).get("object_relation_pattern") or ""

    if agg == "high":
        flags.append("high aggression")
    if obj_rel == "identity_diffusion":
        flags.append("identity diffusion")
    if defense == "projective_identification" and families.get("A3_F5", 0) > 0.5:
        flags.append("projective identification escalation")
    if defense == "splitting" and (families.get("A3_F1", 0) or 0) > 0.5:
        flags.append("splitting escalation")
    if areas.get("A4", 0) > 0.6 and areas.get("A5", 0) > 0.3:
        flags.append("acting out risk")
    return flags


def generate_clinical_report(
    analysis_result: dict[str, Any],
    interpretation: dict[str, Any],
    session_topology: dict[str, Any],
) -> dict[str, Any]:
    """
    Собрать полный клинический отчёт из результатов анализа, интерпретации и топологии.
    """
    summary = generate_session_summary(analysis_result, interpretation)
    defense_desc = describe_defense_patterns(analysis_result)
    relations_desc = describe_object_relations(analysis_result)
    aggression_desc = describe_aggression_profile(analysis_result, session_topology)
    trajectory_str = describe_session_trajectory(session_topology)
    flags = detect_clinical_flags(analysis_result, interpretation)

    dom_area = (interpretation or {}).get("dominant_area") or ""
    defense = (interpretation or {}).get("defense_pattern") or ""
    area_name = AREA_NAMES_RU.get(dom_area, dom_area)
    defense_ru = DEFENSE_NAMES_RU.get(defense, defense) if defense else ""

    dominant_dynamics = (
        f"Основной защитный механизм — {defense_ru}."
        if defense_ru
        else f"Ведущая область: {area_name}."
    )

    return {
        "session_summary": summary,
        "dominant_dynamics": dominant_dynamics,
        "defense_patterns": defense_desc,
        "object_relations": relations_desc,
        "aggression_profile": aggression_desc,
        "session_trajectory": trajectory_str,
        "clinical_flags": flags,
    }


def generate_report_markdown(report: dict[str, Any]) -> str:
    """Отчёт в формате Markdown."""
    lines = [
        "# Клинический отчёт по сессии",
        "",
        "## Резюме",
        report.get("session_summary", ""),
        "",
        "## Доминантная динамика",
        report.get("dominant_dynamics", ""),
        "",
        "## Защитные паттерны",
        report.get("defense_patterns", ""),
        "",
        "## Объектные отношения",
        report.get("object_relations", ""),
        "",
        "## Профиль агрессии",
        report.get("aggression_profile", ""),
        "",
        "## Траектория сессии",
        report.get("session_trajectory", ""),
        "",
        "## Клинические флаги",
    ]
    for f in report.get("clinical_flags") or []:
        lines.append(f"- {f}")
    if not report.get("clinical_flags"):
        lines.append("- нет")
    return "\n".join(lines)


def generate_report_json(report: dict[str, Any], indent: int = 2) -> str:
    """Отчёт в виде JSON-строки."""
    return json.dumps(report, ensure_ascii=False, indent=indent)


def generate_report_text(report: dict[str, Any]) -> str:
    """Плоский текстовый отчёт (русский)."""
    parts = [
        f"Резюме: {report.get('session_summary', '')}",
        f"Доминантная динамика: {report.get('dominant_dynamics', '')}",
        f"Защитные паттерны: {report.get('defense_patterns', '')}",
        f"Объектные отношения: {report.get('object_relations', '')}",
        f"Профиль агрессии: {report.get('aggression_profile', '')}",
        f"Траектория сессии: {report.get('session_trajectory', '')}",
        "Клинические флаги: " + ", ".join(report.get("clinical_flags") or ["нет"]),
    ]
    return "\n".join(parts)


def generate_clinical_report_readable(
    session_summary: dict[str, Any] | None = None,
    analysis_result: dict[str, Any] | None = None,
    interpretation: dict[str, Any] | None = None,
    include_confidence: bool = True,
) -> str:
    """
    Читаемый клинический отчёт в формате:
    Dominant affect: ...
    Primary defense: ...
    Object representation: ...
    Transference pattern: ...
    С опциональным confidence после анализа.
    """
    if session_summary:
        affects = session_summary.get("dominant_affects") or []
        defense = session_summary.get("defense_pattern") or ""
        obj_rel = session_summary.get("object_relations_pattern") or ""
        trans = session_summary.get("transference_indicators") or []
        coupling = session_summary.get("affect_defense_coupling") or {}
        dom_affect = affects[0] if affects else (coupling.get("affect") or "—")
    else:
        interp = interpretation or {}
        dom_affect = "—"
        defense = interp.get("defense_pattern") or ""
        obj_rel = interp.get("object_relation_pattern") or ""
        trans = []

    trans_str = ", ".join(trans) if trans else "—"
    lines = [
        f"Dominant affect: {dom_affect}",
        f"Primary defense: {defense or '—'}",
        f"Object representation: {obj_rel or '—'}",
        f"Transference pattern: {trans_str}",
    ]
    if include_confidence and (session_summary or interpretation):
        interp = interpretation or {}
        ca = (session_summary or {}).get("affect_defense_coupling") or {}
        def_conf = interp.get("defense_confidence") or ca.get("coupling_strength")
        obj_conf = interp.get("object_relation_confidence")
        if def_conf is not None:
            lines.append(f"Defense confidence: {def_conf:.2f}")
        if obj_conf is not None:
            lines.append(f"Object relation confidence: {obj_conf:.2f}")
    return "\n".join(lines)
