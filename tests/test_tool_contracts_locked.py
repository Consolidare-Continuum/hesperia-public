# HESPERIA — Freeze expectations for integrity CLI modules (API + allowlist bytes).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# When intentionally editing runtime/shipping/shipping_import_allowlist.yaml, update
# _SHIPPING_ALLOWLIST_SHA256 below (CI fails on silent expansion).

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SHIPPING_ALLOWLIST = _REPO / "runtime" / "shipping" / "shipping_import_allowlist.yaml"

# sha256 of exact file bytes (bump only with deliberate allowlist edits).
_SHIPPING_ALLOWLIST_SHA256 = (
    "af3093ec88b7fefd60e8807d350462b8c77085a7fc7a6c9576d35505e9a4b970"
)


def _load_tool(rel: str, name: str):
    p = _REPO / rel
    spec = importlib.util.spec_from_file_location(name, p)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_shipping_import_allowlist_bytes_locked() -> None:
    assert _SHIPPING_ALLOWLIST.is_file(), "shipping allowlist missing"
    digest = hashlib.sha256(_SHIPPING_ALLOWLIST.read_bytes()).hexdigest()
    assert digest == _SHIPPING_ALLOWLIST_SHA256, (
        f"allowlist bytes changed ({digest}); bump _SHIPPING_ALLOWLIST_SHA256 if deliberate"
    )


def test_validate_shipping_surface_defines_enforcement_helpers() -> None:
    v = _load_tool("tools/validate_shipping_surface.py", "validate_shipping_surface")
    assert callable(v.main)
    assert callable(v._load_allowlist)
    assert callable(v._collect_imports)
    assert callable(v._allowed_module)


def test_check_engine_projection_boundary_defines_enforcement_helpers() -> None:
    e = _load_tool("tools/check_engine_projection_boundary.py", "check_engine_projection_boundary")
    assert callable(e.main)
    assert callable(e._violations_for_file)
    assert callable(e._is_core_projection)
    assert e._is_core_projection("core.projection")
    assert e._is_core_projection("core.projection.foo")
    assert not e._is_core_projection("core.engine.projection")


def test_audit_shipping_allowlist_defines_collector() -> None:
    a = _load_tool("tools/audit_shipping_allowlist.py", "audit_shipping_allowlist")
    assert callable(a.main)
    assert callable(a._collect_modules_from_shipping)


def test_check_dead_weight_budget_parsers_present() -> None:
    d = _load_tool("tools/check_dead_weight_budget.py", "check_dead_weight_budget")
    assert callable(d.main)
    assert callable(d._parse_max)
    assert callable(d._parse_recorded)
    assert callable(d._parse_max_increase)
