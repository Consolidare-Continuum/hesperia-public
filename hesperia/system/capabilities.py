# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Load ``capabilities.yaml`` and resolve product vs dev exposure (env overrides)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _yaml_load(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return _default_caps()
    if not path.is_file():
        return _default_caps()
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw if isinstance(raw, dict) else _default_caps()


def _default_caps() -> dict[str, Any]:
    return {
        "public": {"analyze": True, "compare": True, "batch": True},
        "internal": {"dynamics": True, "triz": True, "calibration": True},
        "exposed": {"dynamics": False, "triz": False, "calibration": False, "version_endpoint": False},
    }


@lru_cache(maxsize=1)
def load_capabilities() -> dict[str, Any]:
    """Return merged capability dict (cached)."""
    path = Path(__file__).resolve().parent / "capabilities.yaml"
    return _yaml_load(path)


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def is_product_surface_strict() -> bool:
    """
    When True (default), GPT Actions API must not register TRIZ/debug routes;
    shipping API should hide optional endpoints per capabilities.
    """
    return _env_bool("HESPERIA_PRODUCT_SURFACE", True)


def expose_triz_api() -> bool:
    """TRIZ HTTP surface allowed only when product surface is off and yaml/env allow."""
    if is_product_surface_strict():
        return _env_bool("HESPERIA_EXPOSE_TRIZ", False)
    caps = load_capabilities()
    exposed = caps.get("exposed") if isinstance(caps.get("exposed"), dict) else {}
    default = bool(exposed.get("triz", False))
    return _env_bool("HESPERIA_EXPOSE_TRIZ", default)


def expose_version_endpoint() -> bool:
    """GET /version on shipping API (non-product nicety)."""
    if is_product_surface_strict():
        return _env_bool("HESPERIA_EXPOSE_VERSION", False)
    caps = load_capabilities()
    exposed = caps.get("exposed") if isinstance(caps.get("exposed"), dict) else {}
    default = bool(exposed.get("version_endpoint", False))
    return _env_bool("HESPERIA_EXPOSE_VERSION", default)


def public_capability(name: str) -> bool:
    """Named public command (analyze | compare | batch | interpret)."""
    caps = load_capabilities()
    pub = caps.get("public") if isinstance(caps.get("public"), dict) else {}
    return bool(pub.get(name, True))


def internal_dlcr_enabled() -> bool:
    """YAML internal.dlcr — allows DLCR sidecar when env also set."""
    caps = load_capabilities()
    internal = caps.get("internal") if isinstance(caps.get("internal"), dict) else {}
    return bool(internal.get("dlcr", False))


def structural_dlcr_env_requested() -> bool:
    return _env_bool("HESPERIA_DLCR_STRUCTURAL", False)


def structural_dlcr_allowed() -> bool:
    """
    DLCR attachment on structural analysis: env + capability.

    Strict product surface: requires ``internal.dlcr: true`` in capabilities.yaml
    (default false) even if env is set.
    """
    if not structural_dlcr_env_requested():
        return False
    if is_product_surface_strict() and not internal_dlcr_enabled():
        return False
    return True
