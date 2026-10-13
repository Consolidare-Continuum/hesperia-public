# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Maps sphere pipeline outputs to fpf EvidencePrimitive objects."""

from __future__ import annotations

from typing import Any

from fpf_thinking_map.primitives import (
    EvidencePrimitive,
    FGR,
    Freshness,
    GateCheck,
)

from sphere.fpf_bridge.constants import (
    CONTEXT_ID,
    AREA_LABELS,
    NUM_AREAS,
    RULE_FGR_HIGH,
    RULE_FGR_LOW,
    DEFAULT_FGR,
    DOMINANT_SHARE_HIGH,
    ENTROPY_DROP_SIGNIFICANT,
    STABILITY_CURRENT_THRESHOLD,
    STABILITY_STALE_THRESHOLD,
    CONTRADICTION_PRESSURE_NOTABLE,
    CONTRADICTION_FGR_BASE,
    CONTRADICTION_FGR_NEAR_CAP,
    TRUST_TIER_FGR_FORMALITY,
    TRUST_TIER_FGR_SCOPE,
    SYSTEM_CONFIDENCE_FGR_FORMALITY,
    SYSTEM_CONFIDENCE_FGR_SCOPE,
    DECISION_STATUS_FGR,
    EVIDENCE_SUPPORT_FGR_FORMALITY,
    EVIDENCE_SUPPORT_FGR_SCOPE,
    COBALT_CONTEXT_ID,
    KME_PRIMITIVE_FGR_FORMALITY,
    KME_PRIMITIVE_FGR_SCOPE,
    KME_PRIMITIVE_FGR_RELIABILITY_DEFAULT,
    TRIZ_CONTRADICTION_FGR_FORMALITY,
    TRIZ_CONTRADICTION_FGR_SCOPE,
)

KME_PRIMITIVE_NAMES = ("LD", "COH", "NC", "PR", "PV", "CI")


def _rule_fgr(rule_type: str, rule_data: dict[str, Any]) -> FGR:
    """Select FGR trust tuple based on rule type and magnitude."""
    if rule_type == "dominant_area":
        share = float(rule_data.get("share", 0.0))
        return RULE_FGR_HIGH[rule_type] if share >= DOMINANT_SHARE_HIGH else RULE_FGR_LOW.get(rule_type, DEFAULT_FGR)
    if rule_type == "entropy_drop":
        delta = abs(float(rule_data.get("delta_entropy", 0.0)))
        return RULE_FGR_HIGH[rule_type] if delta >= ENTROPY_DROP_SIGNIFICANT else RULE_FGR_LOW.get(rule_type, DEFAULT_FGR)
    return RULE_FGR_HIGH.get(rule_type, DEFAULT_FGR)


def map_stability_to_freshness(dynamism_metrics: dict[str, Any]) -> Freshness:
    """Map stability_index to fpf Freshness enum."""
    stability = float(dynamism_metrics.get("stability_index", 0.0))
    if stability >= STABILITY_CURRENT_THRESHOLD:
        return Freshness.CURRENT
    if stability >= STABILITY_STALE_THRESHOLD:
        return Freshness.STALE
    return Freshness.EXPIRED


