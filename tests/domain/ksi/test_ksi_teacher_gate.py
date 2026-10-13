from __future__ import annotations

import pytest

from core.domain.ksi import (
    GateVerdict,
    KsiThresholds,
    build_teacher_prompt_sections,
    rank_missing_bridges,
    replay_concept_residuals,
    sandbox_residual_improved,
    serialize_teacher_packet,
    validate_proposal,
    validate_proposal_packet,
)
from core.domain.ksi.expected_j import IncomingEdge


LEGAL_TYPES = {"activates", "inhibits", "expresses", "requires"}


class TestTeacherPacket:
    def test_serialize_and_rank_bridges(self) -> None:
        incidents = [
            {
                "incident_type": "DEAD_CONCEPT",
                "concept_id": "SHAME",
                "expected": 0.82,
                "observed": 0.1,
                "residual": 0.72,
                "incoming_edges": [
                    {"source": "FAILURE", "type": "activates", "W_e": 0.8, "R_e": 1.0}
                ],
                "context_area": "interpersonal_regulation",
            }
        ]
        bridges = [
            {"concept_i": "REJECTION", "concept_j": "WITHDRAWAL", "bridge_need_score": 0.55},
            {"concept_i": "FAILURE", "concept_j": "SHAME", "bridge_need_score": 0.71},
        ]
        packet = serialize_teacher_packet(
            session_id="sess-1",
            iteration_id="iter-1",
            incidents=incidents,
            missing_bridges=bridges,
            active_concepts_in_session=["FAILURE", "REJECTION"],
            topology={"areas": ["interpersonal_regulation"]},
        )
        assert packet["ksi_version"] == "0.1"
        assert packet["incidents"][0]["incoming_edges"][0]["W_e"] == 0.8
        ranked = packet["missing_bridges"]
        assert ranked[0]["bridge_need_score"] == 0.71
        sections = build_teacher_prompt_sections(packet, active_areas=["interpersonal_regulation"])
        assert "H62-032" in sections["structure"]
        assert "H62-033" in sections["relations"]
        assert "FAILURE" in sections["structure"]

    def test_rank_missing_bridges_helper(self) -> None:
        ranked = rank_missing_bridges(
            [
                {"bridge_need_score": 0.2},
                {"bridge_need_score": 0.9},
            ]
        )
        assert ranked[0]["bridge_need_score"] == 0.9


class TestAcceptanceGate:
    @pytest.fixture
    def th(self) -> KsiThresholds:
        return KsiThresholds()

    def test_accept_valid_add_edge(self, th: KsiThresholds) -> None:
        proposal = {
            "action": "add_edge",
            "source": "A",
            "target": "B",
            "type": "activates",
            "W_e_proposed": 0.7,
            "justification": "bridge gap",
            "confidence": 0.9,
        }
        verdict = validate_proposal(proposal, legal_relation_types=LEGAL_TYPES, thresholds=th)
        assert verdict.status == "ACCEPT"

    def test_reject_low_confidence(self, th: KsiThresholds) -> None:
        proposal = {
            "action": "add_edge",
            "source": "A",
            "target": "B",
            "type": "activates",
            "W_e_proposed": 0.7,
            "justification": "weak",
            "confidence": 0.5,
        }
        verdict = validate_proposal(proposal, legal_relation_types=LEGAL_TYPES, thresholds=th)
        assert verdict.status == "REJECT"
        assert "confidence_below_tau_teacher" in verdict.reasons

    def test_reject_illegal_type(self, th: KsiThresholds) -> None:
        proposal = {
            "action": "add_edge",
            "source": "A",
            "target": "B",
            "type": "not_a_relation",
            "W_e_proposed": 0.7,
            "justification": "bad type",
            "confidence": 0.9,
        }
        verdict = validate_proposal(proposal, legal_relation_types=LEGAL_TYPES, thresholds=th)
        assert verdict.status == "REJECT"
        assert "type_not_legal" in verdict.reasons

    def test_reject_activation_inhibition_contradiction(self, th: KsiThresholds) -> None:
        proposal = {
            "action": "add_edge",
            "source": "A",
            "target": "B",
            "type": "activates",
            "W_e_proposed": 0.5,
            "justification": "conflict",
            "confidence": 0.9,
        }
        existing = [("A", "B", "inhibits")]
        verdict = validate_proposal(
            proposal,
            legal_relation_types=LEGAL_TYPES,
            existing_edges=existing,
            thresholds=th,
        )
        assert verdict.status == "REJECT"
        assert "activation_inhibition_contradiction" in verdict.reasons

    def test_pause_add_concept(self, th: KsiThresholds) -> None:
        proposal = {
            "action": "add_concept",
            "justification": "new node",
            "confidence": 0.95,
        }
        verdict = validate_proposal(proposal, legal_relation_types=LEGAL_TYPES, thresholds=th)
        assert verdict.status == "PAUSE"

    def test_validate_packet_batch(self, th: KsiThresholds) -> None:
        packet = {
            "proposals": [
                {
                    "action": "update_edge_weight",
                    "source": "A",
                    "target": "B",
                    "W_e_proposed": 0.4,
                    "justification": "tune",
                    "confidence": 0.8,
                }
            ]
        }
        verdicts = validate_proposal_packet(packet, legal_relation_types=LEGAL_TYPES, thresholds=th)
        assert len(verdicts) == 1
        assert verdicts[0].status == "ACCEPT"


class TestSandboxReplay:
    def test_replay_and_improvement_gate(self) -> None:
        edges = [
            IncomingEdge(source="A", target="B", relation_type="activates", w_e=0.5),
        ]
        activations = {"A": 1.0, "B": 0.1}
        before = replay_concept_residuals(["B"], edges, activations)
        after = {"B": before["B"] - 0.1, "A": before.get("A", 0.0)}
        assert sandbox_residual_improved(
            before["B"],
            after["B"],
            incident_concept="B",
            all_before=before,
            all_after=after,
        )
        assert not sandbox_residual_improved(
            before["B"],
            before["B"],
            incident_concept="B",
            all_before=before,
            all_after=before,
        )
