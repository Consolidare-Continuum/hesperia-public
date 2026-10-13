# HESPERIA — RAD. DLCR policy packs (Ethan PO-13, PO-14, PO-30).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_POLICY_CACHE: dict[str, dict[str, Any]] = {}


def _safe_load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_dlcr_policy(repo_root: Path) -> dict[str, Any]:
    """
    Load merged policy: ``assets/data/engine_dynamics_v060/dlcr_policy.yaml``
    overridden by active domain pack (``domain_packs.yaml``).
    """
    cache_key = str(repo_root.resolve())
    if cache_key in _POLICY_CACHE:
        return dict(_POLICY_CACHE[cache_key])

    base = repo_root / "assets" / "data" / "engine_dynamics_v060"
    merged: dict[str, Any] = {}
    merged.update(_safe_load_yaml(base / "dlcr_policy.yaml"))

    packs_path = base / "domain_packs.yaml"
    pack_data = _safe_load_yaml(packs_path)
    active = (
        os.environ.get("HESPERIA_DLCR_DOMAIN_PACK", "").strip()
        or str(pack_data.get("active_pack") or "default")
    )
    packs = pack_data.get("packs") if isinstance(pack_data.get("packs"), dict) else {}
    if isinstance(packs, dict) and active in packs and isinstance(packs[active], dict):
        merged.update(packs[active])

    _POLICY_CACHE[cache_key] = dict(merged)
    return dict(merged)


def clear_dlcr_policy_cache() -> None:
    _POLICY_CACHE.clear()
