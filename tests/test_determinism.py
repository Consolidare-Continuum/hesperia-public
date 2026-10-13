from __future__ import annotations

from pathlib import Path

from core.engine.pipeline_runner import run_pipeline


def test_phase_hashes_stable_across_repeated_runs() -> None:
    config = Path(__file__).resolve().parents[1] / "assets" / "config" / "pipeline.yaml"
    hashes = []
    for _ in range(10):
        out = run_pipeline("determinism stability sample text", config_path=config)
        meta = out.get("meta") or {}
        hashes.append((meta.get("hash_preprocess"), meta.get("hash_project"), meta.get("hash_postprocess")))
    assert len(set(hashes)) == 1

