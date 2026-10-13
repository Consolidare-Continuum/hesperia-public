# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Bridge from sphere pipeline state to KME pipeline.
Maps (matched, F) → ConceptHits + RelationCandidates and provides a synthetic domain graph.
"""

from __future__ import annotations

from core.domain.models import (
    ConceptHit,
    DomainGraph,
    DomainNode,
    RelationCandidate,
)


def synthetic_domain_graph_for_topology(num_families: int = 288) -> DomainGraph:
    """Build a minimal domain graph with one node per family (f_0 .. f_{N-1}), no edges."""
    nodes = {f"f_{i}": DomainNode(concept_id=f"f_{i}") for i in range(num_families)}
    return DomainGraph(nodes=nodes, edges=[])


def pipeline_matched_to_hits_relations(
    matched: list[tuple[int, str]],
    num_families: int = 288,
) -> tuple[list[ConceptHit], list[RelationCandidate]]:
    """Convert pipeline matched list [(family_id, token), ...] to ConceptHits and RelationCandidates."""
    hits: list[ConceptHit] = []
    for token_index, (family_id, _token) in enumerate(matched):
        if 0 <= family_id < num_families:
            hits.append(ConceptHit(concept_id=f"f_{family_id}", token_index=token_index))
    return (hits, [])
