# HESPERIA — Analyze profile (default vs TFP) tests.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from runtime.shipping.analyze_profile import (
    analyze_profile_meta,
    apply_analyze_profile_defaults,
    resolve_analyze_profile,
)


def test_resolve_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_ANALYZE_PROFILE", raising=False)
    assert resolve_analyze_profile() == "default"


def test_resolve_tfp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_ANALYZE_PROFILE", "tfp")
    assert resolve_analyze_profile() == "tfp"


def test_tfp_defaults_set_grain_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_ANALYZE_PROFILE", "tfp")
    monkeypatch.delenv("HESPERIA_AREA_MATH_GRAIN", raising=False)
    monkeypatch.delenv("HESPERIA_CALIB_DICT_VERSION", raising=False)
    monkeypatch.delenv("HESPERIA_TEN_AREA_MODULE", raising=False)
    monkeypatch.delenv("HESPERIA_DLCR_STRUCTURAL", raising=False)
    monkeypatch.delenv("HESPERIA_TFP_DICT_MODE", raising=False)
    import os

    p = apply_analyze_profile_defaults()
    assert p == "tfp"
    assert os.environ.get("HESPERIA_AREA_MATH_GRAIN") == "10"
    # MVP: full TFP dict stack — do not auto-pin tiny calib wave.
    assert not (os.environ.get("HESPERIA_CALIB_DICT_VERSION") or "").strip()
    assert os.environ.get("HESPERIA_DLCR_STRUCTURAL") == "1"
    assert os.environ.get("HESPERIA_TFP_DICT_MODE") == "full_stack"
    meta = analyze_profile_meta()
    assert meta["pack_areas"] == 10
    assert meta["pack_families"] == 240
    assert meta["geometry_areas_lock"] == 12
    assert meta["dict_mode"] == "full_stack"
    assert meta["structure_map"]["area"].endswith("area_structure_tfp.yaml")


def test_tfp_defaults_respect_explicit_grain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_ANALYZE_PROFILE", "tfp")
    monkeypatch.setenv("HESPERIA_AREA_MATH_GRAIN", "12")
    apply_analyze_profile_defaults()
    assert __import__("os").environ.get("HESPERIA_AREA_MATH_GRAIN") == "12"
