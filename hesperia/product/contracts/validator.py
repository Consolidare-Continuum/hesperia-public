from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_ALLOWED = {"low", "medium", "high"}
_PATTERN = {"looping", "fragmented", "coherent"}
_NAMES = {"llm_audit", "tfp_analysis", "document_fingerprint"}


def load_contract(name: str) -> dict[str, Any]:
    if name not in _NAMES:
        raise ValueError(f"contract_unknown:{name}")
    p = _ROOT / f"{name}.schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


def validate_contract(name: str, payload: dict[str, Any]) -> None:
    _ = load_contract(name)
    required = {"stability", "risk", "pattern", "confidence"}
    if set(payload.keys()) != required:
        raise ValueError(f"contract_keys_invalid:{name}")
    if payload["stability"] not in _ALLOWED:
        raise ValueError(f"contract_stability_invalid:{name}")
    if payload["risk"] not in _ALLOWED:
        raise ValueError(f"contract_risk_invalid:{name}")
    if payload["pattern"] not in _PATTERN:
        raise ValueError(f"contract_pattern_invalid:{name}")
    conf = float(payload["confidence"])
    if conf < 0.0 or conf > 1.0:
        raise ValueError(f"contract_confidence_invalid:{name}")

