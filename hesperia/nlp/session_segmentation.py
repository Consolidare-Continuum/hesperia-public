# HESPERIA — Session Segmentation (long sessions)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Длинные сессии (2000–8000 слов) анализировать по сегментам.
Рекомендуется окно 5–10 реплик (utterances).
"""

from __future__ import annotations

from typing import Any

from hesperia.nlp.temporal_dynamics import build_utterance_windows, build_activation_timeline
from hesperia.nlp.session_structure import parse_session_dialogue


def segment_session_by_utterances(
    text: str,
    window_utterances: int = 5,
) -> list[dict[str, Any]]:
    """
    Разбить сессию на сегменты по окну реплик (5–10).
    Возвращает список сегментов: каждый — { "utterances": [...], "text": str, "segment_index": int }.
    """
    utterances = parse_session_dialogue(text)
    if not utterances:
        return []
    windows = build_utterance_windows(utterances, window_size=window_utterances)
    segments = []
    for i, win in enumerate(windows):
        parts = []
        for u in win:
            prefix = "Patient: " if getattr(u, "speaker", "") == "patient" else "Therapist: "
            parts.append(prefix + (u.text or ""))
        segments.append({
            "segment_index": i,
            "utterances": win,
            "text": "\n".join(parts),
            "utterance_count": len(win),
        })
    return segments


def segment_session_by_word_count(
    text: str,
    words_per_segment: int = 500,
) -> list[dict[str, Any]]:
    """
    Разбить сессию по числу слов (приблизительно). Сохраняем границы реплик:
    сегмент = последовательность полных реплик, пока не набрано ~words_per_segment слов.
    """
    utterances = parse_session_dialogue(text)
    if not utterances or words_per_segment < 1:
        return []
    segments = []
    current: list[Any] = []
    current_words = 0
    for u in utterances:
        n = len(getattr(u, "tokens", []) or [])
        if current_words + n > words_per_segment and current:
            parts = []
            for x in current:
                prefix = "Patient: " if getattr(x, "speaker", "") == "patient" else "Therapist: "
                parts.append(prefix + (getattr(x, "text", "") or ""))
            segments.append({
                "segment_index": len(segments),
                "utterances": list(current),
                "text": "\n".join(parts),
                "word_count": current_words,
            })
            current = []
            current_words = 0
        current.append(u)
        current_words += n
    if current:
        parts = []
        for x in current:
            prefix = "Patient: " if getattr(x, "speaker", "") == "patient" else "Therapist: "
            parts.append(prefix + (getattr(x, "text", "") or ""))
        segments.append({
            "segment_index": len(segments),
            "utterances": list(current),
            "text": "\n".join(parts),
            "word_count": current_words,
        })
    return segments
