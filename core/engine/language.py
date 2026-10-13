"""Canonical Hesperia language: signal + result schemas."""

from __future__ import annotations

from typing import Any, TypedDict


class HesperiaSignal(TypedDict):
    family_id: int
    strength: float
    source: str | None


class HesperiaResultRef(TypedDict, total=False):
    area_vector: list[float]
    family_vector: list[float]
    dominant_area: int
    dominant_family: int
    tension: float
    loopability: float
    stability: float
    failure_flags: list[str]
    schema_version: str
    fingerprint: str
    deterministic_hash: str


def language_schema() -> dict[str, Any]:
    return {
        "ctx": {
            "input": "dict{text:str,signals:list[signal]}",
            "signals": "dict[str,Any]",
            "families": "dict[str,float]",
            "areas": "dict[str,float]",
            "metrics": "dict[str,Any]",
            "modules": "dict[module_name,dict[str,Any]]",
        },
        "signal": {"family_id": "int", "strength": "float", "source": "str|None"},
        "result": {
            "area_vector": "list[float]",
            "family_vector": "list[float]",
            "dominant_area": "int",
            "dominant_family": "int",
            "tension": "float",
            "loopability": "float",
            "stability": "float",
            "failure_flags": "list[str]",
            "schema_version": "str",
            "fingerprint": "str",
            "deterministic_hash": "str",
        },
    }


def validate_signal(signal: dict[str, Any]) -> HesperiaSignal:
    if not isinstance(signal, dict):
        raise ValueError("signal_invalid_type")
    if "family_id" not in signal:
        raise ValueError("signal_missing_family_id")
    if "strength" not in signal:
        raise ValueError("signal_missing_strength")
    family_id = signal["family_id"]
    strength = signal["strength"]
    source = signal.get("source")
    if not isinstance(family_id, int):
        raise ValueError("signal_invalid_family_id_type")
    if not isinstance(strength, (int, float)):
        raise ValueError("signal_invalid_strength_type")
    if source is not None and not isinstance(source, str):
        raise ValueError("signal_invalid_source_type")
    return {
        "family_id": int(family_id),
        "strength": float(strength),
        "source": source,
    }


def validate_signals(signals: list[dict[str, Any]] | None) -> list[HesperiaSignal]:
    if signals is None:
        return []
    if not isinstance(signals, list):
        raise ValueError("signals_invalid_type")
    return [validate_signal(s) for s in signals]

