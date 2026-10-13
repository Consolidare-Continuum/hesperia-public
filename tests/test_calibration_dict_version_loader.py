from __future__ import annotations

from pathlib import Path

from hesperia.engine.calibration_dict_paths import calibration_manifest, resolve_dict_file, resolve_metrics_file
from core.engine.lexical_concept.pipeline import run_dlcr_pipeline


def test_versioned_calibration_dict_paths_resolve(monkeypatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("HESPERIA_CALIB_DICT_VERSION", "v0_6_0_clr_v052_5")

    dict_a = resolve_dict_file(repo, "dict_a.jsonl")
    dict_b = resolve_dict_file(repo, "dict_b.jsonl")
    links = resolve_dict_file(repo, "links.jsonl")

    assert dict_a is not None and dict_a.is_file()
    assert dict_b is not None and dict_b.is_file()
    assert links is not None and links.is_file()

    manifest = calibration_manifest(repo)
    assert manifest["enabled"] is True
    assert manifest["version"] == "v0_6_0_clr_v052_5"


def test_metrics_file_falls_back_to_baseline_pack() -> None:
    repo = Path(__file__).resolve().parents[1]
    metrics = resolve_metrics_file(repo, explicit_version="v0_6_0_clr_v052_5")

    assert metrics is not None and metrics.name == "metrics_baseline_v052_2.json"

    manifest = calibration_manifest(repo, explicit_version="v0_6_0_clr_v052_5")
    assert manifest["metrics_exists"] is True
    assert manifest["metrics_filename"] == "metrics_baseline_v052_2.json"


def test_run_dlcr_uses_versioned_assets_and_fires(monkeypatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("HESPERIA_CALIB_DICT_VERSION", "v0_6_0_clr_v052_5")

    text = "объектные отношения, перенос и аффект в клинической динамике пациента."
    out = run_dlcr_pipeline(text, repo_root=repo, mode="clinical_speech")

    assert int(out.get("lexical_hits_accepted") or 0) >= 1
    assert bool(out.get("concept_weights"))
    assert bool(out.get("family_activation"))
