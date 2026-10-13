"""Frozen public engine API contract."""

from __future__ import annotations

from typing import Any

from core.runtime.engine import analyze_engine

ENGINE_API_VERSION = "engine_api_v1"


def run_engine_api_v1(text: str, *, signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    _ = signals  # reserved for contract compatibility; consumed by modular runtime internally.
    return analyze_engine(text)

