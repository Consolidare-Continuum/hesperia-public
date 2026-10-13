# HESPERIA — Config loader
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "clinical_config.yaml"
_CACHE: dict[str, Any] = {}


def load_clinical_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load clinical_config.yaml (thresholds, weights, window sizes)."""
    global _CACHE
    p = Path(path) if path is not None else _CONFIG_PATH
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _CACHE.update(data)
    return dict(data)


def get_clinical_config(path: Path | str | None = None) -> dict[str, Any]:
    """Return config (load if not cached)."""
    if not _CACHE and (path is None or Path(path).exists()):
        load_clinical_config(path)
    return dict(_CACHE)
