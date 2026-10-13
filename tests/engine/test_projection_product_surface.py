# HESPERIA — Task 4 projection gate + capability tests.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from core.engine.projection import enforce_public_schema, project_to_public
from core.engine.projection.schema_enforcer import enforce_public_schema as enforce2


def test_project_to_public_strips_forbidden_keys_nested() -> None:
    raw = {
        "run": "test",
        "L1": {"total_tokens": 3},
        "internal_adjacency_hint": {"x": 1},
    }
    out = project_to_public(raw, validate_schema=True)
    assert "internal_adjacency_hint" not in out


def test_enforce_public_schema_rejects_adjacency_key() -> None:
    with pytest.raises(ValueError, match="public_schema_violation"):
        enforce_public_schema({"my_adjacency": []})


def test_schema_enforcer_facade_matches() -> None:
    with pytest.raises(ValueError):
        enforce2({"topology_index": 1})


def test_expose_triz_respects_product_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    from hesperia.system import capabilities as cap

    cap.load_capabilities.cache_clear()
    monkeypatch.setenv("HESPERIA_PRODUCT_SURFACE", "1")
    monkeypatch.delenv("HESPERIA_EXPOSE_TRIZ", raising=False)
    assert cap.expose_triz_api() is False

    cap.load_capabilities.cache_clear()
    monkeypatch.setenv("HESPERIA_PRODUCT_SURFACE", "0")
    monkeypatch.setenv("HESPERIA_EXPOSE_TRIZ", "1")
    assert cap.expose_triz_api() is True
    cap.load_capabilities.cache_clear()
    monkeypatch.delenv("HESPERIA_PRODUCT_SURFACE", raising=False)
    monkeypatch.delenv("HESPERIA_EXPOSE_TRIZ", raising=False)


def test_gpt_app_has_no_triz_routes_when_product_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    from hesperia.system import capabilities as cap

    cap.load_capabilities.cache_clear()
    monkeypatch.setenv("HESPERIA_PRODUCT_SURFACE", "1")
    monkeypatch.delenv("HESPERIA_EXPOSE_TRIZ", raising=False)

    import importlib

    import runtime.api.main as gpt_main

    importlib.reload(gpt_main)
    paths = [getattr(r, "path", str(r)) for r in gpt_main.app.routes]
    assert "/analysis/triz" not in paths
    assert any("/hesperia/batch" in p for p in paths)
    cap.load_capabilities.cache_clear()
    monkeypatch.delenv("HESPERIA_PRODUCT_SURFACE", raising=False)
