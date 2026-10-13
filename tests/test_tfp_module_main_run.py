from __future__ import annotations

from pathlib import Path

from core.engine.pipeline_runner import run_pipeline


def test_tfp_module_is_executed_in_main_pipeline(monkeypatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("HESPERIA_CALIB_DICT_VERSION", "v0_6_0_clr_v052_1")

    text = (
        "В терапии проявляются перенос и контрперенос, "
        "нарастает агрессия и поляризация объектных отношений."
    )
    dossier = run_pipeline(text, config_path=repo / "assets" / "config" / "pipeline.yaml")

    run_manifest = dict((dossier.get("meta") or {}).get("run_manifest") or {})
    loaded = list(run_manifest.get("modules_loaded") or [])
    assert "tfp.v1" in loaded

    trace = list(dossier.get("trace") or [])
    tfp_trace = [row for row in trace if str(row.get("module")) == "tfp.v1" and str(row.get("phase")) == "project"]
    assert tfp_trace, "expected tfp.v1 project phase to execute"

    signals = dict(dossier.get("signals") or {})
    assert isinstance(signals.get("tfp_conflicts"), list)

