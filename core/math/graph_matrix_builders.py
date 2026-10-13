# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# Ontology → W_F, C_F (pairs), R_F. Indices follow lexicographic sort of family_ids.
#
# Graduated to core 2026-07-31 (was hesperia/extensions/dynamics/matrix_builders.py —
# generic adjacency/contradiction/resistance matrix construction, no domain semantics).
# The old location now re-exports from here for backward compatibility.

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def build_family_index(family_ids: List[str]) -> Dict[str, int]:
    """
    Deterministic family → index mapping (lexicographic sort of ids).
    """
    return {fid: i for i, fid in enumerate(sorted(family_ids))}


def build_family_adjacency_matrix(
    family_ids: List[str],
    relations: List[Tuple[str, str]],
) -> np.ndarray:
    """
    Build symmetric family adjacency W_F from ontology relations (weight 1 per edge).
    Unknown endpoints are skipped.
    """
    index = build_family_index(family_ids)
    n = len(index)

    w = np.zeros((n, n), dtype=np.float64)

    for a, b in relations:
        if a not in index or b not in index or a == b:
            continue
        i = index[a]
        j = index[b]
        w[i, j] = 1.0
        w[j, i] = 1.0

    return w


def build_contradiction_matrix(
    family_ids: List[str],
    contradictions: List[Tuple[str, str, float]],
) -> np.ndarray:
    """
    Build symmetric contradiction strengths from ontology pairs.
    Diagonal left zero; caller may pass through equations.build_contradiction_matrix.
    """
    index = build_family_index(family_ids)
    n = len(index)

    c = np.zeros((n, n), dtype=np.float64)

    for a, b, strength in contradictions:
        if a not in index or b not in index or a == b:
            continue
        if strength < 0:
            raise ValueError("contradiction strength must be non-negative")
        i = index[a]
        j = index[b]
        s = float(strength)
        c[i, j] = max(c[i, j], s)
        c[j, i] = max(c[j, i], s)

    return c


def build_resistance_vector(
    family_ids: List[str],
    resistance_priors: Dict[str, float],
    default_value: float = 0.1,
) -> np.ndarray:
    """
    Per-family resistance diagonal values from ontology priors.
    """
    index = build_family_index(family_ids)
    n = len(index)

    r = np.zeros(n, dtype=np.float64)

    for fid, i in index.items():
        r[i] = float(resistance_priors.get(fid, default_value))
        if r[i] < 0:
            raise ValueError(f"resistance for {fid} must be non-negative")

    return r


__all__ = [
    "build_family_index",
    "build_family_adjacency_matrix",
    "build_contradiction_matrix",
    "build_resistance_vector",
]
