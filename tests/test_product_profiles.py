from __future__ import annotations

from hesperia.product.profiles.loader import load_profile


def test_load_profiles() -> None:
    for name in ("llm_audit", "tfp_analysis", "document_fingerprint"):
        p = load_profile(name)
        assert p["name"] == name
        assert "rule_profile" in p

