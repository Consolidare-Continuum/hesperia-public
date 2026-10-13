# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""KSI-Inspector wire entry — sealed /analyze + hybrid_retriever (additive, flag-gated).

Does not alter sealed physics. When ``HESPERIA_KSI_ENABLED`` is unset/0, callers must
not attach a ``ksi`` block (see :func:`attach_ksi_to_engine_result`).
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .bridge import (
    BridgeSessionState,
    ConceptStructure,
    classify_missing_bridge,
    compute_bridge_need,
    missing_bridge_incident_payload,
)
from .bundle import KsiBundleBlock, KsiConceptMetrics, empty_ksi_block
from .expected_j import (
    IncomingEdge,
    KsiThresholds,
    classify_concept_incident,
    compute_expected_area,
    compute_expected_j,
    compute_residual,
    load_ksi_config,
)
from .flags import (
    ksi_config_path,
    ksi_enabled,
    phi_trace_enabled,
    tau_bridge_override,
    tau_override,
    tau_teacher_override,
    teacher_inspect_only,
    teacher_packet_enabled,
)
from .phi_e import PhiEParams, load_relation_type_coefficients, phi_e_trace, r_e_for_type, sat
from .teacher import serialize_teacher_packet


def _thresholds() -> KsiThresholds:
    cfg_path = ksi_config_path()
    config = load_ksi_config(cfg_path) if cfg_path is not None else load_ksi_config()
    th = KsiThresholds.from_config(config)
    tau = tau_override()
    tau_b = tau_bridge_override()
    tau_t = tau_teacher_override()
    if tau is None and tau_b is None and tau_t is None:
        return th
    return KsiThresholds(
        tau=float(tau) if tau is not None else th.tau,
        tau_active=th.tau_active,
        tau_dead=th.tau_dead,
        tau_expected=th.tau_expected,
        tau_explain=th.tau_explain,
        tau_mirror=th.tau_mirror,
        tau_bridge=float(tau_b) if tau_b is not None else th.tau_bridge,
        tau_teacher=float(tau_t) if tau_t is not None else th.tau_teacher,
        tau_sandbox_delta=th.tau_sandbox_delta,
    )


def activations_from_engine(engine_result: Mapping[str, Any] | None) -> dict[str, float]:
    """Observed_j map from sealed engine envelope (trace / invariant_activation)."""
    if not engine_result:
        return {}
    out: dict[str, float] = {}
    inv = engine_result.get("invariant_activation") or {}
    concepts = inv.get("concepts") if isinstance(inv, dict) else None
    if isinstance(concepts, dict):
        for cid, val in concepts.items():
            if isinstance(val, dict):
                obs = val.get("observed", val.get("activation", 0.0))
            else:
                obs = val
            try:
                out[str(cid)] = float(obs)
            except (TypeError, ValueError):
                continue
    for step in engine_result.get("trace") or []:
        if not isinstance(step, dict):
            continue
        cid = str(step.get("concept_id") or "").strip()
        if not cid:
            continue
        try:
            act = float(step.get("activation") or 0.0)
        except (TypeError, ValueError):
            continue
        # Prefer richer invariant_activation when present; else fill from trace.
        out.setdefault(cid, act)
    return out


def concept_structure_from_engine(
    engine_result: Mapping[str, Any] | None,
) -> dict[str, ConceptStructure]:
    if not engine_result:
        return {}
    structure: dict[str, ConceptStructure] = {}
    for step in engine_result.get("trace") or []:
        if not isinstance(step, dict):
            continue
        cid = str(step.get("concept_id") or "").strip()
        if not cid:
            continue
        structure[cid] = ConceptStructure(
            primary_area=str(step.get("area_id") or ""),
            family=str(step.get("family_id") or ""),
            family_bias=str(step.get("family_id") or ""),
        )
    return structure


def edges_from_engine(engine_result: Mapping[str, Any] | None) -> list[IncomingEdge]:
    """Incoming edges from temp overlay / explicit ksi_edges / propagation_trace stubs."""
    if not engine_result:
        return []
    edges: list[IncomingEdge] = []
    explicit = engine_result.get("ksi_edges") or []
    if isinstance(explicit, list):
        for row in explicit:
            if not isinstance(row, dict):
                continue
            src = str(row.get("source") or row.get("from") or "").strip()
            tgt = str(row.get("target") or row.get("to") or "").strip()
            if not src or not tgt:
                continue
            try:
                w_e = float(row.get("w_e", row.get("W_e", row.get("proposed_strength", 0.5))))
            except (TypeError, ValueError):
                w_e = 0.5
            edges.append(
                IncomingEdge(
                    source=src,
                    target=tgt,
                    relation_type=str(row.get("relation_type") or row.get("type") or "activates"),
                    w_e=max(0.0, min(1.0, w_e)),
                )
            )
    overlay = engine_result.get("temp_relation_overlay") or []
    if isinstance(overlay, list):
        for row in overlay:
            if not isinstance(row, dict):
                continue
            # Overlay is area/family oriented; map to concept ids when present.
            src = str(
                row.get("source_concept_id")
                or row.get("from_concept_id")
                or row.get("from_family_id")
                or ""
            ).strip()
            tgt = str(
                row.get("target_concept_id")
                or row.get("to_concept_id")
                or row.get("to_family_id")
                or ""
            ).strip()
            if not src or not tgt:
                continue
            try:
                w_e = float(row.get("proposed_strength") or row.get("w_e") or 0.5)
            except (TypeError, ValueError):
                w_e = 0.5
            edges.append(
                IncomingEdge(
                    source=src,
                    target=tgt,
                    relation_type=str(row.get("relation_type") or "BRIDGES").lower(),
                    w_e=max(0.0, min(1.0, w_e)),
                )
            )
    return edges


