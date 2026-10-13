# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TCA = _REPO / "tools" / "tfp_calibration_audit.py"
_spec = importlib.util.spec_from_file_location("tfp_calibration_audit", _TCA)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["tfp_calibration_audit"] = _mod
_spec.loader.exec_module(_mod)
run_audit = _mod.run_audit


def test_calibration_audit_detects_analyze_structural_mismatch(tmp_path: Path) -> None:
    d = tmp_path / "bundle"
    d.mkdir()
    (d / "01_structural_batch.json").write_text(
        json.dumps(
            {
                "structural_batch": [
                    {
                        "payload": {
                            "L1": {"ATTRIBUTED_TOKENS": 0, "COVERAGE_RATIO": 0.0},
                            "diagnostics": {"calibration_status": {}},
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "02_session_tfp_stages.json").write_text(
        json.dumps(
            {
                "session_tfp_stages": [
                    {
                        "areas_top": {"A2": 1.0},
                        "areas_raw": {"A2": 0.9, "A3": 0.1},
                        "areas_inhibited": {"A2": 0.7, "A3": 0.1},
                        "areas_final": {"A2": 0.9, "A3": 0.1},
                        "activation_path_id": "tfp_invariant_activation_v2",
                        "config_version": "tfp_signal_calibration_v2",
                        "hex_feedback_active": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "04_dlcr_full.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "concept_weights_stabilized": {"C1": 1.0},
                        "concept_weights_post_hex": {"C1": 1.0},
                        "family_activation_raw": {"F1": 1.0},
                        "family_activation": {"F1": 1.0},
                        "hex_feedback_delta": {"C1": 0.0},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "05_sealed_multiscale.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "hex_activation_map": {"total_mass": 0.0},
                        "concept_layer": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "06_product_analyze.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "extended": {
                            "attribution_coverage": 1.0,
                            "matched_tokens": 100,
                            "total_tokens": 100,
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (d / "09_session_topology.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "session_topology": {
                            "area_curves_raw": {"aggression": [0.2, 0.8]},
                            "area_curves_stable": {"aggression": [0.2, 0.7]},
                            "curve_projection_meta": {"temporal_momentum": {"alpha1": 0.45, "alpha2": 0.2}},
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rep = run_audit(d)
    assert "HIGH_analyze_coverage_with_zero_L1_attributed" in rep["alarms"]
    assert "HEX_LAYER_EFFECT_NEGLIGIBLE" in rep["alarms"]
    assert rep["consistency_score"] < 0.5
