# HESPERIA — family_graph shortest-path cost (24_SPEC §4.2 / METRIC-35).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

from collections import deque
from typing import Any

from sphere.topology.family_embedding import (
    ZONE_KEYS,
    get_bridges,
    get_composite_family_id,
    load_family_embedding_tfp,
)

_ZONE_STEP_COST: dict[str, float] = {
    "center": 0.0,
    "inner_ring": 1.0,
    "middle_ring": 2.0,
    "outer_ring": 3.0,
}

_BRIDGE_COST_DEFAULT = 1.5


def _family_zone_map(embedding: dict[str, Any]) -> dict[str, str]:
    """Map composite family id (A2_F3) → zone key within its area."""
    out: dict[str, str] = {}
    for area_key, area_data in embedding.items():
        if not isinstance(area_data, dict) or area_key in ("version", "domain", "bridges", "zones"):
            continue
        for zone in ZONE_KEYS:
            families = area_data.get(zone)
            if not isinstance(families, list):
                continue
            for fam in families:
                local = str(fam).strip().upper()
                if local.startswith("F"):
                    cid = f"{area_key}_{local}"
                else:
                    cid = f"{area_key}_F{local}"
                out[cid] = zone
    return out


def _build_adjacency(embedding: dict[str, Any]) -> dict[str, list[tuple[str, float]]]:
    """Undirected adjacency with zone + bridge edge costs."""
    zone_map = _family_zone_map(embedding)
    adj: dict[str, list[tuple[str, float]]] = {fid: [] for fid in zone_map}

    # Intra-area ring: connect families in same area by zone step cost delta
    for area_key, area_data in embedding.items():
        if not isinstance(area_data, dict) or area_key in ("version", "domain", "bridges", "zones"):
            continue
        families_in_area: list[str] = []
        for zone in ZONE_KEYS:
            val = area_data.get(zone)
            if isinstance(val, list):
                for fam in val:
                    local = str(fam).strip().upper()
                    fid = local if local.startswith("F") else f"F{local}"
                    families_in_area.append(get_composite_family_id(area_key, fid))
        for i, a in enumerate(families_in_area):
            za = zone_map.get(a, "outer_ring")
            for b in families_in_area[i + 1 :]:
                zb = zone_map.get(b, "outer_ring")
                cost = abs(_ZONE_STEP_COST[za] - _ZONE_STEP_COST[zb]) or 1.0
                adj[a].append((b, cost))
                adj[b].append((a, cost))

    for bridge in get_bridges(embedding):
        a, b = bridge["from"], bridge["to"]
        if a not in adj:
            adj[a] = []
        if b not in adj:
            adj[b] = []
        adj[a].append((b, _BRIDGE_COST_DEFAULT))
        adj[b].append((a, _BRIDGE_COST_DEFAULT))

    return adj


def family_graph_shortest_path_cost(
    from_id: str,
    to_id: str,
    embedding: dict[str, Any] | None = None,
) -> float | None:
    """Shortest-path cost on family_graph layer (YAML zones + bridges)."""
    emb = embedding if embedding is not None else load_family_embedding_tfp()
    adj = _build_adjacency(emb)
    if from_id not in adj or to_id not in adj:
        return None
    if from_id == to_id:
        return 0.0

    dist: dict[str, float] = {from_id: 0.0}
    q: deque[str] = deque([from_id])
    while q:
        u = q.popleft()
        if u == to_id:
            return dist[u]
        for v, w in adj.get(u, []):
            nd = dist[u] + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                q.append(v)
    return None


def family_graph_edge_for_path_metric(
    from_id: str,
    to_id: str,
    embedding: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Single edge dict for path_metric.compute_s_path (metric_layer=family_graph)."""
    cost = family_graph_shortest_path_cost(from_id, to_id, embedding)
    if cost is None:
        return None
    return {
        "layer": "family_graph",
        "from": from_id,
        "to": to_id,
        "zone_path_cost": cost,
    }
