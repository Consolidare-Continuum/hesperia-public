from __future__ import annotations

from pathlib import Path
from typing import Any

from core.engine.pipeline_runner import run_pipeline
from hesperia.product.compression import compress_product_output
from hesperia.product.contracts.validator import validate_contract
from hesperia.product.guardrails import classify_status
from hesperia.product.profiles.loader import load_profile
from hesperia.product.rules.engine import apply_rules


def run_product_profile(text: str, profile_name: str) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    config = repo_root / "assets" / "config" / "pipeline.yaml"
    dossier = run_pipeline(text, config_path=config)
    profile = load_profile(profile_name)
    metrics = dict(dossier.get("metrics") or {})
    status = classify_status(text, dossier)
    if status != "ok":
        return {"status": status, "profile_version": profile.get("profile_version"), "rule_profile": profile.get("rule_profile")}
    rules_out = apply_rules(str(profile.get("rule_profile")), metrics)
    compressed = compress_product_output(metrics)
    payload = {
        "status": "ok",
        "stability": rules_out["stability"],
        "risk": rules_out["risk"],
        "pattern": rules_out["pattern"],
        "confidence": float(rules_out["confidence"]),
        "decision_basis": compressed["decision_basis"],
        "profile_version": profile.get("profile_version"),
        "rule_profile": profile.get("rule_profile"),
    }
    validate_contract(profile_name, {k: payload[k] for k in ("stability", "risk", "pattern", "confidence")})
    return payload

