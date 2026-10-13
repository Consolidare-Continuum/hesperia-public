"""Structured execution context schema and validators."""

from __future__ import annotations

from typing import Any

from core.engine.language import validate_signals


def build_context(text: str, signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    validated_signals = validate_signals(signals)
    return {
        "input": {"text": str(text), "signals": validated_signals},
        "signals": {"validated": validated_signals},
        "families": {},
        "areas": {},
        "metrics": {},
        "modules": {},
        "meta": {"trace": []},
    }


def validate_context(ctx: dict[str, Any], phase: str) -> None:
    required_top = ("input", "signals", "families", "areas", "metrics", "modules", "meta")
    for key in required_top:
        if key not in ctx:
            raise ValueError(f"context_schema_missing:{phase}:{key}")
    if not isinstance(ctx["input"], dict) or not isinstance(ctx["modules"], dict):
        raise ValueError(f"context_schema_invalid_container:{phase}")
    if not isinstance(ctx["input"].get("text"), str):
        raise ValueError(f"context_schema_invalid_input_text:{phase}")
    if not isinstance(ctx["input"].get("signals"), list):
        raise ValueError(f"context_schema_invalid_input_signals:{phase}")

