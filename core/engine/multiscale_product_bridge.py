# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Canonical structural analysis: sealed multiscale stack → internal dict for ``project_to_public``.

Maps engine output (hex-layer-backed) into layer-shaped buckets + ``usf``/``diagnostics`` so shipping,
dossiers, and E2E checks keep stable key presence without exposing forbidden public schema terms
(e.g. renaming ``hex_activation_map`` → ``microcell_activation_map``).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from core.engine.hex_matrix_builders import HEXES_PER_FAMILY_CANON
from core.engine.sealed_multiscale_stack import NUM_FAMILIES, run_sealed_multiscale_stack
from core.projection.area_math_grain import area_math_classifier_meta, project_macro_for_grain
from hesperia.system.version import calibration_profile_bundle_id


def _l1_synthetic_matched_from_family_activation(
    family_activation: list[float],
    total_tokens: int,
    *,
    default_altitude: float = 1.0,
) -> list[tuple[int, float]]:
    """
    Deterministic token→family allocation from sealed ``family_activation_vector`` (largest remainder).

    Used when lexicon marker path attributes zero tokens but sealed hex/family mass is nonzero
    (e.g. uniform concept prior + preserved microphysics mass).
    """
    if total_tokens <= 0:
        return []
    fv = [max(0.0, float(x)) for x in family_activation]
    s = sum(fv)
    if s <= 0.0:
        return []
    probs = [x / s for x in fv]
    quotas = [total_tokens * p for p in probs]
    floors = [int(math.floor(q)) for q in quotas]
    rem = total_tokens - sum(floors)
    order = sorted(range(len(probs)), key=lambda i: quotas[i] - floors[i], reverse=True)
    counts = list(floors)
    for j in range(rem):
        counts[order[j % len(order)]] += 1
    matched: list[tuple[int, float]] = []
    for fi, c in enumerate(counts):
        for _ in range(c):
            matched.append((fi, default_altitude))
    return matched


def _brand_word_trust_from_hspr(hspr: float, decision_code: int) -> str:
    if decision_code != 0:
        return "BLOCKED"
    u = hspr * 1000.0
    if u >= 850:
        return "TRUSTED"
    if u >= 650:
        return "USABLE"
    if u >= 450:
        return "TENTATIVE"
    return "FRAGILE"


def _compute_domain_metrics_dict(
    text: str,
    assets: Path,
    *,
    document_id: str,
    domain_constants_path: str | Path | None,
) -> dict[str, Any]:
    from core.attribution.structural import attribute, load_dict_a, load_dict_b, normalize, tokenize
    from core.domain.bridge import pipeline_matched_to_hits_relations, synthetic_domain_graph_for_topology
    from core.domain.loader import load_frozen_constants
    from core.domain.models import DomainConstants
    from core.domain.pipeline import metric_report_to_dict, run_document
    from core.layers import load_defaults

    defaults = load_defaults()
    f = int(defaults.get("F", 288))
    dict_a = load_dict_a(assets_root=assets) or {}
    dict_b = load_dict_b()
    tokens = tokenize(normalize(text))
    matched, _ = attribute(tokens, dict_a, dict_b)
    if domain_constants_path and Path(domain_constants_path).exists():
        constants = load_frozen_constants(domain_constants_path)
    else:
        constants = DomainConstants(
            domain_node_count=max(1, f),
            domain_degree_p95=1.0,
            domain_distance_p95=1.0,
        )
    domain_graph = synthetic_domain_graph_for_topology(num_families=f)
    hits, relations = pipeline_matched_to_hits_relations(matched, num_families=f)
    report = run_document(domain_graph, constants, document_id, hits, relations, domain_release="")
    return metric_report_to_dict(report)


