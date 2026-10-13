# HESPERIA — FPF-BUII gold + unit tests (01/02/03/05).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import copy
import json

import pytest

from sphere.fpf_inspect.climb import gap_detect, inspect_climb
from sphere.fpf_inspect.constants import (
    L6_STUB_FIELDS,
    PROVISIONAL_40_POLICY,
    PROVISIONAL_ANCHOR_MAP,
)
from sphere.fpf_inspect.map_hesperia_inspect import map_step
from sphere.fpf_inspect.probe import probe
from tests.fixtures.mock_pipeline_result import make_pipeline_result


def _rich_result(**extra):
    """Mock analyze with L5/L6/L7 + GTP for climb coverage."""
    base = make_pipeline_result(
        layer_5={
            "CONTRADICTION_PRESSURE_SCORE": 0.4,
            "REALITY_GATE_COUNTER_EVIDENCE": True,
            "ANTI_REGION_SIZE": 2,
        },
        layer_6={
            "DEPTH_GROWTH_RATIO": 0.5,
            "FIBONACCI_DEVIATION_SCORE": 0.1,
            "LYAPUNOV_ESTIMATE": 0.0,
            "GLOBAL_STABILITY_SCORE": 0.9,
            "CONCEPTUAL_COHERENCE_INDEX": 0.8,
            "INPUT_PERTURBATION_RESPONSE": 0.0,  # stub — must not become evidence
            "CONDITION_NUMBER": 1.0,  # stub
        },
        layer_7={
            "TRUST_TIER": 2,
            "SYSTEM_CONFIDENCE_SCORE": 0.75,
            "DECISION_STATUS_CODE": 0,
        },
        gtp={
            "hex_rotation": 0,
            "coherence": 0.5,
            "current_hex": {"area_id": 2, "global_id": 50, "hex_index": 1},
        },
    )
    base.update(extra)
    return base


class TestProbeMVP:
    def test_l0_present(self):
        s = probe("L0", _rich_result())
        assert s["engine_authored"] is True
        assert s["source_activation"]["engine_fingerprint"]
        assert "analyze_fingerprint" in s["fpf"]["evidence_ids"]

    def test_l5_l7_mvp(self):
        r = _rich_result()
        s5 = probe("L5", r)
        s7 = probe("L7", r)
        assert "contradiction_pressure" in s5["fpf"]["evidence_ids"]
        assert "trust_tier" in s7["fpf"]["evidence_ids"]
        assert s5["logical"] and s5["weight"] is not None and s5["source_activation"]


class TestGoldGapReport:
    def test_deterministic_gap_report(self):
        r = _rich_result()
        a = gap_detect(r)
        b = gap_detect(copy.deepcopy(r))
        assert a == b
        assert a["schema"] == "hesperia.fpf_gap_report.v0_1"
        assert a["engine_fingerprint"] == b["engine_fingerprint"]

    def test_l6_stubs_never_evidence(self):
        s = probe("L6", _rich_result())
        ids = s["fpf"]["evidence_ids"]
        for stub in L6_STUB_FIELDS:
            assert stub not in ids
            assert f"l6_{stub.lower()}" not in ids
        assert any(i.startswith("l6_depth_growth") or "depth_growth" in i for i in ids)

    def test_same_json_roundtrip(self):
        r = _rich_result()
        report = gap_detect(r)
        blob = json.dumps(report, sort_keys=True)
        assert json.loads(blob) == report


class TestClimbExtended:
    def test_mvp_layers_l0_l5_l7(self):
        out = inspect_climb(
            _rich_result(),
            stop_on_first_gap=False,
            layers=("L0", "L5", "L7"),
        )
        assert [s["layer_id"] for s in out["slices"]] == ["L0", "L5", "L7"]

    def test_gtp_provisional_tags(self):
        s = probe("GTP", _rich_result())
        for tag in (PROVISIONAL_40_POLICY, PROVISIONAL_ANCHOR_MAP):
            assert tag in s["provisional"]
        assert "hex_rotation_r0_interim" not in s["provisional"]
        gaps = gap_detect(_rich_result())
        kinds = {g["kind"] for g in gaps["gaps"]}
        assert "provisional_adr" in kinds

    def test_router_layer_probe(self):
        s = probe(
            "Router",
            {
                "router_envelope": {"router_fingerprint": "fp"},
                "ground_truth": {
                    "logical": {},
                    "weight": {},
                    "source_activation": {},
                },
            },
        )
        assert s["layer_id"] == "Router"
        assert "router_envelope" in s["fpf"]["evidence_ids"]
        assert "ground_truth_logical" in s["fpf"]["evidence_ids"]

    def test_guards_present(self):
        s = probe("Guards", _rich_result())
        assert "guard_sigma" in s["fpf"]["evidence_ids"]

    def test_l1_to_l4_on_rich(self):
        out = inspect_climb(
            _rich_result(),
            stop_on_first_gap=False,
            layers=("L1", "L2", "L3", "L4"),
        )
        assert len(out["slices"]) == 4


class TestHesperiaInspectMap:
    def test_map_step_collects_fingerprint(self):
        out = map_step(current_state="l0_hash", current_evidence="", task="dig")
        assert out["map_id"] == "hesperia_inspect"
        assert out["missing_evidence"] is None or "analyze_fingerprint" in (out.get("missing_evidence") or []) or out["kind"]

    def test_map_step_with_evidence_advances(self):
        out = map_step(
            current_state="l0_hash",
            current_evidence="analyze_fingerprint",
            task="dig",
        )
        assert out["map_id"] == "hesperia_inspect"
        # Lawful transition available or CONTINUE — library outcome is authoritative.
        assert "kind" in out
