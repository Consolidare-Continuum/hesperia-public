# HESPERIA — Tool inquiry gate (HSR-V7-07).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""JSON-only deterministic packets for CLI/MCP compliance path — no free-form prose."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TOOL_INQUIRY_SCHEMA = "hesperia.tool_inquiry_packet.v0_1"
ALLOWED_PACKET_KINDS = frozenset({"router_envelope", "context_packet"})


def reject_prose_output(text: str) -> None:
    """Raise when tool surface would emit non-JSON (compliance gate)."""
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("tool_inquiry_empty_output")
    if not stripped.startswith("{") and not stripped.startswith("["):
        raise ValueError("tool_inquiry_requires_json_only")


def serialize_json_only(packet: dict[str, Any]) -> str:
    """Deterministic JSON serialization — sole allowed tool output format."""
    reject_prose_output(json.dumps(packet)[:1])  # always passes for dict
    return json.dumps(packet, sort_keys=True, ensure_ascii=False)


def build_tool_inquiry_packet(
    text: str,
    assets_root: Path | None = None,
    *,
    context_packet: dict[str, Any] | None = None,
    thinking_map_outcome: dict[str, Any] | None = None,
    packet_kind: str = "router_envelope",
) -> dict[str, Any]:
    """Pull inspectable router packet — augment-only, never replace routing."""
    if packet_kind not in ALLOWED_PACKET_KINDS:
        raise ValueError(f"unsupported_packet_kind: {packet_kind}")

    from sphere.router.pre_llm_compiler import compile_router_envelope

    if packet_kind == "context_packet" and context_packet is not None:
        return {
            "schema": TOOL_INQUIRY_SCHEMA,
            "packet_kind": "context_packet",
            "json_only": True,
            "context_packet": context_packet,
        }

    envelope = compile_router_envelope(
        text,
        assets_root,
        context_packet=context_packet,
        thinking_map_outcome=thinking_map_outcome,
    )
    # FPF-HSR-13: mandatory logical/weight/source_activation blocks on this surface too — the
    # CLI (router-inquire) and the hesperia-router MCP tool both go through this function, so
    # this is the one seam that covers both without duplicating the enforcement.
    from sphere.router.ground_truth import enforce_ground_truth

    return {
        "schema": TOOL_INQUIRY_SCHEMA,
        "packet_kind": "router_envelope",
        "json_only": True,
        "router_envelope": envelope,
        "ground_truth": enforce_ground_truth(envelope),
    }


def load_context_packet_json(path: Path) -> dict[str, Any]:
    """Load optional context_rag JSON from file for inquiry augmentation."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("context_packet_must_be_object")
    return data
