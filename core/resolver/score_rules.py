"""Deterministic scoring rules for candidate concepts."""

from __future__ import annotations

import math

from core.dynamics.constants import get_constant
from core.dynamics.numeric import clamp01


MATCH_BASE = {
    "exact": 10.0,
    "phrase": 9.0,
    "lemma": 7.0,
    "stem": 5.0,
    "pattern": 3.0
}


def saturate(value: float) -> float:
    return clamp01(value)


def effective_empirical_weight(override: float | None = None) -> float:
    """Resolve the Dict D weight, honoring an execution-scoped override."""
    value = (
        get_constant("resolver.coherence_empirical_weight", 0.0)
        if override is None
        else override
    )
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise ValueError("empirical_weight_override must be finite and non-negative")
    return float(value)


def score_candidate(
    match_type: str,
    priority: int,
    specificity_rank: int = 0,
    context_overlap: int = 0,
    coherence_boost: float = 0.0,
    locality: float = 1.0,
    empirical_boost: float = 0.0,
    empirical_weight_override: float | None = None,
) -> float:
    relevance = clamp01(
        (MATCH_BASE.get(match_type, 0.0) / 10.0)
        + float(priority) / float(get_constant("resolver.priority_norm", 100.0))
    )
    specificity = clamp01(float(specificity_rank) / float(get_constant("resolver.specificity_norm", 10.0)))
    local_signal = clamp01(
        (float(context_overlap) / float(get_constant("resolver.context_overlap_norm", 5.0)))
        + float(coherence_boost)
        + float(locality) * 0.2
    )
    # CHI-015 O4: Dict D's empirical (corpus-derived) coherence — isolated term, not
    # bundled into local_signal/weight_locality (spec §9 "Preferred" integration path).
    # w4 defaults to 0.0 (engine_constants.json "coherence_empirical_weight") so this
    # term is inert until an operator-reviewed flip, same discipline as w1-w3.
    empirical_signal = clamp01(float(empirical_boost))
    w1 = float(get_constant("resolver.weight_relevance", 0.45))
    w2 = float(get_constant("resolver.weight_specificity", 0.35))
    w3 = float(get_constant("resolver.weight_locality", 0.2))
    w4 = effective_empirical_weight(empirical_weight_override)
    return saturate(
        w1 * relevance
        + w2 * specificity
        + w3 * local_signal
        + w4 * empirical_signal
    )

