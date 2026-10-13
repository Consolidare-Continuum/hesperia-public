# Architecture description (ISO/IEC/IEEE 42010 form)

This document does not re-derive Hesperia's architecture — `docs/foundations/00_INDEX.md` and its
`corners/` already contain that reasoning, source-verified. This document **re-organizes** the same
facts into the stakeholder/concern/viewpoint structure ISO/IEC/IEEE 42010 expects, so an auditor or
new engineer can find "what viewpoint answers my concern" without reading the full foundations
package first. Every factual claim below cites the `docs/foundations/` file it is drawn from.
For an executing agent rather than an auditor, pair this document with
`docs/foundations/agentic_orientation.md`: the architecture here says **what exists**; the
agentic-orientation pass says **how to speak about it without drifting on names, branch scope, or
math claims**.

## 1. Stakeholders and their concerns

| Stakeholder | Primary concern | Viewpoint(s) that address it |
|---|---|---|
| **Operator** (calls `/product/interpret` or `/analyze`) | What comes back, in what shape, under what governance mode | Product Surface Viewpoint |
| **Engineer / maintainer** | Where does logic live, what's safe to change without breaking a contract | Module Decomposition Viewpoint |
| **Auditor / release signer** | Was this run derived by a fixed, documented sequence — not an opaque blob | Pipeline Sequencing Viewpoint, Guard Viewpoint |
| **LLM integration author** | What the LLM is actually allowed to see and say | LLM Boundary Viewpoint |
| **Scientific reviewer** | What's borrowed math vs. Hesperia's own composition | see `docs/publication/NOVELTY_AND_POSITIONING.md` (this document does not restate that content) |

## 2. Module Decomposition Viewpoint

**Concern addressed:** where does logic live, and why isn't the apparent duplication between
`core/` and `sphere/` actually duplication.

Three top-level runtime concerns, each independently testable (`corners/core_runtime.md`,
`corners/sphere_pipeline.md`):

