# Corner: `core/` — Computational Substrate, Distinct from `sphere/` Orchestration

**Location:** `core/` (attribution, contracts, diagnostics, domain, dynamics, guards, hexmap,
layers, lexical, math, metrics, operator, output, pipeline, policy, projection, propagation,
resolver, result, runtime, sequence, services, stability, state, topology).

**Born:** present in some form from v0.4 onward; consolidated as the "modular kernel" across
v0.4.1/v0.5.x (`23f589ae feat: complete modular kernel workflow gates T1-T10`).

## Why this is a distinct concern

`core/` and `sphere/` look superficially redundant — both have topology, propagation, guards,
pipeline subpackages — but they answer different questions. `core/` is the **lower-level
computational substrate**: primitive math (`core/math/conservation.py`, `core_math.py`), the
literal attribution mechanism turning matched lexical spans into structural credit
(`core/attribution/attribution.py`), the resolver performing tie-breaking among competing concept
candidates (`core/resolver/score_rules.py`), and the single canonical runtime entrypoint
(`core/runtime/engine.py`'s `analyze_engine()`). `sphere/` is the **layer-stack orchestration and
interpretation surface** built on top of it — the L1–L10 pipeline, diagnostics detectors, USF
generation, the guard *runtime* (vs. `core/guards/`, which holds the determinism/invariant
primitives the sphere guards call into).

This split exists because primitive operations (is this attribution conserved? is this propagation
step deterministic? which concept wins a scoring tie?) need to be independently testable and
reusable across more than one orchestration context — the modular kernel, calibration scripts, the
sphere pipeline — whereas L1–L10 sequencing is specific to the canonical product pipeline. Mixing
them would force every primitive math change to be re-validated against the full pipeline contract
even when it has no business-logic implication.

## What would break without it

If attribution, resolution, and propagation math lived only inside the sphere pipeline files, the
calibration scripts (`openai_calibrate_*.py`) and the modular kernel's T1–T10 workflow gates would
either have to invoke the entire L1–L10 pipeline just to test one scoring rule, or duplicate the
math ad hoc — both reintroducing the "two code paths can silently disagree" failure mode the guard
triad exists to prevent at the orchestration level.

## How it relates to neighbors

`core/runtime/engine.py`'s `analyze_engine()` is the actual function the API and CLI call; it
delegates to `hesperia.engine.runner.run_orchestration` and runs `core/guards/determinism.py`
before building the result via `core/output/result_builder.py`. `core/contracts/layer_contract.py`
defines `LayerInput`, the shared contract type `sphere/pipeline/contract_validation.py` checks
against — the contract *definition* lives in core, the contract *enforcement* lives in sphere
(see `corners/sphere_pipeline.md`, `corners/layer_contracts_attribution.md`). `core/topology/invariant_catalog.py`
and `core/propagation/invariant_enforcer.py` are the lower-level primitives `gamma_invariants.yaml`'s
rules ultimately resolve to at runtime (see `corners/guards.md`).

**Empirically checked, not just designed this way**: `eras/08_fpf_bridge_v7_2_v7_4.md` confirms
`git diff --stat 9e22af32..HEAD -- core/` is empty across the entire fpf_bridge evidence-expansion
and agentic-interface wave — every corner/sphere-level extension since (fpf_bridge, agentic_bridge,
COBALT scale-up prep) genuinely never touched this directory, not merely by convention.
