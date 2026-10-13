# HESPERIA — Post-LLM router audit (HSR-V7-09).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Re-analyze LLM output, compute alignment, emit RouterDecision."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sphere.router.router_decision_v0_1 import (
    REASON_CODES,
    ROUTER_DECISION_SCHEMA,
    ROUTER_OUTPUT_AUDIT_SCHEMA,
    RouterDecisionKind,
)

_MUTATION_PATTERNS = re.compile(
    r"\b(auto[- ]?apply|apply_graph|mutate_graph|override\s+policy|write\s+to\s+graph)\b",
    re.IGNORECASE,
)
_HIGH_CERTAINTY_PATTERNS = re.compile(
    r"\b(definitely|certainly|proven|diagnosed|confirmed diagnosis)\b",
    re.IGNORECASE,
)


def _output_hash(payload: Any) -> str:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _raw_output_to_text(raw_output: dict[str, Any] | str) -> str:
    if isinstance(raw_output, str):
        return raw_output.strip()
    narrative = raw_output.get("narrative") if isinstance(raw_output, dict) else None
    if isinstance(narrative, str):
        return narrative.strip()
    if isinstance(narrative, dict):
        parts = [
            str(narrative.get("summary") or ""),
            str(narrative.get("clinical_significance") or ""),
        ]
        for action in narrative.get("recommended_actions") or []:
            parts.append(str(action))
        return " ".join(p for p in parts if p).strip()
    return json.dumps(raw_output, sort_keys=True, ensure_ascii=False)


def _alignment_summary(
    input_envelope: dict[str, Any],
    output_trace: dict[str, Any],
) -> dict[str, Any]:
    in_eng = input_envelope.get("engine_trace") or {}
    in_area = in_eng.get("dominant_area_id")
    out_area = output_trace.get("dominant_area_id")
    in_gov = float(in_eng.get("governance") or 0.0)
    out_gov = float(output_trace.get("governance") or 0.0)
    area_match = in_area == out_area and in_area is not None
    gov_delta = round(abs(in_gov - out_gov), 6)
    drift_score = 0.0 if area_match else min(1.0, 0.5 + gov_delta)
    return {
        "input_dominant_area_id": in_area,
        "output_dominant_area_id": out_area,
        "area_match": area_match,
        "governance_delta": gov_delta,
        "drift_score": round(drift_score, 6),
        "contradiction_flags": list(output_trace.get("contradiction_flags") or []),
        "scope_on_task": area_match or drift_score < 0.6,
    }


def _corpus_check(input_envelope: dict[str, Any], output_text: str) -> dict[str, Any]:
    corpus_id = str(input_envelope.get("corpus_snapshot_id") or "corpus-unset")
    retrieval = input_envelope.get("retrieval_context") or {}
    has_retrieval = bool(retrieval.get("chunks"))
    high_certainty = bool(_HIGH_CERTAINTY_PATTERNS.search(output_text))
    if corpus_id == "corpus-unset" and not has_retrieval:
        status = "unsupported" if high_certainty else "missing_evidence"
    elif has_retrieval or corpus_id != "corpus-unset":
        status = "supported"
    else:
        status = "partial"
    return {
        "corpus_snapshot_id": corpus_id,
        "status": status,
        "has_retrieval_chunks": has_retrieval,
        "high_certainty_language": high_certainty,
    }


def _policy_check(input_envelope: dict[str, Any], output_text: str) -> dict[str, Any]:
    policy = input_envelope.get("policy_block") or {}
    risk = str(policy.get("risk_level") or "normal")
    violations: list[str] = []
    warnings: list[str] = []
    if _MUTATION_PATTERNS.search(output_text):
        violations.append("mutation_language_detected")
    if risk == "high" and _HIGH_CERTAINTY_PATTERNS.search(output_text):
        violations.append("high_risk_certainty_language")
    if risk == "elevated":
        warnings.append("elevated_input_risk")
    return {
        "risk_level": risk,
        "violations": violations,
        "warnings": warnings,
    }


