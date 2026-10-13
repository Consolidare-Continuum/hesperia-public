# SPEC: fpf_bridge v7 — Deep Learning Gaps

**Version:** v7.1 (extension)  
**Status:** SPEC — requires Ethan ratification  
**Date:** 2026-06-29  
**Author:** Felix (Developer, Claude Code)  
**Parent:** `spec/fpf_bridge_v7.md`

---

## Context

Three deep learning concepts are absent from Hesperia v7 and would close the loop between deterministic engine output and LLM-based interpretation. Each maps to a specific insertion point in the existing architecture.

Source analysis: UDL terminology stacks (Understanding Deep Learning — Simon J.D. Prince) cross-referenced against Hesperia v7 codebase.

---

## Gap 1: Attention Extraction from LLM

### Problem

`llm_integration.py:174-194` calls the LLM and gets a narrative back (`interpret_prompt_state()`). The narrative is JSON with `summary`, `clinical_significance`, `recommended_actions`, `confidence`. But there's **no signal about which evidence the LLM actually attended to**.

The prompt sends N evidence IDs via `bridge_to_llm_prompt()` → `available_evidence` list. The LLM uses some subset. We don't know which.

### Why it matters

FGR trust tuples in `evidence_mapper.py` are calibrated by rule type (dominant_area → F=0.9, propagation_spread → F=0.6). These are static. If the LLM consistently ignores `area_A7_activation` evidence across 100 interpretations, that evidence has low real-world reliability regardless of what the FGR says. Attention extraction closes the feedback loop.

### Architecture insertion point

**Schema change:** Extend `STRUCTURAL_NARRATIVE_SCHEMA` in `llm_integration.py:24-47` to require `evidence_referenced`:

```python
"evidence_referenced": {
    "type": "array",
    "items": {"type": "string"},
    "description": "Evidence IDs from available_evidence that this interpretation relied on"
}
```

**New file:** `sphere/fpf_bridge/attention_tracker.py`

```
interpret_prompt_state() returns narrative
    → extract narrative["evidence_referenced"]
    → compare against prompt_state["available_evidence"]
    → compute attention_ratio per evidence_id (referenced / total_runs)
    → store in attention_ledger (JSONL append, like KSI corpus_evolution)
```

**FGR feedback:** After N runs (configurable, e.g. 50), read attention_ledger → adjust FGR reliability for evidence IDs with low attention_ratio:

```
evidence_mapper.py: _rule_fgr() reads attention stats
    → if attention_ratio < 0.1 over 50 runs: FGR.reliability *= 0.5
    → if attention_ratio > 0.8: FGR.reliability = min(0.95, FGR.reliability * 1.1)
```

**Storage:** `/data/hesperia/reflection/attention_ledger.jsonl` (same path convention as reflection system, HSPR-12).

**Guard:** FGR adjustments are advisory. Operator can freeze FGR via env `HESPERIA_FGR_FREEZE=1`.

### Files to create/modify

| File | Change |
|---|---|
| `sphere/fpf_bridge/llm_integration.py` | Add `evidence_referenced` to schema |
| `sphere/fpf_bridge/attention_tracker.py` | **NEW** — track, store, compute attention ratios |
| `sphere/fpf_bridge/evidence_mapper.py` | Read attention stats in `_rule_fgr()` when available |
| `sphere/fpf_bridge/constants.py` | Add `ATTENTION_LEDGER_PATH`, `ATTENTION_MIN_RUNS`, `FGR_FREEZE_ENV` |

---

## Gap 2: Area/Family Learned Embeddings

### Problem

Areas are discrete IDs connected by a fixed icosahedral adjacency matrix. `sphere/topology/embedding.py` provides 3D coordinates on the unit sphere — but these are geometric (golden ratio icosahedron), not semantic. A2 is "near" A1 and A3 by graph adjacency, but the semantic similarity between areas is unknown.

`sphere/topology/family_embedding.py` loads zone-based family positions (center/inner_ring/middle_ring/outer_ring) — structural, not learned.

### Why it matters

When the LLM gets `bridge_to_llm_prompt()`, it sees:
```json
"possible_transitions": [
    {"id": "focused_to_distributed", "to_state": "distributed_balanced", ...},
    {"id": "focused_to_unstable", "to_state": "unstable_transition", ...}
]
```

But it has no concept of *how different* these states are semantically. If areas had learned embeddings, the prompt could include:
```json
"area_similarity": {"A2-A7": 0.83, "A2-A4": 0.31}
```

This would let the LLM reason about structural proximity, not just graph topology.

### Architecture insertion point

**Existing infrastructure:**
- `sphere/topology/embedding.py:26-39` — 12 icosahedral vertices (3D, geometric)
- `sphere/topology/embedding_alignment.py` — permutation alignment
- `sphere/topology/family_embedding.py` — zone-based family positions
- `sphere/topology/metrics.py` — geometric metrics on the topology

**New file:** `sphere/topology/learned_embedding.py`

Source of learned vectors: **accumulate from calibration runs**. Each `openai_calibrate_areas.py` run produces area activation vectors for calibration texts. These activation patterns, averaged over the corpus, define the empirical co-occurrence embedding.

```
learned_embedding.py:
    load_learned_embeddings(path) → dict[str, np.ndarray]  # area_id → vector
    compute_area_similarity(emb, area_a, area_b) → float    # cosine
    build_similarity_matrix(emb) → np.ndarray               # 12×12
    enrich_prompt_state(prompt_state, emb) → dict            # adds area_similarity
```

**Integration into fpf_bridge:**
- `bridge.py:bridge_to_llm_prompt()` optionally calls `enrich_prompt_state()` if learned embeddings exist
- Embeddings stored as `assets/embeddings/area_learned_v1.npy` (frozen after calibration)
- `sphere/topology/embedding.py` unchanged — geometric embedding stays canonical

