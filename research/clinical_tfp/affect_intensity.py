# HESPERIA — Affect Intensity Estimation
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Оценка силы аффекта affect_intensity ∈ [0..1] по:
sentiment intensity, lexical patterns, exclamation markers.
Примеры: я злюсь < я в бешенстве < я вас ненавижу.
"""

from __future__ import annotations

import re
from typing import Any

# Маркеры интенсивности (низкая → высокая). Веса для агрессии/негатива.
LOW_INTENSITY = re.compile(
    r"\b(недоволен|раздражен|грустно|обижен|злюсь|злиться)\b",
    re.IGNORECASE,
)
MEDIUM_INTENSITY = re.compile(
    r"\b(злость|ярость|ненависть|в ярости|очень злюсь|сильно обижен)\b",
    re.IGNORECASE,
)
HIGH_INTENSITY = re.compile(
    r"\b(в бешенстве|ненавижу|убить готов|разрывает|бесит|капец|жесть|достал)\b",
    re.IGNORECASE,
)
EXCLAMATION = re.compile(r"[!?]{1,3}\s*$")
MULTIPLE_EXCLAMATION = re.compile(r"!{2,}")


def estimate_affect_intensity(
    text: str,
    tokens: list[str] | None = None,
) -> float:
    """
    Оценка интенсивности аффекта в диапазоне [0..1].
    Учитывает: лексические паттерны (низкая/средняя/высокая), восклицания.
    """
    if not text or not isinstance(text, str):
        return 0.0
    text_lower = text.strip().lower()
    score = 0.0

    if HIGH_INTENSITY.search(text_lower):
        score = max(score, 0.85)
    if MEDIUM_INTENSITY.search(text_lower):
        score = max(score, 0.55)
    if LOW_INTENSITY.search(text_lower):
        score = max(score, 0.35)

    if MULTIPLE_EXCLAMATION.search(text):
        score = min(1.0, score + 0.15)
    elif EXCLAMATION.search(text.strip()):
        score = min(1.0, score + 0.08)

    if score == 0.0 and (tokens or []):
        # Слабый сигнал по токенам аффекта
        affect_tokens = {"зло", "злой", "злиться", "ненависть", "агрессия", "злюсь", "бешусь"}
        norm = [t.lower() for t in (tokens or [])]
        if any(t in affect_tokens for t in norm):
            score = 0.25
    return round(min(1.0, max(0.0, score)), 2)


def estimate_affect_intensity_with_breakdown(text: str, tokens: list[str] | None = None) -> dict[str, Any]:
    """Вернуть intensity и компоненты (low/medium/high hit, exclamation)."""
    if not text:
        return {"intensity": 0.0, "low_hit": False, "medium_hit": False, "high_hit": False, "exclamation": False}
    text_lower = text.strip().lower()
    low = bool(LOW_INTENSITY.search(text_lower))
    medium = bool(MEDIUM_INTENSITY.search(text_lower))
    high = bool(HIGH_INTENSITY.search(text_lower))
    excl = bool(MULTIPLE_EXCLAMATION.search(text) or EXCLAMATION.search(text.strip()))
    intensity = estimate_affect_intensity(text, tokens)
    return {
        "intensity": intensity,
        "low_hit": low,
        "medium_hit": medium,
        "high_hit": high,
        "exclamation": excl,
    }
