# HESPERIA — physics validation fixtures.

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def validation_thresholds(repo_root: Path) -> dict:
    p = repo_root / "assets" / "specs" / "validation_thresholds.json"
    return json.loads(p.read_text(encoding="utf-8"))
