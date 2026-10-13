# FPF-HSR-11 — InterpretBody.context_packet on /product/interpret.
# Ref: governance/ETHAN-FPF-HSR-02-10-ARCHITECTURE-PACKET-2026-07-19.md §FPF-HSR-05.

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from runtime.shipping.api_main import create_app

_TEXT = "FPF-HSR-11 context_packet endpoint test."


def _client() -> TestClient:
    return TestClient(create_app())


def test_context_packet_absent_unaffected() -> None:
    """Backward compat: no context_packet -> unchanged response shape, no gtp key."""
    r = _client().post("/product/interpret", json={"text": _TEXT, "mode": "deterministic"})
    assert r.status_code == 200
    assert "gtp" not in r.json()["router_envelope"]


def test_context_packet_unknown_top_level_key_rejected() -> None:
    r = _client().post(
        "/product/interpret",
        json={"text": _TEXT, "context_packet": {"not_a_real_key": True}},
    )
    assert r.status_code == 422


def test_context_packet_oversized_rejected() -> None:
    huge = {"coherence_hints": {"blob": "x" * 30000}}
    r = _client().post("/product/interpret", json={"text": _TEXT, "context_packet": huge})
    assert r.status_code == 422


def test_context_packet_gtp_current_hex_absent_flag_no_gtp_block() -> None:
    """Flag off by default -> gtp block absent even with gtp_current_hex supplied."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HESPERIA_GTP_ENABLED", None)
        r = _client().post(
            "/product/interpret",
            json={
                "text": _TEXT,
                "context_packet": {"gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10}},
            },
        )
    assert r.status_code == 200
    assert "gtp" not in r.json()["router_envelope"]


def test_context_packet_gtp_current_hex_with_flag_on() -> None:
    with patch.dict(os.environ, {"HESPERIA_GTP_ENABLED": "1"}):
        r = _client().post(
            "/product/interpret",
            json={
                "text": _TEXT,
                "context_packet": {
                    "gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10},
                    "gtp_powv_position": [0.3, -0.2, 0.15],
                },
            },
        )
    assert r.status_code == 200
    env = r.json()["router_envelope"]
    assert env["gtp"]["schema"] == "hesperia.gtp_v0_1"


def test_context_packet_thinking_map_outcome_extracted_and_forwarded() -> None:
    """thinking_map_outcome travels inside context_packet on the wire but drives
    logic_mapping/policy_block via the thinking-map bridge, same as the Python-level path."""
    outcome = {
        "kind": "gold_test_outcome",
        "llm_prompt_state": {"logic": {"facts": ["f1"], "actions": [], "source": "test"}},
    }
    r = _client().post(
        "/product/interpret",
        json={"text": _TEXT, "context_packet": {"thinking_map_outcome": outcome}},
    )
    assert r.status_code == 200
    env = r.json()["router_envelope"]
    assert env["logic_mapping"]["source"] == "test"
    assert env["policy_block"]["outcome_kind"] == "gold_test_outcome"
