# HESPERIA — Pre-LLM router compiler (HSR-V7-06).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Compose /analyze + optional context_rag + thinking-map into RouterInputEnvelope."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from sphere.router.envelope_v0_1 import RouterInputEnvelope, envelope_to_dict
from sphere.router.thinking_map_bridge import (
    logic_mapping_from_thinking_map,
    policy_block_from_thinking_map,
)

_DEFAULT_CORPUS_SNAPSHOT = "corpus-unset"
_DEFAULT_POLICY_SNAPSHOT = "HSR-V7-01"
_GTP_ENABLED_ENV = "HESPERIA_GTP_ENABLED"


def _gtp_enabled() -> bool:
    return os.environ.get(_GTP_ENABLED_ENV, "0").strip() in {"1", "true", "True"}


def compile_gtp_block(
    text: str,
    *,
    current_hex: dict[str, int],
    powv_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    """
    GTP-07: compute the `gtp` envelope block for an explicit session position.

    Callers must supply `current_hex` (area_id/global_id/hex_index) — there is no
    session-position tracker elsewhere in the codebase to derive one from (that is
    IPoW/GCS session-state, separately gated per 22_SPEC §12). This function is the
    wiring point; `compile_router_envelope` only calls it when both
    HESPERIA_GTP_ENABLED=1 and `context_packet["gtp_current_hex"]` is present, so
    default behavior (absent gtp block) is unchanged — same flag-default-off
    discipline as HESPERIA_COBALT_ENABLED.
    """
    from sphere.topology.gtp.neighbors import HexCell
    from sphere.topology.gtp.pipeline import gtp_step_to_dict, run_gtp_step

    h = HexCell(**current_hex)
    result = run_gtp_step(text, h, powv_position=powv_position)
    return gtp_step_to_dict(result)


def _input_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _logic_from_engine(engine: dict[str, Any]) -> dict[str, Any]:
    return {
        "dominant_area_id": engine.get("dominant_area_id"),
        "dominant_family_id": engine.get("dominant_family_id"),
        "dominant_concept_id": engine.get("dominant_concept_id"),
        "trace_content_hash": engine.get("trace_content_hash"),
        "source": "engine_analyze",
    }


def _policy_from_engine(engine: dict[str, Any]) -> dict[str, Any]:
    gov = float(engine.get("governance") or 0.0)
    risk = "normal" if gov >= 0.35 else "elevated" if gov >= 0.2 else "high"
    return {
        "risk_level": risk,
        "governance": engine.get("governance"),
        "loopability": engine.get("loopability"),
        "tension_energy": engine.get("tension_energy"),
        "obstacle_score": engine.get("obstacle_score"),
        "source": "engine_analyze",
    }


def compile_router_envelope(
    text: str,
    assets_root: Path | None = None,
    *,
    context_packet: dict[str, Any] | None = None,
    thinking_map_outcome: dict[str, Any] | None = None,
    overlay_hint: dict[str, Any] | None = None,
    temp_relation_overlay: list[dict[str, Any]] | None = None,
    corpus_snapshot_id: str | None = None,
) -> dict[str, Any]:
    """HSR-V7-06: single inspectable routed envelope before LLM."""
    from sphere.router.engine_analyze_bridge import run_engine_analyze

    engine = run_engine_analyze(
        text,
        assets_root=assets_root,
        overlay_hint=overlay_hint,
        temp_relation_overlay=temp_relation_overlay,
    )
    ctx = context_packet or {}
    corpus_id = (
        corpus_snapshot_id
        or ctx.get("corpus_snapshot_id")
        or os.environ.get("HESPERIA_CORPUS_SNAPSHOT_ID", _DEFAULT_CORPUS_SNAPSHOT)
    )
    if thinking_map_outcome:
        logic_mapping = logic_mapping_from_thinking_map(thinking_map_outcome)
        policy_block = policy_block_from_thinking_map(thinking_map_outcome)
    else:
        logic_mapping = _logic_from_engine(engine)
        policy_block = _policy_from_engine(engine)

    gtp_block: dict[str, Any] | None = None
    gtp_current_hex = ctx.get("gtp_current_hex")
    if _gtp_enabled() and gtp_current_hex:
        gtp_block = compile_gtp_block(
            text,
            current_hex=gtp_current_hex,
            powv_position=tuple(ctx.get("gtp_powv_position") or (0.0, 0.0, 0.0)),
        )

    preview = text if len(text) <= 2000 else text[:2000] + "…"
    env = RouterInputEnvelope(
        router_version="v7-router-0.1",
        input_hash=_input_hash(text),
        input_text=preview,
        engine_trace=engine,
        logic_mapping=logic_mapping,
        retrieval_context=ctx.get("retrieval") or ctx.get("retrieval_context") or {},
        relation_context=ctx.get("relation_context") or {},
        policy_block=policy_block,
        corpus_snapshot_id=str(corpus_id),
        policy_snapshot_id=_DEFAULT_POLICY_SNAPSHOT,
        enabled_modules=["core", "router"],
        calculable=ctx.get("calculable"),
        coherence_hints=ctx.get("coherence_hints"),
        observability=ctx.get("observability"),
        gtp=gtp_block,
    ).finalize()
    return envelope_to_dict(env)
