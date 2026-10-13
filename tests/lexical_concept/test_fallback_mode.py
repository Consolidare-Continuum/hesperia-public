from __future__ import annotations

from runtime.services.dlcr_service import build_degradation_flags, fallback_enabled


def test_fallback_default_off(monkeypatch) -> None:
    monkeypatch.delenv("HESPERIA_DLCR_FALLBACK", raising=False)
    assert fallback_enabled() is False


def test_fallback_on(monkeypatch) -> None:
    monkeypatch.setenv("HESPERIA_DLCR_FALLBACK", "1")
    assert fallback_enabled() is True


def test_degradation_flags_include_fallback_and_missing_anchors() -> None:
    flags = build_degradation_flags(used_fallback=True, missing_anchor_count=2)
    assert "degraded:fallback_word_to_family" in flags
    assert "degraded:missing_anchor_count=2" in flags

