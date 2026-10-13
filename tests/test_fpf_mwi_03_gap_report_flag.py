# FPF-MWI-03 — optional GapReport on /product/interpret (default off).

from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.shipping.api_main import create_app

_TEXT = "FPF-MWI-03 gap_report flag synthetic includes with structure."


def _client() -> TestClient:
    return TestClient(create_app())


def test_gap_report_absent_by_default() -> None:
    r = _client().post("/product/interpret", json={"text": _TEXT, "mode": "deterministic"})
    assert r.status_code == 200
    body = r.json()
    assert "gap_report" not in body
    assert "logical" in body.get("ground_truth", {})


def test_gap_report_present_when_flag_on() -> None:
    r = _client().post(
        "/product/interpret",
        json={"text": _TEXT, "mode": "deterministic", "include_gap_report": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gap_report"]["schema"] == "hesperia.fpf_gap_report.v0_1"
