from __future__ import annotations

from hesperia.product.service import run_product_profile


def test_product_service_llm_audit_shape() -> None:
    out = run_product_profile("product endpoint sample text", "llm_audit")
    assert set(("status", "profile_version", "rule_profile")).issubset(set(out.keys()))
    if out["status"] == "ok":
        assert set(("stability", "risk", "pattern", "confidence", "decision_basis")).issubset(set(out.keys()))


def test_product_service_guardrail_noisy() -> None:
    out = run_product_profile("!!!???---", "llm_audit")
    assert out["status"] in {"noisy_input", "low_coverage", "insufficient_data", "input_too_long"}

