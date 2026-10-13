# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Generic co-occurrence graph: centrality, cluster count, polarity edge proxy."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

import networkx as nx


def run_graph_baseline(text: str, window: int = 8) -> dict[str, Any]:
    toks = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())[:500]
    if len(toks) < 2:
        return {"cluster_count": 0, "edge_polarity_proxy": 0, "mean_centrality": 0.0}
    G = nx.Graph()
    pos = {"growth", "freedom", "gain", "support"}
    neg = {"cut", "ban", "crisis", "fail", "against", "oppose"}
    for i in range(len(toks)):
        for j in range(i + 1, min(i + window, len(toks))):
            a, b = toks[i], toks[j]
            if a == b:
                continue
            x, y = (a, b) if a <= b else (b, a)
            G.add_edge(x, y, weight=G.get_edge_data(x, y, {}).get("weight", 0) + 1)
    if G.number_of_nodes() == 0:
        return {"cluster_count": 0, "edge_polarity_proxy": 0, "mean_centrality": 0.0}
    comms = list(nx.community.louvain_communities(G, seed=42, weight="weight"))
    polar = 0
    for u, v, _ in G.edges(data=True):
        pu = u in pos or u in neg
        pv = v in pos or v in neg
        if pu and pv and ((u in pos and v in neg) or (u in neg and v in pos)):
            polar += 1
    cent = nx.degree_centrality(G)
    mc = sum(cent.values()) / max(len(cent), 1)
    return {
        "cluster_count": len(comms),
        "edge_polarity_proxy": polar,
        "mean_centrality": round(mc, 6),
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }
