# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
E2E flow tests: run all Hesperia entrypoints and assert output exists (no calibration).
Covers: analyze (sentence), L1–L9, R1–R4, sphere_math, domain_metrics, session KME, TRIZ complete,
session topology, TFP smoke batch + stages, and unified run_e2e_all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

# Repo root first on path (see tests/conftest.py). Do not add a `tests/runtime/` package — it shadows `runtime/`.
_REPO = Path(__file__).resolve().parents[1]
_rs = str(_REPO)
if _rs in sys.path:
    sys.path.remove(_rs)
sys.path.insert(0, _rs)

_EXPECTED_VERSION = str(
    (yaml.safe_load((_REPO / "VERSION.yaml").read_text(encoding="utf-8")) or {}).get("system_version")
)


def test_e2e_analyze_sentence_output_exists() -> None:
    """Analyze pipeline returns result + extended with expected keys; output exists."""
    from runtime.pipeline.analyze import analyze

    text = "Justice and fairness support social order."
    minimal, extended = analyze(
        text,
        r1_r4=True,
        r1_r4_book_id="e2e_test",
        r1_r4_levels=["R1", "R2", "R3", "R4"],
    )
    assert minimal is not None
    assert isinstance(minimal, dict)
    for key in ("dominant_area", "dominant_family", "governance", "loopability", "tension_energy", "obstacle_score"):
        assert key in minimal, f"result missing {key}"
    assert extended is not None
    assert isinstance(extended, dict)
    assert "r1_r4" in extended or "family_vector" in extended or "dict_b" in extended


def test_e2e_l1_l9_output_exists() -> None:
    """L1–L9 pipeline returns all layers and diagnostics; output exists."""
    from runtime.pipeline.run_l1_through_l9 import run_pipeline_for_text

    text = "justice lie fairness truth good order harm freedom"
    assets = _REPO / "assets" / "lexicon" / "curated"
    out = run_pipeline_for_text(text, assets_root=assets)
    assert out is not None
    assert "run" in out and out["run"] == "L1_through_L9"
    for lid in range(1, 10):
        key = f"L{lid}"
        assert key in out, f"Layer {key} missing"
        assert isinstance(out[key], dict)
    assert "diagnostics" in out
    assert "L7" in out and "DECISION_STATUS_CODE" in out["L7"]
    assert "L9" in out and "BRAND_WORD_TRUST" in out["L9"]


def test_e2e_r1_r4_output_exists() -> None:
    """R1–R4 pipeline returns units and book_profile; output exists."""
    from runtime.pipeline.r1_r4_pipeline import run_full_pipeline_to_json

    text = "Justice and fairness support social order. Harm and conflict reduce trust."
    result = run_full_pipeline_to_json(text, book_id="e2e_test", levels=["R1", "R2", "R3", "R4"])
    assert result is not None
    assert "units" in result
    assert "book_profile" in result
    assert isinstance(result["units"], list)
    assert isinstance(result["book_profile"], dict)
    assert result["book_profile"].get("book_id") == "e2e_test"


def test_e2e_sphere_math_values_output_exists() -> None:
    """Sphere math values flow produces JSON with L1–L9 keys; output exists."""
    from runtime.pipeline.run_e2e_all import run_e2e_sphere_math_values

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out_path = Path(d) / "sphere_math_values.json"
        run_e2e_sphere_math_values(out_path, "justice fairness order")
        assert out_path.exists()
        data = json.loads(out_path.read_text(encoding="utf-8"))
        for key in ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"):
            assert key in data, f"sphere_math_values missing {key}"
        assert data.get("system_version") == _EXPECTED_VERSION
        assert data.get("build_id")


def test_e2e_sphere_math_100_output_exists() -> None:
    """Sphere math 100 (limited) produces list of results; output exists."""
    from runtime.pipeline.run_e2e_all import run_e2e_sphere_math_100

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out_path = Path(d) / "sphere_math_100.json"
        run_e2e_sphere_math_100(out_path, limit=2)
        assert out_path.exists()
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data.get("system_version") == _EXPECTED_VERSION
        payload = data.get("payload")
        assert isinstance(payload, list)
        assert len(payload) >= 1
        for item in payload:
            assert "L1" in item or "text_preview" in item


