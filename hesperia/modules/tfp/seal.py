# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""TFP module v1 seal hook (TFP-V1-09).

``HESPERIA_TFP_MODULE_SEALED``:
  - unset / 0 / false: no-op
  - 1 / true / yes / on: emit stderr warning when ``TFPModule.project`` runs
  - block: raise RuntimeError on ``project`` (fail-closed for sealed deployments)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _version_yaml_tfp_seal_requested(repo_root: Path) -> bool:
    path = repo_root / "VERSION.yaml"
    if not path.is_file():
        return False
    try:
        import yaml
    except ImportError:
        return False
    doc: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = doc.get("tfp_module_v1") or {}
    if not isinstance(block, dict):
        return False
    return bool(block.get("seal_requested"))


def tfp_module_seal_effective(*, repo_root: Path | None = None) -> str:
    """Return 'off', 'warn', or 'block'."""
    raw = os.environ.get("HESPERIA_TFP_MODULE_SEALED", "").strip().lower()
    if raw in ("block",):
        return "block"
    if raw in ("1", "true", "yes", "on"):
        return "warn"
    root = repo_root or Path(__file__).resolve().parents[3]
    if _version_yaml_tfp_seal_requested(root):
        return "warn"
    return "off"


def enforce_tfp_module_seal_on_project(*, repo_root: Path | None = None) -> None:
    mode = tfp_module_seal_effective(repo_root=repo_root)
    if mode == "off":
        return
    msg = (
        "TFP module v1 seal: project() invoked while seal is active "
        "(HESPERIA_TFP_MODULE_SEALED or VERSION.yaml tfp_module_v1.seal_requested). "
        "Policy: dict/calibration-only changes unless Grace reopened module work. "
        "See docs/governance/TFP_MODULE_V1_SEAL_CHECKLIST.md."
    )
    if mode == "block":
        raise RuntimeError(msg)
    print(f"WARNING: {msg}", file=sys.stderr)
