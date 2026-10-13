# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Domain Profile Layer.
Aggregates N document fingerprints into one corpus-level profile: mean, std, median, p90 per dimension (41).
Enables domain comparison, classification, and drift detection. Deterministic.
"""

from __future__ import annotations

import math
import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import DomainFingerprint, DomainProfile

VECTOR_LENGTH = 41


def _percentile90(values: list[float]) -> float:
    """Deterministic 90th percentile: sorted_values[ceil(0.90 * n) - 1] clamped to valid index."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    index = int(math.ceil(0.90 * n)) - 1
    index = max(0, min(n - 1, index))
    return sorted_vals[index]


def _column(values_per_doc: list[list[float]], i: int) -> list[float]:
    """Extract i-th dimension across all documents."""
    return [doc[i] for doc in values_per_doc if i < len(doc)]


def _profile_hash(mean_vector: list[float]) -> str:
    """SHA-256 of canonical mean vector string (6 decimals, deterministic)."""
    import hashlib
    parts = [f"{max(0.0, min(1.0, round(x * 1e6) / 1e6)):.6f}" for x in mean_vector]
    payload = ",".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_profile(domain_id: str, fingerprints: list["DomainFingerprint"]) -> "DomainProfile":
    """
    Build domain profile from N fingerprints. For each dimension i: mean, std, median, p90.
    profile_hash = SHA-256 of canonical mean vector. Vector length 41.
    """
    from core.domain.models import DomainProfile

    domain_id = (domain_id or "").strip()
    n = len(fingerprints)

    if n == 0:
        zeros = [0.0] * VECTOR_LENGTH
        return DomainProfile(
            domain_id=domain_id,
            document_count=0,
            mean_vector=zeros,
            std_vector=zeros,
            median_vector=zeros,
            p90_vector=zeros,
            profile_hash=_profile_hash(zeros),
        )

    values_per_doc = [list(fp.metric_values) for fp in fingerprints]
    for v in values_per_doc:
        while len(v) < VECTOR_LENGTH:
            v.append(0.0)
        if len(v) > VECTOR_LENGTH:
            v[:] = v[:VECTOR_LENGTH]

    mean_vec: list[float] = []
    std_vec: list[float] = []
    median_vec: list[float] = []
    p90_vec: list[float] = []

    for i in range(VECTOR_LENGTH):
        col = _column(values_per_doc, i)
        if not col:
            mean_vec.append(0.0)
            std_vec.append(0.0)
            median_vec.append(0.0)
            p90_vec.append(0.0)
            continue
        mean_vec.append(statistics.mean(col))
        if len(col) > 1:
            std_vec.append(statistics.stdev(col))
        else:
            std_vec.append(0.0)
        median_vec.append(statistics.median(col))
        p90_vec.append(_percentile90(col))

    return DomainProfile(
        domain_id=domain_id,
        document_count=n,
        mean_vector=mean_vec,
        std_vector=std_vec,
        median_vector=median_vec,
        p90_vector=p90_vec,
        profile_hash=_profile_hash(mean_vec),
    )


def domain_distance(profile_a: "DomainProfile", profile_b: "DomainProfile") -> float:
    """Euclidean distance between two domain profiles (mean vectors)."""
    from core.domain.fingerprint import euclidean_distance
    return euclidean_distance(profile_a.mean_vector, profile_b.mean_vector)


def classify_document(
    fingerprint: "DomainFingerprint",
    profiles: list["DomainProfile"],
) -> str | None:
    """Return domain_id of the profile whose mean is closest to the document fingerprint. None if profiles empty."""
    if not profiles:
        return None
    from core.domain.fingerprint import euclidean_distance
    best_id: str | None = None
    best_dist = float("inf")
    for p in profiles:
        d = euclidean_distance(fingerprint.metric_values, p.mean_vector)
        if d < best_dist:
            best_dist = d
            best_id = p.domain_id
    return best_id