@pytest.mark.tfp
def test_e2e_run_e2e_all_produces_all_artifacts() -> None:
    """Unified run_e2e_all with field dynamics: 19 base + field_dynamics; second run bumps state_t."""
    import os
    from runtime.pipeline.run_e2e_all import (
        E2E_OUTPUTS_WITH_FIELD_DYNAMICS,
        run_all,
    )

    import tempfile

    old_fd = os.environ.get("HESPERIA_FIELD_DYNAMICS")
    old_triz = os.environ.get("HESPERIA_FIELD_DYNAMICS_TRIZ")
    old_cal = os.environ.get("HESPERIA_E2E_CALIBRATION_BATCH_N")
    try:
        os.environ["HESPERIA_FIELD_DYNAMICS"] = "1"
        os.environ["HESPERIA_FIELD_DYNAMICS_TRIZ"] = "0"
        os.environ["HESPERIA_E2E_CALIBRATION_BATCH_N"] = "5"

        def _assert_all(written: dict) -> None:
            assert len(written) == len(E2E_OUTPUTS_WITH_FIELD_DYNAMICS)
            for name in E2E_OUTPUTS_WITH_FIELD_DYNAMICS:
                assert name in written
                path = written[name]
                assert path.exists(), f"E2E output missing: {name}"
                content = path.read_text(encoding="utf-8")
                assert len(content) > 0
                if path.suffix == ".json":
                    json.loads(content)

        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            written = run_all(out_dir=out_dir, text="justice fairness order")
            _assert_all(written)
            summ = json.loads(
                written["run_output_e2e_calibration_100_summary.json"].read_text(encoding="utf-8")
            )
            assert summ.get("system_version") == _EXPECTED_VERSION
            assert summ.get("sentence_count") == 5
            assert summ.get("run") == "e2e_calibration_batch_summary"
            fd_path = written[E2E_OUTPUTS_WITH_FIELD_DYNAMICS[-1]]
            fd = json.loads(fd_path.read_text(encoding="utf-8"))
            assert fd.get("HESPERIA_FIELD_DYNAMICS") is True
            assert fd.get("state_t") == 1
            assert len(fd.get("area_state") or []) == 12
            assert fd.get("triz_contradiction_meta", {}).get("triz_skipped") is True
            assert "semantic_field_v1" in fd

            sf = json.loads(written["run_output_e2e_semantic_field.json"].read_text(encoding="utf-8"))
            assert sf.get("system_version") == _EXPECTED_VERSION
            assert sf.get("pipeline_version") == "e2e_v2"
            assert sf.get("matrices_provenance") == "ontology"
            cal = json.loads(written["run_output_e2e_field_calibration.json"].read_text(encoding="utf-8"))
            assert cal.get("schema") == "hspr_field_calibration_v1"
            assert cal.get("best") is not None

            written2 = run_all(out_dir=out_dir, text="harm conflict trust")
            _assert_all(written2)
            fd2 = json.loads(written2[E2E_OUTPUTS_WITH_FIELD_DYNAMICS[-1]].read_text(encoding="utf-8"))
            assert fd2.get("state_t") == 2
    finally:
        if old_fd is None:
            os.environ.pop("HESPERIA_FIELD_DYNAMICS", None)
        else:
            os.environ["HESPERIA_FIELD_DYNAMICS"] = old_fd
        if old_triz is None:
            os.environ.pop("HESPERIA_FIELD_DYNAMICS_TRIZ", None)
        else:
            os.environ["HESPERIA_FIELD_DYNAMICS_TRIZ"] = old_triz
        if old_cal is None:
            os.environ.pop("HESPERIA_E2E_CALIBRATION_BATCH_N", None)
        else:
            os.environ["HESPERIA_E2E_CALIBRATION_BATCH_N"] = old_cal


