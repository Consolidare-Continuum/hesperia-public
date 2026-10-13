# HESPERIA — RouterDecision v0.1 (HSR-V7-09).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Decision enum, reason codes, and audit schema identifiers."""

from __future__ import annotations

from typing import Literal

RouterDecisionKind = Literal["ALLOW", "WARN", "REVIEW_REQUIRED", "BLOCK"]

ROUTER_OUTPUT_AUDIT_SCHEMA = "hesperia.router_output_audit.v0_1"
ROUTER_DECISION_SCHEMA = "hesperia.router_decision.v0_1"

# Machine-readable reason codes (HSR-V7-D-34 registry subset — v0.1 core set).
REASON_CODES: dict[str, str] = {
    "ALIGNMENT_OK": "Output trace aligns with input envelope within tolerance.",
    "SEMANTIC_DRIFT": "Re-analyzed output dominant region differs from input route.",
    "INTENT_DRIFT": "Output narrative scope diverges from input task.",
    "UNSUPPORTED_CLAIM": "High-certainty claims without corpus snapshot backing.",
    "CORPUS_MISSING": "corpus_snapshot_id unset — corpus evidence not wired.",
    "POLICY_VIOLATION": "Output conflicts with envelope policy_block constraints.",
    "MUTATION_ATTEMPT": "Output attempts graph/apply authority (forbidden).",
    "HIGH_RISK_OUTPUT": "Elevated policy risk combined with weak alignment.",
    "EMPTY_OUTPUT": "Model returned empty or unusable output.",
    "OUTPUT_REANALYZE_FAILED": "Structural re-analysis of output could not complete.",
}

ALLOWED_DECISIONS = frozenset({"ALLOW", "WARN", "REVIEW_REQUIRED", "BLOCK"})
