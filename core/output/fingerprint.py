"""Fingerprint generation for canonical results."""

from __future__ import annotations

from core.diagnostics.determinism import deterministic_hash


def build_fingerprint(payload: dict) -> str:
    return deterministic_hash(payload)

