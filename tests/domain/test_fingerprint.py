# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Task 6 — Domain Fingerprint Engine. Acceptance tests A–G."""

from __future__ import annotations

import pytest

from core.domain.models import DerivedMetrics, DomainFingerprint, PrimitiveMetrics
from core.domain.derived_metrics import compute_derived_metrics
from core.domain.fingerprint import (
    build_fingerprint,
    round6,
    same_fingerprint,
    euclidean_distance,
    manhattan_distance,
    cosine_similarity,
    marketable_derived_from_map,
    FINGERPRINT_VERSION,
    FULL_ORDER,
    MARKETABLE_DERIVED_ORDER,
    DERIVED_ORDER,
)


def _test_primitive() -> PrimitiveMetrics:
    return PrimitiveMetrics(LD=0.42, COH=0.61, NC=0.12, PR=0.27, PV=0.09, CI=0.44)


def _test_derived() -> DerivedMetrics:
    p = _test_primitive()
    return compute_derived_metrics(p)


def build_test_fingerprint() -> DomainFingerprint:
    p = _test_primitive()
    d = _test_derived()
    return build_fingerprint(p, d, domain_release="law_v0_3", source_id="doc_001")


def build_modified_fingerprint() -> DomainFingerprint:
    """Same as test but with one primitive changed so hash differs."""
    p = PrimitiveMetrics(LD=0.43, COH=0.61, NC=0.12, PR=0.27, PV=0.09, CI=0.44)
    d = compute_derived_metrics(p)
    return build_fingerprint(p, d, domain_release="law_v0_3", source_id="doc_001")


# ---------------------------------------------------------------------------
# Test A — Stable Vector Length
# ---------------------------------------------------------------------------
def test_fingerprint_length() -> None:
    """metricValues and metricNames have length 41."""
    fp = build_test_fingerprint()
    assert len(fp.metric_values) == 41
    assert len(fp.metric_names) == 41


# ---------------------------------------------------------------------------
# Test B — Stable Order
# ---------------------------------------------------------------------------
def test_fingerprint_order() -> None:
    """First name LD, second COH, third NC; last name KVI."""
    fp = build_test_fingerprint()
    assert fp.metric_names[0] == "LD"
    assert fp.metric_names[1] == "COH"
    assert fp.metric_names[2] == "NC"
    assert fp.metric_names[40] == "KVI"


# ---------------------------------------------------------------------------
# Test C — Hash Determinism
# ---------------------------------------------------------------------------
def test_hash_determinism() -> None:
    """Same inputs -> same vectorHash."""
    a = build_test_fingerprint()
    b = build_test_fingerprint()
    assert a.vector_hash == b.vector_hash


# ---------------------------------------------------------------------------
# Test D — Value Determinism
# ---------------------------------------------------------------------------
def test_value_determinism() -> None:
    """Same inputs -> same metricValues."""
    a = build_test_fingerprint()
    b = build_test_fingerprint()
    assert a.metric_values == b.metric_values


# ---------------------------------------------------------------------------
# Test E — Distance Identity
# ---------------------------------------------------------------------------
def test_distance_identity() -> None:
    """Distance of vector to self: euclidean=0, manhattan=0, cosine=1."""
    fp = build_test_fingerprint()
    v = fp.metric_values
    assert euclidean_distance(v, v) == 0.0
    assert manhattan_distance(v, v) == 0.0
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Test F — Hash Changes on Metric Change
# ---------------------------------------------------------------------------
def test_hash_changes_when_metric_changes() -> None:
    """Modified fingerprint -> different vectorHash."""
    a = build_test_fingerprint()
    b = build_modified_fingerprint()
    assert a.vector_hash != b.vector_hash


# ---------------------------------------------------------------------------
# Test G — Rounding Stability
# ---------------------------------------------------------------------------
def test_rounding_stability() -> None:
    """round6 rounds to 6 decimals correctly."""
    assert round6(0.1234567) == pytest.approx(0.123457, abs=1e-9)
    assert round6(0.1234564) == pytest.approx(0.123456, abs=1e-9)


# ---------------------------------------------------------------------------
# Additional: same_fingerprint, build requires non-null
# ---------------------------------------------------------------------------
def test_same_fingerprint() -> None:
    a = build_test_fingerprint()
    b = build_test_fingerprint()
    assert same_fingerprint(a, b) is True
    assert same_fingerprint(a, None) is False
    assert same_fingerprint(None, b) is False


def test_build_requires_primitive() -> None:
    with pytest.raises(ValueError, match="PrimitiveMetrics"):
        build_fingerprint(None, _test_derived())


def test_build_requires_derived() -> None:
    with pytest.raises(ValueError, match="DerivedMetrics"):
        build_fingerprint(_test_primitive(), None)


def test_marketable_derived_subset() -> None:
    """Marketable subset has 14 metrics, each in full DERIVED_ORDER."""
    assert len(MARKETABLE_DERIVED_ORDER) == 14
    derived_set = set(DERIVED_ORDER)
    for name in MARKETABLE_DERIVED_ORDER:
        assert name in derived_set, f"{name} must be in DERIVED_ORDER"
    fp = build_test_fingerprint()
    marketable = marketable_derived_from_map(fp.derived_map)
    assert len(marketable) == 14
    assert set(marketable.keys()) == set(MARKETABLE_DERIVED_ORDER)


def test_fingerprint_version_and_to_dict() -> None:
    fp = build_test_fingerprint()
    assert fp.fingerprint_version == FINGERPRINT_VERSION
    d = fp.to_dict()
    assert d["fingerprintVersion"] == FINGERPRINT_VERSION
    assert d["domainRelease"] == "law_v0_3"
    assert d["sourceId"] == "doc_001"
    assert "metricNames" in d and "metricValues" in d
    assert "primitiveMap" in d and "derivedMap" in d
    assert "vectorHash" in d
    assert len(d["metricValues"]) == 41