def _mutation_boundary_check(output_text: str) -> dict[str, Any]:
    matched = _MUTATION_PATTERNS.findall(output_text)
    return {
        "mutation_attempt": bool(matched),
        "matched_patterns": matched[:5],
    }


def _decide(
    *,
    alignment: dict[str, Any],
    corpus: dict[str, Any],
    policy: dict[str, Any],
    mutation: dict[str, Any],
    output_text: str,
) -> tuple[RouterDecisionKind, list[str]]:
    reasons: list[str] = []
    if not output_text:
        return "BLOCK", ["EMPTY_OUTPUT"]
    if mutation.get("mutation_attempt"):
        return "BLOCK", ["MUTATION_ATTEMPT"]
    if policy.get("violations"):
        return "BLOCK", ["POLICY_VIOLATION"]
    if corpus.get("status") == "unsupported":
        return "REVIEW_REQUIRED", ["UNSUPPORTED_CLAIM", "CORPUS_MISSING"]
    if corpus.get("status") == "missing_evidence" and corpus.get("high_certainty_language"):
        return "REVIEW_REQUIRED", ["CORPUS_MISSING", "UNSUPPORTED_CLAIM"]
    if not alignment.get("area_match") and float(alignment.get("drift_score") or 0) >= 0.5:
        return "WARN", ["SEMANTIC_DRIFT"]
    if str((policy.get("risk_level") or "")) == "high" and float(alignment.get("drift_score") or 0) > 0.3:
        return "WARN", ["HIGH_RISK_OUTPUT", "SEMANTIC_DRIFT"]
    if alignment.get("area_match"):
        reasons.append("ALIGNMENT_OK")
    else:
        reasons.append("INTENT_DRIFT")
    return "ALLOW", reasons


def audit_router_output(
    input_envelope: dict[str, Any],
    raw_output: dict[str, Any] | str,
    assets_root: Path | None = None,
) -> dict[str, Any]:
    """HSR-V7-09: full RouterOutputAudit + RouterDecision."""
    from sphere.router.engine_analyze_bridge import run_engine_analyze

    output_text = _raw_output_to_text(raw_output)
    out_hash = _output_hash(raw_output if not isinstance(raw_output, str) else output_text)

    if not output_text:
        decision: RouterDecisionKind = "BLOCK"
        decision_reasons = ["EMPTY_OUTPUT"]
        output_trace: dict[str, Any] = {}
        alignment: dict[str, Any] = {}
        corpus: dict[str, Any] = {"status": "missing_evidence"}
        policy: dict[str, Any] = {"violations": [], "warnings": []}
        mutation: dict[str, Any] = {"mutation_attempt": False, "matched_patterns": []}
    else:
        output_trace = run_engine_analyze(output_text, assets_root=assets_root)
        alignment = _alignment_summary(input_envelope, output_trace)
        corpus = _corpus_check(input_envelope, output_text)
        policy = _policy_check(input_envelope, output_text)
        mutation = _mutation_boundary_check(output_text)
        decision, decision_reasons = _decide(
            alignment=alignment,
            corpus=corpus,
            policy=policy,
            mutation=mutation,
            output_text=output_text,
        )

    audit = {
        "schema": ROUTER_OUTPUT_AUDIT_SCHEMA,
        "output_hash": out_hash,
        "output_trace": output_trace,
        "alignment_summary": alignment,
        "corpus_check": corpus,
        "policy_check": policy,
        "mutation_check": mutation,
        "decision": decision,
        "decision_reasons": decision_reasons,
        "reason_code_descriptions": {code: REASON_CODES.get(code, "") for code in decision_reasons},
    }
    router_decision = {
        "schema": ROUTER_DECISION_SCHEMA,
        "decision": decision,
        "decision_reasons": decision_reasons,
        "input_hash": input_envelope.get("input_hash"),
        "output_hash": out_hash,
        "router_fingerprint": input_envelope.get("router_fingerprint"),
        "policy_snapshot_id": input_envelope.get("policy_snapshot_id"),
        "corpus_snapshot_id": input_envelope.get("corpus_snapshot_id"),
    }
    return {
        "audit": audit,
        "router_decision": router_decision,
    }
