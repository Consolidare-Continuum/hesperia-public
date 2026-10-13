# HESPERIA — LEVEL 15 Speaker-aware session parsing
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Split session text into patient/therapist utterances; support speaker-weighted
concept activation (patient = mental dynamics, therapist = intervention).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from hesperia.nlp.transcript_speaker_labels import (
    PATIENT_LINE_PREFIX as PATIENT_PREFIX,
    THERAPIST_LINE_PREFIX as THERAPIST_PREFIX,
)

Speaker = Literal["patient", "therapist"]
Target = Literal["therapist", "patient", "third"]
YOU_PATTERN = re.compile(r"\b(ты|тебя|тобой|вас|вам|вами|вы)\b", re.IGNORECASE)
THIRD_PERSON_PATTERN = re.compile(
    r"\b(он[аи]?|его|её|ей|им|ими|мама|папа|муж|жена|начальник|коллега|друг|подруга|родител)\b",
    re.IGNORECASE,
)


def infer_utterance_target(speaker: Speaker, text: str, tokens: list[str]) -> Target:
    """
    Infer who the utterance is directed at (role_direction target).
    patient + "ты/вы/вам" → therapist; therapist + "ты/вы" → patient;
    patient + third-person refs, no you → third; default patient→therapist, therapist→patient.
    """
    text_lower = text.lower() if text else ""
    has_you = bool(YOU_PATTERN.search(text_lower))
    has_third = bool(THIRD_PERSON_PATTERN.search(text_lower))
    if speaker == "patient":
        if has_you:
            return "therapist"
        if has_third:
            return "third"
        return "therapist"
    if has_you:
        return "patient"
    return "patient"


@dataclass
class Utterance:
    """Single turn: speaker, target (who it's directed at), text and tokens."""
    speaker: Speaker
    text: str
    tokens: list[str]
    target: Target = "therapist"


def parse_session_dialogue(text: str) -> list[Utterance]:
    """
    Split transcript into utterances by speaker labels.

    Rules:
    - ``Patient:`` / ``Пациент:`` (any case) → speaker = ``patient``
    - ``Therapist:`` / ``Терапевт:`` (any case) → speaker = ``therapist``
    - If no label on a line: default speaker = ``patient``

    Labels are defined in ``hesperia.nlp.transcript_speaker_labels``.

    Returns list of Utterance(speaker, text, tokens). Tokens are filled by
    tokenize_text + normalize_tokens (caller or integrate with session_parser).
    """
    if not text or not isinstance(text, str):
        return []
    utterances: list[Utterance] = []
    current_speaker: Speaker = "patient"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if not current_lines:
            return
        combined = " ".join(current_lines).strip()
        if not combined:
            current_lines = []
            return
        from hesperia.nlp.session_parser import tokenize_text, normalize_tokens
        tokens = normalize_tokens(tokenize_text(combined))
        target = infer_utterance_target(current_speaker, combined, tokens)
        utterances.append(Utterance(speaker=current_speaker, text=combined, tokens=tokens, target=target))
        current_lines = []

    for line in text.splitlines():
        if PATIENT_PREFIX.match(line):
            flush()
            current_speaker = "patient"
            rest = PATIENT_PREFIX.sub("", line, count=1).strip()
            if rest:
                current_lines = [rest]
            else:
                current_lines = []
        elif THERAPIST_PREFIX.match(line):
            flush()
            current_speaker = "therapist"
            rest = THERAPIST_PREFIX.sub("", line, count=1).strip()
            if rest:
                current_lines = [rest]
            else:
                current_lines = []
        else:
            if line.strip():
                current_lines.append(line.strip())
    flush()
    return utterances
