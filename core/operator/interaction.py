"""Interaction law: activation scoring under locality constraints."""

from __future__ import annotations

from core.resolver.score_rules import saturate


def interaction_gain(
    *,
    relevance: float,
    specificity: float,
    locality: float,
    w1: float = 0.45,
    w2: float = 0.35,
    w3: float = 0.2,
) -> float:
    return saturate(w1 * relevance + w2 * specificity + w3 * locality)

