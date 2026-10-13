# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Map concept pairs to TRIZ-style resolution principles (deterministic)."""

from __future__ import annotations

from hesperia.extensions.triz.models import Contradiction

_RAW_TABLE: dict[tuple[str, str], str] = {
    ("regulation", "freedom"): "counterbalance",
    ("growth", "stability"): "parameter_change",
    ("security", "privacy"): "segmentation",
    ("centralization", "autonomy"): "dynamic_adaptation",
}

DEFAULT_PRINCIPLE = "parameter_change"


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_")


def _symmetric_table() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for (a, b), v in _RAW_TABLE.items():
        x, y = sorted((_norm(a), _norm(b)))
        out[(x, y)] = v
    return out


TRIZ_PAIR_TO_PRINCIPLE: dict[tuple[str, str], str] = _symmetric_table()


def classify_contradiction(concept_a: str, concept_b: str) -> str:
    """Return TRIZ principle for the pair; unknown → parameter_change."""
    a, b = _norm(concept_a), _norm(concept_b)
    if not a or not b:
        return DEFAULT_PRINCIPLE
    key = tuple(sorted((a, b)))
    return TRIZ_PAIR_TO_PRINCIPLE.get(key, DEFAULT_PRINCIPLE)


def classify_contradictions(contradictions: list[Contradiction]) -> list[Contradiction]:
    """Apply TRIZ classification to each contradiction (stable order)."""
    for c in sorted(contradictions, key=lambda x: (x.concept_a, x.concept_b)):
        c.triz_class = classify_contradiction(c.concept_a, c.concept_b)
    return sorted(contradictions, key=lambda x: (-x.score, x.concept_a, x.concept_b))
