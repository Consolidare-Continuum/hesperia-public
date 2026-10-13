# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Narrative paths over area topology: routes, strongest paths, route typing."""

from __future__ import annotations

from typing import Any

from hesperia.extensions.triz.topology_metrics import area_distance, get_area_neighbors


def extract_narrative_routes(propagation_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Ordered area sequence by descending final activation (dominant narrative spine).
    """
    final = propagation_result.get("area_activation_final")
    if not final or not isinstance(final, (list, tuple)):
        return []
    ranked = sorted(range(len(final)), key=lambda i: (-float(final[i]), i))
    threshold = 0.08
    active = [i for i in ranked if float(final[i]) >= threshold]
    if not active:
        active = ranked[: min(5, len(ranked))]
    return [
        {
            "step": idx,
            "area": a,
            "activation": round(float(final[a]), 6),
        }
        for idx, a in enumerate(active)
    ]


def _path_score(
    path: list[int],
    area_final: list[float],
    contradiction_pressure: dict[int, float],
    damping_per_hop: float = 0.04,
) -> float:
    act = sum(float(area_final[a]) for a in path)
    damp = damping_per_hop * max(len(path) - 1, 0)
    pen = sum(float(contradiction_pressure.get(a, 0.0)) for a in path) * 0.2
    return act - damp - pen


def _bfs_path(nm: dict[int, list[int]], start: int, goal: int) -> list[int] | None:
    from collections import deque

    if start == goal:
        return [start]
    q = deque([(start, [start])])
    seen = {start}
    while q:
        u, path = q.popleft()
        for v in nm.get(u, []):
            if v in seen:
                continue
            seen.add(v)
            npth = path + [v]
            if v == goal:
                return npth
            q.append((v, npth))
    return None


def get_strongest_narrative_paths(
    narrative_id: str,
    propagation_result: dict[str, Any],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Shortest canonical paths from seed (max base) to high-activation targets."""
    final = propagation_result.get("area_activation_final") or []
    base = propagation_result.get("area_base") or final
    pressure = propagation_result.get("contradiction_pressure") or {}
    nm = get_area_neighbors()
    if not final:
        return []
    seed = max(range(len(base)), key=lambda i: (float(base[i]), -i))
    targets = sorted(range(len(final)), key=lambda i: (-float(final[i]), i))[:6]
    paths_scored: list[tuple[float, list[int]]] = []

    for t in targets:
        if t == seed:
            paths_scored.append((_path_score([seed], list(final), pressure), [seed]))
        else:
            pth = _bfs_path(nm, seed, t)
            if pth:
                paths_scored.append((_path_score(pth, list(final), pressure), pth))

    paths_scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[dict[str, Any]] = []
    for sc, pth in paths_scored[: max(1, top_k)]:
        rt = _classify_route_type(pth, pressure, final)
        out.append(
            {
                "narrative_id": narrative_id,
                "path": pth,
                "path_score": round(float(sc), 6),
                "route_type": rt,
            }
        )
    return out


def _classify_route_type(
    path: list[int],
    pressure: dict[int, float],
    final: list[float],
) -> str:
    if len(path) <= 1:
        return "local_route"
    dtot = 0
    for i in range(len(path) - 1):
        dtot += area_distance(path[i], path[i + 1])
    avg_p = sum(pressure.get(a, 0.0) for a in path) / max(len(path), 1)
    end_act = float(final[path[-1]]) if path else 0.0
    if avg_p > 0.35 and end_act < 0.15:
        return "blocked_route"
    if dtot <= len(path) - 1:
        return "local_route"
    if dtot >= 2 * (len(path) - 1):
        return "cross_domain_route"
    return "spillover_route"


def summarize_routes_for_monitor(
    propagation_result: dict[str, Any],
    narrative_id: str = "narrative_primary",
) -> dict[str, Any]:
    """Dominant routes + blocked/spillover labels for narrative monitor."""
    paths = get_strongest_narrative_paths(narrative_id, propagation_result, top_k=8)
    final = propagation_result.get("area_activation_final") or []
    blocked = sorted({p["path"][-1] for p in paths if p["route_type"] == "blocked_route"})
    spill = sorted({p["path"][-1] for p in paths if p["route_type"] == "spillover_route"})
    return {
        "dominant_routes": extract_narrative_routes(propagation_result),
        "strongest_paths": paths,
        "blocked_areas": blocked,
        "spillover_targets": spill,
    }