def map_triggered_rules_to_evidence(
    logic_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """Convert L9 triggered_rules to fpf EvidencePrimitive objects."""
    freshness = map_stability_to_freshness(dynamism_metrics)
    evidence: list[EvidencePrimitive] = []
    seen_types: set[str] = set()

    for rule in logic_metrics.get("triggered_rules", []):
        if not isinstance(rule, dict):
            continue
        rule_type = str(rule.get("type", ""))
        if not rule_type or rule_type in seen_types:
            continue
        seen_types.add(rule_type)

        fgr = _rule_fgr(rule_type, rule)
        evidence.append(EvidencePrimitive(
            evidence_id=f"rule_{rule_type}",
            label=f"L9 structural rule: {rule_type}",
            context_id=context_id,
            claim=f"Structural event detected: {rule_type}",
            source="sphere.logic.rule_engine",
            fgr=fgr,
            freshness=freshness,
        ))

    return evidence


def map_area_activations_to_evidence(
    shadow_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """Convert corrected area vector to fpf EvidencePrimitive per active area."""
    corrected = shadow_metrics.get("corrected_area_vector") or []
    if not corrected:
        return []

    freshness = map_stability_to_freshness(dynamism_metrics)
    total = sum(abs(float(v)) for v in corrected)
    if total == 0:
        return []

    evidence: list[EvidencePrimitive] = []
    for i, val in enumerate(corrected[:NUM_AREAS]):
        activation = float(val)
        if activation <= 0:
            continue
        relative = activation / total
        fgr = FGR(
            formality=min(0.9, 0.5 + relative),
            scope=relative,
            reliability=min(0.95, 0.6 + activation),
        )
        label = AREA_LABELS.get(i, f"A{i}")
        evidence.append(EvidencePrimitive(
            evidence_id=f"area_{label}_activation",
            label=f"Area {label} activation: {activation:.3f}",
            context_id=context_id,
            claim=f"Area {label} shows {relative:.1%} relative activation",
            source="sphere.shadow.engine",
            fgr=fgr,
            freshness=freshness,
        ))

    return evidence


def map_stability_to_evidence(
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> EvidencePrimitive | None:
    """Create stability evidence if stability is sufficient for recovery transitions."""
    stability = float(dynamism_metrics.get("stability_index", 0.0))
    if stability < STABILITY_STALE_THRESHOLD:
        return None
    freshness = Freshness.CURRENT if stability >= STABILITY_CURRENT_THRESHOLD else Freshness.STALE
    return EvidencePrimitive(
        evidence_id="stability_sufficient",
        label=f"Stability index: {stability:.3f}",
        context_id=context_id,
        claim=f"Structure is {'stable' if stability >= STABILITY_CURRENT_THRESHOLD else 'moderately stable'}",
        source="sphere.dynamism",
        fgr=FGR(formality=0.8, scope=0.5, reliability=min(0.95, stability)),
        freshness=freshness,
    )


def map_anomaly_flags_to_gate_checks(
    logic_metrics: dict[str, Any],
) -> list[GateCheck]:
    """Convert anomaly flags to fpf GateCheck objects."""
    flags = logic_metrics.get("anomaly_flags") or []
    checks: list[GateCheck] = []
    for flag in flags:
        if not isinstance(flag, str) or not flag:
            continue
        checks.append(GateCheck(
            check_id=f"anomaly_{flag}",
            description=f"Anomaly flag: {flag}",
            required_evidence=[f"anomaly_{flag}_resolved"],
        ))
    return checks


def map_contradiction_to_evidence(
    l5_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """fpf_bridge v7.2 pilot: L5 CONTRADICTION_PRESSURE_SCORE / REALITY_GATE_COUNTER_EVIDENCE
    as EvidencePrimitives, scoped context_id="core" (sealed-pipeline output, branch-agnostic).

    Uses the native `contradicts` field (spec §4.2.1): contradiction_pressure evidence names
    which other evidence_id it is in tension with, rather than floating as a lone score.
    """
    if not l5_metrics:
        return []

    pressure = l5_metrics.get("CONTRADICTION_PRESSURE_SCORE")
    if pressure is None:
        return []
    pressure = float(pressure)
    if pressure < CONTRADICTION_PRESSURE_NOTABLE:
        return []

    gate_passed = bool(l5_metrics.get("REALITY_GATE_COUNTER_EVIDENCE", True))
    freshness = map_stability_to_freshness(dynamism_metrics)
    fgr = CONTRADICTION_FGR_BASE if gate_passed else CONTRADICTION_FGR_NEAR_CAP

    # Anti-region families are the concrete "what this contradicts" — fall back to the dominant
    # area's own rule evidence if no anti-region detail is present, so `contradicts` is never empty
    # when pressure is notable.
    anti_region_size = int(l5_metrics.get("ANTI_REGION_SIZE", 0) or 0)
    contradicts = ["rule_dominant_area"] if anti_region_size else []

    pressure_ev = EvidencePrimitive(
        evidence_id="contradiction_pressure",
        label=f"Contradiction pressure: {pressure:.3f}",
        context_id=context_id,
        claim=(
            f"Counter-evidence pressure is {'within' if gate_passed else 'exceeding'} policy cap"
        ),
        source="core.layers.layer_5",
        fgr=fgr,
        freshness=freshness,
        contradicts=contradicts,
    )
    gate_ev = EvidencePrimitive(
        evidence_id="counter_evidence_gate",
        label=f"Counter-evidence gate: {'pass' if gate_passed else 'fail'}",
        context_id=context_id,
        claim="REALITY_GATE_COUNTER_EVIDENCE " + ("passed" if gate_passed else "failed"),
        source="core.layers.layer_5",
        fgr=fgr,
        freshness=freshness,
    )
    return [pressure_ev, gate_ev]


def map_decision_state_to_evidence(
    l7_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """fpf_bridge v7.2 Phase 2: L7 TRUST_TIER / SYSTEM_CONFIDENCE_SCORE / DECISION_STATUS_CODE
    as EvidencePrimitives. context_id="core" — sealed-pipeline composites, branch-agnostic."""
    if not l7_metrics:
        return []
    freshness = map_stability_to_freshness(dynamism_metrics)
    evidence: list[EvidencePrimitive] = []

    tier = l7_metrics.get("TRUST_TIER")
    if tier is not None:
        tier = int(tier)
        evidence.append(EvidencePrimitive(
            evidence_id="trust_tier",
            label=f"Trust tier: {tier}/3",
            context_id=context_id,
            claim=f"Gate cascade reached tier {tier} of 3",
            source="core.layers.layer_7",
            fgr=FGR(
                formality=TRUST_TIER_FGR_FORMALITY,
                scope=TRUST_TIER_FGR_SCOPE,
                reliability=min(0.95, tier / 3.0) if tier > 0 else 0.9,
            ),
            freshness=freshness,
        ))

    confidence = l7_metrics.get("SYSTEM_CONFIDENCE_SCORE")
    if confidence is not None:
        confidence = float(confidence)
        evidence.append(EvidencePrimitive(
            evidence_id="system_confidence",
            label=f"System confidence: {confidence:.3f}",
            context_id=context_id,
            claim=f"Four-factor aggregated confidence is {confidence:.3f}",
            source="core.layers.layer_7",
            fgr=FGR(
                formality=SYSTEM_CONFIDENCE_FGR_FORMALITY,
                scope=SYSTEM_CONFIDENCE_FGR_SCOPE,
                reliability=max(0.1, min(0.95, confidence)),
            ),
            freshness=freshness,
        ))

    code = l7_metrics.get("DECISION_STATUS_CODE")
    if code is not None:
        code = int(code)
        evidence.append(EvidencePrimitive(
            evidence_id="decision_status",
            label=f"Decision status code: {code}",
            context_id=context_id,
            claim="Gate cascade passed cleanly" if code == 0 else f"First failing gate: code {code}",
            source="core.layers.layer_7",
            fgr=DECISION_STATUS_FGR,
            freshness=freshness,
        ))

    return evidence


def map_evidence_support_to_evidence(
    l4_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """fpf_bridge v7.2 Phase 2: L4 EVIDENCE_SUPPORT_INDEX_BASELINE (COBALT-relevant) as
    EvidencePrimitive. Reliability discounted by INTEGRITY_CHECK_PASS_RATIO per spec §2.1."""
    if not l4_metrics:
        return []
    support = l4_metrics.get("EVIDENCE_SUPPORT_INDEX_BASELINE")
    if support is None:
        return []
    support = float(support)
    integrity = float(l4_metrics.get("INTEGRITY_CHECK_PASS_RATIO", 1.0))
    freshness = map_stability_to_freshness(dynamism_metrics)
    return [EvidencePrimitive(
        evidence_id="evidence_support_baseline",
        label=f"Evidence support: {support:.3f}",
        context_id=context_id,
        claim=f"Retrieved evidence supports the dominant read at {support:.1%}",
        source="core.layers.layer_4",
        fgr=FGR(
            formality=EVIDENCE_SUPPORT_FGR_FORMALITY,
            scope=EVIDENCE_SUPPORT_FGR_SCOPE,
            reliability=max(0.1, min(0.9, support * integrity)),
        ),
        freshness=freshness,
    )]


def map_kme_primitives_to_evidence(
    primitive_map: dict[str, Any],
    derived_map: dict[str, Any] | None,
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """fpf_bridge v7.2 Phase 3: KME's 6 bounded primitives (+ KSI) as EvidencePrimitives.

    Correction from the original draft: KME is core Hesperia semantics — six bounded [0,1]
    measures over *any* activated concept graph (density, coherence, coverage, spread), domain
    agnostic by construction (corners/kme.md never scopes it to a domain). TFP was simply the
    first corpus it was validated against, not what it measures. Defaults to the same "core"
    context L4/L5/L7 evidence uses. A caller who knows a specific run's `primitive_map` was
    computed from TFP session content may pass `context_id=TFP_CONTEXT_ID` explicitly for that
    run — that's a property of the input provenance, not of what KME itself is.

    Accepts plain dicts (e.g. MetricReport.primitive_map / .derived_map) rather than the KME
    dataclasses directly, keeping this module decoupled from hesperia.engine.kme's internals —
    same "no duplicate client" spirit as COBALT-10, applied to imports rather than a network client.
    """
    if not primitive_map:
        return []
    freshness = map_stability_to_freshness(dynamism_metrics)
    evidence: list[EvidencePrimitive] = []

    for name in KME_PRIMITIVE_NAMES:
        value = primitive_map.get(name)
        if value is None:
            continue
        value = float(value)
        evidence.append(EvidencePrimitive(
            evidence_id=f"kme_{name.lower()}",
            label=f"KME {name}: {value:.3f}",
            context_id=context_id,
            claim=f"KME primitive {name} = {value:.3f}",
            source="hesperia.engine.kme.primitives",
            fgr=FGR(
                formality=KME_PRIMITIVE_FGR_FORMALITY,
                scope=KME_PRIMITIVE_FGR_SCOPE,
                reliability=KME_PRIMITIVE_FGR_RELIABILITY_DEFAULT,
            ),
            freshness=freshness,
        ))

    ksi = (derived_map or {}).get("KSI")
    if ksi is not None:
        ksi = float(ksi)
        evidence.append(EvidencePrimitive(
            evidence_id="kme_ksi",
            label=f"KME-KSI-score: {ksi:.3f}",
            context_id=context_id,
            claim=f"Structural efficiency (coherent density per unit propagation radius) = {ksi:.3f}",
            source="hesperia.engine.kme.derived",
            fgr=FGR(
                formality=KME_PRIMITIVE_FGR_FORMALITY,
                scope=KME_PRIMITIVE_FGR_SCOPE,
                reliability=KME_PRIMITIVE_FGR_RELIABILITY_DEFAULT,
            ),
            freshness=freshness,
        ))

    return evidence


def map_triz_contradiction_to_evidence(
    contradictions: list[dict[str, Any]] | None,
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
) -> list[EvidencePrimitive]:
    """fpf_bridge v7.2 Phase 4: TRIZ Policy Contradiction Detector as EvidencePrimitives.

    Correction from the original draft (same class of mistake as KME): TRIZ is also a general-
    purpose Hesperia mechanism — a problem/contradiction/solution-path advisor derived from
    Altshuller's TRIZ (Theory of Inventive Problem Solving), not a COBALT-exclusive tool
    (`corners/triz_extension.md`: operates on any `ActiveGraph`, isolated from but not scoped to
    any one domain). COBALT retrieving library evidence for TRIZ to analyze is one application of
    it, not what it is. Defaults to the same "core" context L4/L5/L7/KME evidence uses; a caller
    analyzing specifically COBALT-retrieved library content may pass `context_id=COBALT_CONTEXT_ID`
    explicitly for that run.

    Deliberately namespaced (`triz_contradiction_*`, never `contradiction_pressure`) so this is
    never silently averaged with L5's own, differently computed contradiction signal — same
    mechanism-name collision discipline provenance.md already applies to Sigma/Gamma/Theta vs
    FPF's Γ.

    Functionally gated on real corpus attribution existing (fpf_bridge_v7_4) when applied to
    COBALT library content specifically — this mapper is correct and testable against synthetic
    input today regardless of domain; the corpus gate concerns COBALT's specific application, not
    the mechanism's general validity.
    """
    if not contradictions:
        return []
    freshness = map_stability_to_freshness(dynamism_metrics)
    evidence: list[EvidencePrimitive] = []
    for i, c in enumerate(contradictions):
        score = c.get("contradiction_score")
        if score is None:
            continue
        score = float(score)
        principle = c.get("triz_principle", "unknown")
        evidence.append(EvidencePrimitive(
            evidence_id=f"triz_contradiction_{i}",
            label=f"TRIZ contradiction ({principle}): {score:.3f}",
            context_id=context_id,
            claim=f"TRIZ-classified contradiction, principle={principle}, score={score:.3f}",
            source="hesperia.extensions.triz.contradiction_engine",
            fgr=FGR(
                formality=TRIZ_CONTRADICTION_FGR_FORMALITY,
                scope=TRIZ_CONTRADICTION_FGR_SCOPE,
                reliability=max(0.1, min(0.85, score)),
            ),
            freshness=freshness,
        ))
    return evidence


def collect_all_evidence(
    logic_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    context_id: str = CONTEXT_ID,
    l5_metrics: dict[str, Any] | None = None,
    l7_metrics: dict[str, Any] | None = None,
    l4_metrics: dict[str, Any] | None = None,
    kme_primitives: dict[str, Any] | None = None,
    kme_derived: dict[str, Any] | None = None,
    triz_contradictions: list[dict[str, Any]] | None = None,
) -> list[EvidencePrimitive]:
    """Collect all evidence from sphere outputs into a single list.

    `l5_metrics`/`l7_metrics`/`l4_metrics`/`kme_*`/`triz_contradictions` are optional and
    additive (fpf_bridge v7.2) — absent/None reproduces today's behavior exactly; callers gate
    inclusion behind HESPERIA_FPF_EVIDENCE_EXPANSION / HESPERIA_FPF_KME_EVIDENCE.
    """
    evidence: list[EvidencePrimitive] = []
    evidence.extend(map_triggered_rules_to_evidence(logic_metrics, dynamism_metrics, context_id))
    evidence.extend(map_area_activations_to_evidence(shadow_metrics, dynamism_metrics, context_id))
    stability_ev = map_stability_to_evidence(dynamism_metrics, context_id)
    if stability_ev:
        evidence.append(stability_ev)
    if l5_metrics:
        evidence.extend(map_contradiction_to_evidence(l5_metrics, dynamism_metrics, context_id))
    if l7_metrics:
        evidence.extend(map_decision_state_to_evidence(l7_metrics, dynamism_metrics, context_id))
    if l4_metrics:
        evidence.extend(map_evidence_support_to_evidence(l4_metrics, dynamism_metrics, context_id))
    if kme_primitives:
        evidence.extend(
            map_kme_primitives_to_evidence(kme_primitives, kme_derived, dynamism_metrics)
        )
    if triz_contradictions:
        evidence.extend(
            map_triz_contradiction_to_evidence(triz_contradictions, dynamism_metrics)
        )
    return evidence
