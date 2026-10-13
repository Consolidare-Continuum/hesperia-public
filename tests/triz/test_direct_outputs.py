"""Atomic TRIZ direct metrics and corpus comparison."""

from __future__ import annotations

from hesperia.extensions.triz.direct_outputs import TRIZDirectMetrics, compare_triz_direct


def test_compare_triz_direct_deterministic() -> None:
    a = TRIZDirectMetrics(
        contradiction_density=0.1,
        innovation_score=0.5,
        narrative_penetration=0.3,
        innovation_cluster_count=4,
    )
    b = TRIZDirectMetrics(
        contradiction_density=0.18,
        innovation_score=0.82,
        narrative_penetration=0.63,
        innovation_cluster_count=6,
    )
    d = compare_triz_direct(a, b)
    assert d["contradiction_delta"] == 0.08
    assert d["innovation_delta"] == 0.32
    assert d["narrative_shift"] == 0.33
    assert d["cluster_emergence_rate"] == 0.5
