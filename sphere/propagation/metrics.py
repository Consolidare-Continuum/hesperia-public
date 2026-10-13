# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Propagation diagnostics: meta-node flow ratio and related metrics.
"""

from __future__ import annotations

import numpy as np


def meta_flow_ratio(
    propagation_matrix: np.ndarray,
    meta_indices: frozenset[int] | set[int],
) -> float:
    """
    Ratio of flow through meta nodes to total flow.
    Definition: flow_through_meta / total_flow.
    Flow through meta = sum of W[i,j] where i in meta or j in meta (edges incident to meta).
    Total flow = sum of all W (or number of edges × mean weight); for row-stochastic W,
    total "outflow" per row is 1, so total_flow = num_nodes = 12. We define flow_through_meta
    as the sum of weights on edges incident to meta nodes (each edge counted once).
    Returns value in [0, 1] for use in diagnostics.
    """
    W = np.asarray(propagation_matrix, dtype=np.float64)
    meta = set(meta_indices)
    n = W.shape[0]
    flow_through_meta = 0.0
    for i in range(n):
        for j in range(n):
            if W[i, j] > 0 and (i in meta or j in meta):
                flow_through_meta += W[i, j]
    # Each edge (i,j) appears as W[i,j] in row i; so sum of all W = n (row-stochastic).
    # Flow through meta counts weights on edges touching meta; divide by n for ratio.
    total_flow = float(n)
    if total_flow <= 0:
        return 0.0
    return float(flow_through_meta / total_flow)
