# HESPERIA — Path action S_path computation (24_SPEC §5 / METRIC-24).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import math
from typing import Any

_PATH_ACTION_VERSION = "0.1"

_DEFAULT_WEIGHTS: dict[str, float] = {
    "area_sphere": 1.0,
    "family_graph": 1.0,
    "hex_graph": 1.0,
    "concept_graph": 1.0,
}


def _edge_length(edge: dict[str, Any], layer: str) -> float:
    if layer == "area_sphere":
        return float(edge.get("geodesic_distance", 0.0))
    if layer == "family_graph":
        return float(edge.get("zone_path_cost", 0.0))
    if layer == "hex_graph":
        g = edge.get("gradient")
        return abs(float(g)) if g is not None else 1.0
    if layer == "concept_graph":
        w_e = float(edge.get("weight", 0.0))
        return -math.log(max(w_e, 1e-12))
    return float(edge.get("cost", 0.0))


def compute_s_path(
    edges: list[dict[str, Any]],
    *,
    layer_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute S_path(P) = Σ w_layer(e) · ℓ_layer(e) over sealed path edges.

    Each edge dict should contain at minimum ``layer`` (str) and a length
    field appropriate to that layer (``geodesic_distance``, ``zone_path_cost``,
    ``gradient``, or ``weight``).

    Returns the optional export block from 24_SPEC §5.
    """
    weights = {**_DEFAULT_WEIGHTS, **(layer_weights or {})}
    total = 0.0
    layers_seen: list[str] = []

    for edge in edges:
        layer = str(edge.get("layer", "hex_graph"))
        length = _edge_length(edge, layer)
        w = weights.get(layer, 1.0)
        total += w * length
        if layer not in layers_seen:
            layers_seen.append(layer)

    return {
        "path_metric_cost": round(total, 6),
        "path_metric_layers": layers_seen,
        "path_action_version": _PATH_ACTION_VERSION,
    }


def attach_path_metric(payload: dict[str, Any], edges: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Attach path_metric_cost fields to a matrix_run or traversal payload."""
    if not edges:
        return payload
    out = dict(payload)
    out.update(compute_s_path(edges))
    return out
