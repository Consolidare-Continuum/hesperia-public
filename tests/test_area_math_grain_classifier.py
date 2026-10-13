# HESPERIA — Area-math grain classifier tests (10 vs 12).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from core.projection.area_math_grain import (
    area_math_classifier_meta,
    area_math_grain,
    area_math_totals,
    classify_area_math_grain,
    project_macro_for_grain,
    ten_area_module_enabled,
)
from core.projection.default_twelve import area_name_at, project_default_twelve_macro
from core.projection.ten_area_module import TEN_AREA_COUNT, project_ten_area_macro
from core.topology.invariant_catalog import AREAS, CANONICAL_AREA_ORDER


def test_default_grain_is_twelve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_AREA_MATH_GRAIN", raising=False)
    monkeypatch.delenv("HESPERIA_TEN_AREA_MODULE", raising=False)
    assert AREAS == 12
    assert len(CANONICAL_AREA_ORDER) == 12
    assert classify_area_math_grain() == 12
    assert area_math_grain() == 12
    assert ten_area_module_enabled() is False
    assert area_name_at(10) == "CREATION"


def test_classifier_env_12_and_10(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_TEN_AREA_MODULE", raising=False)
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "12")
    assert classify_area_math_grain() == 12
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "10")
    assert classify_area_math_grain() == 10
    assert ten_area_module_enabled() is True


def test_legacy_ten_area_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_AREA_MATH_GRAIN", raising=False)
    monkeypatch.setenv("HESPERIA_TEN_AREA_MODULE", "1")
    assert classify_area_math_grain() == 10


def test_explicit_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "10")
    assert classify_area_math_grain(explicit=12) == 12
    assert classify_area_math_grain(explicit="ten") == 10


def test_project_macro_for_grain_lengths() -> None:
    area = [0.0] * 12
    area[10] = 2.0
    area[3] = 1.0
    m12, d12, g12 = project_macro_for_grain(area, grain=12)
    assert g12 == 12 and len(m12) == 12 and d12 == 10
    m10, d10, g10 = project_macro_for_grain(area, grain=10)
    assert g10 == 10 and len(m10) == TEN_AREA_COUNT == 10 and d10 == 3


def test_totals_and_meta() -> None:
    t12 = area_math_totals(12)
    assert t12["areas"] == 12 and t12["families"] == 288
    t10 = area_math_totals(10)
    assert t10["areas"] == 10 and t10["families"] == 240
    assert t10["geometry_areas_lock"] == 12
    meta = area_math_classifier_meta(grain=12)
    assert meta["area_math_grain"] == 12
    assert meta["switch_env"] == "HESPERIA_AREA_MATH_GRAIN"


def test_helpers_match_classifier() -> None:
    area = [0.1] * 12
    assert project_default_twelve_macro(area)[0] == project_macro_for_grain(area, grain=12)[0]
    assert project_ten_area_macro(area)[0] == project_macro_for_grain(area, grain=10)[0]


def test_invalid_grain_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "11")
    with pytest.raises(ValueError):
        classify_area_math_grain()
