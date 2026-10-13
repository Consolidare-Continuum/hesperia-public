# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Propagation corridors: one-step flow and high-gradient pathways."""

from __future__ import annotations

import numpy as np

__all__ = ["compute_propagation_corridors"]


def compute_propagation_corridors(
    hex_activation: np.ndarray,
    adjacency: list[list[int]],
    resistance: np.ndarray,
    *,
    alpha: float = 0.15,
    beta: float = 0.08,
    steps: int = 1,
    corridor_top_k: int = 64,
) -> dict[str, np.ndarray | list]:
    """
    A_h(t+1) = A_h(t) + α Σ_{n∈N(h)} A_n(t) − β R_h (clipped ≥ 0).

    Returns propagated state, flow matrix for last step, and top corridor edges by |ΔA| across links.
    """
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1).copy()
    r = np.asarray(resistance, dtype=np.float64).reshape(-1)
    n = a.shape[0]
    if len(r) != n or len(adjacency) != n:
        raise ValueError("shape mismatch")

    flow = np.zeros((n, n), dtype=np.float64)
    for _ in range(max(1, int(steps))):
        a_new = np.zeros(n, dtype=np.float64)
        flow.fill(0.0)
        for h in range(n):
            neigh_sum = sum(a[j] for j in adjacency[h])
            for j in adjacency[h]:
                flow[h, j] = alpha * float(a[j])
            a_new[h] = float(a[h] + alpha * neigh_sum - beta * r[h])
        a = np.maximum(a_new, 0.0)

    edges: list[dict[str, float | int]] = []
    seen: set[tuple[int, int]] = set()
    for h in range(n):
        for j in adjacency[h]:
            e = (min(h, j), max(h, j))
            if e in seen:
                continue
            seen.add(e)
            g = abs(float(a[h] - a[j]))
            edges.append({"from": e[0], "to": e[1], "gradient": g})
    edges.sort(key=lambda x: -x["gradient"])
    top = edges[: max(0, int(corridor_top_k))]

    return {
        "hex_propagation_vector": a,
        "propagation_flow_matrix": flow,
        "corridor_edges": top,
    }
