# HESPERIA — Load OpenAI API key for shipping / tools.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Resolve ``OPENAI_API_KEY`` without re-hunting.

Operator decision 2026-08-10: durable SoT is
``Consolidare-Continuum/hesperia`` tip file ``openai_api_key.txt``
(local clone ``/data/consolidare-continuum/hesperia/openai_api_key.txt``).
Env and ``.env.openai`` still win when already set.
"""

from __future__ import annotations

import os
from pathlib import Path

# Operator-endorsed durable home (CC prod-of-record clone on cluster).
_CC_KEY_FILE = Path("/data/consolidare-continuum/hesperia/openai_api_key.txt")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_key_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    # Allow either bare key or KEY=value line.
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("OPENAI_API_KEY="):
            s = s.split("=", 1)[1].strip().strip('"').strip("'")
        if s.startswith("sk-") and len(s) > 20:
            return s
    return None


def ensure_openai_api_key(*, force_refresh_from_cc: bool = False) -> str | None:
    """
    Ensure ``OPENAI_API_KEY`` is in ``os.environ``.

    Order:
    1. Existing env (unless ``force_refresh_from_cc``)
    2. Repo ``.env.openai`` / ``.env``
    3. Repo ``openai_api_key.txt`` (if present on this tree)
    4. CC tip ``/data/consolidare-continuum/hesperia/openai_api_key.txt``
    """
    if not force_refresh_from_cc:
        existing = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if existing.startswith("sk-"):
            return existing

    repo = _repo_root()
    candidates = [
        repo / ".env.openai",
        repo / ".env",
        repo / "openai_api_key.txt",
        _CC_KEY_FILE,
    ]
    for path in candidates:
        if path.name in (".env.openai", ".env"):
            if not path.is_file():
                continue
            try:
                for raw in path.read_text(encoding="utf-8").splitlines():
                    line = raw.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val.startswith("sk-"):
                            os.environ["OPENAI_API_KEY"] = val
                            return val
            except OSError:
                continue
            continue
        key = _read_key_file(path)
        if key:
            os.environ["OPENAI_API_KEY"] = key
            return key
    return (os.environ.get("OPENAI_API_KEY") or "").strip() or None