**Bootstrap:** Run `openai_calibrate_areas.py` on the existing calibration corpus → extract area co-activation matrix → SVD → top-k components → save as learned embedding. One-time, offline.

### Files to create/modify

| File | Change |
|---|---|
| `sphere/topology/learned_embedding.py` | **NEW** — load, cosine, similarity matrix, prompt enrichment |
| `sphere/fpf_bridge/bridge.py` | Add optional `enrich_prompt_state()` call in `bridge_to_llm_prompt()` |
| `tools/build_learned_area_embeddings.py` | **NEW** — offline script: calibration corpus → SVD → embedding file |
| `assets/embeddings/` | **NEW** directory — frozen embedding files |

---

## Gap 3: Reward Signal for Traversal (RL)

### Problem

The fpf_bridge state machine has 5 states, 13 transitions, 8 gates. But it's stateless per document — no memory of whether past interpretations were accepted or rejected. The traversal doesn't learn.

### Why it matters

If the operator accepts 90% of interpretations from `focused_dominant` but only 40% from `unstable_transition`, the system should learn that `unstable_transition` needs more evidence before the LLM interprets. Currently, the evidence requirements for each transition are static (`state_graph.py`).

fpf-thinking-map already has the primitives for this: `SpeechActPrimitive` (approve/revoke), `WorkPrimitive` (record of occurrence). But the bridge doesn't create them — "Bridge sets up the board. LLM integration layer creates work records" (spec/fpf_bridge_v7.md).

### Architecture insertion point

**Existing primitives (fpf_thinking_map/primitives.py):**
- `SpeechActPrimitive` — `act_type: APPROVE | REVOKE`, `actor_id`, `institutes`, `revokes`
- `WorkPrimitive` — record of enactment with `inputs`, `outputs`, `evidence_refs`
- `CommitmentPrimitive` — `DeonticModality.SHOULD` with `evidence_refs`

**Existing acceptance patterns:**
- KSI `ksi_acceptance_gate` (acceptance gate for proposals)
- Reflection system `ReflectionAcceptanceGate` (HSPR-04, thresholds: score 0.70, similarity 0.65)
- `CorpusEvolutionLedger` (HSPR-07, JSONL append, epoch snapshots)

**New file:** `sphere/fpf_bridge/reward_tracker.py`

```
reward_tracker.py:
    record_interpretation_outcome(
        document_id: str,
        structural_state: str,
        narrative: dict,
        outcome: "accepted" | "rejected" | "revised",
        operator_id: str,
    ) → None  # append to reward_ledger.jsonl

    compute_state_acceptance_rate(
        state: str,
        window: int = 100,
    ) → float  # acceptance rate over last N interpretations

    suggest_gate_adjustments(
        acceptance_rates: dict[str, float],
        threshold: float = 0.5,
    ) → list[GateAdjustment]  # which gates need more/less evidence
```

**Integration into fpf_bridge:**
- `bridge.py:_build_semantic_map()` creates `SpeechActPrimitive` when operator outcome is available (from previous runs for same structural state)
- `bridge.py:build_runtime_binding()` adjusts `risk_level` upward for states with low acceptance rate
- Gate adjustments are **proposals only** — operator must approve via `EvolutionRestructuringProposal` pattern (same as KSI §14)

**Storage:** `/data/hesperia/reflection/reward_ledger.jsonl`

**Guard:** Reward-driven adjustments are advisory. Production gates unchanged until operator approves. Env `HESPERIA_REWARD_LEARNING=1` enables.

### Files to create/modify

| File | Change |
|---|---|
| `sphere/fpf_bridge/reward_tracker.py` | **NEW** — record outcomes, compute rates, suggest adjustments |
| `sphere/fpf_bridge/bridge.py` | Read acceptance rates for risk_level adjustment |
| `sphere/fpf_bridge/binding_builder.py` | Adjust risk_level when acceptance rate data available |
| `sphere/fpf_bridge/state_graph.py` | Accept `GateAdjustment` proposals (add/remove evidence requirements) |
| `sphere/fpf_bridge/constants.py` | Add `REWARD_LEDGER_PATH`, `REWARD_LEARNING_ENV`, `ACCEPTANCE_WINDOW` |

---

## Dependency Graph

```
Gap 1 (attention) ──────────────┐
                                ├──→ FGR self-calibrating loop
Gap 3 (reward) ─────────────────┘
                                     ↕ (attention informs reward,
                                        reward validates attention)
Gap 2 (embeddings) ──→ richer LLM prompt ──→ better interpretations ──→ more reward signal
```

Gap 1 and Gap 3 are tightly coupled — attention tells us what the LLM used, reward tells us if the result was good. Together they form a self-calibrating loop.

Gap 2 is independent and can ship first (offline embedding computation, no runtime feedback needed).

---

## Implementation Order

1. **Gap 2** (embeddings) — offline script + prompt enrichment. No runtime feedback. Lowest risk.
2. **Gap 1** (attention) — schema extension + ledger. Requires LLM integration (FPF-V7-11) live.
3. **Gap 3** (reward) — operator feedback loop. Requires Gap 1 data + operator workflow. Highest value, highest coupling.

---

## What this does NOT include

- Training neural networks on Hesperia data (no model training in engine)
- Replacing deterministic pipeline layers with learned components
- Any modification to L1–L10 sphere pipeline

All three gaps are post-pipeline, post-bridge extensions. Sphere determinism is preserved.

---

SIGNED: Developer (Felix) | Claude Code context | 2026-06-29 | fpf_bridge v7.1 deep learning gaps spec
