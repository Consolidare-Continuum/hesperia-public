# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Load domain graph from JSON.
Canonicalizes: dedupe edges (undirected), ensure all edge endpoints exist as nodes.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.domain.models import DomainEdge, DomainGraph, DomainNode


def load_domain_graph_from_json(path: Path | str) -> DomainGraph:
    """
    Load domain graph from a JSON file.
    Accepts nodes: list or dict; edges: list of { sourceConceptId, targetConceptId, relationType }.
    """
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)

    nodes_raw = data.get("nodes")
    if nodes_raw is None:
        nodes = {}
    elif isinstance(nodes_raw, list):
        nodes = {}
        for item in nodes_raw:
            cid = item.get("conceptId") if isinstance(item, dict) else None
            if cid is not None:
                nodes[cid] = DomainNode(concept_id=cid)
    elif isinstance(nodes_raw, dict):
        nodes = {}
        for nid, val in nodes_raw.items():
            cid = val.get("conceptId", nid) if isinstance(val, dict) else nid
            nodes[cid] = DomainNode(concept_id=cid)
    else:
        nodes = {}

    edges_raw = data.get("edges", [])
    edges: list[DomainEdge] = []
    seen_undirected: set[tuple[str, str]] = set()
    for e in edges_raw:
        if not isinstance(e, dict):
            continue
        src = e.get("sourceConceptId")
        tgt = e.get("targetConceptId")
        rel = e.get("relationType", "")
        if src is None or tgt is None:
            continue
        src, tgt = str(src), str(tgt)
        key = (min(src, tgt), max(src, tgt))
        if key in seen_undirected:
            continue
        seen_undirected.add(key)
        edges.append(DomainEdge(source_concept_id=src, target_concept_id=tgt, relation_type=rel))

    for e in edges:
        if e.source_concept_id not in nodes:
            nodes[e.source_concept_id] = DomainNode(concept_id=e.source_concept_id)
        if e.target_concept_id not in nodes:
            nodes[e.target_concept_id] = DomainNode(concept_id=e.target_concept_id)

    return DomainGraph(nodes=nodes, edges=edges)


def load_frozen_constants(path: Path | str) -> "DomainConstants":
    """Load frozen domain constants from JSON (e.g. assets/data/domain_constants.json)."""
    from core.domain.models import DomainConstants

    p = Path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return DomainConstants(
        domain_node_count=int(data["domain_node_count"]),
        domain_degree_p95=float(data["domain_degree_p95"]),
        domain_distance_p95=float(data["domain_distance_p95"]),
    )