def run_ksi_inspect(
    *,
    activations: Mapping[str, float],
    incoming_edges: Sequence[IncomingEdge] | None = None,
    concept_structure: Mapping[str, ConceptStructure] | None = None,
    active_areas: frozenset[str] | None = None,
    session_id: str = "analyze",
    iteration_id: str = "0",
    include_phi_trace: bool | None = None,
    include_teacher_packet: bool | None = None,
) -> dict[str, Any]:
    """Φ_e → Expected_j → residual → incidents → optional phi_trace / teacher packet."""
    th = _thresholds()
    coeffs = load_relation_type_coefficients()
    edges = list(incoming_edges or [])
    structure = dict(concept_structure or {})
    areas_set = active_areas or frozenset(
        s.primary_area for s in structure.values() if s.primary_area
    )

    by_target: dict[str, list[IncomingEdge]] = {}
    for edge in edges:
        by_target.setdefault(edge.target, []).append(edge)

    concept_ids = set(activations.keys()) | set(by_target.keys())
    concepts_out: dict[str, KsiConceptMetrics] = {}
    incidents: list[dict[str, Any]] = []
    phi_trace: dict[str, Any] = {}
    want_phi = phi_trace_enabled() if include_phi_trace is None else bool(include_phi_trace)

    expected_by_concept: dict[str, float] = {}
    for cid in sorted(concept_ids):
        obs = float(activations.get(cid, 0.0))
        inc_edges = by_target.get(cid, [])
        expected = compute_expected_j(cid, inc_edges, activations, coefficients=coeffs)
        expected_by_concept[cid] = expected
        residual = compute_residual(expected, obs)
        incident = classify_concept_incident(
            expected_j=expected, observed_j=obs, residual_j=residual, thresholds=th
        )
        concepts_out[cid] = KsiConceptMetrics(
            expected=round(expected, 6),
            observed=round(obs, 6),
            residual=round(residual, 6),
            incident=incident,
        )
        if incident:
            edge_payload = [
                {
                    "source": e.source,
                    "relation_type": e.relation_type,
                    "w_e": e.w_e,
                    "type": e.relation_type,
                    "W_e": e.w_e,
                    "R_e": r_e_for_type(e.relation_type, coeffs),
                }
                for e in inc_edges
            ]
            struct = structure.get(cid)
            incidents.append(
                {
                    "incident_type": incident,
                    "concept_id": cid,
                    "expected": round(expected, 6),
                    "observed": round(obs, 6),
                    "residual": round(residual, 6),
                    "incoming_edges": edge_payload,
                    "context_area": struct.primary_area if struct else "",
                }
            )
        if want_phi and inc_edges:
            for e in inc_edges:
                a_i = float(activations.get(e.source, 0.0))
                r_e = r_e_for_type(e.relation_type, coeffs)
                params = PhiEParams(
                    a_i=a_i,
                    w_e=e.w_e,
                    r_e=r_e,
                    q_e=e.q_e,
                    s_e=e.s_e,
                    c_e=e.c_e,
                    p_e=e.p_e,
                    d_e=e.d_e,
                    k_e=e.k_e,
                )
                key = f"{e.source}→{e.target}"
                phi_trace[key] = phi_e_trace(params)

    primary_area = {cid: (structure[cid].primary_area if cid in structure else "") for cid in concept_ids}
    area_ids = sorted({a for a in primary_area.values() if a})
    areas_out: dict[str, KsiConceptMetrics] = {}
    for area_id in area_ids:
        exp_a = compute_expected_area(area_id, primary_area, expected_by_concept)
        obs_a = sum(
            float(activations.get(cid, 0.0))
            for cid, a in primary_area.items()
            if a == area_id
        )
        # Soft sat for area observed roll-up (mirror Expected area sat).
        obs_a_sat = sat(obs_a)
        res_a = compute_residual(exp_a, obs_a_sat)
        areas_out[area_id] = KsiConceptMetrics(
            expected=round(exp_a, 6),
            observed=round(obs_a_sat, 6),
            residual=round(res_a, 6),
            incident=None,
        )

    edge_strength: dict[tuple[str, str], float] = {
        (e.source, e.target): float(e.w_e) for e in edges
    }
    session = BridgeSessionState(
        activations=dict(activations),
        concept_structure=structure,
        active_areas=areas_set,
        edge_strength=edge_strength,
    )
    missing_bridges: list[dict[str, Any]] = []
    active_ids = [cid for cid, a in activations.items() if float(a) >= th.tau_active]
    for i, src in enumerate(active_ids):
        for tgt in active_ids[i + 1 :]:
            if (src, tgt) in edge_strength or (tgt, src) in edge_strength:
                continue
            residual_j = float(concepts_out.get(tgt).residual if tgt in concepts_out else 0.0)
            need = compute_bridge_need(src, tgt, session, residual_j=residual_j, thresholds=th)
            if classify_missing_bridge(src, tgt, need, thresholds=th):
                missing_bridges.append(missing_bridge_incident_payload(src, tgt, need, session))

    block = KsiBundleBlock(
        version="0.1",
        concepts=concepts_out,
        areas=areas_out,
        incidents=incidents,
        missing_bridges=missing_bridges,
        phi_trace=phi_trace if want_phi else None,
    )
    payload = block.model_dump()
    want_teacher = teacher_packet_enabled() if include_teacher_packet is None else bool(include_teacher_packet)
    if want_teacher:
        packet = serialize_teacher_packet(
            session_id=session_id,
            iteration_id=iteration_id,
            incidents=incidents,
            missing_bridges=missing_bridges,
            active_concepts_in_session=sorted(activations.keys()),
            topology={"areas": area_ids},
        )
        # Hard gate: no apply before 0.7.0 — inspect-only on this wire path.
        packet["mode"] = "inspect_only"
        packet["inspect_only_flag"] = bool(teacher_inspect_only())
        packet["apply_allowed"] = False
        packet["apply_gate"] = "blocked_until_0.7.0"
        payload["teacher_packet"] = packet
    return payload


