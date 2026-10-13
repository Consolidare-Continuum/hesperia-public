# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA provenance metadata.
Deterministic engine state for dossier traceability.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import timezone
from pathlib import Path
from typing import Any, Dict

SCHEMA_VERSION = "HSD_v1.0"
PIPELINE_VERSION = "L1-L9"


def _find_repo_root() -> Path:
    """Find repo root (directory containing .git or pyproject.toml)."""
    path = Path(__file__).resolve().parent
    for _ in range(6):
        if (path / ".git").exists() or (path / "pyproject.toml").exists():
            return path
        parent = path.parent
        if parent == path:
            break
        path = parent
    return Path(__file__).resolve().parents[2]


def _engine_version_from_pyproject(root: Path) -> str | None:
    """Read [project] version from pyproject.toml if present."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if m:
            return m.group(1).strip()
        m = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


def _engine_version_from_git(root: Path) -> str | None:
    """Return short git commit hash for root, or None."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return None


def get_engine_provenance() -> Dict[str, Any]:
    """
    Return provenance metadata for embedding in dossiers.
    Deterministic at call time: engine_version from pyproject.toml or git, UTC timestamp.
    """
    from datetime import datetime

    root = _find_repo_root()
    engine_version = _engine_version_from_pyproject(root) or _engine_version_from_git(root) or "unknown"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return {
        "engine_version": engine_version,
        "pipeline_version": PIPELINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generation_timestamp": timestamp,
        "python_version": python_version,
    }
