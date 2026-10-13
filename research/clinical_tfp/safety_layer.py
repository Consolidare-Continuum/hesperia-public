# HESPERIA — Safety Layer
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Защита от hallucinated interpretation, over-activation, false clinical conclusions:
minimum evidence threshold, минимальное число маркеров для интерпретации.
"""

from __future__ import annotations

from typing import Any

from hesperia.config.config_loader import get_clinical_config

DEFAULT_MIN_EVIDENCE_THRESHOLD = 0.02
DEFAULT_MIN_MARKERS = 1


def get_minimum_evidence_threshold() -> float:
    """Порог: не считать активацию значимой ниже этого (из clinical_config)."""
    cfg = get_clinical_config()
    return float(cfg.get("minimum_evidence_threshold", DEFAULT_MIN_EVIDENCE_THRESHOLD))


def get_min_markers_for_interpretation() -> int:
    """Минимум маркеров/активаций для выдачи интерпретации."""
    cfg = get_clinical_config()
    return int(cfg.get("min_markers_for_interpretation", DEFAULT_MIN_MARKERS))


def apply_safety_filter(
    activation: dict[str, Any],
    min_evidence: float | None = None,
    min_markers: int | None = None,
) -> dict[str, Any]:
    """
    Отфильтровать activation: обнулить concept/family/area ниже min_evidence;
    если суммарное число ненулевых концептов < min_markers, вернуть пустые areas/families/concepts
    (не выдавать интерпретацию при недостаточном доказательстве).
    """
    min_ev = min_evidence if min_evidence is not None else get_minimum_evidence_threshold()
    min_m = min_markers if min_markers is not None else get_min_markers_for_interpretation()

    concepts = dict(activation.get("concepts") or {})
    families = dict(activation.get("families") or {})
    areas = dict(activation.get("areas") or {})

    concepts = {k: v for k, v in concepts.items() if float(v) >= min_ev}
    families = {k: v for k, v in families.items() if float(v) >= min_ev}
    areas = {k: v for k, v in areas.items() if float(v) >= min_ev}

    if len(concepts) < min_m:
        concepts = {}
        families = {}
        areas = {}

    out = dict(activation)
    out["concepts"] = concepts
    out["families"] = families
    out["areas"] = areas
    out["safety_filter_applied"] = True
    return out
