from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hesperia.product.contracts.validator import validate_contract

_ROOT = Path(__file__).resolve().parent
_RULE_FILES = {
    "llm_audit": _ROOT / "llm_audit.rules.json",
    "tfp_analysis": _ROOT / "tfp.rules.json",
}


def _match(condition: dict[str, float], metrics: dict[str, Any]) -> bool:
    for k, v in condition.items():
        if k.endswith("_min"):
            key = k[:-4]
            if float(metrics.get(key, 0.0)) < float(v):
                return False
        elif k.endswith("_max"):
            key = k[:-4]
            if float(metrics.get(key, 0.0)) > float(v):
                return False
    return True


def apply_rules(profile: str, metrics: dict[str, Any]) -> dict[str, Any]:
    p = _RULE_FILES.get(profile)
    if p is None:
        raise ValueError(f"rules_profile_unknown:{profile}")
    payload = json.loads(p.read_text(encoding="utf-8"))
    for r in list(payload.get("rules") or []):
        if _match(dict(r.get("if") or {}), metrics):
            out = dict(r.get("then") or {})
            validate_contract(profile, out)
            return out
    out = dict(payload.get("default") or {})
    validate_contract(profile, out)
    return out

