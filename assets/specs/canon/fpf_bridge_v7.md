# SPEC: fpf_bridge — Layer 11 (LLM Reasoning Bridge)

**Version:** v7  
**Status:** IMPLEMENTED  
**Date:** 2026-06-27  
**Author:** Felix (Developer, Claude Code)  
**Package:** `sphere/fpf_bridge/`  
**Dependency:** `fpf-thinking-map` (PyPI v1.2.1+)

---

## Purpose

Bridge between Hesperia's deterministic pipeline output (L1–L10) and fpf-thinking-map's structured reasoning substrate. Produces a bounded semantic field for LLM traversal — not raw JSON, but a state machine with evidence-gated transitions, deterministic guards, and propositional logic constraints.

**Sphere stays deterministic.** fpf_bridge is a pure consumer — zero modifications to existing sphere code.

---

## Input Contract

Pipeline result dict (as produced by `sphere/pipeline/pipeline_runner.py` or `runtime/services/analysis_service.py`):

```
result = {
    "document_id": str,
    "shadow_metrics": {
        "corrected_area_vector": list[float],  # 12 elements
        "shadow_diagnostics": dict,
    },
    "logic_metrics": {
        "triggered_rules": list[dict],  # type, area_id, share, delta_entropy, ...
        "anomaly_flags": list[str],
    },
    "interpretation_metrics": {
        "structural_state": str,  # one of 5 states
        "interpretation_flags": list[str],
    },
    "prolog_logic": {
        "derived_facts": list[dict | str],  # predicate names
    },
    "guards": {
        "sigma": {"passed": bool, "failed_checks": list},
        "gamma": {"passed": bool, "failed_checks": list},
        "theta": {"approved": bool, "warnings": list, "violations": list},
    },
    "dynamism_metrics": {
        "stability_index": float,  # 0..1
    },
    "pipeline_metadata": dict,
}
```

---

## Output Contract

`bridge_pipeline_result(result) -> (ThinkingMapTraversal, ActiveState)`

The ActiveState contains:
- **SemanticMap**: 1 context, 1 role, N evidence primitives, 8 gates, 13 transitions, 1 commitment
- **RuntimeBinding**: task, goal, actor, risk_level, evidence IDs, constraints
- **current_state**: one of the 5 structural states
- **GuardEngine**: 9 fpf built-in guards + 3 Hesperia guards (Sigma/Gamma/Theta)
- **LogicLayer**: 7 decision rules using all 6 propositional operators

`bridge_to_llm_prompt(result) -> dict` — JSON for LLM consumption, including logic evaluation and initial outcome.

---

## State Graph (5 states, 13 transitions)

```
                    ┌────────────────────────────┐
                    │                            │
                    ▼                            │
            ┌──────────────┐              ┌─────┴────────┐
         ┌──│   focused    │──────────────│   unstable   │──┐
         │  │  dominant    │◄─────────────│  transition  │  │
         │  └──────┬───────┘              └──────────────┘  │
         │         │                             ▲          │
         │         ▼                             │          │
         │  ┌──────────────┐              ┌──────┴───────┐  │
         │  │ distributed  │──────────────│   tension    │◄─┘
         └─▶│  balanced    │◄─────────────│  elevated    │
            └──────┬───────┘              └──────────────┘
                   │
                   ▼
            ┌──────────────┐
            │   diffuse    │
            │   spread     │
            └──────────────┘
```

Each transition is gated by evidence requirements. Available evidence (from L9 triggered_rules) determines which transitions can fire.

---

## Mapping Table

| Sphere output | fpf primitive | Mapping |
|---|---|---|
| `interpretation_metrics.structural_state` | `ActiveState.current_state` | Direct (5 states) |
| `interpretation_metrics.interpretation_flags` | `RuntimeBinding.constraints` | Direct (list of strings) |
| `logic_metrics.triggered_rules[].type` | `EvidencePrimitive` per rule | FGR calibrated by severity |
| `shadow_metrics.corrected_area_vector[i]` | `EvidencePrimitive` per area | FGR from relative activation |
| `dynamism_metrics.stability_index` | `Freshness` on all evidence | ≥0.7→CURRENT, ≥0.3→STALE, <0.3→EXPIRED |
| `guards.sigma/gamma/theta` | `Guard` closures (pre-evaluated) | DENY/WARN/ALLOW from results |
| `prolog_logic.derived_facts` | `CustomProp` atoms in LogicLayer | Pre-resolved booleans |
| structural_state | `RuntimeBinding.risk_level` | focused→normal, distributed→low, unstable/tension→high, diffuse→normal |
| `logic_metrics.anomaly_flags` | `GateCheck` objects | BLOCK if unresolved |

