# HESPERIA — Text Normalization Layer
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Очистка сырого текста стенограмм: fillers removal, speech disfluency cleanup,
punctuation normalization. Без этого активации будут шумными.
"""

from __future__ import annotations

import re
from typing import Any

# Заполнители пауз и паразитные слова (рус. / англ.)
FILLERS = re.compile(
    r"\b(эээ|э-э-э|ммм|м-м-м|ну|типа|как бы|вот|значит|короче|блин|кстати|собственно|это самое|как сказать)\b",
    re.IGNORECASE,
)
FILLERS_EN = re.compile(
    r"\b(um|uh|er|like|you know|I mean|well|so|actually|basically)\b",
    re.IGNORECASE,
)
# Повторяющиеся точки/многоточие, смех, паузы
DISFLUENCY = re.compile(
    r"\.{2,}|\.\s*\.\s*\.|\(смех\)|\(пауза\)|\(laughter\)|\(pause\)|\[\.\.\.\]|—\s*—",
    re.IGNORECASE,
)
# Нормализация пунктуации: множественные пробелы, лишние запятые
MULTI_SPACE = re.compile(r"\s{2,}")
TRAILING_PUNCT = re.compile(r"[\s.,;:!?]+$")
LEADING_PUNCT = re.compile(r"^[\s.,;:!?]+")


def remove_fillers(text: str) -> str:
    """Удалить заполнители пауз и паразитные слова (ну, типа, эээ, like, um)."""
    if not text or not isinstance(text, str):
        return ""
    out = FILLERS.sub(" ", text)
    out = FILLERS_EN.sub(" ", out)
    return MULTI_SPACE.sub(" ", out).strip()


def cleanup_speech_disfluency(text: str) -> str:
    """Убрать обозначения пауз, смеха, многоточия как шум."""
    if not text:
        return ""
    out = DISFLUENCY.sub(" ", text)
    return MULTI_SPACE.sub(" ", out).strip()


def normalize_punctuation(text: str) -> str:
    """Нормализовать пунктуацию: множественные пробелы в один, обрезка по краям."""
    if not text:
        return ""
    out = MULTI_SPACE.sub(" ", text)
    out = TRAILING_PUNCT.sub("", out)
    out = LEADING_PUNCT.sub("", out)
    return out.strip()


def normalize_transcript_text(text: str) -> str:
    """
    Полная нормализация текста стенограммы для подачи в пайплайн:
    fillers removal → speech disfluency cleanup → punctuation normalization.
    """
    if not text or not isinstance(text, str):
        return ""
    out = remove_fillers(text)
    out = cleanup_speech_disfluency(out)
    out = normalize_punctuation(out)
    return out
