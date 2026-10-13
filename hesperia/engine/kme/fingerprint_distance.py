# HESPERIA — Cross-session fingerprint distance metrics
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Distance between KME fingerprints for patient similarity, therapy progress, cluster detection.
Uses metric_values (41-dim vector) from DomainFingerprint.
"""

from __future__ import annotations

import math
from typing import Any


def _vector_from_fingerprint(fp: Any) -> list[float]:
    """Extract 41-dim vector from DomainFingerprint or dict with metricValues/metric_values."""
    if hasattr(fp, "metric_values"):
        return list(fp.metric_values)
    if isinstance(fp, dict):
        v = fp.get("metricValues") or fp.get("metric_values")
        if v is not None:
            return list(v)
    if isinstance(fp, (list, tuple)) and len(fp) == 41:
        return [float(x) for x in fp]
    raise ValueError("Fingerprint must have metric_values or be 41-dim list")


def cosine_distance(a: Any, b: Any) -> float:
    """
    Cosine distance = 1 - cosine_similarity. Range [0, 2]; 0 = identical, 2 = opposite.
    For nonnegative KME vectors typically [0, 1].
    """
    from core.domain.fingerprint import cosine_similarity
    va = _vector_from_fingerprint(a)
    vb = _vector_from_fingerprint(b)
    sim = cosine_similarity(va, vb)
    return 1.0 - sim


def euclidean_distance(a: Any, b: Any) -> float:
    """Euclidean distance between two fingerprint vectors."""
    from core.domain.fingerprint import euclidean_distance as _euc
    return _euc(_vector_from_fingerprint(a), _vector_from_fingerprint(b))


def wasserstein_distance(a: Any, b: Any) -> float:
    """
    1D Wasserstein (Earth Mover's) distance between fingerprint vectors.
    Vectors normalized to sum=1, then sum of |CDF_a(i) - CDF_b(i)| over dimensions.
    """
    va = _vector_from_fingerprint(a)
    vb = _vector_from_fingerprint(b)
    if len(va) != len(vb):
        raise ValueError("Vector size mismatch")
    n = len(va)
    sa = sum(va)
    sb = sum(vb)
    if sa <= 0:
        sa = 1.0
    if sb <= 0:
        sb = 1.0
    cdf_a = 0.0
    cdf_b = 0.0
    total = 0.0
    for i in range(n):
        cdf_a += va[i] / sa
        cdf_b += vb[i] / sb
        total += abs(cdf_a - cdf_b)
    return total


def fingerprint_distance(a: Any, b: Any, metric: str = "cosine") -> float:
    """
    Single entry point: cosine, euclidean, or wasserstein.
    metric: "cosine" | "euclidean" | "wasserstein"
    """
    if metric == "cosine":
        return cosine_distance(a, b)
    if metric == "euclidean":
        return euclidean_distance(a, b)
    if metric == "wasserstein":
        return wasserstein_distance(a, b)
    raise ValueError(f"Unknown metric: {metric}")
