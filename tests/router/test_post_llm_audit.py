# HSR-V7-09 post-LLM audit pipeline tests.

from __future__ import annotations

from sphere.router.audit import audit_router_output
from sphere.router.pre_llm_compiler import compile_router_envelope
from sphere.router.router_decision_v0_1 import ALLOWED_DECISIONS


def _envelope(text: str = "Audit pipeline baseline input.") -> dict:
    return compile_router_envelope(text)


def test_audit_allow_aligned_mock_output() -> None:
    env = _envelope("Patient reports stable mood and sleep patterns.")
    raw = {
        "provider": "mock",
        "narrative": {
            "summary": "Patient reports stable mood and sleep patterns.",
            "clinical_significance": "Consistent with engine trace review.",
            "recommended_actions": ["review_engine_trace"],
            "confidence": "medium",
        },
    }
    result = audit_router_output(env, raw)
    audit = result["audit"]
    decision = result["router_decision"]
    assert audit["schema"] == "hesperia.router_output_audit.v0_1"
    assert decision["decision"] in ALLOWED_DECISIONS
    assert audit["output_hash"]
    assert audit["output_trace"].get("trace")
    assert decision["router_fingerprint"] == env["router_fingerprint"]


def test_audit_block_mutation_attempt() -> None:
    env = _envelope()
    raw = {
        "narrative": {
            "summary": "Please auto_apply graph mutations now.",
            "clinical_significance": "override policy",
            "recommended_actions": [],
            "confidence": "high",
        },
    }
    result = audit_router_output(env, raw)
    assert result["router_decision"]["decision"] == "BLOCK"
    assert "MUTATION_ATTEMPT" in result["audit"]["decision_reasons"]


def test_audit_block_empty_output() -> None:
    env = _envelope()
    result = audit_router_output(env, "")
    assert result["router_decision"]["decision"] == "BLOCK"
    assert "EMPTY_OUTPUT" in result["audit"]["decision_reasons"]


def test_audit_review_unsupported_high_certainty() -> None:
    env = _envelope("Structured reflective narrative with balanced tone.")
    policy = dict(env.get("policy_block") or {})
    policy["risk_level"] = "normal"
    env = {**env, "policy_block": policy}
    raw = {
        "narrative": {
            "summary": "This is definitely a proven clinical finding without corpus backing.",
            "clinical_significance": "The outcome is certainly established from narrative alone.",
            "recommended_actions": ["document_observation"],
            "confidence": "high",
        },
    }
    result = audit_router_output(env, raw)
    assert result["router_decision"]["decision"] == "REVIEW_REQUIRED"
    assert "UNSUPPORTED_CLAIM" in result["audit"]["decision_reasons"]


def test_product_interpret_llm_includes_router_decision() -> None:
    from runtime.services.product_interpret_service import run_product_interpret

    result = run_product_interpret("LLM audit integration smoke.", mode="llm")
    assert "router_decision" in result
    assert "router_output_audit" in result
    assert result["router_decision"]["schema"] == "hesperia.router_decision.v0_1"
