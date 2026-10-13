# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path

from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

_REPO = Path(__file__).resolve().parents[1]
_V060 = _REPO / "assets/data/engine_dynamics_v060"
_CAL_A = _REPO / "assets/calibration/dicts/v0_tfp_cal_wave_002/dict_a.jsonl"


def test_dlcr_with_calibrated_dict_a_layer_fires_concepts() -> None:
    assert _CAL_A.is_file(), "freeze v0_tfp_cal_wave_002 first"
    text = (
        "объектные отношения и перенос у пациента с пограничным расстройством личности."
    )
    da_paths = [
        _V060 / "dict_a/dict_a_seed.jsonl",
        _V060 / "dict_a/dict_a_tfp.jsonl",
        _V060 / "dict_a/dict_a_tfp_ru_core.jsonl",
        _V060 / "dict_a/dict_a_tfp_ru_variants.jsonl",
        _V060 / "dict_a/dict_a_tfp_ru_speech.jsonl",
        _V060 / "dict_a/dict_a_tfp_ru_negative.jsonl",
        _V060 / "dict_a/dict_a_tfp_ru_aligned.jsonl",
        _CAL_A,
    ]
    db_paths = [
        _V060 / "dict_b/dict_b_seed.jsonl",
        _V060 / "dict_b/dict_b_tfp_ru_v060.jsonl",
        _V060 / "dict_b/dict_b_tfp.jsonl",
    ]
    anch = _V060 / "anchors/concept_hex_anchors_tfp.json"
    out = run_dlcr_pipeline(
        text,
        repo_root=_REPO,
        dict_a_paths=da_paths,
        dict_b_paths=db_paths,
        anchors_path=anch,
        mode="clinical_speech",
    )
    assert int(out.get("lexical_hits_accepted") or 0) >= 1
    cw = out.get("concept_weights") or {}
    assert cw, "expected at least one resolved concept"
