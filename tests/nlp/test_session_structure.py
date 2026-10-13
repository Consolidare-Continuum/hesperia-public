# HESPERIA — LEVEL 15 Speaker-aware session parsing tests
"""Tests: speaker detection, tokenization per speaker, activation per speaker."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_parse_session_dialogue_speaker_detection() -> None:
    """Lines with Patient: / Therapist: produce correct speaker; unlabeled default patient."""
    from hesperia.nlp.session_structure import parse_session_dialogue, Utterance

    text = """Patient: I feel like you suddenly became cold.
Therapist: What made you think that?
Patient: You stopped caring about me."""
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 3
    assert isinstance(utterances[0], Utterance)
    assert utterances[0].speaker == "patient"
    assert "cold" in utterances[0].text
    assert utterances[1].speaker == "therapist"
    assert "think" in utterances[1].text
    assert utterances[2].speaker == "patient"
    assert "caring" in utterances[2].text


def test_parse_session_dialogue_default_patient() -> None:
    """Lines without label default to patient."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    text = """First line no label.
Second line also no label."""
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 1
    assert utterances[0].speaker == "patient"
    assert "First line" in utterances[0].text and "Second line" in utterances[0].text


def test_parse_session_dialogue_case_insensitive() -> None:
    """PATIENT: and THERAPIST: (case variants) are recognized."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    text = """PATIENT: Hello.
THERAPIST: Hi."""
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 2
    assert utterances[0].speaker == "patient" and "Hello" in utterances[0].text
    assert utterances[1].speaker == "therapist" and "Hi" in utterances[1].text


def test_parse_session_dialogue_russian_labels() -> None:
    """Пациент: / Терапевт: align with English Patient:/Therapist: (transcript_speaker_labels)."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    text = """Пациент: Я чувствую, что вы отстранились.
Терапевт: Что для вас значит «отстранились»?
Пациент: Не смотрите на меня."""
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 3
    assert utterances[0].speaker == "patient" and "отстранились" in utterances[0].text
    assert utterances[1].speaker == "therapist" and "значит" in utterances[1].text
    assert utterances[2].speaker == "patient"


def test_tokenization_per_speaker() -> None:
    """Each Utterance has tokens from tokenize + normalize."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    text = """Patient: I feel you hate me now.
Therapist: I notice you feel rejected."""
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 2
    assert all(isinstance(u.tokens, list) for u in utterances)
    assert all(isinstance(t, str) for u in utterances for t in u.tokens)
    # Normalized: lower case
    assert all(t == t.lower() for u in utterances for t in u.tokens)
    assert "feel" in utterances[0].tokens
    assert "notice" in utterances[1].tokens or "feel" in utterances[1].tokens


def test_analyze_session_speaker_aware_shape() -> None:
    """analyze_session_speaker_aware returns areas, families, concepts + speaker_activation."""
    from hesperia.nlp.session_parser import analyze_session_speaker_aware

    text = """Patient: I feel you hate me now.
Therapist: I notice you feel rejected."""
    result = analyze_session_speaker_aware(text)
    assert "areas" in result and "families" in result and "concepts" in result
    assert "speaker_activation" in result
    sa = result["speaker_activation"]
    assert "patient" in sa and "therapist" in sa
    for role in ("patient", "therapist"):
        assert "areas" in sa[role] and "families" in sa[role] and "concepts" in sa[role]


def test_activation_per_speaker_weights() -> None:
    """Patient markers weighted 1.0, therapist 0.5; speaker_activation reflects per-speaker scores."""
    from hesperia.nlp.session_parser import (
        analyze_session_speaker_aware,
        PATIENT_MARKER_WEIGHT,
        THERAPIST_MARKER_WEIGHT,
    )

    assert PATIENT_MARKER_WEIGHT == 1.0
    assert THERAPIST_MARKER_WEIGHT == 0.5

    text = """Patient: I feel you hate me now.
Therapist: I notice you feel rejected."""
    result = analyze_session_speaker_aware(text)
    # Combined activation uses weighted sum; per-speaker blocks are separate
    assert isinstance(result["speaker_activation"]["patient"]["concepts"], dict)
    assert isinstance(result["speaker_activation"]["therapist"]["concepts"], dict)


def test_parse_session_dialogue_empty() -> None:
    """Empty or whitespace input returns empty list."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    assert parse_session_dialogue("") == []
    assert parse_session_dialogue("   \n  ") == []


def test_transcript_has_both_clinical_speakers_ru_and_nbsp() -> None:
    """RU labels + NBSP before label (real _noone_local transcripts) count as dialogue."""
    from hesperia.nlp.transcript_speaker_labels import transcript_has_both_clinical_speakers

    assert not transcript_has_both_clinical_speakers("Пациент: только я.")
    assert transcript_has_both_clinical_speakers(
        "\xa0Пациент: первая реплика.\n\xa0Терапевт: вторая реплика."
    )
    assert transcript_has_both_clinical_speakers(
        "Пациент: одна строка.\nТерапевт: другая строка."
    )


def test_transcript_has_both_clinical_speakers_en() -> None:
    from hesperia.nlp.transcript_speaker_labels import transcript_has_both_clinical_speakers

    assert transcript_has_both_clinical_speakers(
        "Patient: Hello.\nTherapist: Hi there."
    )
