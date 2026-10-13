# HESPERIA — RouterPromptEnvelope builder + policy enforcement (HSR-V7-D-13/14).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Prompt-facing subset of RouterInputEnvelope — bounded LLM substrate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SCHEMA_ID = "hesperia.router_prompt_envelope.v0_1"

_DEFAULT_ALLOWED_TASKS = (
    "interpret_structural_state",
    "summarize_engine_trace",
    "list_bounded_recommended_actions",
)

_DEFAULT_FORBIDDEN_ACTIONS = (
    "mutate_graph",
    "auto_apply_relations",
    "override_policy_block",
    "claim_clinical_truth_without_corpus_evidence",
    "treat_black_box_reasoning_as_evidence",
)

_ANSWER_INSTRUCTIONS = (
    "Respond with JSON only. Ground claims in engine_trace, logic_mapping, "
    "retrieval_context, and policy_block. Do not invent measurements or diagnoses "
    "absent from the envelope. Do not present hidden model reasoning as evidence."
)

_FORBIDDEN_TOP_LEVEL_KEYS = frozenset(
    {
        "input_text",
        "hidden_reasoning",
        "chain_of_thought",
        "reasoning_trace",
        "scratchpad",
        "internal_monologue",
    }
)

_FORBIDDEN_NESTED_KEYS = frozenset(
    {
        "hidden_reasoning",
        "chain_of_thought",
        "reasoning_trace",
        "scratchpad",
        "internal_monologue",
        "cot",
    }
)

_FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"\bmy\s+internal\s+reasoning\b", re.IGNORECASE),
    re.compile(r"\bchain\s+of\s+thought\b", re.IGNORECASE),
    re.compile(r"\bblack[- ]box\s+reasoning\b", re.IGNORECASE),
)


@dataclass
class PromptPolicyViolation(Exception):
    violations: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"PromptPolicyViolation({self.violations})"


def build_prompt_envelope(input_envelope: dict[str, Any]) -> dict[str, Any]:
    """HSR-V7-D-13: RouterPromptEnvelope from RouterInputEnvelope dict."""
    policy = input_envelope.get("policy_block") or {}
    allowed = list(policy.get("allowed_tasks") or _DEFAULT_ALLOWED_TASKS)
    forbidden = list(policy.get("forbidden_actions") or _DEFAULT_FORBIDDEN_ACTIONS)
    evidence_refs: list[str] = []
    if input_envelope.get("corpus_snapshot_id"):
        evidence_refs.append(f"corpus:{input_envelope['corpus_snapshot_id']}")
    if input_envelope.get("input_hash"):
        evidence_refs.append(f"input_hash:{input_envelope['input_hash']}")
    ret = input_envelope.get("retrieval_context") or {}
    for key in ("evidence_ids", "snippet_ids"):
        for item in ret.get(key) or []:
            evidence_refs.append(f"retrieval:{item}")

    out: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "router_version": input_envelope.get("router_version", "v7-router-0.1"),
        "input_hash": input_envelope["input_hash"],
        "router_fingerprint": input_envelope.get("router_fingerprint", ""),
        "engine_trace": input_envelope.get("engine_trace") or {},
        "logic_mapping": input_envelope.get("logic_mapping") or {},
        "retrieval_context": ret,
        "relation_context": input_envelope.get("relation_context") or {},
        "policy_block": policy,
        "corpus_snapshot_id": input_envelope.get("corpus_snapshot_id", "corpus-unset"),
        "policy_snapshot_id": input_envelope.get("policy_snapshot_id", "HSR-V7-01"),
        "allowed_tasks": allowed,
        "forbidden_actions": forbidden,
        "answer_instructions": _ANSWER_INSTRUCTIONS,
        "evidence_references": evidence_refs,
    }
    if input_envelope.get("calculable") is not None:
        out["calculable"] = input_envelope["calculable"]
    if input_envelope.get("coherence_hints") is not None:
        out["coherence_hints"] = input_envelope["coherence_hints"]
    return out


def _walk_forbidden(obj: Any, path: str, violations: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = str(key).lower()
            if key_l in _FORBIDDEN_NESTED_KEYS or key in _FORBIDDEN_TOP_LEVEL_KEYS:
                violations.append(f"forbidden_key:{path}.{key}")
            _walk_forbidden(value, f"{path}.{key}", violations)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_forbidden(item, f"{path}[{i}]", violations)
    elif isinstance(obj, str):
        for pat in _FORBIDDEN_VALUE_PATTERNS:
            if pat.search(obj):
                violations.append(f"forbidden_phrase:{path}")
                break


def enforce_prompt_policy(prompt_envelope: dict[str, Any]) -> list[str]:
    """HSR-V7-D-14: verify no forbidden content in prompt substrate. Empty list = pass."""
    violations: list[str] = []
    for key in prompt_envelope:
        if key in _FORBIDDEN_TOP_LEVEL_KEYS:
            violations.append(f"forbidden_top_level:{key}")
    if "input_text" in prompt_envelope:
        violations.append("forbidden_top_level:input_text")
    _walk_forbidden(prompt_envelope, "root", violations)
    return sorted(set(violations))


def enforce_prompt_policy_or_raise(prompt_envelope: dict[str, Any]) -> dict[str, Any]:
    violations = enforce_prompt_policy(prompt_envelope)
    if violations:
        raise PromptPolicyViolation(violations=violations)
    return prompt_envelope
