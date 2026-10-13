# HESPERIA — Dialogue Role Layer, Transference, Temporal Dynamics, Stage Detection
"""Tests: role_direction / target inference, activation_by_direction, transference, timeline, TFP stage."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_infer_utterance_target_patient_to_therapist() -> None:
    """Patient saying 'you' (ты/вы) → target therapist."""
    from hesperia.nlp.session_structure import infer_utterance_target

    assert infer_utterance_target("patient", "Вы меня ненавидите.", ["вы", "меня", "ненавидите"]) == "therapist"
    assert infer_utterance_target("patient", "Ты меня не понимаешь.", []) == "therapist"


def test_infer_utterance_target_therapist_to_patient() -> None:
    """Therapist saying 'you' → target patient."""
    from hesperia.nlp.session_structure import infer_utterance_target

    assert infer_utterance_target("therapist", "Что вы чувствуете?", []) == "patient"


def test_infer_utterance_target_patient_to_third() -> None:
    """Patient with third-person ref, no you → third."""
    from hesperia.nlp.session_structure import infer_utterance_target

    assert infer_utterance_target("patient", "Моя мама меня не понимает.", []) == "third"


def test_parse_session_dialogue_sets_target() -> None:
    """parse_session_dialogue sets Utterance.target from content."""
    from hesperia.nlp.session_structure import parse_session_dialogue

    text = "Patient: Вы меня ненавидите.\nTherapist: Что вы чувствуете?"
    utterances = parse_session_dialogue(text)
    assert len(utterances) == 2
    assert utterances[0].speaker == "patient" and utterances[0].target == "therapist"
    assert utterances[1].speaker == "therapist" and utterances[1].target == "patient"


def test_analyze_session_speaker_aware_activation_by_direction() -> None:
    """analyze_session_speaker_aware returns activation_by_direction and role_direction."""
    from hesperia.nlp.session_parser import analyze_session_speaker_aware

    text = "Patient: Вы меня ненавидите.\nTherapist: Я слышу вас."
    result = analyze_session_speaker_aware(text)
    assert "activation_by_direction" in result
    assert "role_direction" in result
    assert "patient_to_therapist" in result["role_direction"]
    assert result["role_direction"]["patient_to_therapist"]["speaker"] == "patient"
    assert result["role_direction"]["patient_to_therapist"]["target"] == "therapist"


@pytest.mark.tfp
def test_detect_transference() -> None:
    """detect_transference returns positive/negative/projective/idealization/devaluation."""
    from hesperia.tfp import detect_transference

    activation = {
        "activation_by_direction": {
            "patient_to_therapist": {
                "areas": {"A2": 0.5, "A3": 0.3, "A4": 0.6, "A7": 0.2},
                "families": {"A2_F3": 0.5, "A3_F5": 0.2},
            },
        },
    }
    out = detect_transference(activation, "patient_to_therapist")
    assert "negative_transference" in out
    assert "persecutory_object" in out
    assert "scores" in out


@pytest.mark.tfp
def test_transference_summary() -> None:
    """transference_summary returns per-direction detection."""
    from hesperia.tfp import transference_summary

    activation = {"activation_by_direction": {"patient_to_therapist": {"families": {}, "areas": {}}}}
    out = transference_summary(activation)
    assert "patient_to_therapist" in out
    assert "therapist_to_patient" in out
    assert "patient_to_third" in out


def test_build_utterance_windows() -> None:
    """build_utterance_windows splits list into windows of N."""
    from hesperia.nlp.temporal_dynamics import build_utterance_windows

    class U:
        pass
    utts = [U() for _ in range(12)]
    windows = build_utterance_windows(utts, window_size=5)
    assert len(windows) == 3
    assert len(windows[0]) == 5 and len(windows[1]) == 5 and len(windows[2]) == 2


def test_build_activation_timeline() -> None:
    """build_activation_timeline returns list of activation dicts per window."""
    from hesperia.nlp.temporal_dynamics import build_activation_timeline

    text = "Patient: A.\nTherapist: B.\nPatient: C.\nTherapist: D.\nPatient: E.\nTherapist: F."
    timeline = build_activation_timeline(text, window_utterances=2)
    assert isinstance(timeline, list)
    assert len(timeline) >= 1
    for step in timeline:
        assert "areas" in step and "families" in step


@pytest.mark.tfp
def test_detect_tfp_stage() -> None:
    """detect_tfp_stage returns one of chaotic/defense_clarification/interpretation/integration."""
    from hesperia.tfp import TFP_STAGES, detect_tfp_stage

    assert detect_tfp_stage({"A4": 0.7, "A3": 0.5, "A7": 0.1}) in TFP_STAGES
    assert detect_tfp_stage({"A7": 0.6, "A4": 0.2}) == "integration"


@pytest.mark.tfp
def test_stage_from_timeline() -> None:
    """stage_from_timeline computes stage from last N windows."""
    from hesperia.tfp import stage_from_timeline

    timeline = [{"areas": {"A7": 0.6, "A4": 0.1}}, {"areas": {"A7": 0.5}}]
    stage = stage_from_timeline(timeline, last_n=2)
    assert stage in ("chaotic", "defense_clarification", "interpretation", "integration")