- **`core/`** — the computational substrate: primitive math (`core/math/core_math.py`,
  `conservation.py`), attribution (`core/attribution/attribution.py`), tie-break resolution
  (`core/resolver/score_rules.py`), and the single canonical runtime entrypoint
  (`core/runtime/engine.py`'s `analyze_engine()`). `core.domain` is the canonical home for shared
  KME/domain measurement implementation and `core.runtime` is the canonical home for generic runtime
  modules. Reusable across more than one orchestration
  context (the sphere pipeline, calibration scripts, the modular kernel's T1–T10 gates).
- **`sphere/`** — layer-stack orchestration and interpretation: the L1–L10 pipeline
  (`sphere/pipeline/pipeline_runner.py`), diagnostics, USF generation, the fpf_bridge (Layer 11).
  `pipeline_runner.py`'s own docstring states its scope precisely: "Single canonical entrypoint;
  strict order; contract and isolation validation... No layer logic here."
- **`runtime/`** — the boundary layer to external contracts: `runtime/services/
  product_interpret_service.py` (the governed `/product/interpret` surface),
  `runtime/pipeline/run_e2e_all.py` (the canonical release-proof E2E runner).

**Why the split is load-bearing, not incidental:** mixing `core/` primitives into `sphere/`
orchestration files would force every primitive math change to be re-validated against the full
pipeline contract even when it has no business-logic implication (`corners/core_runtime.md`).
Mixing orchestration into `runtime/` would make the governed HTTP surface responsible for
sequencing correctness instead of just consuming an already-sequenced result.

## 3. Pipeline Sequencing Viewpoint

**Concern addressed:** was this specific run derived by a fixed, documented sequence, not by
whichever code path happened to assemble it.

The L1–L10 chain (`sphere/pipeline/pipeline_runner.py`) is the single canonical entrypoint; Gamma's
`GAMMA_001 layer_order_valid` invariant checks against it as source of truth
(`corners/sphere_pipeline.md`). The nine numbered layers (`core/layers/layer_1.py`…`layer_9.py`)
each implement one canonical spec (`34_SPEC`–`42_SPEC`, restored at `docs/specs/history/`) —
`docs/foundations/output_catalog.md` §§1–9 is the exhaustive, source-verified variable-level view
of this layer stack, and is the authoritative reference this viewpoint defers to rather than
duplicating.

`layer_registry.py` is the single place "what counts as a layer in this run" is decided;
`contract_validation.py` and `isolation_validation.py` answer two separable questions (did each
layer receive/emit data matching its declared contract; was each layer's view of upstream state
actually isolated) that Gamma checks at a coarser level (`corners/sphere_pipeline.md`).

## 4. Guard Viewpoint

**Concern addressed:** what makes an output trustworthy enough to certify, and in what order that
trust is actually checked.

Sigma (static artifact shape) → Gamma (dynamic execution-order soundness) → Theta
(release/governance eligibility) — three categorically different verdicts, sequenced because each
is meaningless to evaluate before the one before it has passed (`corners/guards.md`,
`corners/logic_guards.md`). This triad is Hesperia-native — confirmed by direct `grep` *not* to
derive from FPF's own "Γ (Gamma)" aggregation operator despite the shared letter
(`docs/foundations/provenance.md`'s explicit non-derivation note). Full invariant-by-invariant
detail: `docs/foundations/layers/GUARDS_sigma_gamma_theta.md`.

## 5. LLM Boundary Viewpoint

**Concern addressed:** what does an LLM actually receive and say, and how is what it says checked.

Layer 11 (`sphere/fpf_bridge/`) is a **read-only projection**, never a second source of truth
(`corners/fpf_bridge.md`, `00_INDEX.md`'s "Roof" section): it consumes L1–L10's already-certified
output and produces a bounded state machine — 5 structural states, verified exact string values in
`sphere/fpf_bridge/constants.py` (`docs/foundations/output_catalog.md` §12) — that an LLM can only
narrate inside. `sphere/router/llm_interpret.py` performs the call; `sphere/router/audit.py`
re-measures the LLM's own output against the router envelope and produces an
ALLOW/WARN/REVIEW/BLOCK verdict (`runtime/services/product_interpret_service.py`, verified
directly against source — see `docs/publication/NOVELTY_AND_POSITIONING.md` item 1 for why this
boundary is the system's actual novel contribution, not an implementation detail).

## 6. Product Surface Viewpoint

**Concern addressed:** what does an external caller actually receive, and under which of the two
live contracts.

In the repo's later productization wording (`docs/publication/UPCELERATOR_PRODUCTIZATION_QA.md`),
this viewpoint is the system location closest to phrases like **deterministic validation**,
**accountable AI**, and **evidence-grade audit trace**. Those are buyer-language summaries of this
surface, not alternate architecture.

Two independently-versioned response contracts coexist — see `output_catalog.md` §0 for the full,
source-verified field-by-field breakdown, not restated here:

- **`/analyze`** (frozen HSPR-01/02, `docs/ENGINE-ANALYZE-CONTRACT.md`) — the legacy 9-field
  contract `HesperiaPublicSnapshot.from_engine_result()` parses against.
- **`/product/interpret`** (FPF-V7-12, `runtime/services/product_interpret_service.py`) — the
  current governed V7 router surface, gated by `HESPERIA_ROUTER_MODE`
  (`observe`/`warn`/`strict`). If a product or pilot needs the buyer-facing artifact described in
  the productization docs, this is the contract family it is actually talking about.

## 7. Analytical Read-Only Viewpoint

**Concern addressed:** what consumes the pipeline's output for comparison/analytics purposes
without being allowed to feed back into it — a distinct concern from the Product Surface Viewpoint
because these two subsystems are read-only against L1–L11 by explicit design, not because they lack
a caller.

- **KME** (Knowledge Metrics Engine, `corners/kme.md`) — canonical implementation in `core.domain`
  with `hesperia.engine.kme` retained as a compatibility facade; six bounded primitives (`LD, COH, NC, PR,
  PV, CI`) reduced from the activation graph, 35 pure-algebra derived ratios (formulas verified
  letter-for-letter against `core/domain/derived_metrics.py` — `output_catalog.md` §10),
  and a 41-element hashed fingerprint for cross-run/cross-document structural comparison. KME is a
  core semantic mechanism, not a TFP-only subsystem; TFP was simply the first branch it was
  validated against.
- **TRIZ** (`corners/triz_extension.md`) — a deliberately narrow slice of Altshuller's framework (3
  relation kinds, 4 of 40 principles, no full 39×39 matrix), exporting three named
  decision-intelligence products (`output_catalog.md` §11), read-only over the same concept graph
  KME consumes. TRIZ is likewise general-purpose core analytics, not COBALT-only; COBALT is one
  branch where those exports may be especially useful.

Both are explicitly read-only against everything in §2–§6 — see each corner's own "why read-only"
section for why that boundary is load-bearing, not incidental (`00_INDEX.md`'s summary of this
distinction).

## 8. What this viewpoint set deliberately excludes

`hesperia/extensions/dynamics/` (field dynamics, `corners/field_dynamics.md`) is real, tested code
with no wiring into any viewpoint above — it does not appear in the Product Surface Viewpoint
because it has no path to either response contract today. Per this document's own standard (and
`NOVELTY_AND_POSITIONING.md`'s "do not overclaim" section), an architecture description that
included it as a current viewpoint would be describing aspiration, not the system.

## Appendix A: exhaustive corner/layer/era register

The six viewpoints above (§2–§7) organize by *concern*. This appendix grinds through
`00_INDEX.md`'s full catalog — every corner doc, every layer doc, every era — so no entry in the
foundations package is left unregistered against this architecture description. Each row cites the
corner/layer/era file directly; none of this content is re-derived, only indexed.

### A.1 Corners (22 total)

| Corner doc | Viewpoint it registers under |
|---|---|
| `corners/lexicon_resolver.md` | §2 Module Decomposition — the only place raw natural language is touched (Dict A/B/C freeze discipline); upstream of §3's L1 |
| `corners/hex_substrate.md` | §3 Pipeline Sequencing — the 72k/72,240-cell layer between resolved concepts and family/area rollup |
| `corners/topology_geometry.md` | §3 Pipeline Sequencing — the icosahedral area sphere and family zone lattice §3's BFS traversal runs over |
| `corners/metric_registry.md` | §7 Analytical Read-Only — the `metric_layer` enum and frozen `anchor_map_v1` disambiguating "distance" across geometries, consumed by comparability tooling, not the certification path |
| `corners/propagation_dynamics.md` | §3 Pipeline Sequencing — diffusion-based propagation and trajectory/dynamism over time, upstream of L2/L6 |
| `corners/shadow_correction.md` | §3 Pipeline Sequencing / §4 Guard — bounded correction of propagation's entropy/dominance side effects, feeding L3's shadow-run gate |
| `corners/logic_guards.md` | §4 Guard Viewpoint — Layer-9 declarative rules, optional Prolog inference, and the Sigma/Gamma/Theta triad together |
| `corners/guards.md` | §4 Guard Viewpoint — Sigma/Gamma/Theta in focused detail (already cited) |
| `corners/prolog_logic.md` | §4 Guard Viewpoint — the optional L9b symbolic inference layer |
| `corners/interpretation_usf.md` | §6 Product Surface — the 5-state classifier and USF consolidation feeding both response contracts |
| `corners/sphere_pipeline.md` | §3 Pipeline Sequencing (already cited) |
| `corners/core_runtime.md` | §2 Module Decomposition (already cited) |
| `corners/layer_contracts_attribution.md` | §2 Module Decomposition / §3 Pipeline Sequencing — the inter-layer contract type `contract_validation.py` checks against |
| `corners/schemas_contracts.md` | §6 Product Surface — USF and the frozen `/analyze` contract as versioned, checkable shapes |
| `corners/fpf_bridge.md` | §5 LLM Boundary (already cited) |
| `corners/calibration.md` | §2 Module Decomposition — offline tooling; also registers in `docs/iso/LIFECYCLE_PROCESS.md` §2 (validation process) |
| `corners/release_seal.md` | Out of architecture-description scope — belongs to `docs/iso/LIFECYCLE_PROCESS.md` §4, not a runtime viewpoint |
| `corners/release_governance.md` | Same — `docs/iso/LIFECYCLE_PROCESS.md` §3 |
| `corners/kme.md` | §7 Analytical Read-Only |
| `corners/triz_extension.md` | §7 Analytical Read-Only |
| `corners/corpus_wiring.md` | §2 Module Decomposition — what corpus exists and what never ships; also registers in `docs/iso/QUALITY_MODEL.md`'s Security row (proprietary-data exclusion) |
| `corners/field_dynamics.md` | §8 Deliberate exclusion (already cited) |
| `corners/core_math_contract.md` | §2 Module Decomposition — `core/math/core_math.py`, the pre-v0.4 Core Math Contract still live today |
| `corners/geometry_math_coupling.md` | §3 Pipeline Sequencing — cross-cutting: how topology/hex substrate directly constrain the math (`W` IS the adjacency matrix) |
| `corners/physics_dynamics_coupling.md` | §3 Pipeline Sequencing — cross-cutting: the physics of motion underneath propagation/dynamism (L6) |
| `corners/activation_landing_loops.md` | §2 Module Decomposition — cross-cutting: Dict A's authority boundary, the two matcher implementations, the seed handoff into the hex substrate |
| `corners/pipeline_l1_l11_science.md` | Cross-cutting synthesis of §2–§7 in one pass; the single document to read if only one is read |

### A.2 Layers (11 total: L1–L10 + GUARDS)

Each registers under §3 Pipeline Sequencing; the exact variable-level content for L1–L9 is not
repeated here — `output_catalog.md` §§1–9 is the authoritative, source-verified table this
appendix defers to.

Note: "output §N" below refers to `output_catalog.md`'s own section numbers, not this document's
viewpoint sections — the two numbering schemes are independent and both run 1–9 for L1–L9, which is
coincidental, not a cross-reference.

| Layer doc | One-line register |
|---|---|
| `layers/L1_structural_activation_census.md` | 27-variable census, pure arithmetic over attribution — output §1 |
| `layers/L2_topology_traversal.md` | 27 variables (25 spec + 2 handoffs), BFS depth 8 — output §2 |
| `layers/L3_baseline_shadow_comparison.md` | 25 variables, baseline/shadow dual-run comparison — output §3 |
| `layers/L4_evidence_retrieval.md` | 25 variables, BM25 evidence quality — output §4 |
| `layers/L5_counter_evidence_and_trig_invariants.md` | 25 variables, two halves (contradiction pressure + trig self-test, 6 of 13 residuals reserved) — output §5 |
| `layers/L6_dynamical_stability_scaffold.md` | 25 variables, only 4 live — output §6 |
| `layers/L7_consistency_and_decision.md` | 25 variables, `SYSTEM_CONFIDENCE_SCORE` + `DECISION_STATUS_CODE` — output §7 |
| `layers/L8_unit_standardization.md` | 30 variables (incl. 3 always-present policy fields), pure re-expression — output §8 |
| `layers/L9_pillars_and_brand_labels.md` | 25 variables, terminus, all user-facing — output §9 |
| `layers/L10_analysis_report_placeholder.md` | Declared, not implemented — a placeholder stub in `pipeline_runner.py`; active governance consequence is `THETA_004` (verified, `REQUIREMENTS_SPECIFICATION.md` NFR-G1). Registered here as an honest gap, not a built layer. |
| `layers/GUARDS_sigma_gamma_theta.md` | Full invariant-by-invariant detail behind §4 Guard Viewpoint — 15 Sigma, 8 Gamma, 5 Theta invariants |

### A.3 Eras (8 total) — why this architecture looks this way, not just what it is

42010 doesn't require a historical viewpoint, but every architectural boundary in §2–§7 above was a
response to a specific, dated gap — recording that trace here prevents a future reader from
"fixing" a boundary that was already deliberately drawn:

| Era | What architectural decision it produced |
|---|---|
| `eras/01_genesis_v0.2_v0.3.md` | Guard scripts existed before any layered pipeline existed to guard — "process before product" precedent §4 inherits |
| `eras/02_v0.4_freeze_and_seal.md` | First full L1–L9 stack, lexicon freeze — origin of §2's `core/`/`sphere/` split and §3's canonical sequencing |
| `eras/03_engine_dynamics_v0.5.x.md` | Calibration becomes governed/versioned — origin of `docs/iso/LIFECYCLE_PROCESS.md` §2 |
| `eras/04_v0.5.8_contradiction_track.md` | Contradiction threaded as a cross-cutting signal — origin of L5's `CONTRADICTION_PRESSURE_SCORE` cross-layer thread (`NOVELTY_AND_POSITIONING.md` item 4) |
| `eras/05_sealed_0.6.x.md` | The 0.6.0 sealed mainline and dev/prod split — origin of `docs/iso/LIFECYCLE_PROCESS.md` §5 |
| `eras/06_metric_wave_v0.7.0.md` | The `metric_layer` registry and frozen `anchor_map_v1` — origin of §7's `metric_registry.md` entry |
| `eras/07_v7_router_fpf_bridge.md` | The read-only LLM reasoning bridge, Layer 11 — origin of §5 LLM Boundary Viewpoint entirely |
| `eras/08_fpf_bridge_v7_2_v7_4.md` | Evidence expansion + agentic Cursor interface — extends §5's LLM Boundary Viewpoint (wider evidence surface, same read-only guarantee) without redefining it |

## Correspondence rules (42010's required cross-viewpoint consistency statement)

- Every module named in the Module Decomposition Viewpoint must appear in at least one of the other
  viewpoints (§3–§7), or be flagged (as §8 does) as intentionally out of scope.
- The Pipeline Sequencing Viewpoint's layer list must match `output_catalog.md`'s §1–§9 headers
  exactly — if a layer is renumbered or added, both documents change together.
- The Guard Viewpoint's triad order (Sigma → Gamma → Theta) is invariant across every other
  viewpoint that mentions certification; no viewpoint may describe a different check order.

## Closing the description set

Architecture descriptions answer *what exists* and *which viewpoint covers which concern*. Questions about **why the whole project exists** and **when a deploy is cyber-safe** are closed by the ISO program statement — not by extending this file:

→ [`PURPOSE_AND_CYBER_SAFETY_STATEMENT.md`](PURPOSE_AND_CYBER_SAFETY_STATEMENT.md) (descriptions → statement; operator Referat **348**)

## Navigation

← [`docs/README.md`](../README.md) (start here) · [`docs/foundations/00_INDEX.md`](../foundations/00_INDEX.md) (full system trace) · [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`REQUIREMENTS_SPECIFICATION.md`](REQUIREMENTS_SPECIFICATION.md) (requirements traced to this document's components) · [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) (§6 Product Surface Viewpoint, practical form) · [`PURPOSE_AND_CYBER_SAFETY_STATEMENT.md`](PURPOSE_AND_CYBER_SAFETY_STATEMENT.md) (purpose / conditional cyber-safety) · [`../publication/NOVELTY_AND_POSITIONING.md`](../publication/NOVELTY_AND_POSITIONING.md) (what's novel about §5's LLM Boundary Viewpoint)
