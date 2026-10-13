# FPF-HSR-13 — mandatory logical/weight/source_activation ground-truth blocks.
# Ref: governance/ETHAN-FPF-HSR-02-10-ARCHITECTURE-PACKET-2026-07-19.md §FPF-HSR-07.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from runtime.services.product_interpret_service import run_product_interpret
from runtime.shipping.api_main import create_app
from sphere.router.ground_truth import (
    GROUND_TRUTH_SCHEMA,
    GroundTruthMissingError,
    derive_ground_truth_blocks,
    enforce_ground_truth,
)
from sphere.router.pre_llm_compiler import compile_router_envelope
from sphere.router.tool_inquiry import build_tool_inquiry_packet

_TEXT = "FPF-HSR-13 ground truth block test."


def test_enforce_ground_truth_on_real_envelope_has_all_three_blocks() -> None:
    envelope = compile_router_envelope(_TEXT)
    gt = enforce_ground_truth(envelope)
    assert gt["schema"] == GROUND_TRUTH_SCHEMA
    assert gt["logical"]
    assert gt["weight"]
    assert gt["source_activation"]


def test_enforce_ground_truth_hard_fails_on_empty_envelope() -> None:
    with pytest.raises(GroundTruthMissingError):
        enforce_ground_truth({})


def test_derive_ground_truth_blocks_missing_names_reported() -> None:
    blocks = derive_ground_truth_blocks({})
    assert blocks == {"logical": {}, "weight": {}, "source_activation": {}}
    with pytest.raises(GroundTruthMissingError, match="logical.*weight.*source_activation"):
        enforce_ground_truth({})


def test_enforce_ground_truth_includes_gtp_when_present() -> None:
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"HESPERIA_GTP_ENABLED": "1"}):
        envelope = compile_router_envelope(
            _TEXT,
            context_packet={"gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10}},
        )
    gt = enforce_ground_truth(envelope)
    assert gt["logical"]["gtp_fired_sides"] is not None
    assert gt["source_activation"]["gtp_current_hex"] == {
        "area_id": 0,
        "global_id": 3,
        "hex_index": 10,
    }


def test_run_product_interpret_response_carries_ground_truth() -> None:
    out = run_product_interpret(_TEXT, mode="deterministic")
    assert out["ground_truth"]["schema"] == GROUND_TRUTH_SCHEMA
    assert out["ground_truth"]["logical"]
    assert out["ground_truth"]["weight"]
    assert out["ground_truth"]["source_activation"]


def test_product_interpret_endpoint_response_carries_ground_truth() -> None:
    client = TestClient(create_app())
    r = client.post("/product/interpret", json={"text": _TEXT, "mode": "deterministic"})
    assert r.status_code == 200
    assert r.json()["ground_truth"]["schema"] == GROUND_TRUTH_SCHEMA


def test_tool_inquiry_packet_carries_ground_truth() -> None:
    packet = build_tool_inquiry_packet(_TEXT)
    assert packet["ground_truth"]["schema"] == GROUND_TRUTH_SCHEMA
    assert packet["ground_truth"]["logical"]
    assert packet["ground_truth"]["weight"]
    assert packet["ground_truth"]["source_activation"]
