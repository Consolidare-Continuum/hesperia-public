# HESPERIA — Temporal Session Dynamics (TFP)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Split session into utterance windows; build activation timeline for
defense escalation, affect spikes, transference shifts.
"""

from __future__ import annotations

from typing import Any


def build_utterance_windows(
    utterances: list[Any],
    window_size: int = 5,
) -> list[list[Any]]:
    """
    Split utterances into non-overlapping windows of window_size (e.g. 5–10).
    Returns list of windows, each window = list of utterances.
    """
    if not utterances or window_size < 1:
        return []
    return [utterances[i : i + window_size] for i in range(0, len(utterances), window_size)]


def build_activation_timeline(
    text: str,
    window_utterances: int = 5,
    analyze_fn: Any = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Split session into utterance windows; run analyze_fn on each window's text;
    return list of activation dicts (timeline).

    analyze_fn(text, **kwargs) should return dict with areas, families, concepts.
    Default: uses hesperia.nlp.session_parser.analyze_session_speaker_aware.
    """
    from hesperia.nlp.session_structure import parse_session_dialogue

    utterances = parse_session_dialogue(text)
    if not utterances:
        return []

    windows = build_utterance_windows(utterances, window_size=window_utterances)
    if analyze_fn is None:
        from hesperia.nlp.session_parser import analyze_session_speaker_aware
        analyze_fn = analyze_session_speaker_aware

    timeline: list[dict[str, Any]] = []
    for win in windows:
        parts = []
        for u in win:
            if not u.text:
                continue
            prefix = "Patient: " if getattr(u, "speaker", "") == "patient" else "Therapist: "
            parts.append(prefix + u.text)
        window_text = "\n".join(parts) if parts else ""
        if not window_text.strip():
            timeline.append({"areas": {}, "families": {}, "concepts": {}})
            continue
        act = analyze_fn(window_text, **kwargs)
        timeline.append({
            "areas": act.get("areas", {}),
            "families": act.get("families", {}),
            "concepts": act.get("concepts", {}),
            "activation_by_direction": act.get("activation_by_direction", {}),
        })
    return timeline


def detect_escalation(
    timeline: list[dict[str, Any]],
    area: str = "A4",
    threshold_rise: float = 0.2,
) -> list[int]:
    """
    Return indices of windows where area score rises by at least threshold_rise
    compared to previous window (defense/affect escalation).
    """
    out: list[int] = []
    for i in range(1, len(timeline)):
        prev = (timeline[i - 1].get("areas") or {}).get(area, 0.0)
        curr = (timeline[i].get("areas") or {}).get(area, 0.0)
        if curr - prev >= threshold_rise:
            out.append(i)
    return out
