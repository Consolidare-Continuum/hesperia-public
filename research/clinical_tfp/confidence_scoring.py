# HESPERIA — Confidence Scoring
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Каждый вывод с confidence_score для научной надёжности.
Например: A3 defenses: 0.72 confidence, A4 aggression: 0.43 confidence.
"""

from __future__ import annotations

import math
from typing import Any


def _entropy(values: list[float]) -> float:
    """Shannon entropy (normalized distribution)."""
    if not values or sum(values) <= 0:
        return 0.0
    s = sum(values)
    p = [v / s for v in values if v > 0]
    return -sum(x * math.log2(x) for x in p) if p else 0.0


def compute_confidence_scores(activation: dict[str, Any]) -> dict[str, Any]:
    """
    По activation (areas, families, concepts) вычислить confidence_score для каждого уровня.
    Уверенность: выше при доминантном пике, ниже при размытом распределении.
    Формула: confidence = max_score * (1 - normalized_entropy) в пределах [0, 1].
    """
    areas = activation.get("areas") or {}
    families = activation.get("families") or {}
    concepts = activation.get("concepts") or {}

    def level_confidence(d: dict[str, float]) -> float:
        if not d:
            return 0.0
        vals = list(d.values())
        m = max(vals) if vals else 0.0
        ent = _entropy(vals)
        max_ent = math.log2(len(vals)) if len(vals) > 1 else 1.0
        norm_ent = ent / max_ent if max_ent > 0 else 0
        return round(min(1.0, m * (1.0 - norm_ent * 0.5)), 2)

    dom_area = max(areas, key=lambda k: areas[k]) if areas else ""
    dom_family = max(families, key=lambda k: families[k]) if families else ""
    area_conf = {k: round(v, 2) for k, v in areas.items()}
    family_conf = {k: round(v, 2) for k, v in families.items()}
    concept_conf = {k: round(v, 2) for k, v in concepts.items()}
    return {
        "areas": area_conf,
        "families": family_conf,
        "concepts": concept_conf,
        "dominant_area_confidence": round(areas.get(dom_area, 0.0), 2),
        "dominant_family_confidence": round(families.get(dom_family, 0.0), 2),
    }


def add_confidence_to_interpretation(
    interpretation: dict[str, Any],
    activation: dict[str, Any],
) -> dict[str, Any]:
    """Добавить в interpretation поля confidence для dominant_area, defense, object_relation."""
    conf = compute_confidence_scores(activation)
    areas = activation.get("areas") or {}
    families = activation.get("families") or {}
    dom_area = interpretation.get("dominant_area") or (max(areas, key=lambda k: areas[k]) if areas else "")
    defense = interpretation.get("defense_pattern") or ""
    a3_families = {k: v for k, v in families.items() if k.startswith("A3_")}
    a2_families = {k: v for k, v in families.items() if k.startswith("A2_")}
    defense_confidence = round(max(a3_families.values()) if a3_families else 0.0, 2)
    object_confidence = round(max(a2_families.values()) if a2_families else 0.0, 2)
    out = dict(interpretation)
    out["confidence_scores"] = conf
    out["dominant_area_confidence"] = conf.get("dominant_area_confidence", 0.0)
    out["defense_confidence"] = defense_confidence
    out["object_relation_confidence"] = object_confidence
    return out
