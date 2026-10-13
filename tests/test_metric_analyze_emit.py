"""METRIC-22/23 live ``/analyze`` emit wiring."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from runtime.services import engine_analyze_contract
from runtime.shipping import api_main
from runtime.shipping.env_guard import ALLOWED_HESPERIA_ENV


_BASE_ENGINE_RESULT: dict[str, Any] = {
    "contract_version": "v1.0",
    "trace": [],
    "dominant_area_id": "A1",
    "dominant_family_id": "family_000",
    "dominant_concept_id": "synthetic_family_000",
    "governance": 0.0,
    "loopability": 0.0,
    "tension_energy": 0.0,
    "obstacle_score": 1.0,
    "contradiction_flags": [],
    "weak_signals": [],
}


def _install_fast_analyze_stubs(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "runtime.services.analysis_service.run_structural_analysis",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        engine_analyze_contract,
        "_run_engine_analyze",
        lambda *_args, **_kwargs: dict(_BASE_ENGINE_RESULT),
    )


def test_metric_flags_are_allowed_by_shipping_env_guard() -> None:
    assert {"HESPERIA_METRIC_EMIT", "HESPERIA_GCS_EMIT"} <= ALLOWED_HESPERIA_ENV


def test_analyze_flags_off_preserve_public_response_shape(monkeypatch: Any) -> None:
    monkeypatch.delenv("HESPERIA_METRIC_EMIT", raising=False)
    monkeypatch.delenv("HESPERIA_GCS_EMIT", raising=False)
    _install_fast_analyze_stubs(monkeypatch)

    response = TestClient(api_main.create_app()).post("/analyze", json={"text": "metric off"})

    assert response.status_code == 200
    body = response.json()
    assert body["engine_result"] == _BASE_ENGINE_RESULT
    assert "meta" not in body["engine_result"]


def test_analyze_metric_emit_adds_ipow_and_gcs_without_other_drift(monkeypatch: Any) -> None:
    monkeypatch.setenv("HESPERIA_METRIC_EMIT", "1")
    monkeypatch.setenv("HESPERIA_GCS_EMIT", "1")
    _install_fast_analyze_stubs(monkeypatch)

    response = TestClient(api_main.create_app()).post("/analyze", json={"text": "metric on"})

    assert response.status_code == 200
    engine_result = response.json()["engine_result"]
    meta = engine_result.pop("meta")
    assert engine_result == _BASE_ENGINE_RESULT

    metric = meta["hesperia_metric"]
    assert metric["hesperia_metric_version"] == "0.1.0"
    assert metric["geodesic_sphere"]["anchor_map_id"] == "anchor_map_v1"

    ipow = meta["interior_point_of_world_view"]
    assert ipow["powv_point_zero"] is True
    assert ipow["powv_position"] == [0.0, 0.0, 0.0]
    assert ipow["powv_step"] == 0
    assert ipow["powv_distances_tier1"] == [1.0] * 12
    assert len(ipow["powv_barycentric_areas"]) == 12