---

## Guard Behavior

| Guard | Source | Verdict |
|---|---|---|
| `hesperia_sigma` | `guards.sigma.passed` | DENY if False |
| `hesperia_gamma` | `guards.gamma.passed` | DENY if False |
| `hesperia_theta` | `guards.theta.approved` / `.warnings` | DENY if not approved; WARN if warnings |
| 9 fpf built-ins | fpf-thinking-map defaults | Role conflict, evidence freshness, gate pass, scope check, etc. |

Guards are **pre-evaluated** — closures over sphere results, not re-computation.

---

## Logic Rules (7 rules, all 6 operators used)

| Rule | Kind | Operator | Condition |
|---|---|---|---|
| `elevated_risk` | BLOCK | CustomProp | Prolog derived `elevated_risk` |
| `structural_focus` | HINT | AND | `InState(focused_dominant) ∧ prolog(structural_focus)` |
| `propagation_wave` | WARN | CustomProp | Prolog derived `propagation_wave` |
| `transition_risk` | ROUTE | CustomProp | Prolog derived `transition_risk` |
| `risk_evidence_gap` | WARN | AND + IMPLIES | `RiskAbove(high) ∧ InState(tension) → HasMissingEvidence` |
| `state_evidence_alignment` | HINT | IFF | `InState(focused) ↔ Evidence(rule_dominant_area)` |
| `spread_vs_focus` | HINT | XOR | `Evidence(propagation) ⊕ Evidence(dominant_area)` |

---

## Files

| File | Purpose |
|---|---|
| `sphere/fpf_bridge/__init__.py` | Public API |
| `sphere/fpf_bridge/constants.py` | States, FGR tables, thresholds |
| `sphere/fpf_bridge/state_graph.py` | 5 states, 13 transitions, 8 gates |
| `sphere/fpf_bridge/evidence_mapper.py` | L9 rules + areas → EvidencePrimitive |
| `sphere/fpf_bridge/guard_bridge.py` | Sigma/Gamma/Theta → fpf Guard closures |
| `sphere/fpf_bridge/logic_bridge.py` | Prolog facts → LogicLayer with 7 rules |
| `sphere/fpf_bridge/binding_builder.py` | RuntimeBinding from pipeline result |
| `sphere/fpf_bridge/bridge.py` | Main entry: `bridge_pipeline_result()`, `bridge_to_llm_prompt()` |
| `tests/test_fpf_bridge.py` | 33 deterministic tests |
| `tests/fixtures/mock_pipeline_result.py` | Factory for mock pipeline results |

---

## No-Modification Guarantee

The following sphere files are READ ONLY — fpf_bridge consumes their output but never modifies them:

- `sphere/pipeline/pipeline_runner.py`
- `sphere/interpretation/state_classifier.py`
- `sphere/interpretation/engine.py`
- `sphere/logic/rule_engine.py`
- `sphere/logic/rule_types.py`
- `sphere/prolog_logic/engine.py`
- `sphere/guards/guard_runtime.py`
- All files under `sphere/dynamism/`, `sphere/shadow/`, `sphere/propagation/`

---

## Test Coverage

33 tests, all deterministic (no LLM, no pipeline execution):

- **State graph**: connectivity, completeness, transition count, context scoping
- **Evidence**: FGR calibration (high/low share), stability→freshness boundaries, area exclusion
- **Guards**: all-pass, sigma denial, theta warning, theta denial
- **Logic**: structural_focus fires, elevated_risk blocks, empty prolog
- **Bridge**: state mapping per structural state, transition fire/abstain/collect, sigma blocks traversal
- **Determinism**: identical input → identical output
- **Read-only**: bridge doesn't mutate input
- **LLM prompt**: required keys, logic structure, all 5 states valid

---

## What Comes Next (separate deliverables)

1. LLM integration layer — calls Claude/OpenAI with `bridge_to_llm_prompt()` output
2. Hesperia API endpoint — `/product/interpret` returning LLM-generated structural narrative
3. Calibration replacement — fpf-driven LLM calls replacing `openai_calibrate_*.py`
4. Output views — UI for LLM-generated clinical reports

---

SIGNED: Developer (Felix) | Claude Code context | 2026-06-27 | sphere/fpf_bridge v7 spec
