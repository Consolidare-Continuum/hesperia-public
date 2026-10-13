# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Domain Profile Layer: build_profile, domain_distance, classify_document."""

from __future__ import annotations

import pytest

from core.domain.models import DomainFingerprint
from core.domain.fingerprint import FULL_ORDER
from core.domain.profile import build_profile, domain_distance, classify_document


def _make_fingerprint(values: list[float], source_id: str = "doc") -> DomainFingerprint:
    """Build a fingerprint with given 41 metric values (pad/trim to 41). Clamp to [0,1] for consistency."""
    vals = list(values)
    while len(vals) < 41:
        vals.append(0.0)
    if len(vals) > 41:
        vals = vals[:41]
    vals = [max(0.0, min(1.0, x)) for x in vals]
    return DomainFingerprint(
        fingerprint_version="hesperia_fp_v0_1",
        domain_release="",
        source_id=source_id,
        metric_names=FULL_ORDER,
        metric_values=vals,
        primitive_map={},
        derived_map={},
        vector_hash="",
    )


def test_build_profile_empty() -> None:
    """Zero fingerprints -> profile with document_count=0, zero vectors, hash of zeros."""
    from core.domain.models import DomainProfile

    profile = build_profile("physics", [])
    assert profile.domain_id == "physics"
    assert profile.document_count == 0
    assert len(profile.mean_vector) == 41
    assert all(x == 0.0 for x in profile.mean_vector)
    assert profile.profile_hash is not None
    assert len(profile.profile_hash) == 64


def test_build_profile_single() -> None:
    """One fingerprint -> mean=median=that vector, std=0, p90=that vector."""
    fp = _make_fingerprint([0.5] * 41, "d1")
    profile = build_profile("law", [fp])
    assert profile.document_count == 1
    assert profile.mean_vector[0] == 0.5
    assert profile.std_vector[0] == 0.0
    assert profile.median_vector[0] == 0.5
    assert profile.p90_vector[0] == 0.5
    assert profile.profile_hash is not None


def test_build_profile_two() -> None:
    """Two fingerprints -> mean midpoint, std non-zero, p90 is max."""
    fp1 = _make_fingerprint([0.2] * 41, "d1")
    fp2 = _make_fingerprint([0.8] * 41, "d2")
    profile = build_profile("economics", [fp1, fp2])
    assert profile.document_count == 2
    assert profile.mean_vector[0] == pytest.approx(0.5)
    # Sample stdev of [0.2, 0.8]: sqrt(0.18) ≈ 0.424
    assert profile.std_vector[0] == pytest.approx(0.424, rel=0.01)
    assert profile.median_vector[0] == pytest.approx(0.5)
    assert profile.p90_vector[0] == pytest.approx(0.8)  # 90th percentile -> index 1 -> 0.8
    assert profile.profile_hash is not None


def test_profile_determinism() -> None:
    """Same fingerprints -> same profile (same mean, same hash)."""
    fp1 = _make_fingerprint([0.3, 0.4] + [0.0] * 39, "d1")
    fp2 = _make_fingerprint([0.5, 0.6] + [0.0] * 39, "d2")
    p1 = build_profile("phil", [fp1, fp2])
    p2 = build_profile("phil", [fp1, fp2])
    assert p1.mean_vector == p2.mean_vector
    assert p1.profile_hash == p2.profile_hash


def test_domain_distance() -> None:
    """Distance between two profiles = euclidean(mean_a, mean_b)."""
    fp1 = _make_fingerprint([1.0] * 41, "a")
    fp2 = _make_fingerprint([0.0] * 41, "b")
    prof_a = build_profile("physics", [fp1])
    prof_b = build_profile("law", [fp2])
    d = domain_distance(prof_a, prof_b)
    # sqrt(41 * 1^2) = sqrt(41)
    assert d == pytest.approx(41 ** 0.5)
    assert domain_distance(prof_a, prof_a) == pytest.approx(0.0)


def test_classify_document() -> None:
    """Classify returns domain_id of profile with closest mean to document fingerprint."""
    fp_physics = _make_fingerprint([0.9] * 41, "p")
    fp_law = _make_fingerprint([0.1] * 41, "l")
    prof_physics = build_profile("physics", [fp_physics])
    prof_law = build_profile("law", [fp_law])
    profiles = [prof_physics, prof_law]
    doc_near_physics = _make_fingerprint([0.85] * 41, "doc")
    doc_near_law = _make_fingerprint([0.15] * 41, "doc")
    assert classify_document(doc_near_physics, profiles) == "physics"
    assert classify_document(doc_near_law, profiles) == "law"
    assert classify_document(doc_near_physics, []) is None


def test_domain_profile_to_dict() -> None:
    """to_dict has domainId, documentCount, meanVector, stdVector, medianVector, p90Vector, profileHash."""
    fp = _make_fingerprint([0.5] * 41, "d1")
    profile = build_profile("math", [fp])
    d = profile.to_dict()
    assert d["domainId"] == "math"
    assert d["documentCount"] == 1
    assert "meanVector" in d and len(d["meanVector"]) == 41
    assert "stdVector" in d and "medianVector" in d and "p90Vector" in d
    assert "profileHash" in d
