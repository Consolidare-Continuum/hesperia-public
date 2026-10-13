# HESPERIA — Therapist Intervention Classification (Area 9 — Technique)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Классификация интервенций терапевта: clarification, confrontation, interpretation,
limit_setting, support. Соответствует Area 9 (Technique).
"""

from __future__ import annotations

import re
from typing import Any

InterventionType = str  # "clarification" | "confrontation" | "interpretation" | "limit_setting" | "support"

# Паттерны и ключевые фразы по типам (рус. / англ.)
CLARIFICATION_PATTERNS = [
    r"\b(что вы имеете в виду|что вы чувствуете|что происходит|расскажите подробнее|как это было|уточните)\b",
    r"\b(what do you mean|what are you feeling|can you say more|tell me more|how was that)\b",
]
CONFRONTATION_PATTERNS = [
    r"\b(заметил противоречие|с одной стороны.*с другой|вы только что сказали|но ранее вы)\b",
    r"\b(I notice a contradiction|on one hand.*on the other|you just said|but earlier you)\b",
]
INTERPRETATION_PATTERNS = [
    r"\b(возможно вы|похоже что|как если бы|это может означать|интерпретируя)\b",
    r"\b(perhaps you|it seems that|as if|this might mean|interpreting)\b",
]
LIMIT_SETTING_PATTERNS = [
    r"\b(нельзя|нужно остановиться|граница|правило|должен прервать)\b",
    r"\b(we need to stop|boundary|rule|I have to interrupt|cannot allow)\b",
]
SUPPORT_PATTERNS = [
    r"\b(понимаю|слышу вас|это трудно|принимаю|поддерживаю)\b",
    r"\b(I understand|I hear you|that is hard|I accept|support)\b",
]

_COMPILED: dict[str, list[re.Pattern[str]]] = {}


def _compile_patterns() -> dict[str, list[re.Pattern[str]]]:
    global _COMPILED
    if _COMPILED:
        return _COMPILED
    _COMPILED = {
        "clarification": [re.compile(p, re.IGNORECASE) for p in CLARIFICATION_PATTERNS],
        "confrontation": [re.compile(p, re.IGNORECASE) for p in CONFRONTATION_PATTERNS],
        "interpretation": [re.compile(p, re.IGNORECASE) for p in INTERPRETATION_PATTERNS],
        "limit_setting": [re.compile(p, re.IGNORECASE) for p in LIMIT_SETTING_PATTERNS],
        "support": [re.compile(p, re.IGNORECASE) for p in SUPPORT_PATTERNS],
    }
    return _COMPILED


def classify_intervention(text: str) -> InterventionType:
    """
    Классифицировать реплику терапевта по типу интервенции.
    Возвращает первый совпавший тип или "support" по умолчанию.
    """
    if not text or not isinstance(text, str):
        return "support"
    text_lower = text.lower().strip()
    patterns = _compile_patterns()
    for label in ("confrontation", "limit_setting", "interpretation", "clarification", "support"):
        for pat in patterns[label]:
            if pat.search(text_lower):
                return label
    return "support"


def classify_intervention_with_scores(text: str) -> dict[str, Any]:
    """Вернуть тип и флаги по каждому классу (для калибровки)."""
    if not text:
        return {"type": "support", "scores": {}}
    text_lower = text.lower()
    patterns = _compile_patterns()
    scores: dict[str, float] = {}
    for label, pats in patterns.items():
        scores[label] = 1.0 if any(p.search(text_lower) for p in pats) else 0.0
    type_ = "support"
    for candidate in ("confrontation", "limit_setting", "interpretation", "clarification"):
        if scores.get(candidate):
            type_ = candidate
            break
    return {"type": type_, "scores": scores}
