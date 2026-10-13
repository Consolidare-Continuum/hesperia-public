"""Deterministic concept-to-hex projection."""

from __future__ import annotations

from core.dynamics.operator import compute_h_total
from core.hexmap.topology import interaction
from core.state.semantic_state import SemanticState


def project_concepts_to_hex(
    concept_weights: dict[str, float],
    anchor_registry: dict[str, str],
    *,
    index_map: dict[str, int] | None = None,
    return_state: bool = False,
) -> tuple[SemanticState | dict[str, float], list[str]]:
    hex_state: dict[str, float] = {}
    contributor_count: dict[str, int] = {}
    degradation_flags: list[str] = []
    for concept_id, weight in concept_weights.items():
        hex_id = anchor_registry.get(concept_id)
        if not hex_id:
            degradation_flags.append(f"missing_anchor:{concept_id}")
            continue
        local = [hex_id]
        if index_map:
            local = sorted(
                (sym for sym in index_map if interaction(hex_id, sym, index_map) >= 0.5),
                key=lambda sym: sym,
            ) or [hex_id]
        if not index_map:
            interaction_sum = float(len(local))
        else:
            interaction_sum = sum(interaction(hex_id, sym, index_map) for sym in local)
        if interaction_sum <= 0:
            interaction_sum = float(len(local))
        for sym in local:
            if not index_map:
                spread = float(weight) / interaction_sum
            else:
                spread = float(weight) * (interaction(hex_id, sym, index_map) / interaction_sum)
            hex_state[sym] = hex_state.get(sym, 0.0) + spread
            contributor_count[sym] = contributor_count.get(sym, 0) + 1

    conflict_scale = 0.0
    if contributor_count:
        conflicts = [max(0, c - 1) for c in contributor_count.values()]
        conflict_scale = sum(conflicts) / max(1, len(conflicts))
    inhibited_state, _ = compute_h_total(
        hex_state,
        {
            "decay": 0.0,
            "coupling_alpha": 0.0,
            "inhibition_alpha": min(1.0, 0.1 * conflict_scale),
        },
    )
    state = SemanticState(mass_vector=inhibited_state, position=dict(anchor_registry))
    if return_state:
        return state, degradation_flags
    return state.mass_vector, degradation_flags

