# HESPERIA — FPF-HSR-13: mandatory engine-governed ground-truth blocks.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Three-axis doctrine (governance/SPEC-ETHAN-HESPERIA-AGENT-AUTONOMOUS-INVOCATION.md, brain repo):
operational freedom is unrestricted, but every agent-facing response must carry three
engine-authored blocks — logical, weight, source_activation — never optional pass-through
fields an agent could omit by construction.

Ref: governance/ETHAN-FPF-HSR-02-10-ARCHITECTURE-PACKET-2026-07-19.md §FPF-HSR-07.

Applied at exactly two seams so both agent-facing surfaces inherit it from one place:
- runtime/services/product_interpret_service.py (HTTP /product/interpret, FPF-HSR-11)
- sphere/router/tool_inquiry.py (CLI router-inquire + hesperia-router MCP, FPF-HSR-12)
"""

from __future__ import annotations

from typing import Any

GROUND_TRUTH_SCHEMA = "hesperia.agent_response_ground_truth.v0_1"


class GroundTruthMissingError(ValueError):
    """Raised when one of the three mandatory blocks cannot be derived — hard fail, not silent omit."""


def derive_ground_truth_blocks(envelope: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract logical / weight / source_activation from a RouterInputEnvelope-shaped dict."""
    engine_trace = envelope.get("engine_trace") or {}
    gtp = envelope.get("gtp")

    logical: dict[str, Any] = {}
    if engine_trace:
        logical["engine_trace_present"] = True
    if envelope.get("logic_mapping"):
        logical["logic_mapping"] = envelope["logic_mapping"]
    if gtp:
        imprint = gtp.get("thought_imprint") or {}
        logical["gtp_fired_sides"] = imprint.get("fired_sides")
        logical["gtp_fired_operators"] = imprint.get("fired_operators")

    weight: dict[str, Any] = {}
    for key in ("governance", "loopability", "tension_energy", "obstacle_score"):
        if key in engine_trace:
            weight[key] = engine_trace[key]
    policy_block = envelope.get("policy_block") or {}
    if "risk_level" in policy_block:
        weight["risk_level"] = policy_block["risk_level"]
    if gtp:
        weight["gtp_coherence"] = gtp.get("coherence")

    source_activation: dict[str, Any] = {}
    for key in ("corpus_snapshot_id", "policy_snapshot_id"):
        if envelope.get(key):
            source_activation[key] = envelope[key]
    if envelope.get("retrieval_context"):
        source_activation["retrieval_context_present"] = True
    if gtp:
        source_activation["gtp_current_hex"] = gtp.get("current_hex")
        source_activation["gtp_next_hex"] = (gtp.get("gtpa") or {}).get("next_hex")

    return {"logical": logical, "weight": weight, "source_activation": source_activation}


def enforce_ground_truth(envelope: dict[str, Any]) -> dict[str, Any]:
    """
    Compute the three blocks and hard-fail if any is empty — never silently omit one.
    Returns the `ground_truth` block to attach under that key on the response.
    """
    blocks = derive_ground_truth_blocks(envelope)
    missing = [name for name, block in blocks.items() if not block]
    if missing:
        raise GroundTruthMissingError(
            f"missing engine-governed ground-truth block(s): {missing}"
        )
    return {"schema": GROUND_TRUTH_SCHEMA, **blocks}
