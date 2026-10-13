from __future__ import annotations

import importlib


def test_compatibility_shims_remain_importable() -> None:
    assert importlib.import_module("hesperia.engine.kme") is not None
    assert importlib.import_module("hesperia.engine.kme.clinical_bridge") is not None


def test_canonical_core_packages_importable() -> None:
    assert importlib.import_module("core.domain") is not None
    assert importlib.import_module("core.runtime") is not None
