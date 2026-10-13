"""Minimal KSI teacher packet serializer for 0.6.3 (values-only Teacher input)."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


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
