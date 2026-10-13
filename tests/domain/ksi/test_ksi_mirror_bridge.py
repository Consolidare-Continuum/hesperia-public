from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.domain.ksi import (
    BridgeSessionState,
    ConceptStructure,
    IncomingEdge,
    KsiThresholds,
    classify_mirror_deficit_incident,
    classify_missing_bridge,
    compute_bridge_need,
    compute_mirror_cause_scores,
    compute_mirror_deficit,
    gap,
    missing_bridge_incident_payload,
)
from core.domain.ksi.bridge import _co_activation, _context_match, _family_compatibility

MIRROR_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ksi_mirror_graph_v01.json"


class TestMirrorCauseScores:
    @pytest.fixture(scope="class")
    def fixture(self) -> dict:
        with MIRROR_FIXTURE.open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_ranking_matches_gold(self, fixture: dict) -> None:
        edges = [IncomingEdge(**e) for e in fixture["edges"]]
        target = fixture["concept_id"]
        observed = fixture["observed_j"]
        scores = compute_mirror_cause_scores(target, edges, observed)
        got = [(row.source, pytest.approx(row.cause_score, abs=1e-9)) for row in scores]
        expected = [(row["source"], pytest.approx(row["cause_score"], abs=1e-9)) for row in fixture["ranked_causes"]]
        assert got == expected

    def test_mirror_deficit_and_incident(self, fixture: dict) -> None:
        edges = [IncomingEdge(**e) for e in fixture["edges"]]
        activations = fixture["activations"]
        observed = fixture["observed_j"]
        scores = compute_mirror_cause_scores(fixture["concept_id"], edges, observed)
        deficit = compute_mirror_deficit(observed, scores, activations)
        assert deficit == pytest.approx(fixture["mirror_deficit"], abs=1e-9)
        th = KsiThresholds()
        assert (
            classify_mirror_deficit_incident(
                observed_j=observed,
                mirror_deficit=deficit,
                thresholds=th,
            )
            == fixture["expected_incident"]
        )


class TestBridgeNeedComponents:
    def test_co_activation_requires_both_active(self) -> None:
        th = KsiThresholds()
        assert _co_activation("A", "B", {"A": 0.6, "B": 0.2}, th.tau_active) == 0.0
        assert _co_activation("A", "B", {"A": 0.6, "B": 0.7}, th.tau_active) == 1.0

    def test_context_and_family_match(self) -> None:
        session = BridgeSessionState(
            activations={"A": 0.7, "B": 0.8},
            concept_structure={
                "A": ConceptStructure(primary_area="reg", family="f1"),
                "B": ConceptStructure(primary_area="reg", family="f1"),
            },
            active_areas=frozenset({"reg"}),
        )
        assert _context_match("A", "B", session) == 1.0
        assert _family_compatibility("A", "B", session) == 1.0
        assert gap("A", "B", session) == 1.0


class TestBridgeNeedAndMissingBridge:
    def test_bridge_need_product(self) -> None:
        session = BridgeSessionState(
            activations={"REJECTION": 0.72, "WITHDRAWAL": 0.68},
            concept_structure={
                "REJECTION": ConceptStructure(primary_area="interpersonal_regulation", family="avoidance"),
                "WITHDRAWAL": ConceptStructure(primary_area="interpersonal_regulation", family="avoidance"),
            },
            active_areas=frozenset({"interpersonal_regulation"}),
            edge_strength={},
        )
        need = compute_bridge_need("REJECTION", "WITHDRAWAL", session, residual_j=0.72)
        assert need == pytest.approx(0.72, abs=1e-9)
        assert classify_missing_bridge("REJECTION", "WITHDRAWAL", need) == "MISSING_BRIDGE"

    def test_weak_bridge_below_threshold(self) -> None:
        session = BridgeSessionState(
            activations={"REJECTION": 0.72, "WITHDRAWAL": 0.68},
            concept_structure={
                "REJECTION": ConceptStructure(primary_area="interpersonal_regulation"),
                "WITHDRAWAL": ConceptStructure(primary_area="interpersonal_regulation"),
            },
            edge_strength={("REJECTION", "WITHDRAWAL"): 0.9},
        )
        need = compute_bridge_need("REJECTION", "WITHDRAWAL", session, residual_j=0.72)
        assert need == pytest.approx(0.072, abs=1e-9)
        assert classify_missing_bridge("REJECTION", "WITHDRAWAL", need) is None

    def test_missing_bridge_payload(self) -> None:
        session = BridgeSessionState(activations={"A": 0.8, "B": 0.8})
        payload = missing_bridge_incident_payload("A", "B", 0.71, session)
        assert payload["incident_type"] == "MISSING_BRIDGE"
        assert payload["bridge_need_score"] == 0.71
