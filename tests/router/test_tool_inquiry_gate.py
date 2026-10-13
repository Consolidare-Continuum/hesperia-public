# HSR-V7-07 tool inquiry gate tests.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sphere.router.tool_inquiry import (
    TOOL_INQUIRY_SCHEMA,
    build_tool_inquiry_packet,
    reject_prose_output,
    serialize_json_only,
)


def test_reject_prose_output() -> None:
    with pytest.raises(ValueError, match="json_only"):
        reject_prose_output("This is free-form prose, not JSON.")
    reject_prose_output('{"ok": true}')


def test_build_tool_inquiry_packet_router_envelope() -> None:
    packet = build_tool_inquiry_packet("Inquiry gate smoke.")
    assert packet["schema"] == TOOL_INQUIRY_SCHEMA
    assert packet["json_only"] is True
    assert packet["packet_kind"] == "router_envelope"
    env = packet["router_envelope"]
    assert env["schema"] == "hesperia.router_input_envelope.v0_1"
    assert env["router_fingerprint"]


def test_serialize_json_only_is_valid_json() -> None:
    packet = build_tool_inquiry_packet("Serialize test.")
    raw = serialize_json_only(packet)
    reject_prose_output(raw)
    parsed = json.loads(raw)
    assert parsed["schema"] == TOOL_INQUIRY_SCHEMA


def test_cli_router_inquire_json_only() -> None:
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [
            sys.executable,
            str(repo / "runtime" / "shipping" / "cli_main.py"),
            "router-inquire",
            "--text",
            "CLI inquiry smoke.",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    reject_prose_output(proc.stdout)
    body = json.loads(proc.stdout)
    assert body["json_only"] is True


def test_cli_router_inquire_thinking_map_outcome_extracted(tmp_path: Path) -> None:
    """FPF-HSR-12: thinking_map_outcome inside --context-json is extracted and forwarded,
    same convention as the HTTP context_packet field (api_main.py)."""
    repo = Path(__file__).resolve().parents[2]
    ctx_path = tmp_path / "ctx.json"
    ctx_path.write_text(
        json.dumps(
            {
                "thinking_map_outcome": {
                    "kind": "cli_gold_outcome",
                    "llm_prompt_state": {"logic": {"facts": [], "actions": [], "source": "cli_test"}},
                }
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(repo / "runtime" / "shipping" / "cli_main.py"),
            "router-inquire",
            "--text",
            "CLI thinking_map_outcome smoke.",
            "--context-json",
            str(ctx_path),
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    env = body["router_envelope"]
    assert env["logic_mapping"]["source"] == "cli_test"
    assert env["policy_block"]["outcome_kind"] == "cli_gold_outcome"
