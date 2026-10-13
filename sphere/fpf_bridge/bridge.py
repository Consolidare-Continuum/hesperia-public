# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Main bridge — maps sphere pipeline result to fpf ActiveState for LLM traversal."""

from __future__ import annotations

import os
from typing import Any

from fpf_thinking_map.primitives import (
    AgencyLevel,
    CommitmentPrimitive,
    ContextPrimitive,
    DeonticModality,
    RolePrimitive,
)
from fpf_thinking_map.guards import GuardEngine
from fpf_thinking_map.state import ActiveState, SemanticMap
from fpf_thinking_map.traversal import ThinkingMapTraversal

from sphere.fpf_bridge.constants import CONTEXT_ID, CONTEXT_LABEL, STATE_DISTRIBUTED_BALANCED
from sphere.fpf_bridge.state_graph import build_structural_gates, build_structural_state_graph
from sphere.fpf_bridge.evidence_mapper import collect_all_evidence
from sphere.fpf_bridge.guard_bridge import build_hesperia_guards
from sphere.fpf_bridge.logic_bridge import build_hesperia_logic_layer
from sphere.fpf_bridge.binding_builder import build_runtime_binding


def _evidence_expansion_enabled() -> bool:
    """fpf_bridge v7.2 — HESPERIA_FPF_EVIDENCE_EXPANSION, default off (spec §6)."""
    return os.environ.get("HESPERIA_FPF_EVIDENCE_EXPANSION", "0").strip() == "1"


def _contradiction_gate_enabled() -> bool:
    """fpf_bridge v7.2 — HESPERIA_FPF_CONTRADICTION_GATE, default off (spec §6)."""
    return os.environ.get("HESPERIA_FPF_CONTRADICTION_GATE", "0").strip() == "1"


def _extract_l5_metrics(result: dict[str, Any]) -> dict[str, Any]:
    """L5 output key varies by pipeline path (legacy dev pipeline vs sealed stack) — try both
    known shapes rather than assuming one. Empty dict (not an error) if neither is present."""
    return result.get("layer_5") or result.get("l5_metrics") or {}


