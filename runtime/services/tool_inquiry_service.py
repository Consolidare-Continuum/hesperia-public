# HESPERIA — Tool inquiry service facade.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.services.testing_params_emit import attach_testing_params_to_inquiry
from sphere.router.tool_inquiry import (
    build_tool_inquiry_packet,
    load_context_packet_json as _load_context_packet_json,
    serialize_json_only,
)

def load_context_packet_json(path: Path) -> dict[str, Any]:
    """Load optional context_rag JSON from file for inquiry augmentation."""
    return _load_context_packet_json(path)


def run_tool_inquiry(
    text: str,
    assets_root: Path | None = None,
    *,
    context_packet: dict[str, Any] | None = None,
    thinking_map_outcome: dict[str, Any] | None = None,
) -> str:
    """Return JSON-only string for CLI/MCP surfaces."""
    try:
        from runtime.shipping.analyze_profile import apply_analyze_profile_defaults, resolve_analyze_profile

        apply_analyze_profile_defaults()
        if resolve_analyze_profile() == "tfp" and context_packet is None:
            from runtime.shipping.tfp_mvp_context import build_tfp_mvp_context_packet

            context_packet = build_tfp_mvp_context_packet(query_text=text)
        elif resolve_analyze_profile() == "tfp":
            from runtime.shipping.tfp_mvp_context import merge_tfp_mvp_context

            context_packet = merge_tfp_mvp_context(context_packet, query_text=text)
    except Exception:
        pass
    packet = build_tool_inquiry_packet(
        text,
        assets_root,
        context_packet=context_packet,
        thinking_map_outcome=thinking_map_outcome,
    )
    packet = attach_testing_params_to_inquiry(packet)
    return serialize_json_only(packet)
