from __future__ import annotations

import pytest

from hesperia.product.contracts.validator import validate_contract


def test_contracts_accept_valid_payload() -> None:
    payload = {"stability": "high", "risk": "low", "pattern": "coherent", "confidence": 0.7}
    for name in ("llm_audit", "tfp_analysis", "document_fingerprint"):
        validate_contract(name, dict(payload))


def test_contracts_reject_invalid_confidence() -> None:
    payload = {"stability": "high", "risk": "low", "pattern": "coherent", "confidence": 1.3}
    with pytest.raises(ValueError, match="contract_confidence_invalid"):
        validate_contract("llm_audit", payload)