def build_structural_internal_from_multiscale(
    text: str,
    assets: Path,
    *,
    policy_mode: str | None = None,
    enable_domain_metrics: bool = False,
    domain_constants_path: str | Path | None = None,
    use_triz_contradiction: bool = False,
    document_id: str = "analysis_service",
) -> dict[str, Any]:
    """
    Run ``run_sealed_multiscale_stack`` and assemble internal payload for projection.

    Raises RuntimeError if hex-layer activation is missing or malformed (no silent degradation).
    """
    from core.lexical.analysis_input import prepare_structural_analysis_text

    text, text_prep_meta = prepare_structural_analysis_text(text, policy_mode=policy_mode)

    sealed = run_sealed_multiscale_stack(
        text,
        assets,
        use_triz_contradiction=use_triz_contradiction,
    )
    ham = sealed.get("hex_activation_map")
    if not isinstance(ham, dict):
        raise RuntimeError("canonical pipeline failed: missing microcell activation map (hex layer)")
    shp = ham.get("shape")
    if (
        not isinstance(shp, list)
        or len(shp) != 2
        or int(shp[0]) != NUM_FAMILIES
        or int(shp[1]) != HEXES_PER_FAMILY_CANON
    ):
        raise RuntimeError("canonical pipeline failed: hex activation shape invariant violated")

    from core.layers import compute_L1, load_defaults
    from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

    defaults = load_defaults()
    act = markers_to_concept_activation(text, assets)
    tokens = act["tokens"]
    matched = act["concept_matches"]
    semantic_ev = act.get("semantic_evidence")
    f_sz = int(defaults.get("F", 288))
    a_sz = int(defaults.get("A", 12))
    eps = float(defaults.get("eps", 1e-9))
    L1_core = compute_L1(len(tokens), matched, F=f_sz, A=a_sz, eps=eps)
    l1_fallback_kind: str | None = None
    if int(L1_core.get("ATTRIBUTED_TOKENS") or 0) == 0:
        fav = sealed.get("family_activation_vector") or []
        synth = _l1_synthetic_matched_from_family_activation(fav, len(tokens))
        if synth:
            L1_core = compute_L1(len(tokens), synth, F=f_sz, A=a_sz, eps=eps)
            l1_fallback_kind = "sealed_family_activation_to_L1"
    L1_out = {**L1_core, "CANONICAL_PIPELINE": "sealed_multiscale_v1"}
    if l1_fallback_kind:
        L1_out["CALIBRATION_FALLBACK_USED"] = l1_fallback_kind

    area = [float(x) for x in (sealed.get("area_activation_vector") or [])]
    macro, dom, grain_used = project_macro_for_grain(area)
    grain_meta = area_math_classifier_meta(grain=grain_used)
    hspr = float(sealed.get("hspr_index") or 0.0)
    decision_code = 0
    # Align with legacy L7 vocabulary (HIGH / MED / LOW).
    if hspr >= 0.7:
        trust_tag, trust_tier = "HIGH", 3
    elif hspr >= 0.4:
        trust_tag, trust_tier = "MED", 2
    else:
        trust_tag, trust_tier = "LOW", 1

    microcell_activation = {
        "shape": ham.get("shape"),
        "sample_ring_slice": ham.get("sample_ring_slice"),
        "total_mass": ham.get("total_mass"),
    }

    raw: dict[str, Any] = {
        "run": "structural_analysis",
        "text_preview": text[:80],
        "execution_flow": sealed.get("execution_flow", "sealed_multiscale_v1"),
        "pipeline_version": sealed.get("execution_flow", "sealed_multiscale_v1"),
        "L1": L1_out,
        "L2": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L3": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L4": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L5": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L6": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L7": {
            "OUTPUT_TRUST_TAG": trust_tag,
            "TRUST_TIER": trust_tier,
            "DECISION_STATUS_CODE": decision_code,
            "SYSTEM_CONFIDENCE_SCORE": round(hspr, 8),
        },
        "L8": {"CANONICAL_PIPELINE": "sealed_multiscale_v1"},
        "L9": {
            "BRAND_WORD_TRUST": _brand_word_trust_from_hspr(hspr, decision_code),
            "CANONICAL_PIPELINE": "sealed_multiscale_v1",
        },
        "usf": {
            "raw_metrics": {
                "macro_domain_vector": macro,
                "dominant_macro_domain": dom,
                "area_math_grain": grain_used,
                "area_math_classifier": grain_meta,
            },
        },
        "multiscale_signals": {
            "microcell_activation_map": microcell_activation,
            "family_activation_vector": sealed.get("family_activation_vector"),
            "area_activation_vector": sealed.get("area_activation_vector"),
            "hotspot_map": sealed.get("hotspot_map") or {},
            "contradiction_pressure": sealed.get("contradiction_pressure"),
            "propagation_strength": sealed.get("propagation_strength"),
            "narrative_density": sealed.get("narrative_density"),
            "innovation_index": sealed.get("innovation_index"),
            "hspr_index": sealed.get("hspr_index"),
            "hspr_components": sealed.get("hspr_components"),
            "product_signals": sealed.get("product_signals") or {},
        },
        "diagnostics": {
            "canonical_pipeline": "sealed_multiscale_v1",
            "calibration_status": {
                "marker_concept_mass": (sealed.get("concept_layer") or {}).get("marker_concept_mass"),
                "uniform_concept_prior_fallback_used": (sealed.get("concept_layer") or {}).get(
                    "uniform_concept_prior_fallback_used"
                ),
                "hex_upstream_fallback_used": (sealed.get("concept_layer") or {}).get(
                    "hex_upstream_fallback_used"
                ),
                "l1_calibration_fallback": l1_fallback_kind,
                "true_absence_of_marker_signal": (
                    (sealed.get("concept_layer") or {}).get("marker_concept_mass", 1.0) or 0.0
                )
                <= 0.0,
            },
            "text_preprocess": text_prep_meta,
            "semantic_path_guards": {
                "concept_evidence_required_default": True,
                "semantic_evidence": semantic_ev,
                "note": "Set HESPERIA_CONCEPT_EVIDENCE_GUARD=observe|strict for PO-11/PO-12 (strict excludes Dict-A direct family hits from L1 matches).",
            },
            "concept_registry_version": (sealed.get("concept_layer") or {}).get("registry_version"),
            "n_concept": (sealed.get("concept_layer") or {}).get("n_concept"),
            "interpretability_trace": (sealed.get("concept_layer") or {}).get("interpretability_trace"),
            "hex_topology_manifest_version": "v1",
            "calibration_profile_bundle": calibration_profile_bundle_id(),
            "matrix_bundle_version": sealed.get("matrix_bundle_version"),
            "pch_bundle_version": sealed.get("pch_bundle_version"),
            "hex_energy_trace": sealed.get("hex_energy_trace"),
            "hex_energy_mode": sealed.get("hex_energy_mode"),
            "interpretation_policy_mode": policy_mode or defaults.get("interpretation_policy_mode") or "STRUCTURE_PLUS_CONTEXT",
            # Δ-stability-shaped envelope for reading-scale aggregation (mean anomaly → document_anomaly).
            "stability": {
                "anomaly_score": 0.0,
                "regime": "canonical_multiscale",
            },
        },
    }

    if enable_domain_metrics:
        try:
            raw["domain_metrics"] = _compute_domain_metrics_dict(
                text,
                assets,
                document_id=document_id,
                domain_constants_path=domain_constants_path,
            )
        except Exception as e:
            raw["domain_metrics"] = {
                "_error": str(e),
                "sourceId": document_id,
                "primitives": {},
                "derived": {},
                "fingerprint": {"fingerprintVersion": "", "vectorHash": "", "vectorSize": 41},
            }

    return raw
