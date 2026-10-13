"""HSR-V7-03/04 — router envelope + fingerprint."""

from __future__ import annotations

import json
from pathlib import Path

from sphere.router.envelope_v0_1 import RouterInputEnvelope, envelope_to_dict
from sphere.router.fingerprint import compute_router_fingerprint, fingerprint_contract_v0_1
from sphere.router.thinking_map_bridge import (
    logic_mapping_from_thinking_map,
    policy_block_from_thinking_map,
)


def test_fingerprint_deterministic() -> None:
    a = compute_router_fingerprint(
        input_hash="abc123",
        engine_trace={"step": 1},
        retrieval_context={"chunks": []},
        policy_snapshot_id="policy-v1",
        router_version="v7-router-0.1",
        enabled_modules=["core", "fpf_bridge"],
    )
    b = compute_router_fingerprint(
        input_hash="abc123",
        engine_trace={"step": 1},
        retrieval_context={"chunks": []},
        policy_snapshot_id="policy-v1",
        router_version="v7-router-0.1",
        enabled_modules=["fpf_bridge", "core"],
    )
    assert a == b
    assert len(a) == 64


def test_fingerprint_contract_version() -> None:
    c = fingerprint_contract_v0_1()
    assert c["contract_id"] == "hesperia.router_fingerprint.v0_1"
    assert "sha256" in c["algorithm"]


def test_envelope_schema_file_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = root / "assets" / "schemas" / "router" / "router_input_envelope_v0_1.schema.json"
    assert schema.is_file()
    data = json.loads(schema.read_text(encoding="utf-8"))
    assert data["properties"]["schema"]["const"] == "hesperia.router_input_envelope.v0_1"


def test_thinking_map_bridge_sample() -> None:
    outcome = {
        "kind": "OutcomeKind.CONTINUE",
        "llm_prompt_state": {
            "logic": {"actions": [{"rule": "ci_ready", "satisfied": False}]},
            "gate_status": {},
            "risk_level": "normal",
        },
    }
    logic = logic_mapping_from_thinking_map(outcome)
    policy = policy_block_from_thinking_map(outcome)
    assert "actions" in logic
    assert policy["outcome_kind"] == "OutcomeKind.CONTINUE"
    assert policy["source"] == "fpf-thinking-map"


def test_thinking_map_bridge_pass_through_transitions_and_contract() -> None:
    """FPF-MWI-04: possible_transitions + response_contract pass through."""
    outcome = {
        "kind": "OutcomeKind.COLLECT_EVIDENCE",
        "possible_transitions": [{"id": "execute_safe", "to_state": "verifying"}],
        "response_contract": {"formality": "high"},
        "llm_prompt_state": {"gate_status": {}, "risk_level": "normal"},
    }
    policy = policy_block_from_thinking_map(outcome)
    assert policy["possible_transitions"][0]["id"] == "execute_safe"
    assert policy["response_contract"]["formality"] == "high"


def test_envelope_finalize() -> None:
    env = RouterInputEnvelope(
        router_version="v7-router-0.1",
        input_hash="deadbeef",
        input_text="sample",
        engine_trace={"analyze": True},
        logic_mapping={"actions": []},
        retrieval_context={},
        relation_context={},
        policy_block={"risk_level": "normal"},
        corpus_snapshot_id="corpus-2026-06-28",
        policy_snapshot_id="HSR-V7-01",
    ).finalize()
    d = envelope_to_dict(env)
    assert d["schema"] == "hesperia.router_input_envelope.v0_1"
    assert d["router_fingerprint"]
