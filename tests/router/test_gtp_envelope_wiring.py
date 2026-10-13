# GTP-07 — gtp block wiring into RouterInputEnvelope (flag-gated additive field).

from __future__ import annotations

import os
from unittest.mock import patch

from jsonschema import Draft202012Validator

from sphere.router.pre_llm_compiler import compile_gtp_block, compile_router_envelope

_TEXT = "TFP reflective narrative: patient mood regulation sleep anxiety therapy session."


def test_gtp_absent_by_default() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HESPERIA_GTP_ENABLED", None)
        env = compile_router_envelope(_TEXT, corpus_snapshot_id="test-corpus")
    assert "gtp" not in env


def test_gtp_absent_when_flag_on_but_no_current_hex() -> None:
    with patch.dict(os.environ, {"HESPERIA_GTP_ENABLED": "1"}):
        env = compile_router_envelope(_TEXT, corpus_snapshot_id="test-corpus")
    assert "gtp" not in env


def test_gtp_absent_when_current_hex_present_but_flag_off() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HESPERIA_GTP_ENABLED", None)
        env = compile_router_envelope(
            _TEXT,
            corpus_snapshot_id="test-corpus",
            context_packet={"gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10}},
        )
    assert "gtp" not in env


def test_gtp_present_when_flag_on_and_current_hex_given() -> None:
    with patch.dict(os.environ, {"HESPERIA_GTP_ENABLED": "1"}):
        env = compile_router_envelope(
            _TEXT,
            corpus_snapshot_id="test-corpus",
            context_packet={
                "gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10},
                "gtp_powv_position": [0.3, -0.2, 0.15],
            },
        )
    assert "gtp" in env
    assert env["gtp"]["schema"] == "hesperia.gtp_v0_1"


def test_gtp_block_validates_against_its_own_schema() -> None:
    import json
    from pathlib import Path

    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / "assets" / "schemas" / "gtp" / "gtp_v0_1.schema.json"
        ).read_text(encoding="utf-8")
    )
    block = compile_gtp_block(_TEXT, current_hex={"area_id": 0, "global_id": 3, "hex_index": 10})
    Draft202012Validator(schema).validate(block)
