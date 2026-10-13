# HESPERIA — perturbation battery + report schema tests
from __future__ import annotations

import pytest

from sphere.kam.bounds import load_kam_bounds
from sphere.kam.critical_paths import extract_critical_paths, with_critical_paths
from sphere.kam.kam_score import aggregate_measures, compute_kam_semantic_score
from sphere.kam.perturbation_battery import P2_SHADOW, P3_EDGE, P4_TEACHER, run_perturbation_battery
from sphere.kam.report import SCHEMA_ID, build_kam_report
from sphere.kam.sisr import compute_sisr
from sphere.kam.trajectory_fingerprint import build_trajectory_fingerprint


def _bundle() -> dict:
    return {
        "concepts_activated": [
            {"id": "TFP_TRANSFERENCE", "weight": 0.9},
            {"id": "B_A10_F13_001", "weight": 0.7},
            {"id": "TFP_MALIGNANT_NARCISSISM", "weight": 0.6},
        ],
        "families_activated": [{"id": "F5", "weight": 0.8}],
        "areas_activated": [{"id": "A10", "weight": 0.85}],
        "propagation_trace": [
            {"rule_tag": "within_area:A10"},
            {"corridor_id": "family:F12->hex_cluster:H221"},
        ],
        "contradiction_pressure": 0.42,
        "propagation_corridors": {
            "corridor_edges": [
                {"id": "family:F12->hex_cluster:H221", "mass": 0.55},
                {"id": "within_area:A10", "mass": 0.4},
                {"source": "TFP_TRANSFERENCE", "target": "B_A10_F13_001", "mass": 0.3},
            ]
        },
    }


def _baseline():
    fp = build_trajectory_fingerprint(_bundle())
    paths = extract_critical_paths(fp, _bundle())
    return with_critical_paths(fp, paths)


class TestFingerprintAndPaths:
    def test_nonempty_pi_star(self) -> None:
        b = _baseline()
        assert len(b.critical_paths) > 0
        assert b.dominant_area == "A10"
        assert b.baseline_id.startswith("sha256:")

    def test_empty_pi_star_when_no_structure(self) -> None:
        fp = build_trajectory_fingerprint({})
        paths = extract_critical_paths(fp, {})
        assert paths == ()


class TestBattery:
    def test_p2_p3_offline_active(self) -> None:
        baseline = _baseline()
        bat = run_perturbation_battery(baseline)
        ids = {r.id for r in bat.active_rows}
        assert P2_SHADOW in ids
        assert P3_EDGE in ids
        assert all(0.0 <= r.path_survival <= 1.0 for r in bat.active_rows)

    def test_p4_skipped_without_teacher(self) -> None:
        baseline = _baseline()
        bat = run_perturbation_battery(
            baseline,
            active=[P2_SHADOW, P4_TEACHER],
        )
        skipped = [r for r in bat.rows if r.id == P4_TEACHER][0]
        assert skipped.skipped is True
        assert bat.incomplete is True


class TestReport:
    def test_schema_and_populated_fields(self) -> None:
        bounds = load_kam_bounds()
        baseline = _baseline()
        bat = run_perturbation_battery(baseline, bounds=bounds)
        active = bat.active_rows
        sisr = compute_sisr(
            (r.path_survival for r in active),
            baseline_path_count=len(baseline.critical_paths),
        )
        measures = aggregate_measures([r.as_dict() for r in active])
        score = compute_kam_semantic_score(sisr, bounds=bounds, **measures)
        report = build_kam_report(
            baseline, bat, sisr, score, bounds_version=bounds.version
        )
        assert report["schema"] == SCHEMA_ID
        assert report["SISR_min"] is not None
        assert report["SISR_mean"] is not None
        assert report["KAM_semantic_score"] is not None
        assert report["kam_verdict"] in {
            "structurally_robust",
            "conditionally_stable",
            "fragile_trajectory",
        }
        assert isinstance(report["perturbations"], list)
        assert len(report["perturbations"]) >= 1
