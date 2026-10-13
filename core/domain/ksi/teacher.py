# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

TEACHER_STRUCTURE_TEMPLATE = """# KSI Teacher - structure teaching (H62-032)
Session: {session_id} | iteration: {iteration_id}
Active areas: {active_areas}
Concept topology (areas / families):
{topology_lines}
Active concepts in session: {active_concepts}
"""

TEACHER_RELATIONS_TEMPLATE = """# KSI Teacher - relation teaching (H62-033)
Incidents ({incident_count}):
{incident_lines}
Ranked missing bridges:
{bridge_lines}
Allowed proposal actions: add_edge, remove_edge, update_edge_weight, add_concept, update_cd_field.
Edge semantics: W_e in [0,1], R_e from relation_type_coefficients, types must be legal.
"""


def _incoming_edges_for_incident(incident: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = incident.get("incoming_edges") or []
    detail: list[dict[str, Any]] = []
    for edge in raw:
        if not isinstance(edge, dict):
            continue
        detail.append(
            {
                "source": edge.get("source"),
                "type": edge.get("type") or edge.get("relation_type"),
                "W_e": edge.get("W_e", edge.get("w_e")),
                "R_e": edge.get("R_e", edge.get("r_e")),
            }
        )
    return detail


def rank_missing_bridges(missing_bridges: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked = [dict(row) for row in missing_bridges]
    ranked.sort(key=lambda row: float(row.get("bridge_need_score", 0.0)), reverse=True)
    return ranked


def serialize_teacher_packet(
    *,
    session_id: str,
    iteration_id: str,
    incidents: Sequence[Mapping[str, Any]],
    missing_bridges: Sequence[Mapping[str, Any]],
    active_concepts_in_session: Sequence[str] | None = None,
    topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    enriched_incidents: list[dict[str, Any]] = []
    for inc in incidents:
        row = dict(inc)
        row["incoming_edges"] = _incoming_edges_for_incident(inc)
        if active_concepts_in_session is not None and "active_concepts_in_session" not in row:
            row["active_concepts_in_session"] = list(active_concepts_in_session)
        enriched_incidents.append(row)

    bridges = rank_missing_bridges(missing_bridges)

    packet: dict[str, Any] = {
        "ksi_version": "0.1",
        "session_id": session_id,
        "iteration_id": iteration_id,
        "incidents": enriched_incidents,
        "missing_bridges": bridges,
    }
    if topology is not None:
        packet["topology"] = dict(topology)
    return packet


def build_teacher_prompt_sections(
    packet: Mapping[str, Any],
    *,
    active_areas: Sequence[str] | None = None,
) -> dict[str, str]:
    topology = packet.get("topology") or {}
    topo_lines = json.dumps(topology, indent=2, sort_keys=True) if topology else "(none)"
    active_concepts: set[str] = set()
    for inc in packet.get("incidents") or []:
        if isinstance(inc, dict) and inc.get("concept_id"):
            active_concepts.add(str(inc["concept_id"]))
        acs = inc.get("active_concepts_in_session") if isinstance(inc, dict) else None
        if isinstance(acs, list):
            active_concepts.update(str(x) for x in acs)

    incident_lines = json.dumps(list(packet.get("incidents") or []), indent=2, sort_keys=True)
    bridge_lines = json.dumps(list(packet.get("missing_bridges") or []), indent=2, sort_keys=True)

    structure = TEACHER_STRUCTURE_TEMPLATE.format(
        session_id=packet.get("session_id", ""),
        iteration_id=packet.get("iteration_id", ""),
        active_areas=", ".join(active_areas or []),
        topology_lines=topo_lines,
        active_concepts=", ".join(sorted(active_concepts)),
    )
    relations = TEACHER_RELATIONS_TEMPLATE.format(
        incident_count=len(list(packet.get("incidents") or [])),
        incident_lines=incident_lines,
        bridge_lines=bridge_lines,
    )
    return {"structure": structure, "relations": relations}