def run_ksi_inspect_from_engine(
    engine_result: Mapping[str, Any] | None,
    *,
    session_id: str = "analyze",
    iteration_id: str = "0",
) -> dict[str, Any]:
    """Wire entry: build KSI block from a sealed engine /analyze envelope."""
    if not engine_result:
        return empty_ksi_block().model_dump()
    activations = activations_from_engine(engine_result)
    if not activations:
        return empty_ksi_block().model_dump()
    return run_ksi_inspect(
        activations=activations,
        incoming_edges=edges_from_engine(engine_result),
        concept_structure=concept_structure_from_engine(engine_result),
        session_id=session_id,
        iteration_id=iteration_id,
    )


def attach_ksi_to_engine_result(
    engine_result: dict[str, Any],
    *,
    session_id: str = "analyze",
    iteration_id: str = "0",
) -> dict[str, Any]:
    """Attach ``ksi`` when enabled. No-op (identity) when flag unset/0."""
    if not ksi_enabled():
        return engine_result
    if not isinstance(engine_result, dict):
        return engine_result
    if engine_result.get("ksi"):
        return engine_result
    out = dict(engine_result)
    out["ksi"] = run_ksi_inspect_from_engine(
        engine_result, session_id=session_id, iteration_id=iteration_id
    )
    return out


def build_ksi_analyze_block(
    engine_result: Mapping[str, Any] | None,
    *,
    session_id: str = "analyze",
    iteration_id: str = "0",
) -> dict[str, Any]:
    """Alias — build inspect block from engine/analyze carrier."""
    return run_ksi_inspect_from_engine(
        engine_result, session_id=session_id, iteration_id=iteration_id
    )


def attach_ksi_to_extended(
    extended_out: dict[str, Any],
    *,
    summary: Mapping[str, Any] | None = None,
    session_id: str = "analyze",
    iteration_id: str = "0",
) -> dict[str, Any]:
    """Attach ``ksi`` onto analyze ``extended_out`` when enabled (legacy/runtime.pipeline path)."""
    if not ksi_enabled():
        return extended_out
    carrier: dict[str, Any] = {
        "summary": dict(summary or {}),
        "trace": extended_out.get("ksi_trace") or extended_out.get("trace") or [],
        "invariant_activation": extended_out.get("invariant_activation") or {},
        "ksi_edges": extended_out.get("ksi_edges") or [],
        "temp_relation_overlay": extended_out.get("temp_relation_overlay") or [],
    }
    wrapped = attach_ksi_to_engine_result(
        carrier, session_id=session_id, iteration_id=iteration_id
    )
    out = dict(extended_out)
    if isinstance(wrapped, dict) and wrapped.get("ksi") is not None:
        out["ksi"] = wrapped["ksi"]
    return out
