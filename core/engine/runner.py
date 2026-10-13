"""Pure orchestration runner for modular engine execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.engine.core import HesperiaEngine


def run_orchestration(
    text: str,
    *,
    repo_root: Path | None = None,
    config_path: Path | None = None,
    signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    cfg = config_path or (root / "assets" / "config" / "pipeline.yaml")
    engine = HesperiaEngine()
    engine.load_from_config(cfg)
    return engine.run(text, signals=signals)

