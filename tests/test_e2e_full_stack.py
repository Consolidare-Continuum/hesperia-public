# HESPERIA — run_e2e_full_stack orchestration (mocked smoke).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_run_e2e_full_stack_writes_manifest_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid full pipeline cost; verify wiring + manifest shape."""

    def fake_run_all(out_dir=None, text=None):
        d = Path(out_dir)
        p = d / "run_output_e2e_sentence.json"
        p.write_text('{"mock": true}', encoding="utf-8")
        return {"run_output_e2e_sentence.json": p}

    def fake_physics(r: Path):
        return 0, ""

    def fake_product(out_dir: Path, text: str) -> Path:
        p = out_dir / "run_output_e2e_full_product_surface.json"
        p.write_text('{"mock_product": true}', encoding="utf-8")
        return p

    monkeypatch.setattr("runtime.pipeline.run_e2e_all.run_all", fake_run_all)
    monkeypatch.setattr("runtime.pipeline.run_e2e_full_stack._run_physics_validation", fake_physics)
    monkeypatch.setattr("runtime.pipeline.run_e2e_full_stack._write_product_surface", fake_product)
    monkeypatch.setattr(
        "hesperia.system.system_seal.run_system_seal_gate",
        lambda *a, **k: {
            "status": "PASS",
            "checks": {"pipeline": True},
            "notes": {"pipeline": "ok"},
        },
    )

    from runtime.pipeline.run_e2e_full_stack import run_e2e_full_stack

    m = run_e2e_full_stack(
        tmp_path,
        text="short text",
        calibration_batch_n=2,
        dynamics=False,
        run_physics=True,
        run_seal=True,
    )

    assert m.get("ok") is True
    assert m.get("system_seal_skip_physics_subprocess") is True
    mf = tmp_path / "run_output_e2e_full_stack_manifest.json"
    assert mf.is_file()
    loaded = json.loads(mf.read_text(encoding="utf-8"))
    assert loaded.get("run") == "e2e_full_stack"
    assert loaded.get("artifact_count") == 2
    basenames = {a["basename"] for a in loaded.get("artifacts", [])}
    assert "run_output_e2e_sentence.json" in basenames
    assert "run_output_e2e_full_product_surface.json" in basenames
    for a in loaded.get("artifacts", []):
        assert "sha256" in a and len(a["sha256"]) == 64
    assert loaded.get("out_dir")
