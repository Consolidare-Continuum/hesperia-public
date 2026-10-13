# HESPERIA — hesperia-dev-test engine_trace seam. Copyright © 2026 igareosh.com.
"""Build the internal engine_trace-shaped dict that sphere.fpf_inspect.probe() expects, via the
same tool_inquiry seam tools/fpf_hand_roll_harness.py already uses (_dig_loop). Composition only —
no edits inside sphere/router or sphere/fpf_inspect.
"""

from __future__ import annotations

from typing import Any


def build_dig_input(token: str) -> dict[str, Any]:
    from sphere.router.tool_inquiry import build_tool_inquiry_packet

    inquire = build_tool_inquiry_packet(token)
    envelope = inquire.get("router_envelope") or {}
    engine = envelope.get("engine_trace") or {}
    dig_input = dict(engine)
    dig_input.setdefault("router_envelope", envelope)
    dig_input.setdefault("ground_truth", inquire.get("ground_truth") or {})
    return dig_input
