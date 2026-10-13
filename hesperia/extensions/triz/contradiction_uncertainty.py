# HESPERIA — Lexical/concept uncertainty package for contradiction coupling (v0.5.8 task5).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import math
from typing import Any

from core.math.basic_stats import clamp01 as _clamp01
from core.math.entropy_metrics import compute_normalized_entropy_from_weights as _entropy_normalized

_EPS = 1e-15
UNCERTAINTY_VERSION = "uncertainty_task6"


def build_uncertainty_package(
    lexical_output: dict[str, Any] | None,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Canonical uncertainty bundle from DLCR output (lexical summaries) + optional activation concepts.

    When ``lexical_output`` is empty, falls back to activation-only heuristics (still deterministic).
    """
    lex = lexical_output or {}
    act = activation or {}
    luc = lex.get("lexical_uncertainty_summary") or {}
    cuc = lex.get("concept_uncertainty_summary") or {}
    csup = lex.get("concept_support_summary") or {}

    unmapped = float(luc.get("unmapped_lexical_ratio") or 0.0)
    low_pri = float(luc.get("low_priority_link_ratio") or 0.0)
    fuzzy = float(luc.get("fuzzy_link_ratio") or 0.0)
    alias = float(luc.get("alias_link_ratio") or 0.0)

    weak = float(cuc.get("weak_concept_share") or 0.0)
    amb = float(cuc.get("ambiguous_concept_share") or 0.0)
    ent = float(cuc.get("concept_entropy") or 0.0)
    mss = float(cuc.get("mean_concept_support_strength") or csup.get("mean") or 0.0)

    concepts = act.get("concepts") or act.get("concept_weights_post_hex") or {}
    if isinstance(concepts, dict) and concepts and not cuc:
        ent = _entropy_normalized({str(k): float(v) for k, v in concepts.items()})
        mx = max(float(v) for v in concepts.values()) if concepts else 0.0
        if mx > _EPS:
            weak = sum(1 for v in concepts.values() if float(v) < 0.15 * mx) / float(len(concepts))

    lexical_uncertainty = _clamp01(0.5 * unmapped + 0.28 * low_pri + 0.12 * fuzzy + 0.1 * alias)
    concept_uncertainty = _clamp01(0.42 * ent + 0.35 * weak + 0.23 * amb)
    if not luc and not cuc and concepts:
        concept_uncertainty = max(concept_uncertainty, _clamp01(0.55 * ent + 0.45 * weak))

    support = float(mss) if mss > _EPS else max(0.0, min(1.0, 1.0 - 0.55 * weak - 0.35 * amb))

    active = bool(lex) or bool(concepts)
    lex_neg = lex.get("negation_summary") if isinstance(lex.get("negation_summary"), dict) else {}

    out: dict[str, Any] = {
        "uncertainty_version": UNCERTAINTY_VERSION,
        "lexical_uncertainty": round(lexical_uncertainty, 6),
        "concept_uncertainty": round(concept_uncertainty, 6),
        "fuzzy_link_ratio": round(fuzzy, 6),
        "weak_concept_share": round(weak, 6),
        "ambiguous_concept_share": round(amb, 6),
        "concept_support_strength": round(support, 6),
        "uncertainty_coupling_active": active,
    }
    if lex_neg:
        out["lexical_negation_summary"] = dict(lex_neg)
    out["calibration_pathology_prior"] = round(
        _clamp01(0.5 * lexical_uncertainty + 0.5 * concept_uncertainty),
        6,
    )
    out["runtime_conflict_prior"] = round(_clamp01(1.0 - float(out["calibration_pathology_prior"])), 6)
    return out
