# HESPERIA — RAD. TFP / clinical transcript speaker labels (RU + EN → canonical roles)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Single source of truth for dialogue role **surface forms** in transcripts.

Internal pipeline roles stay English: ``patient`` | ``therapist`` (APIs, JSON, weights).

Input transcripts may use:

- English: ``Patient:``, ``Therapist:`` (case-insensitive)
- Russian: ``Пациент:``, ``Терапевт:`` (case-insensitive)
- Short RU (legacy / inline): ``П`` / ``Т`` before ``:`` or whitespace (see ``SPEAKER_PATTERN``)
"""

from __future__ import annotations

import re

# --- Canonical roles (do not rename — used across session_parser, DLCR, tests) ---
ROLE_PATIENT = "patient"
ROLE_THERAPIST = "therapist"

# --- English surface labels (fixtures, international transcripts) ---
LABEL_PATIENT_EN = "Patient"
LABEL_THERAPIST_EN = "Therapist"

# --- Russian surface labels (Ethan TFP RU corpus, _noone_local transcripts) ---
LABEL_PATIENT_RU = "Пациент"
LABEL_THERAPIST_RU = "Терапевт"

# --- Short Cyrillic tags (transcript_parser compatibility; prefer full labels in new text) ---
LABEL_PATIENT_RU_SHORT = "П"
LABEL_THERAPIST_RU_SHORT = "Т"

# Map normalized lowercase token → canonical role
SPEAKER_ALIASES: dict[str, str] = {
    LABEL_PATIENT_EN.lower(): ROLE_PATIENT,
    LABEL_THERAPIST_EN.lower(): ROLE_THERAPIST,
    LABEL_PATIENT_RU.lower(): ROLE_PATIENT,
    LABEL_THERAPIST_RU.lower(): ROLE_THERAPIST,
    LABEL_PATIENT_RU_SHORT.lower(): ROLE_PATIENT,
    LABEL_THERAPIST_RU_SHORT.lower(): ROLE_THERAPIST,
}


def _alt_group(words: tuple[str, ...]) -> str:
    return "|".join(re.escape(w) for w in words)


# Level-15 ``parse_session_dialogue``: line must start with label + colon + optional space
_PATIENT_WORDS = (LABEL_PATIENT_EN, LABEL_PATIENT_RU)
_THERAPIST_WORDS = (LABEL_THERAPIST_EN, LABEL_THERAPIST_RU)

PATIENT_LINE_PREFIX = re.compile(
    rf"^\s*(?:{_alt_group(_PATIENT_WORDS)})\s*:\s*",
    re.IGNORECASE,
)
THERAPIST_LINE_PREFIX = re.compile(
    rf"^\s*(?:{_alt_group(_THERAPIST_WORDS)})\s*:\s*",
    re.IGNORECASE,
)

# Transcript turn parser: allows ``:`` or whitespace after label; includes short П/Т
_SPEAKER_TOKENS = (
    LABEL_PATIENT_RU,
    LABEL_THERAPIST_RU,
    LABEL_PATIENT_EN,
    LABEL_THERAPIST_EN,
    LABEL_PATIENT_RU_SHORT,
    LABEL_THERAPIST_RU_SHORT,
)
SPEAKER_PATTERN = re.compile(
    rf"^\s*(?P<lbl>{_alt_group(_SPEAKER_TOKENS)})\s*[:\s]",
    re.IGNORECASE,
)

# Optional clinical strip (``analysis_input``): line-start role tags → folded away
CLINICAL_ROLE_STRIP_PATTERN = re.compile(
    rf"^(?:patient|therapist|doctor|client|clinician|{_alt_group((LABEL_PATIENT_RU, LABEL_THERAPIST_RU))})\s*:\s*",
    re.IGNORECASE,
)


def resolve_speaker_token(raw_label: str) -> str:
    """Map matched label (any case) to ``patient`` / ``therapist`` / original if unknown."""
    key = (raw_label or "").strip().lower()
    return SPEAKER_ALIASES.get(key, key)


def transcript_has_both_clinical_speakers(text: str) -> bool:
    """
    True when the text contains at least one line starting with a **patient** role label
    and one with a **therapist** role label (RU or EN, same rules as ``SPEAKER_PATTERN``).

    Used to decide whether to run ``analyze_session_speaker_aware`` on real transcripts
    (e.g. ``Пациент:`` / ``Терапевт:``) without hard-coding English ``Patient:`` / ``Therapist:``.
    """
    if not text or not isinstance(text, str):
        return False
    has_patient = False
    has_therapist = False
    for line in text.splitlines():
        m = SPEAKER_PATTERN.match(line)
        if not m:
            continue
        role = resolve_speaker_token(m.group("lbl").strip())
        if role == ROLE_PATIENT:
            has_patient = True
        elif role == ROLE_THERAPIST:
            has_therapist = True
        if has_patient and has_therapist:
            return True
    return False