def _extract_l7_metrics(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("layer_7") or result.get("l7_metrics") or {}


def _extract_l4_metrics(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("layer_4") or result.get("l4_metrics") or {}


def _kme_evidence_enabled() -> bool:
    """fpf_bridge v7.2 Phase 3 — HESPERIA_FPF_KME_EVIDENCE, default off (spec §6). Separate from
    the general expansion flag because it's a new data source (clinical_bridge.py), not just a
    new field on data the bridge already reads."""
    return os.environ.get("HESPERIA_FPF_KME_EVIDENCE", "0").strip() == "1"


def _extract_kme(result: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """KME output lives under result['kme'] as a MetricReport-shaped dict, when a caller ran
    run_kme_from_activation and attached it — absent by default, no error if missing."""
    kme = result.get("kme") or {}
    return kme.get("primitive_map"), kme.get("derived_map")


def _extract_triz_contradictions(result: dict[str, Any]) -> list[dict[str, Any]] | None:
    """TRIZ contradictions, when a caller attached result['kme']['triz_signals']['contradictions']
    (already the shape hesperia.extensions.triz.kme_bridge.run_triz_for_kme produces via
    MetricReport.triz_signals). Not imported directly — evidence_mapper.py stays decoupled from
    TRIZ/KME internals, same as it already is from core.layers.*."""
    kme = result.get("kme") or {}
    triz = kme.get("triz_signals") or {}
    contradictions = triz.get("contradictions")
    return contradictions if contradictions else None


def _build_semantic_map(
    result: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> SemanticMap:
    """Build the static semantic map from sphere outputs."""
    logic_metrics = result.get("logic_metrics") or {}
    shadow_metrics = result.get("shadow_metrics") or {}
    dynamism_metrics = _extract_dynamism(result)
    expansion_on = _evidence_expansion_enabled()
    l5_metrics = _extract_l5_metrics(result) if expansion_on else None
    l7_metrics = _extract_l7_metrics(result) if expansion_on else None
    l4_metrics = _extract_l4_metrics(result) if expansion_on else None
    kme_on = _kme_evidence_enabled()
    kme_primitives, kme_derived = _extract_kme(result) if kme_on else (None, None)
    triz_contradictions = _extract_triz_contradictions(result) if expansion_on else None

    sm = SemanticMap()

    # NOTE: KME evidence is core Hesperia semantics (corners/kme.md — domain-agnostic bounded
    # primitives over any activated concept graph), not clinical/TFP-exclusive, so its glossary
    # terms register into the core context below, not a separate TFP-only one. TFP_CONTEXT_ID
    # stays available for a caller who explicitly knows a given run's input was a TFP session
    # (get_hesperia_bridge_state's `branch` argument, once threaded through — not yet wired here).
    core_glossary = {
        "area": "one of 12 icosahedral zones in the structural topology",
        "family": "one of 24 concept families per area (288 total)",
        "tension": "structural tension between competing area activations",
        "dominance": "disproportionate activation concentration in one area",
        "propagation": "activation spreading across area boundaries",
        "stability": "consistency of structural pattern over the analysis window",
    }
    if kme_on:
        core_glossary["kme_primitive"] = (
            "one of 6 bounded [0,1] measures (LD/COH/NC/PR/PV/CI) of the activated concept "
            "graph's density, coherence, coverage, and spread — domain-agnostic, not TFP-specific"
        )
        core_glossary["kme_ksi"] = (
            "structural efficiency: coherent density achieved per unit of propagation radius "
            "spent reaching it"
        )
    if expansion_on:
        # TRIZ is also core, general-purpose Hesperia machinery (Altshuller's problem/
        # contradiction/solution-path advisor, corners/triz_extension.md) — not COBALT-exclusive,
        # same correction as KME above. Glossary term lives in core_glossary, not a COBALT-only
        # context. COBALT_CONTEXT_ID stays available for a caller scoping a specific run to
        # COBALT-retrieved library content explicitly.
        core_glossary["triz_contradiction"] = (
            "a TRIZ-classified tension between two active concepts, one of 4 inventive "
            "principles — a distinct mechanism from L5's contradiction_pressure, never averaged "
            "with it, and not COBALT-exclusive"
        )

    sm.register_context(ContextPrimitive(
        context_id=context_id,
        label=CONTEXT_LABEL,
        glossary=core_glossary,
        invariants=[
            "deterministic_pipeline",
            "no_upstream_mutation",
            "all_scores_normalized",
        ],
    ))

    sm.register_role(RolePrimitive(
        role_id="structural_analyst",
        label="Structural Analyst",
        context_id=context_id,
        agency_level=AgencyLevel.DELIBERATIVE,
        responsibilities=[
            "interpret_structural_state",
            "identify_anomalies",
            "assess_clinical_significance",
            "recommend_further_analysis",
        ],
    ))

    all_evidence = collect_all_evidence(
        logic_metrics, shadow_metrics, dynamism_metrics, context_id,
        l5_metrics=l5_metrics, l7_metrics=l7_metrics, l4_metrics=l4_metrics,
        kme_primitives=kme_primitives, kme_derived=kme_derived,
        triz_contradictions=triz_contradictions,
    )
    for ev in all_evidence:
        sm.register_evidence(ev)

    for gate in build_structural_gates(context_id):
        sm.register_gate(gate)

    for transition in build_structural_state_graph(context_id):
        sm.register_transition(transition)

    area_evidence_ids = [
        ev_id for ev_id in [e.evidence_id for e in all_evidence]
        if ev_id.startswith("area_")
    ]
    if area_evidence_ids:
        sm.register_commitment(CommitmentPrimitive(
            commitment_id="evidence_coverage",
            label="Area evidence should be considered",
            modality=DeonticModality.SHOULD,
            context_id=context_id,
            subject="structural_analyst",
            scope="structural_interpretation",
            evidence_refs=area_evidence_ids,
        ))

    return sm


def bridge_pipeline_result(
    result: dict[str, Any],
    *,
    context_id: str = CONTEXT_ID,
    include_prolog: bool = True,
) -> tuple[ThinkingMapTraversal, ActiveState]:
    """Bridge sphere pipeline result to fpf ActiveState ready for LLM traversal.

    Returns (traversal_engine, active_state) so the caller can call:
        outcome = traversal.step(state)
        outcome = traversal.attempt_transition(state, transition_id)
    """
    interpretation = result.get("interpretation_metrics") or {}
    logic_metrics = result.get("logic_metrics") or {}
    prolog_logic = result.get("prolog_logic") or {} if include_prolog else {}
    guards_result = result.get("guards") or {}

    structural_state = str(interpretation.get("structural_state", STATE_DISTRIBUTED_BALANCED))

    sm = _build_semantic_map(result, context_id)
    binding = build_runtime_binding(result, context_id)

    guard_engine = GuardEngine()
    for g in build_hesperia_guards(guards_result):
        guard_engine.add_guard(g)

    l5_metrics = _extract_l5_metrics(result) if _contradiction_gate_enabled() else None
    logic_layer = build_hesperia_logic_layer(logic_metrics, interpretation, prolog_logic, l5_metrics=l5_metrics)

    traversal = ThinkingMapTraversal(sm, guard_engine, logic_layer)
    state = traversal.build_active_state(binding, current_state=structural_state)

    return traversal, state


def bridge_to_llm_prompt(
    result: dict[str, Any],
    *,
    context_id: str = CONTEXT_ID,
    include_prolog: bool = True,
    logic_tags: set[str] | None = None,
) -> dict[str, Any]:
    """Shortcut: pipeline result -> complete JSON dict for LLM prompt.

    Returns the semantic state the LLM reasons over, including logic evaluation.
    """
    traversal, state = bridge_pipeline_result(
        result, context_id=context_id, include_prolog=include_prolog,
    )

    prompt_state = state.to_llm_prompt_state()

    if traversal.logic_layer:
        prompt_state["logic"] = traversal.logic_layer.to_llm_context(
            state, tags=logic_tags,
        )

    outcome = traversal.step(state, logic_tags=logic_tags)
    prompt_state["initial_outcome"] = outcome.to_dict()

    return prompt_state


def _extract_dynamism(result: dict[str, Any]) -> dict[str, Any]:
    """Extract dynamism metrics from pipeline result."""
    if "dynamism_metrics" in result:
        return dict(result["dynamism_metrics"])
    usf = result.get("usf") or {}
    if "dynamism" in usf:
        return dict(usf["dynamism"])
    return {"stability_index": 0.5}
