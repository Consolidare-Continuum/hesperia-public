# Ava smoke — TFP-POLES-04 + HES-TFP-100 inspector

from __future__ import annotations

from pathlib import Path

import pytest

from hesperia.engine.tfp_signal_calibration import load_area_inhibition_matrix
from hesperia.modules.tfp.grain12_profile import grain12_profile_meta, tfp_grain12_enabled
from research.clinical_tfp.pole_cascade import build_pole_cascade


def test_poles03_inhibition_nonzero_a11_a12() -> None:
    load_area_inhibition_matrix.cache_clear()
    inh = load_area_inhibition_matrix()
    m = inh["matrix"]
    assert any(abs(x) > 0 for x in m[10]), "A11 row must be non-zero"
    assert any(abs(x) > 0 for x in m[11]), "A12 row must be non-zero"
    assert m[10][4] > 0  # A11 → A5
    assert m[11][5] > 0  # A12 → A6
    assert m[4][10] > 0  # A5 → A11
    assert m[5][11] > 0  # A6 → A12


def test_poles03_grain12_profile_meta() -> None:
    meta = grain12_profile_meta()
    assert meta["area_math_grain"] == 12
    assert meta["sealed_areas"] == 12


def test_poles04_pole_cascade_legs() -> None:
    areas = {f"A{i}": 0.0 for i in range(1, 13)}
    areas["A5"] = 0.4
    areas["A11"] = 0.2
    areas["A6"] = 0.3
    areas["A12"] = 0.15
    out = build_pole_cascade(areas_raw=areas, areas_inhibited=areas)
    assert "seed" in out or "hop1_delta" in out or "tension" in out
    # keys present for poles path
    blob = str(out)
    assert "A11" in blob or "a11" in blob.lower() or "tension" in out


def test_analyze_api_bundle_profile_fields() -> None:
    from output_views.segment.analyze_api_bundle import build_session_inspector_v1_from_analyze_json

    body = {
        "multiscale_signals": {
            "area_activation_vector": [0.1] * 12,
            "hspr_index": 0.42,
        },
        "analyze_profile_meta": {
            "area_math": 12,
            "pack_areas": 12,
            "dict_mode": "tfp_v1",
            "structure_map": "area_structure_tfp.yaml",
        },
        "input_text": "smoke",
    }
    b = build_session_inspector_v1_from_analyze_json(body, session_id="t")
    params = b["iterations"][0]["parameters"]
    assert params["tfp_profile"]["grain"] == 12
    assert params["tfp_profile"]["pack"] == 12
    assert "A11" in params["areas"] and "A12" in params["areas"]


def test_inspector_exports_exist() -> None:
    root = Path("hesperia/modules/tfp/data/tfp_v1/inspector_exports")
    assert root.is_dir()
    files = list(root.glob("*"))
    assert files, "inspector_exports must remain as sample inputs"
