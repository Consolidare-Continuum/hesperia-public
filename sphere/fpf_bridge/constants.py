# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Constants for the fpf_bridge layer."""

from __future__ import annotations

from fpf_thinking_map.primitives import FGR
from core.topology.invariant_catalog import AREAS as NUM_AREAS

CONTEXT_ID = "hesperia_structural_analysis"
CONTEXT_LABEL = "Hesperia Structural Analysis"

# Structural states from sphere/interpretation/state_classifier.py
STATE_FOCUSED_DOMINANT = "focused_dominant"
STATE_DISTRIBUTED_BALANCED = "distributed_balanced"
STATE_UNSTABLE_TRANSITION = "unstable_transition"
STATE_TENSION_ELEVATED = "tension_elevated"
STATE_DIFFUSE_SPREAD = "diffuse_spread"

ALL_STATES = frozenset({
    STATE_FOCUSED_DOMINANT,
    STATE_DISTRIBUTED_BALANCED,
    STATE_UNSTABLE_TRANSITION,
    STATE_TENSION_ELEVATED,
    STATE_DIFFUSE_SPREAD,
})

AREA_LABELS = {i: f"A{i}" for i in range(NUM_AREAS)}

# structural_state -> fpf risk_level
STATE_RISK_MAP: dict[str, str] = {
    STATE_FOCUSED_DOMINANT: "normal",
    STATE_DISTRIBUTED_BALANCED: "low",
    STATE_UNSTABLE_TRANSITION: "high",
    STATE_TENSION_ELEVATED: "high",
    STATE_DIFFUSE_SPREAD: "normal",
}

# L9 rule type -> FGR trust tuple (formality, scope, reliability)
# Calibrated by structural significance of each event type
RULE_FGR_HIGH: dict[str, FGR] = {
    "dominant_area": FGR(formality=0.9, scope=0.7, reliability=0.9),
    "entropy_drop": FGR(formality=0.8, scope=0.6, reliability=0.8),
    "tension_increase": FGR(formality=0.7, scope=0.5, reliability=0.7),
    "propagation_spread": FGR(formality=0.6, scope=0.8, reliability=0.6),
    "dominance_transition": FGR(formality=0.8, scope=0.6, reliability=0.5),
}

RULE_FGR_LOW: dict[str, FGR] = {
    "dominant_area": FGR(formality=0.7, scope=0.5, reliability=0.7),
    "entropy_drop": FGR(formality=0.6, scope=0.4, reliability=0.6),
    "tension_increase": FGR(formality=0.5, scope=0.4, reliability=0.5),
    "propagation_spread": FGR(formality=0.5, scope=0.6, reliability=0.5),
    "dominance_transition": FGR(formality=0.6, scope=0.4, reliability=0.4),
}

DEFAULT_FGR = FGR(formality=0.5, scope=0.5, reliability=0.5)

# Thresholds for FGR calibration (matching state_classifier.py)
DOMINANT_SHARE_HIGH = 0.35
ENTROPY_DROP_SIGNIFICANT = 0.15

# Stability -> Freshness thresholds
STABILITY_CURRENT_THRESHOLD = 0.7
STABILITY_STALE_THRESHOLD = 0.3

# --- fpf_bridge v7.2 evidence expansion (spec: fpf_bridge_v7_2_evidence_expansion.md) ---
# Pilot slice: L5 CONTRADICTION_PRESSURE_SCORE / REALITY_GATE_COUNTER_EVIDENCE.
# Default off — enable via HESPERIA_FPF_EVIDENCE_EXPANSION / HESPERIA_FPF_CONTRADICTION_GATE.

# Policy cap CONTRADICTION_PRESSURE_SCORE is checked against inside REALITY_GATE_COUNTER_EVIDENCE
# itself (layer_5.py); this is a second, LLM-facing threshold for when pressure is high enough to
# be worth a dedicated logic rule, independent of whether the underlying gate already passed/failed.
CONTRADICTION_PRESSURE_NOTABLE = 0.4

# FGR for contradiction_pressure evidence: formality high (well-defined weighted composite,
# see layer_5.py), reliability scaled down the closer pressure sits to its own policy cap
# (near the cap = more likely borderline/noise than a clean contradiction signal).
CONTRADICTION_FGR_BASE = FGR(formality=0.85, scope=0.6, reliability=0.7)
CONTRADICTION_FGR_NEAR_CAP = FGR(formality=0.85, scope=0.6, reliability=0.45)

# --- fpf_bridge v7.2 Phase 2: L7 decision trio + L4 evidence support ---

# TRUST_TIER is int 0-3; reliability scales with tier/3 directly (tier IS the reliability signal).
TRUST_TIER_FGR_FORMALITY = 0.9  # well-defined, traceable gate cascade (corners/guards.md)
TRUST_TIER_FGR_SCOPE = 0.7

# SYSTEM_CONFIDENCE_SCORE: the most-aggregated number in the system — high formality, reliability
# scales with the score's own value (a low confidence score is itself highly reliable information).
SYSTEM_CONFIDENCE_FGR_FORMALITY = 0.9
SYSTEM_CONFIDENCE_FGR_SCOPE = 0.8

# DECISION_STATUS_CODE: clean enum (0/10.../75), one of the closest existing outputs to an FPF
# gated-transition concept — "which gate blocked you," already computed.
DECISION_STATUS_FGR = FGR(formality=0.9, scope=0.7, reliability=0.85)

# EVIDENCE_SUPPORT_INDEX_BASELINE (L4) — reliability discounted by INTEGRITY_CHECK_PASS_RATIO,
# per spec §2.1: a shaky integrity check should discount how much the support number can be trusted.
EVIDENCE_SUPPORT_FGR_FORMALITY = 0.75
EVIDENCE_SUPPORT_FGR_SCOPE = 0.6

# --- fpf_bridge v7.2 Phase 3/4: branch-scoped bounded contexts (spec §3, resolved via real
# ContextPrimitive registration rather than a synthetic new field on EvidencePrimitive — see
# corners/fpf_bridge.md's A.1.1 U.BoundedContext anchor: evidence's context_id IS the mechanism
# FPF already provides for "which bounded context does this claim belong to.") ---
TFP_CONTEXT_ID = "hesperia_tfp_clinical"
TFP_CONTEXT_LABEL = "Hesperia TFP Clinical Grounding"
COBALT_CONTEXT_ID = "hesperia_cobalt_library"
COBALT_CONTEXT_LABEL = "Hesperia COBALT Library Evidence"

# KME primitives (LD, COH, NC, PR, PV, CI) — new data source to the bridge (clinical_bridge.py),
# not just a new field on existing pipeline data; deliberately not started at the same reliability
# ceiling as the L1-L9 pipeline evidence (no track record yet in this bridge).
KME_PRIMITIVE_FGR_FORMALITY = 0.8  # bounded, deterministic, clamp01-proven
KME_PRIMITIVE_FGR_SCOPE = 0.5
KME_PRIMITIVE_FGR_RELIABILITY_DEFAULT = 0.6

# TRIZ Policy Contradiction Detector — deliberately coarse classification (4 principles, hash
# fallback per corners/triz_extension.md), lower formality than L5's own contradiction signal.
TRIZ_CONTRADICTION_FGR_FORMALITY = 0.6
TRIZ_CONTRADICTION_FGR_SCOPE = 0.5