@pytest.mark.tfp
def test_e2e_run_e2e_all_optional_dlcr_artifact() -> None:
    """With HESPERIA_E2E_DLCR=1, run_all emits run_output_e2e_dlcr.json (Ethan INT-015)."""
    import os
    from runtime.pipeline.run_e2e_all import (
        E2E_OUTPUT_DLCR,
        E2E_OUTPUTS_WITH_FIELD_DYNAMICS_AND_DLCR,
        run_all,
    )

    import tempfile

    old_fd = os.environ.get("HESPERIA_FIELD_DYNAMICS")
    old_triz = os.environ.get("HESPERIA_FIELD_DYNAMICS_TRIZ")
    old_cal = os.environ.get("HESPERIA_E2E_CALIBRATION_BATCH_N")
    old_dlcr = os.environ.get("HESPERIA_E2E_DLCR")
    try:
        os.environ["HESPERIA_FIELD_DYNAMICS"] = "1"
        os.environ["HESPERIA_FIELD_DYNAMICS_TRIZ"] = "0"
        os.environ["HESPERIA_E2E_CALIBRATION_BATCH_N"] = "5"
        os.environ["HESPERIA_E2E_DLCR"] = "1"

        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            written = run_all(out_dir=out_dir, text="justice fairness order truth")
            assert len(written) == len(E2E_OUTPUTS_WITH_FIELD_DYNAMICS_AND_DLCR)
            assert E2E_OUTPUT_DLCR in written
            dlcr_path = written[E2E_OUTPUT_DLCR]
            assert dlcr_path.exists()
            data = json.loads(dlcr_path.read_text(encoding="utf-8"))
            assert data.get("run") == "e2e_dlcr"
            assert "lexical_hits_accepted" in data
            assert data.get("system_version") == _EXPECTED_VERSION
    finally:
        for key, old in (
            ("HESPERIA_FIELD_DYNAMICS", old_fd),
            ("HESPERIA_FIELD_DYNAMICS_TRIZ", old_triz),
            ("HESPERIA_E2E_CALIBRATION_BATCH_N", old_cal),
            ("HESPERIA_E2E_DLCR", old_dlcr),
        ):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def test_e2e_session_kme_and_triz_artifacts_shape() -> None:
    """Session engine stages produce report or triz_complete (or _error), never empty file."""
    from runtime.pipeline.run_e2e_all import run_e2e_session_kme, run_e2e_triz_complete, run_e2e_session_topology

    text = "Терапевт интерпретирует перенос и границы сессии."
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        sk = base / "session_kme.json"
        run_e2e_session_kme(sk, text)
        data = json.loads(sk.read_text(encoding="utf-8"))
        assert "report" in data or "_error" in data
        tc = base / "triz.json"
        run_e2e_triz_complete(tc, text)
        tdata = json.loads(tc.read_text(encoding="utf-8"))
        assert "triz_complete" in tdata or "_error" in tdata
        st = base / "topo.json"
        run_e2e_session_topology(st, text)
        sdata = json.loads(st.read_text(encoding="utf-8"))
        assert "session_topology" in sdata or "_error" in sdata


def test_e2e_capability_matrix_wires_blocks() -> None:
    """Capability matrix artifact lists cross-stack blocks; most succeed without _error."""
    from runtime.pipeline.run_e2e_all import run_e2e_capability_matrix

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cap.json"
        run_e2e_capability_matrix(p, "justice fairness order harm crisis")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("run") == "e2e_capability_matrix"
        blocks = data.get("blocks") or {}
        assert len(blocks) >= 23
        for key in (
            "structural_L1_L2",
            "shipping_compare",
            "interpret_session",
            "dlcr_pipeline",
            "run_triz_analysis_core",
            "propagate_activation",
            "kme_run_document_and_corpus",
            "batch_runner_dossiers",
            "mvp_acceptance",
            "experiment_runner",
        ):
            assert key in blocks
            assert "_error" not in blocks[key], f"{key}: {blocks[key]}"
        kme = blocks["kme_run_document_and_corpus"]
        assert kme["run_document"]["primitives_n"] == 6
        assert kme["run_corpus"]["report_count"] == 2
        assert blocks["batch_runner_dossiers"]["dossiers_written"] == 2
        assert blocks["mvp_acceptance"]["passed"] is True
        assert blocks["experiment_runner"]["sessions"] == 2
        rm = blocks.get("reading_multiscale") or {}
        assert "_skipped" in rm or "_error" not in rm


