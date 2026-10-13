"""Dynamic module loader with optional aliases."""

from __future__ import annotations

import importlib
from typing import Any

from core.engine.module_aliases import MODULE_ALIASES


def resolve_module_path(path_or_alias: str) -> str:
    return MODULE_ALIASES.get(path_or_alias, path_or_alias)


def load_module(
    path_or_alias: str,
    *,
    matrix_pass: bool | None = None,
    skip_entitlement: bool = False,
) -> Any:
    """Load module create() after commercial entitlement gate (HESP-LIC)."""
    if not skip_entitlement:
        from hesperia.product.commercial_entitlement import assert_module_entitlement

        assert_module_entitlement(path_or_alias, matrix_pass=matrix_pass)
    module_path = resolve_module_path(path_or_alias)
    mod = importlib.import_module(module_path)
    create_fn = getattr(mod, "create", None)
    if not callable(create_fn):
        raise ValueError(f"module_create_missing:{module_path}")
    return create_fn()

