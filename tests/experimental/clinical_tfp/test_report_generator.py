# HESPERIA — Tests for LEVEL 11 Clinical report generator
"""Report fields, aggression profile, session trajectory, optional output formats."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _analysis(areas=None, families=None):
    return {
        "areas": areas or {},
        "families": families or {},
        "concepts": {},
    }


def _interpretation(
    dominant_area="",
    dominant_family="",
    defense_pattern="",
    object_relation_pattern="",
    aggression_level="low",
):
    return {
        "dominant_area": dominant_area,
        "dominant_family": dominant_family,
        "defense_pattern": defense_pattern,
        "object_relation_pattern": object_relation_pattern,
        "aggression_level": aggression_level,
    }


def _topology(transitions=None, aggression_curve=None, state_sequence=None):
    return {
        "transitions": transitions or [],
        "aggression_curve": aggression_curve or [],
        "state_sequence": state_sequence or [],
    }


def test_report_fields_generated() -> None:
    from research.clinical_tfp.report_generator import generate_clinical_report

    analysis = _analysis(
        areas={"A3": 0.7, "A2": 0.5, "A4": 0.6},
        families={"A3_F1": 0.8, "A2_F3": 0.5},
    )
    interpretation = _interpretation(
        dominant_area="A3",
        defense_pattern="splitting",
        object_relation_pattern="persecutory_object",
        aggression_level="high",
    )
    topology = _topology(
        transitions=[["A2", "A3"], ["A3", "A4"]],
        aggression_curve=[0.1, 0.3, 0.7],
        state_sequence=["A2", "A3", "A4"],
    )
    report = generate_clinical_report(analysis, interpretation, topology)

    assert "session_summary" in report
    assert "dominant_dynamics" in report
    assert "defense_patterns" in report
    assert "object_relations" in report
    assert "aggression_profile" in report
    assert "session_trajectory" in report
    assert "clinical_flags" in report
    assert isinstance(report["clinical_flags"], list)
    assert "защит" in report["session_summary"] or "A3" in report["session_summary"]
    assert "расщепление" in report["dominant_dynamics"] or "splitting" in report["dominant_dynamics"]


def test_aggression_description_correct() -> None:
    from research.clinical_tfp.report_generator import describe_aggression_profile

    # rising curve → нарастание
    analysis = _analysis(areas={"A4": 0.8})
    topology = _topology(aggression_curve=[0.2, 0.4, 0.6, 0.8])
    text = describe_aggression_profile(analysis, topology)
    assert "агресси" in text.lower() or "A4" in text
    assert "нарастание" in text or "уровень" in text or "высок" in text.lower()

    # low aggression, empty curve
    analysis_low = _analysis(areas={"A4": 0.1})
    text_low = describe_aggression_profile(analysis_low, _topology())
    assert "низкий" in text_low or "низк" in text_low.lower()


def test_transitions_described_correctly() -> None:
    from research.clinical_tfp.report_generator import describe_session_trajectory

    topo = _topology(state_sequence=["A2", "A3", "A3", "A4", "A7"])
    traj = describe_session_trajectory(topo)
    assert "A2" in traj and "A3" in traj and "A4" in traj
    assert " → " in traj

    topo2 = _topology(transitions=[["A2", "A3"], ["A3", "A4"]])
    traj2 = describe_session_trajectory(topo2)
    assert "A2" in traj2 and "A4" in traj2


def test_clinical_flags_detected() -> None:
    from research.clinical_tfp.report_generator import detect_clinical_flags

    analysis = _analysis(areas={"A4": 0.7, "A5": 0.4}, families={"A3_F1": 0.6, "A3_F5": 0.6})
    interp = _interpretation(aggression_level="high", defense_pattern="projective_identification")
    flags = detect_clinical_flags(analysis, interp)
    assert "high aggression" in flags

    interp2 = _interpretation(object_relation_pattern="identity_diffusion")
    flags2 = detect_clinical_flags(_analysis(), interp2)
    assert "identity diffusion" in flags2


def test_generate_report_markdown() -> None:
    from research.clinical_tfp.report_generator import generate_clinical_report, generate_report_markdown

    report = generate_clinical_report(
        _analysis(areas={"A3": 0.5}, families={"A3_F1": 0.5}),
        _interpretation(dominant_area="A3", defense_pattern="splitting"),
        _topology(state_sequence=["A2", "A3"]),
    )
    md = generate_report_markdown(report)
    assert "# Клинический отчёт" in md
    assert "## Резюме" in md
    assert "## Защитные паттерны" in md
    assert report["session_summary"] in md


def test_generate_report_json() -> None:
    from research.clinical_tfp.report_generator import generate_clinical_report, generate_report_json

    report = generate_clinical_report(
        _analysis(areas={"A2": 0.5}),
        _interpretation(dominant_area="A2"),
        _topology(),
    )
    js = generate_report_json(report)
    parsed = json.loads(js)
    assert parsed["session_summary"] == report["session_summary"]
    assert "clinical_flags" in parsed


def test_generate_report_text() -> None:
    from research.clinical_tfp.report_generator import generate_clinical_report, generate_report_text

    report = generate_clinical_report(
        _analysis(areas={"A4": 0.5}),
        _interpretation(dominant_area="A4", aggression_level="moderate"),
        _topology(aggression_curve=[0.3, 0.5]),
    )
    text = generate_report_text(report)
    assert "Резюме:" in text
    assert "Профиль агрессии:" in text
    assert report["session_summary"] in text
