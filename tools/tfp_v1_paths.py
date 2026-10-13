# HESPERIA — Canonical paths for module `tfp_v1` data tree (TFP-DATA-T04+).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import os
from pathlib import Path

_ENV_ROOT = "HESPERIA_TFP_MODULE_DATA_ROOT"


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def tfp_v1_root(repo: Path | None = None) -> Path:
    r = repo or repo_root_from_here()
    env = os.environ.get(_ENV_ROOT, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (r / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1").resolve()


def default_corpus_ru(repo: Path | None = None) -> Path:
    return tfp_v1_root(repo) / "corpus" / "original" / "ru"


def default_corpus_en(repo: Path | None = None) -> Path:
    return tfp_v1_root(repo) / "corpus" / "original" / "en"


def default_corpus_sessions(repo: Path | None = None) -> Path:
    """Clinical session Markdown from noone ingest (DD-MM-YYYY.md); was legacy `_noone_local/sessions/` under `research/`."""
    return tfp_v1_root(repo) / "corpus" / "sessions"


def default_corpus_ru_str(repo: Path | None = None) -> str:
    return str(default_corpus_ru(repo))


def default_corpus_en_str(repo: Path | None = None) -> str:
    return str(default_corpus_en(repo))


def default_corpus_sessions_str(repo: Path | None = None) -> str:
    return str(default_corpus_sessions(repo))
