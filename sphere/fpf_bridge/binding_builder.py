# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Builds fpf RuntimeBinding from sphere pipeline result."""

from __future__ import annotations

import os
from typing import Any

from fpf_thinking_map.state import RuntimeBinding

from sphere.fpf_bridge.constants import CONTEXT_ID, STATE_RISK_MAP
from sphere.fpf_bridge.evidence_mapper import collect_all_evidence


def _evidence_expansion_enabled() -> bool:
    """fpf_bridge v7.2 — HESPERIA_FPF_EVIDENCE_EXPANSION, default off (spec §6).

    Duplicated from bridge.py rather than imported, to avoid a circular import
    (bridge.py imports build_runtime_binding from this module).
    """
    return os.environ.get("HESPERIA_FPF_EVIDENCE_EXPANSION", "0").strip() == "1"


def _kme_evidence_enabled() -> bool:
    """fpf_bridge v7.2 Phase 3 — HESPERIA_FPF_KME_EVIDENCE, default off (spec §6)."""
    return os.environ.get("HESPERIA_FPF_KME_EVIDENCE", "0").strip() == "1"


def build_runtime_binding(
    result: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> RuntimeBinding:
    """Build fpf RuntimeBinding from pipeline result dict."""
    interpretation = result.get("interpretation_metrics") or {}
    pipeline_meta = result.get("pipeline_metadata") or {}
    logic_metrics = result.get("logic_metrics") or {}
    shadow_metrics = result.get("shadow_metrics") or {}
    dynamism_metrics = _extract_dynamism(result)
    document_id = str(result.get("document_id", "unknown"))

    structural_state = str(interpretation.get("structural_state", "distributed_balanced"))
    risk_level = STATE_RISK_MAP.get(structural_state, "normal")

    expansion_on = _evidence_expansion_enabled()
    kme_on = _kme_evidence_enabled()
    l5_metrics = (result.get("layer_5") or result.get("l5_metrics") or {}) if expansion_on else None
    l7_metrics = (result.get("layer_7") or result.get("l7_metrics") or {}) if expansion_on else None
    l4_metrics = (result.get("layer_4") or result.get("l4_metrics") or {}) if expansion_on else None
    kme_dict = result.get("kme") or {}
    kme_primitives = kme_dict.get("primitive_map") if kme_on else None
    kme_derived = kme_dict.get("derived_map") if kme_on else None
    triz_signals = kme_dict.get("triz_signals") or {}
    triz_contradictions = (triz_signals.get("contradictions") or None) if expansion_on else None
    evidence = collect_all_evidence(
        logic_metrics, shadow_metrics, dynamism_metrics, context_id,
        l5_metrics=l5_metrics, l7_metrics=l7_metrics, l4_metrics=l4_metrics,
        kme_primitives=kme_primitives, kme_derived=kme_derived,
        triz_contradictions=triz_contradictions,
    )
    evidence_ids = [e.evidence_id for e in evidence]

    constraints = [str(f) for f in (interpretation.get("interpretation_flags") or []) if f]

    return RuntimeBinding(
        task=f"structural_analysis:{document_id}",
        goal="interpret_structural_state",
        actor="hesperia_engine",
        actor_role_ids=["structural_analyst"],
        audience="clinical_interpreter",
        available_tools=["traverse", "collect_evidence", "escalate"],
        current_evidence=evidence_ids,
        risk_level=risk_level,
        active_context_id=context_id,
        constraints=constraints,
        candidate_actions=[
            "interpret_dominant_area",
            "assess_tension",
            "review_propagation",
            "compare_with_previous",
            "escalate_review",
            "collect_evidence",
        ],
        environment={
            "pipeline_version": str(pipeline_meta.get("pipeline_version", "")),
            "document_id": document_id,
            "deterministic": True,
            "structural_state": structural_state,
        },
    )


def _extract_dynamism(result: dict[str, Any]) -> dict[str, Any]:
    """Extract dynamism metrics from pipeline result (may be nested in usf or top-level)."""
    if "dynamism_metrics" in result:
        return dict(result["dynamism_metrics"])
    usf = result.get("usf") or {}
    if "dynamism" in usf:
        return dict(usf["dynamism"])
    return {"stability_index": 0.5}
