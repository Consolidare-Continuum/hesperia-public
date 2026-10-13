# HESPERIA — Projection layer follows area-math grain switch.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from core.projection.public_projection_layer import (
    apply_public_projection,
    project_public_areas,
    project_public_metrics,
)
from core.topology.reserve_loader import is_reserved_area, is_reserved_family


def test_reserve_inactive_under_grain_12(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_TEN_AREA_MODULE", raising=False)
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "12")
    assert is_reserved_area(10) is False
    assert is_reserved_area(11) is False
    assert is_reserved_family(250) is False


def test_reserve_active_under_grain_10(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "10")
    assert is_reserved_area(10) is True
    assert is_reserved_area(11) is True
    assert is_reserved_family(250) is True
    assert is_reserved_area(3) is False


def test_project_public_areas_follows_grain(monkeypatch: pytest.MonkeyPatch) -> None:
    av = [float(i) for i in range(12)]
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "12")
    out12 = project_public_areas(av)
    assert out12["area_math_grain"] == 12
    assert len(out12["macro_domain_vector"]) == 12
    assert out12["macro_domain_vector"][10] == 10.0

    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "10")
    out10 = project_public_areas(av)
    assert out10["area_math_grain"] == 10
    assert len(out10["macro_domain_vector"]) == 10


def test_project_public_metrics_and_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "12")
    metrics = {
        "area_vector": [0.0] * 9 + [1.0, 2.0, 3.0],
        "family_counts": [1.0] * 288,
        "dominant_area": 10,
        "loopability": 0.5,
    }
    out = project_public_metrics(metrics)
    assert len(out["macro_domain_vector"]) == 12
    assert out["dominant_macro_domain"] == 10
    assert len(out["policy_family_counts"]) == 288

    payload = apply_public_projection({"area_vector": metrics["area_vector"], "L1": {"x": 1}})
    assert payload["area_math_grain"] == 12
    assert len(payload["macro_domain_vector"]) == 12


def test_explicit_grain_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "10")
    av = [1.0] * 12
    out = project_public_areas(av, grain=12)
    assert out["area_math_grain"] == 12
    assert len(out["macro_domain_vector"]) == 12
