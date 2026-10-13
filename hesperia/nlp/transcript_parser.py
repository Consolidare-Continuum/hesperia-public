# HESPERIA — Real transcript ingestion: speaker parsing and turn segmentation
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Parse TFP-style transcripts with Russian or English speaker labels.

Surface forms and regex live in ``transcript_speaker_labels`` (single source of truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hesperia.nlp.transcript_speaker_labels import (
    SPEAKER_ALIASES,
    SPEAKER_PATTERN,
    resolve_speaker_token,
)


@dataclass
class Turn:
    speaker: str
    text: str
    turn_index: int


def parse_speaker_turns(text: str) -> list[Turn]:
    """
    Split transcript into turns by speaker labels.
    Lines starting with "Пациент:" or "Терапевт:" (or Patient/Therapist) start a new turn.
    Returns list of Turn(speaker, text, turn_index).
    """
    if not text or not isinstance(text, str):
        return []
    turns: list[Turn] = []
    current_speaker: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        m = SPEAKER_PATTERN.match(line)
        if m:
            if current_speaker is not None and current_lines:
                turns.append(Turn(
                    speaker=current_speaker,
                    text=" ".join(current_lines).strip(),
                    turn_index=len(turns),
                ))
                current_lines = []
            raw = m.group(1).strip()
            current_speaker = resolve_speaker_token(raw)
            rest = line[m.end() :].strip()
            if rest:
                current_lines.append(rest)
        else:
            if current_speaker is not None:
                current_lines.append(line.strip())
            elif line.strip():
                current_speaker = "unknown"
                current_lines.append(line.strip())
    if current_speaker is not None and current_lines:
        turns.append(Turn(
            speaker=current_speaker,
            text=" ".join(current_lines).strip(),
            turn_index=len(turns),
        ))
    return turns


def segment_by_speaker(text: str) -> dict[str, list[str]]:
    """
    Return dict: {"patient": [text1, text2, ...], "therapist": [text1, ...]}.
    Concatenates consecutive turns of the same speaker.
    """
    turns = parse_speaker_turns(text)
    out: dict[str, list[str]] = {"patient": [], "therapist": []}
    for t in turns:
        s = "patient" if t.speaker in ("patient", "п") else "therapist" if t.speaker in ("therapist", "т") else t.speaker
        if s not in out:
            out[s] = []
        out[s].append(t.text)
    return out


def get_patient_text_only(text: str) -> str:
    """Return concatenated patient turns (for analysis focused on patient speech)."""
    seg = segment_by_speaker(text)
    return " ".join(seg.get("patient", []))


def get_therapist_text_only(text: str) -> str:
    """Return concatenated therapist turns."""
    seg = segment_by_speaker(text)
    return " ".join(seg.get("therapist", []))
