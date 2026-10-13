# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Single TRIZ entry point for HESPERIA: activations + relations + area adjacency → TRIZSignals.
"""

from __future__ import annotations

from hesperia.extensions.triz.contradiction_engine import build_contradiction_signals
from hesperia.extensions.triz.models import (
    ConceptActivation,
    ConceptRelation,
    TRIZSignals,
)
from hesperia.extensions.triz.novelty_engine import (
    compute_contradiction_density,
    detect_concept_clusters,
    score_innovation_clusters,
)
from hesperia.extensions.triz.direct_outputs import build_triz_direct_metrics
from hesperia.extensions.triz.propagation_engine import (
    aggregate_area_activation,
    build_narrative_signals,
    propagate_activation_with_history,
)
from hesperia.extensions.triz.topology_binding import bind_concepts_to_coordinates


def run_triz_analysis(
    activations: list[ConceptActivation],
    relations: list[ConceptRelation],
    topology_adjacency: dict[int, list[int]],
    *,
    narrative_id: str = "narrative_primary",
    family_count: int = 240,
    propagation_steps: int = 3,
    damping: float = 0.2,
    min_contradiction_score: float = 0.15,
) -> TRIZSignals:
    """
    1. Contradictions + TRIZ class + coordinates
    2. Contradiction density
    3. Clusters + innovation scores
    4. Area propagation + narrative signals
    Deterministic: sorted contradictions/clusters, 6-decimal floats.
    """
    concept_coords = bind_concepts_to_coordinates(activations)
    contradictions = build_contradiction_signals(
        activations,
        relations,
        concept_coords,
        min_score=min_contradiction_score,
    )
    density = compute_contradiction_density(contradictions, relations)
    clusters = list(detect_concept_clusters(relations))
    covered = {x for cl in clusters for x in cl}
    for act in sorted(activations, key=lambda x: x.concept_id):
        if act.concept_id not in covered:
            clusters.append([act.concept_id])
            covered.add(act.concept_id)
    if not clusters:
        clusters = [[a.concept_id] for a in sorted(activations, key=lambda x: x.concept_id)]
    clusters.sort(key=lambda c: (c[0] if c else "", len(c), c))
    act_map = {a.concept_id: float(a.activation) for a in activations}
    total_c = max(len(activations), 1)
    innovation_clusters = score_innovation_clusters(
        clusters,
        density,
        concept_coords,
        total_concepts=total_c,
        final_activations=act_map,
        min_cluster_size=1,
    )
    innovation_clusters.sort(key=lambda x: (-x.innovation_score, x.cluster_id))

    area_act = aggregate_area_activation(activations)
    if not area_act:
        for a in range(12):
            area_act[a] = 0.0
    history, propagated = propagate_activation_with_history(
        area_act, topology_adjacency, steps=propagation_steps, damping=damping
    )
    narratives = build_narrative_signals(
        propagated,
        family_count,
        activations=activations,
        steps=propagation_steps,
        narrative_id=narrative_id,
    )
    direct = build_triz_direct_metrics(
        activations,
        relations,
        topology_adjacency,
        contradictions,
        innovation_clusters,
        narratives,
        propagation_history=history,
        final_propagated=propagated,
        propagation_steps=propagation_steps,
        damping=damping,
        family_count=family_count,
        area_activation_base=dict(area_act),
    )

    return TRIZSignals(
        contradictions=contradictions,
        innovation_clusters=innovation_clusters,
        narratives=narratives,
        narrative_routes=[],
        direct_metrics=direct,
    )
