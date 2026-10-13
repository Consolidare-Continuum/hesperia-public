# HESPERIA — L6 /analyze perturbation producer tests (HES-PROD-B03).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import os

import pytest

from core.layers import build_canonical_stub_adjacency
from core.layers.layer_1 import compute_L1
from core.layers.layer_2 import compute_L2
from runtime.services.l6_perturbation_producer import (
    compute_l6_with_optional_producer,
    l6_perturbation_enabled,
)


def _base_l1_l2_hits():
    F, A, D = 288, 12, 8
    hits = [0] * F
    hits[0] = 8
    hits[1] = 3
    hits[24] = 2
    matched = [(i, 0.5) for i, h in enumerate(hits) for _ in range(h)]
    token_count = max(1, sum(hits))
    l1 = compute_L1(token_count, matched, F=F, A=A)
    adj = build_canonical_stub_adjacency(F, A)
    l2 = compute_L2(l1, hits, adjacency=adj, F=F, A=A, MAX_ALLOWED_DEPTH=D)
    return l1, l2, hits, adj


def test_l6_producer_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_L6_PERTURBATION", raising=False)
    assert l6_perturbation_enabled() is False
    l1, l2, hits, adj = _base_l1_l2_hits()
    out = compute_l6_with_optional_producer(l1, l2, hits, adjacency=adj)
    assert out["COVERAGE_GRADIENT"] == 0.0
    assert out["INPUT_PERTURBATION_RESPONSE"] == 0.0
    assert out["DOMINANT_FAMILY_STABILITY"] is True


def test_l6_producer_on_computes_finite_differences(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_L6_PERTURBATION", "1")
    monkeypatch.setenv("HESPERIA_L6_PERTURBATION_EPS", "0.1")
    l1, l2, hits, adj = _base_l1_l2_hits()
    out = compute_l6_with_optional_producer(l1, l2, hits, adjacency=adj, total_tokens=sum(hits))
    # At least one first-difference slot leaves sealed zero when mass scales.
    assert (
        out["COVERAGE_GRADIENT"] != 0.0
        or out["ENTROPY_GRADIENT"] != 0.0
        or out["INPUT_PERTURBATION_RESPONSE"] != 0.0
        or out["POTENTIAL_GRADIENT"] != 0.0
    )


def test_env_guard_allows_l6_flags() -> None:
    from runtime.shipping.env_guard import ALLOWED_HESPERIA_ENV

    assert "HESPERIA_L6_PERTURBATION" in ALLOWED_HESPERIA_ENV
    assert "HESPERIA_L6_PERTURBATION_EPS" in ALLOWED_HESPERIA_ENV
