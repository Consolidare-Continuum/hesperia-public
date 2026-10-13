# HESPERIA — FPF-V7-12 /product/interpret tests.

from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.services.product_interpret_service import run_product_interpret
from runtime.shipping.api_main import create_app


def test_run_product_interpret_deterministic() -> None:
    result = run_product_interpret("Structural test input for interpret.", mode="deterministic")
    assert result["schema"] == "hesperia.product_interpret.v0_1"
    assert result["mode"] == "deterministic"
    env = result["router_envelope"]
    assert env["schema"] == "hesperia.router_input_envelope.v0_1"
    assert env["router_fingerprint"]
    assert result["interpretation"]["trace_steps"] >= 0


def test_run_product_interpret_llm_mock() -> None:
    result = run_product_interpret("LLM mock interpret path.", mode="llm")
    assert "llm" in result
    assert "narrative" in result["llm"]
    assert result["llm"]["narrative"]["confidence"] in ("low", "medium", "high")
    assert result.get("router_decision", {}).get("decision") in (
        "ALLOW",
        "WARN",
        "REVIEW_REQUIRED",
        "BLOCK",
    )


def test_product_interpret_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    r = client.post("/product/interpret", json={"text": "API interpret smoke.", "mode": "deterministic"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("schema") == "hesperia.product_interpret.v0_1"
    assert "router_envelope" in body
    env = body["router_envelope"]
    assert env.get("schema") == "hesperia.router_input_envelope.v0_1"
    assert env.get("router_fingerprint")


def test_product_interpret_llm_endpoint_decision_fields() -> None:
    """HSR-V7-D-47: API returns router_decision + audit on llm path."""
    app = create_app()
    client = TestClient(app)
    r = client.post(
        "/product/interpret",
        json={"text": "API LLM path with router decision.", "mode": "llm"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("router_decision", {}).get("decision") in (
        "ALLOW",
        "WARN",
        "REVIEW_REQUIRED",
        "BLOCK",
    )
    assert body.get("router_output_audit", {}).get("schema") == "hesperia.router_output_audit.v0_1"
