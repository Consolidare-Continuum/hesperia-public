# Corner: Sphere Pipeline — L1–L10 Orchestration

**Location:** `sphere/pipeline/` (pipeline_runner.py, layer_registry.py, pipeline_state.py,
contract_validation.py, isolation_validation.py).

**Born:** `dcb4695a Add sphere layer stack: topology, dynamism, logic, metrics, USF, pipeline,
guards` (v0.4.x era), extended at `63febce1 Layer-10 interpretation, USF consolidation, Prolog
L9b, multi-step propagation, fingerprint drift`.

## Why this is a distinct concern

Hesperia's claim to authority rests on "this verdict was derived by a fixed, documented sequence of
layers, not by an opaque blob of logic." That is only true if something *enforces* a canonical
order and refuses to run layers out of sequence or with leaked state between them.
`pipeline_runner.py`'s own docstring states the job precisely: "Single canonical entrypoint; strict
order; contract and isolation validation... No layer logic here."

This is distinct from the layers themselves (`core/layers/layer_1.py` ... `layer_9.py`,
`sphere/interpretation/engine.py` for L10) because the orchestrator's only job is sequencing and
boundary enforcement — it must not contain domain logic, or auditing "did this run correctly" would
collapse into auditing "did this compute correctly," merging two independently checkable questions
into one unauditable one. `contract_validation.py` and `isolation_validation.py` are separate files
(not folded into the runner) because they answer two distinct questions Gamma later checks at a
coarser level: did each layer receive/emit data matching its declared contract
(`core/contracts/layer_contract.py`), and was each layer's view of upstream state actually
isolated?

## What would break without it

Without a single canonical entrypoint, different callers (CLI, API, tests, calibration scripts)
could each assemble the L1–L10 sequence slightly differently — skipping a layer, calling two out of
order, passing the wrong intermediate dict — and produce different "canonical" outputs for the same
input depending on which caller ran it. That is exactly the determinism leak Gamma's
`GAMMA_001 layer_order_valid` and `GAMMA_007 registry_count_matches_triggered_rules` invariants
exist to catch — but they can only catch it because the runner makes "canonical order" a checkable,
singular fact rather than an emergent property of whichever code path happened to run.

## How it relates to neighbors

The pipeline runner is what Gamma checks *against* — the source of truth `gamma_invariants.yaml`'s
`layer_order_valid` rule references. It is also explicitly named in the fpf_bridge spec's
no-modification list (`sphere/pipeline/pipeline_runner.py` is READ ONLY for fpf_bridge), which only
makes sense because the runner's output — `shadow_metrics`, `logic_metrics`,
`interpretation_metrics`, `prolog_logic`, `guards`, `dynamism_metrics` — is exactly the input
contract the bridge spec documents (see `corners/fpf_bridge.md`, `corners/schemas_contracts.md`).
`layer_registry.py` is the single place where "what counts as a layer in this run" is decided, the
thing every topology/dynamism/logic/prolog/interpretation/guard module registers into.
