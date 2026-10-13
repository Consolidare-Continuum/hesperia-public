# HESPERIA — Operational clinical analytics tests
"""Dialogue structure, intervention classifier, affect intensity, object tracking, session summary."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_build_turns_and_interaction_pairs() -> None:
    """dialogue_structure: build_turns, build_interaction_pairs from Utterances."""
    from hesperia.nlp.session_structure import parse_session_dialogue
    from hesperia.nlp.dialogue_structure import build_turns, build_interaction_pairs

    text = "Patient: A.\nTherapist: B.\nPatient: C."
    utterances = parse_session_dialogue(text)
    turns = build_turns(utterances)
    assert len(turns) == 3
    pairs = build_interaction_pairs(utterances)
    assert len(pairs) == 1
    assert pairs[0].patient_turn.utterance.speaker == "patient"
    assert pairs[0].therapist_intervention.utterance.speaker == "therapist"
    assert pairs[0].patient_reaction.utterance.speaker == "patient"


def test_classify_intervention() -> None:
    """Intervention classifier returns clarification, confrontation, interpretation, limit_setting, support."""
    from research.clinical_tfp.intervention_classifier import classify_intervention, classify_intervention_with_scores

    assert classify_intervention("Что вы чувствуете?") == "clarification"
    assert classify_intervention("I notice a contradiction.") == "confrontation"
    assert classify_intervention("Perhaps you are angry.") == "interpretation"
    assert classify_intervention("We need to stop here.") == "limit_setting"
    assert classify_intervention("I understand.") == "support"
    out = classify_intervention_with_scores("Что вы имеете в виду?")
    assert out["type"] == "clarification"
    assert "scores" in out


def test_estimate_affect_intensity() -> None:
    """Affect intensity in [0..1] from lexical and exclamation."""
    from research.clinical_tfp.affect_intensity import estimate_affect_intensity, estimate_affect_intensity_with_breakdown

    assert 0 <= estimate_affect_intensity("я злюсь") <= 1
    assert estimate_affect_intensity("я в бешенстве") >= 0.5
    assert estimate_affect_intensity("я вас ненавижу!!") >= 0.5
    b = estimate_affect_intensity_with_breakdown("достал!")
    assert "intensity" in b and "high_hit" in b


def test_track_object_representations() -> None:
    """Object representation tracking returns therapist/self/third."""
    from research.clinical_tfp.object_representation_tracking import track_object_representations

    activation = {
        "families": {"A2_F1": 0.3, "A2_F3": 0.5},
        "activation_by_direction": {
            "patient_to_therapist": {"families": {"A2_F3": 0.6}, "areas": {}},
        },
    }
    out = track_object_representations(activation)
    assert "therapist_representation" in out
    assert "self_representation" in out
    assert "third_objects" in out
    assert "score" in out["therapist_representation"]


def test_detect_interaction_loops() -> None:
    """Interaction loop detection finds accusation → escalation."""
    from research.clinical_tfp.interaction_loop_detection import detect_interaction_loops

    timeline = [
        {"areas": {"A4": 0.5}, "families": {"A2_F3": 0.4}},
        {"areas": {"A4": 0.7}, "families": {}},
    ]
    loops = detect_interaction_loops(timeline)
    assert isinstance(loops, list)


def test_couple_affect_defense() -> None:
    """Affect-defense coupling returns affect, expected_defense, coupling_strength."""
    from research.clinical_tfp.affect_defense_coupling import couple_affect_defense, infer_affect_from_areas

    activation = {"areas": {"A4": 0.6}, "families": {"A3_F1": 0.4}}
    out = couple_affect_defense(activation)
    assert "affect" in out and "expected_defense" in out
    assert infer_affect_from_areas({"A4": 0.8}) in ("anger", "rage", "")


def test_build_session_summary() -> None:
    """Session summary contains dominant affects, defenses, object relations, transference."""
    from research.clinical_tfp.session_summary import build_session_summary

    activation = {
        "areas": {"A2": 0.4, "A3": 0.3, "A4": 0.2},
        "families": {"A2_F3": 0.3, "A3_F1": 0.2},
        "activation_by_direction": {},
    }
    summary = build_session_summary(activation, affect_intensity=0.6)
    assert "dominant_affects" in summary
    assert "active_defenses" in summary
    assert "object_relations_pattern" in summary
    assert "transference_indicators" in summary
    assert "object_representations" in summary
    assert "affect_defense_coupling" in summary
