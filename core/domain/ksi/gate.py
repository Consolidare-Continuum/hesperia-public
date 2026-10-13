# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from .expected_j import KsiThresholds

GateStatus = Literal["ACCEPT", "REJECT", "PAUSE"]


@dataclass(frozen=True, slots=True)
class GateVerdict:
    status: GateStatus
    reasons: tuple[str, ...] = ()


def _proposal_required_fields(proposal: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if "action" not in proposal:
        missing.append("action")
    if "confidence" not in proposal:
        missing.append("confidence")
    if "justification" not in proposal or not str(proposal.get("justification", "")).strip():
        missing.append("justification")
    action = proposal.get("action")
    if action == "add_edge":
        for key in ("source", "target", "type", "W_e_proposed"):
            if key not in proposal:
                missing.append(key)
    elif action == "update_edge_weight":
        for key in ("source", "target", "W_e_proposed"):
            if key not in proposal:
                missing.append(key)
    return missing


def _w_e_in_range(value: Any) -> bool:
    try:
        w = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= w <= 1.0


def _edge_polarity(relation_type: str) -> int:
    if relation_type in {"inhibits", "opposes"}:
        return -1
    return 1


def _creates_activation_inhibition_contradiction(
    proposal: Mapping[str, Any],
    existing_edges: Sequence[tuple[str, str, str]],
) -> bool:
    action = proposal.get("action")
    if action != "add_edge":
        return False
    src = str(proposal.get("source", ""))
    tgt = str(proposal.get("target", ""))
    new_type = str(proposal.get("type", "activates"))
    new_pol = _edge_polarity(new_type)
    for es, et, etype in existing_edges:
        if es == src and et == tgt:
            if _edge_polarity(etype) != new_pol:
                return True
    return False


def validate_proposal(
    proposal: Mapping[str, Any],
    *,
    legal_relation_types: set[str],
    existing_edges: Sequence[tuple[str, str, str]] | None = None,
    thresholds: KsiThresholds | None = None,
) -> GateVerdict:
    th = thresholds or KsiThresholds.from_config()
    reasons: list[str] = []

    missing = _proposal_required_fields(proposal)
    if missing:
        reasons.append(f"schema_missing:{','.join(missing)}")
        return GateVerdict(status="REJECT", reasons=tuple(reasons))

    action = str(proposal["action"])
    allowed_actions = {
        "add_edge",
        "remove_edge",
        "update_edge_weight",
        "add_concept",
        "update_cd_field",
    }
    if action not in allowed_actions:
        reasons.append("schema_invalid_action")
        return GateVerdict(status="REJECT", reasons=tuple(reasons))

    if action in {"add_edge", "update_edge_weight"}:
        w_key = "W_e_proposed"
        if not _w_e_in_range(proposal.get(w_key)):
            reasons.append("w_e_out_of_range")
            return GateVerdict(status="REJECT", reasons=tuple(reasons))

    if action == "add_edge":
        rel_type = str(proposal.get("type", ""))
        if rel_type not in legal_relation_types:
            reasons.append("type_not_legal")
            return GateVerdict(status="REJECT", reasons=tuple(reasons))
        edges = existing_edges or ()
        if _creates_activation_inhibition_contradiction(proposal, edges):
            reasons.append("activation_inhibition_contradiction")
            return GateVerdict(status="REJECT", reasons=tuple(reasons))

    try:
        confidence = float(proposal.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < th.tau_teacher:
        reasons.append("confidence_below_tau_teacher")
        return GateVerdict(status="REJECT", reasons=tuple(reasons))

    if action in {"add_concept", "remove_edge"}:
        reasons.append("human_in_loop_required")
        return GateVerdict(status="PAUSE", reasons=tuple(reasons))

    return GateVerdict(status="ACCEPT", reasons=tuple(reasons))


def validate_proposal_packet(
    packet: Mapping[str, Any],
    *,
    legal_relation_types: set[str],
    existing_edges: Sequence[tuple[str, str, str]] | None = None,
    thresholds: KsiThresholds | None = None,
) -> list[GateVerdict]:
    proposals = packet.get("proposals") or []
    verdicts: list[GateVerdict] = []
    for prop in proposals:
        if isinstance(prop, dict):
            verdicts.append(
                validate_proposal(
                    prop,
                    legal_relation_types=legal_relation_types,
                    existing_edges=existing_edges,
                    thresholds=thresholds,
                )
            )
    return verdicts