@pytest.mark.tfp
def test_e2e_tfp_smoke_artifact_shape() -> None:
    """TFP E2E artifact: structural batch + tfp_stage per session + speaker-aware smoke."""
    from hesperia.tfp import TFP_STAGES
    from runtime.pipeline.run_e2e_all import run_e2e_tfp_smoke

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "tfp_smoke.json"
        run_e2e_tfp_smoke(p)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("run") == "e2e_tfp_smoke"
        assert data.get("tfp_stages_enum") == list(TFP_STAGES)
        assert isinstance(data.get("structural_batch"), list)
        assert len(data["structural_batch"]) >= 1
        assert isinstance(data.get("session_tfp_stages"), list)
        for row in data["session_tfp_stages"]:
            assert "session_id" in row
            assert row.get("tfp_stage") in TFP_STAGES or "_error" in row
        sas = data.get("speaker_aware_smoke") or {}
        assert sas.get("tfp_stage") in TFP_STAGES or "_error" in sas
        hx = data.get("session_hex_microstructure_tfp") or []
        assert isinstance(hx, list) and len(hx) >= 1
        for row in hx:
            assert "session_id" in row
            if "_error" not in row:
                assert "microstructure_analytics" in row
                assert "hex_option_a_summary" in row


@pytest.mark.tfp
def test_e2e_tfp_smoke_with_dlcr_bundles() -> None:
    """HESPERIA_TFP_DLCR=1 adds session_dlcr_bundles (Ethan INT-017)."""
    import os
    from runtime.pipeline.run_e2e_all import run_e2e_tfp_smoke

    import tempfile

    old = os.environ.get("HESPERIA_TFP_DLCR")
    try:
        os.environ["HESPERIA_TFP_DLCR"] = "1"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tfp_smoke_dlcr.json"
            run_e2e_tfp_smoke(p)
            data = json.loads(p.read_text(encoding="utf-8"))
            bundles = data.get("session_dlcr_bundles")
            assert isinstance(bundles, list) and len(bundles) >= 1
            for row in bundles:
                assert "session_id" in row or "_error" in row
                if "_error" not in row:
                    assert "span_count" in row
                    assert "degradation_flags" in row
    finally:
        if old is None:
            os.environ.pop("HESPERIA_TFP_DLCR", None)
        else:
            os.environ["HESPERIA_TFP_DLCR"] = old


@pytest.mark.tfp
def test_e2e_hex_microstructure_tfp_artifact() -> None:
    from runtime.pipeline.run_e2e_all import run_e2e_hex_microstructure_tfp

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "hex_tfp.json"
        run_e2e_hex_microstructure_tfp(p, "justice order fairness care trust")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("run") == "e2e_hex_microstructure_tfp"
        pb = data.get("primary_bundle") or {}
        assert "microstructure_analytics" in pb or "_error" in pb
        assert "hex_option_a_summary" in pb or "_error" in pb.get("hex_option_a_summary", {})
        assert "tfp_topology" in pb
        assert isinstance(data.get("tfp_smoke_session_bundles"), list)


def test_e2e_sealed_multiscale_artifact() -> None:
    from runtime.pipeline.run_e2e_all import run_e2e_sealed_multiscale

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "sealed.json"
        run_e2e_sealed_multiscale(p, "justice fairness order boundaries trust")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("run") == "e2e_sealed_multiscale"
        assert data.get("execution_flow") == "sealed_multiscale_v1"
        assert len(data.get("family_activation_vector") or []) == 288
        assert len(data.get("area_activation_vector") or []) == 12
        assert "hspr_index" in data
        assert "hotspot_map" in data
        assert "innovation_index" in data


def test_e2e_domain_metrics_stage_in_pipeline() -> None:
    """Main pipeline with enable_domain_metrics returns domain_metrics (41 signals, hash)."""
    from sphere.pipeline.pipeline_runner import run_pipeline

    config = {
        "pipeline_version": "v1",
        "deterministic": True,
        "enable_domain_metrics": True,
    }
    result = run_pipeline("Justice and fairness support order.", config, document_id="e2e_metrics")
    assert "domain_metrics" in result
    dm = result["domain_metrics"]
    assert dm.get("sourceId") == "e2e_metrics"
    assert "_error" not in dm, f"domain_metrics stage failed: {dm.get('_error')}"
    assert len(dm.get("primitives", {})) == 6
    assert len(dm.get("derived", {})) == 35
    fp = dm.get("fingerprint", {})
    assert len(fp.get("metricValues", [])) == 41
    assert fp.get("vectorHash")
    assert fp.get("fingerprintVersion") == "hesperia_fp_v0_1"
