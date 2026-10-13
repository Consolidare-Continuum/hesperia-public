# HESPERIA — Default twelve vs optional ten-area helpers (compat tests).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from core.projection.area_math_grain import classify_area_math_grain, ten_area_module_enabled
from core.projection.default_twelve import area_name_at, project_default_twelve_macro
from core.projection.ten_area_module import TEN_AREA_COUNT, project_ten_area_macro
from core.topology.invariant_catalog import AREAS, CANONICAL_AREA_ORDER


def test_default_grain_is_twelve() -> None:
    assert AREAS == 12
    assert len(CANONICAL_AREA_ORDER) == 12
    assert CANONICAL_AREA_ORDER[10] == "CREATION"
    assert CANONICAL_AREA_ORDER[11] == "DECEIT"
    assert area_name_at(0) == "GOOD"


def test_default_twelve_macro_includes_creation_deceit() -> None:
    area = [0.0] * 12
    area[10] = 2.0
    area[11] = 1.0
    macro, dom = project_default_twelve_macro(area)
    assert len(macro) == 12
    assert abs(sum(macro) - 1.0) < 1e-9
    assert dom == 10
    assert macro[10] > macro[11] > 0


def test_ten_area_macro_drops_10_11() -> None:
    area = [0.0] * 12
    area[3] = 1.0
    area[10] = 9.0
    macro, dom = project_ten_area_macro(area)
    assert len(macro) == TEN_AREA_COUNT == 10
    assert abs(sum(macro) - 1.0) < 1e-9
    assert dom == 3


def test_ten_area_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_AREA_MATH_GRAIN", raising=False)
    monkeypatch.delenv("HESPERIA_TEN_AREA_MODULE", raising=False)
    assert ten_area_module_enabled() is False
    assert classify_area_math_grain() == 12
    monkeypatch.setenv("HESPERIA_TEN_AREA_MODULE", "1")
    assert ten_area_module_enabled() is True
    assert classify_area_math_grain() == 10
