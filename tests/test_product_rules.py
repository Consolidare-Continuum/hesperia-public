from __future__ import annotations

from hesperia.product.rules.engine import apply_rules


def test_llm_rules_high_risk_case() -> None:
    out = apply_rules("llm_audit", {"tension": 0.9, "stability": 0.2})
    assert out["risk"] == "high"
    assert out["pattern"] == "looping"


def test_tfp_rules_default_case() -> None:
    out = apply_rules("tfp_analysis", {"tension": 0.5, "stability": 0.5, "loopability": 0.4})
    assert out["risk"] == "medium"

