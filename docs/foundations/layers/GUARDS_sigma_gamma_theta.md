# Guards — Sigma (static), Gamma (dynamic), Theta (governance)

Source: `sphere/guards/sigma_validator.py`, `sphere/guards/gamma_validator.py`,
`sphere/guards/theta_governance.py`, `sphere/guards/guard_runtime.py`, plus the
declarative specs `specs/canon/sigma_invariants.yaml` (15 invariants),
`specs/canon/gamma_invariants.yaml` (8 invariants), and
`specs/canon/theta_governance_rules.yaml` (5 rules). Supporting modules:
`core/guards/determinism.py`, `core/guards/invariants.py`.

This document is the "afterwards" companion to the L1–L9 layer documents,
written at the same level of rigor: every invariant ID, its actual enforced
check (read from the Python validator, not just the YAML's human-readable
`name`), and its formal/mathematical lineage. The conceptual framing — why
three guards instead of one, why YAML instead of Python conditionals — is
already covered in [`corners/guards.md`](../corners/guards.md) and
[`corners/logic_guards.md`](../corners/logic_guards.md) and is not repeated
here; this document is the missing exhaustive enumeration those two corner
docs reference but do not spell out invariant-by-invariant.

**Where guards sit relative to the numbered layers**: the guard triad does not
slot in as "Layer 10" — it is a separate orchestration (`guard_runtime.py`)
that runs *after* the L1–L9 chain completes, reading the layers' combined
output and runtime metadata as its input. `THETA_004` explicitly references "a
placeholder Layer-10" as a thing that exists but cannot itself confer
canonical status — confirming Layer 10 is a distinct, separately-tracked
concern from the Sigma/Gamma/Theta guard triad documented here.

## Part 1 — Sigma: static structural invariants (15 invariants)

`sigma_validator.py`'s own docstring: *"Enforces hard structural bounds, shape,
mapping integrity. Deterministic, audit-friendly."* Each invariant is a
single-snapshot check against one artifact, with no notion of execution order
or "before/after" — the same role **preconditions** play in Hoare logic (C.A.R.
Hoare, *An Axiomatic Basis for Computer Programming*, 1969) and in **Design by
Contract** (Bertrand Meyer, *Object-Oriented Software Construction*, 1988,
formalized in the Eiffel language) — assertions that must hold about a piece of
data independent of how it was produced, checked at a boundary before deeper
computation trusts it.

The resolver (`_get_path`) walks a dotted path (e.g. `raw_metrics.area_vector`)
into the artifacts dict; `optional_target: true` invariants pass vacuously if
the path is simply absent (a graceful-degradation choice, not a strict
all-paths-must-exist contract).

| ID | Target | Rule (as actually implemented) | Formal grounding |
|---|---|---|---|
| `SIGMA_001` | `raw_metrics.area_vector` | `len(val) == 12` | Schema/shape assertion — the 12-area decomposition from the icosahedral geometry (see [`geometry_math_coupling.md`](../corners/geometry_math_coupling.md)) enforced as a hard contract on the artifact, not just assumed. |
| `SIGMA_002` | `raw_metrics.family_counts` | `len(val) == 288` | Same shape assertion for the 288-family vector (`F = 288` used throughout L1–L9). |
| `SIGMA_003` | `topology.adjacency_matrix` | `len(val)==12` and each row `len==12` (optional target) | Matrix dimensionality check — confirms the adjacency artifact's rank matches the 12-area space. |
| `SIGMA_004` | `topology.adjacency_matrix` | `∀i,j: A[i][j] == A[j][i]` (optional target) | Direct application of the linear-algebra definition of a **symmetric matrix** (`A = Aᵀ`) — encodes that the area-adjacency relation is undirected, the precondition L2's BFS traversal silently assumes by treating edges as bidirectional. |
| `SIGMA_005` | `propagation_metrics.propagated_area_vector` | `len(val) == 12` | Shape conservation check on the *propagated* (post-energy-flow) area vector — the dynamic-side counterpart to `SIGMA_001`. |
| `SIGMA_006` | `propagation_metrics.propagated_family_counts` | `len(val) == 288` | Shape conservation counterpart to `SIGMA_002`. |
| `SIGMA_007` | `dynamism_metrics.transition_matrix` | `12×12` shape | Confirms the area-to-area transition-count matrix has the same 12-area dimensionality as everything else. |
| `SIGMA_008` | `topology.family_to_area` | `len(val) == 288` (optional target) | Confirms the family→area lookup table itself has one entry per family — a mapping-integrity check distinct from checking any one vector's length. |
| `SIGMA_009` | `raw_metrics.area_vector` | no element is `NaN` (via `math.isnan`) | IEEE-754 floating-point sanity check — the same NaN-detection concern documented for L5's `g10`/`CONSIST_STABILITY_REGIME_VALID` in L7, here applied proactively to the raw structural artifact rather than reactively to a derived scalar. |
| `SIGMA_010` | `raw_metrics.family_counts` | all elements `≥ 0` | Non-negativity constraint — the precondition every entropy, Gini, and ratio formula computed in L1 implicitly assumes about its inputs (you cannot take a meaningful proportion of a negative count). |
| `SIGMA_011` | `raw_metrics.coverage` | `0 ≤ val ≤ 1` | Closed-interval membership — the same `[0,1]` bound that L1/L7/L8/L9's `clamp01`-style helpers (`_clamp01`, `_c`, `_clamp`) all assume holds for ratio-typed quantities; Sigma checks the precondition those clamp functions are designed to enforce defensively downstream. |
| `SIGMA_012` | `dynamism_metrics.jump_rate` | scalar `0 ≤ val ≤ 1`, **or** a dict containing key `jump_rate` itself in `[0,1]` | A polymorphic-input defensive check (the artifact may arrive either as a raw float or wrapped in an object) — an engineering robustness choice, not a distinct mathematical concept from `SIGMA_011`/`013`/`014`. |
| `SIGMA_013` | `dynamism_metrics.stability_index` | `0 ≤ val ≤ 1` | Same closed-interval check applied to the dynamism layer's own stability figure. |
| `SIGMA_014` | `raw_metrics.loopability` | `0 ≤ val ≤ 1` | Same closed-interval check applied to a loop-tendency measure. |
| `SIGMA_015` | `raw_metrics.dominant_area` | `int(val)` integer in `0..11` | Domain check on the area-id space — consistent with the 12-area (0-indexed) geometry used throughout the pipeline. |

Severity is `critical` for 11 of the 15 invariants and `high` for the remaining
four (`SIGMA_012`–`SIGMA_014`, the dynamism-metric range checks, plus none
else) — meaning a Sigma failure on shape/mapping/NaN/non-negativity is treated
as more severe than an out-of-range ratio on the dynamism side, even though
both are encoded the same way structurally.

A `_builtin_sigma_invariants()` fallback exists for when the YAML spec file is
missing at runtime — it reproduces 12 of the 15 invariants in code (omitting
`SIGMA_003`, `SIGMA_004`, `SIGMA_008`, the three `optional_target` ones),
ensuring Sigma can still run a meaningful subset of checks even without the
declarative spec present.

## Part 2 — Gamma: dynamic execution invariants (8 invariants)

`gamma_validator.py`'s docstring: *"Enforces runtime order, isolation, sequence
consistency."* Unlike Sigma, every Gamma check requires information about *how*
the pipeline executed (order, mutation, counts across the run), not just the
shape of one artifact. Documented here with the same honesty discipline applied
to L6's stubs: several of these checks are **conditionally vacuous** — they
pass automatically when the supporting runtime metadata isn't supplied, rather
than failing closed. This is stated plainly because it changes what "Gamma
passed" actually proves in a given run.

| ID | Rule | What is actually checked |
|---|---|---|
| `GAMMA_001` | `layers_executed_canonical_order` | `runtime_metadata["executed_layers"] == list(range(1, 11))` exactly — a strict total-order equality check against the canonical sequence 1→10 (note: 10, not 9 — this check expects a 10-layer execution trace, consistent with a Layer 10 existing as a placeholder per `THETA_004`). |
| `GAMMA_002` | `no_illegal_mutation_of_upstream` | **Always passes** unless explicitly told otherwise: returns `True` if `runtime_metadata["isolation_validation_passed"] is True`, and *also* returns `True` (with the comment "we cannot verify without snapshots; pass if not specified") when that flag is simply absent. As implemented, this check cannot independently detect a mutation — it only relays a flag computed elsewhere (or defaults to trusting). Documented honestly: this is a **passthrough**, not an independent verification, the same distinction drawn for L6's stub constants. |
| `GAMMA_003` | `raw_propagated_artifacts_must_be_distinct` | If both `layer_3` and `layer_7` are present in `layer_outputs`, fails only if `layer_7` explicitly carries `raw_area_vector_overwritten: True` or `raw_family_counts_overwritten: True`. This is a **self-reporting check**: it does not diff the actual raw vs. propagated arrays itself, it relies on the layer that would have done the overwriting to flag that it did. Default-permissive unless a positive violation signal fires. |
| `GAMMA_004` | `area_sequence_values_in_0_11` | If `runtime_metadata["area_sequence"]` is present, every value must satisfy `0 ≤ int(x) < 12`; vacuously passes if the sequence isn't supplied. Domain check, same `0..11` area-id space as `SIGMA_015`, applied here to a sequence rather than a single dominant-area scalar. |
| `GAMMA_005` | `transition_matrix_sum_equals_transitions` | `sum(all cells of L6's transition_matrix) == max(len(area_sequence) - 1, 0)`. This is a direct application of the basic counting identity that **a sequence of N visited states has exactly N−1 adjacent transitions** — the same elementary counting principle underlying empirical transition-count estimation for a discrete-time Markov chain (the matrix being validated is literally a transition-count matrix in the Markov-chain sense; see the project's established discipline of naming the real shape rather than calling every stochastic-looking object "Markov" — here the *counting identity* is what's verified, not any Markov property itself). |
| `GAMMA_006` | `propagated_lengths_match_raw` | Compares `len(raw.area_vector)` vs `len(propagated.propagated_area_vector)`, and the same for `family_counts`, sourced from a `usf` dict in metadata/config. This is the **dynamic-side cross-check** corresponding to Sigma's static `SIGMA_001`/`002` vs `SIGMA_005`/`006` pairs — Sigma checks each vector's length in isolation; Gamma checks that the *same* length was preserved across the raw→propagated transition within one run. |
| `GAMMA_007` | `registry_count_matches_triggered_rules` | `len(layer_outputs["layer_9"]["triggered_rules"]) == layer_outputs["layer_9"]["rule_trigger_registry"]["count"]`. **Naming collision worth flagging explicitly**: the `"layer_9"` key read here refers to the **YAML-driven logic rule engine's** output (`sphere/logic/`, which exposes `build_rule_trigger_registry`), documented conceptually in [`corners/logic_guards.md`](../corners/logic_guards.md) — it is a *different* "Layer 9" from `core/layers/layer_9.py`'s `compute_L9` (pillars, bands, brand-word labels), documented in [`L9_pillars_and_brand_labels.md`](L9_pillars_and_brand_labels.md). Both are labeled "layer_9" in their respective dictionaries but are structurally unrelated systems — the same kind of name overlap already flagged for "shadow" (L3 vs. L8) and "counter-evidence" (L5) elsewhere in this series. |
| `GAMMA_008` | `deterministic_flag_true` | `runtime_metadata["deterministic"] is True` — a hard, non-vacuous boolean check (no "pass if absent" branch; absence means `det is not True`, so the check fails). This is the one Gamma check that fails closed rather than open. |

Severity: `critical` for five (`GAMMA_001`, `002`, `003`, `006`, `008`),
`high` for two (`GAMMA_005`, `007`), and `critical` again for `GAMMA_004`.

A `_builtin_gamma_invariants()` fallback reproduces all 8 invariant IDs (just
the id+rule pairs, no severity/name metadata) for when the YAML spec is
missing — unlike Sigma's fallback, this one is complete (all 8, not a subset).

## Part 3 — Theta: governance / canonical-output eligibility (5 rules)

`theta_governance.py`'s docstring: *"Gates canonical output eligibility;
classifies violations; no free-form eval."* Theta does not re-derive facts —
`_build_governance_facts` assembles a small fact dictionary from Sigma's
result, Gamma's result, and the artifact bundle, and every rule is then
evaluated as a declarative `{fact, op, value}` condition tree (`all`/`any` with
`eq`/`ne`), never as arbitrary executed code — the rule interpreter
(`_eval_condition`) supports exactly two boolean combinators and two
comparison operators, deliberately small enough to review exhaustively (the
same "no free-form eval" discipline already named in
[`corners/logic_guards.md`](../corners/logic_guards.md)).

| ID | Condition (all facts must hold unless noted) | Action if condition fails / holds |
|---|---|---|
| `THETA_001` | `sigma_passed == True AND gamma_passed == True` | If not met: `approved=False`, `status="quarantined"`, adds `NON_CANONICAL_OUTPUT` flag. The direct dependency encoding — Theta cannot approve anything if either upstream guard failed. |
| `THETA_002` | `raw_artifact_mutation == False` | Same quarantine action if violated. Note: `_build_governance_facts` hardcodes `raw_artifact_mutation: False` into the fact dict unconditionally — nothing in the shown code path currently sets it `True`, so as implemented today this rule cannot fail. (Consistent with the project's honesty discipline: documented as currently-unfalsifiable given the visible fact-construction logic, not claimed as an active, currently-exercised safeguard.) |
| `THETA_003` | `has_usf AND has_raw_metrics AND has_logic_outputs AND has_provenance` (all derived from inspecting `artifacts["usf"]`'s sub-keys) | Quarantine action if any required artifact is missing — this is the "four pillars of a canonical result" completeness check named in `corners/guards.md`. |
| `THETA_004` | `any: layer10_placeholder == True` | Different action family: `flag_non_canonical_interpretation` — does **not** quarantine the output, instead appends a warning and a `NON_CANONICAL_INTERPRETATION` governance flag. This is the one Theta rule that downgrades trust in the *narrative interpretation* without rejecting the *structural* result, and it is the rule that confirms a numbered "Layer 10" exists as a recognized placeholder elsewhere in the system, distinct from the Sigma/Gamma/Theta guards themselves. |
| `THETA_005` | `deterministic == True` (sourced from `usf.provenance.deterministic`, or from `config["deterministic"]` as a fallback) | Quarantine action if violated — the governance-level consumer of the same determinism concept Gamma's `GAMMA_008` checks at the runtime-metadata level; Theta checks it again from the artifact's own recorded provenance, a second independent read of the same fact from a different source. |

`status` starts as `"canonical"` and flips permanently to `"quarantined"` the
first time any `approve_canonical`-action rule's condition fails — there is no
path back to `"canonical"` within one evaluation once any such rule fails,
consistent with quarantine being a terminal classification for that run's
output. `approved` and `status` are reported alongside the specific
`violations` (each carrying its own `rule_id`, `severity`, `message`) and any
non-blocking `warnings`, so a caller can distinguish "this output cannot be
canonical, and here specifically why" from "this output is canonical but one
soft concern was flagged."

## Orchestration: `guard_runtime.run_all_guards`

Sequencing is fixed and explicit: **Sigma → Gamma → Theta**, matching the
dependency order Theta's own `THETA_001` encodes (governance cannot be
meaningfully evaluated over data already known to violate shape or execution
invariants). Before running the validators, the orchestrator backfills
`runtime_metadata` with convenience defaults pulled from `artifacts` when
absent — `usf`, `executed_layers` (defaulting to `list(range(1, 11))`),
`isolation_validation_passed` (defaulting to `True`), `deterministic`
(defaulting to `True`). **This default-true behavior is the same
default-permissive pattern already flagged for `GAMMA_002`/`GAMMA_003`** — in
the absence of explicit `pipeline_metadata`, the orchestrator hands Gamma
inputs that are pre-disposed to pass, not neutral. The docstring is explicit
that this module performs *"Orchestration only; no policy logic here"* — all
of the actual judgment lives in the three validators and their YAML specs, and
the orchestrator's only logic is sequencing plus metadata backfill.

## `core/guards/` — two smaller, structurally distinct guard utilities

These two modules are **not** part of the Sigma/Gamma/Theta triad — they live
in `core/guards/` (not `sphere/guards/`) and are invoked at different points in
the system. Documented here because the project's "guards" vocabulary spans
both locations and the distinction matters.

- **`determinism.py`**: `guard_determinism(result)` is a one-line wrapper
  around `validate_result_contract(result)` (defined in
  `core/result/contract.py`, not itself read for this document), plus
  re-exports of `canonical_json`/`deterministic_hash` from
  `core/diagnostics/determinism.py`. This is a **contract-validation guard at
  the result boundary**, not a Sigma/Gamma/Theta invariant — it is the kind of
  check `GAMMA_008`/`THETA_005`'s `deterministic` fact is presumably backed by
  elsewhere in the system (the actual hash/canonicalization logic that proves
  determinism, rather than just reading a boolean flag someone else set).
- **`invariants.py`**: `enforce_invariants(state, max_total_mass=1e6, clamp=True)`
  operates on a `SemanticState`'s mass and activation vectors directly — a
  different kind of guard from Sigma/Gamma/Theta's read-only validation: this
  one **mutates and repairs** the state in place (when `clamp=True`) rather
  than only reporting pass/fail. It clamps negative mass/activation values to
  zero (non-negativity, mirroring `SIGMA_010`'s precondition but *enforced*
  rather than *checked*), rescales total mass back under `max_total_mass` by a
  uniform scale factor when exceeded (the same proportional-rescaling idea as
  normalizing a vector to a target sum), and **renormalizes the activation
  vector to sum to 1** when its total is non-negligible (`act_total > EPS`) —
  turning an arbitrary non-negative vector into a discrete probability
  distribution by dividing through by its own sum, the textbook construction
  of a probability mass function from non-negative weights. Each correction
  taken is recorded as a named violation string (`negative_mass:<key>`,
  `total_mass_bound_exceeded`, `activation_zero_sum`) rather than silently
  applied, so the repair is itself auditable. This module's name ("invariants")
  overlaps with Sigma's *checked* invariants conceptually but is structurally a
  **corrective/repair guard**, not a pass/fail validator — worth distinguishing
  from Sigma's invariant *checks*, which never modify the data they inspect.

## Relationship to neighboring layers and corners

- **L1–L9 → guards**: the guard triad reads artifacts and layer outputs
  produced by the numbered pipeline (`raw_metrics`, `propagation_metrics`,
  `dynamism_metrics`, and the `layer_3`/`layer_6`/`layer_7` outputs
  specifically named in Gamma's checks) — it is the first place in this
  documentation series where the L1–L9 chain's outputs are checked rather than
  consumed for further computation.
- **`corners/guards.md`** and **`corners/logic_guards.md`**: hold the
  conceptual "why three guards, why YAML" narrative this document does not
  repeat; this document supplies the invariant-by-invariant enumeration those
  two corner docs reference but summarize.
- **`corners/fpf_bridge.md`**: treats `guards.sigma.passed` /
  `guards.gamma.passed` / `guards.theta.approved`/`.warnings` as pre-evaluated
  read-only closures — only safe because, as shown here, all three validators
  are pure functions over already-computed artifacts with no side effects of
  their own (the one exception being `core/guards/invariants.py`'s
  `enforce_invariants`, which is a different, non-triad guard that does mutate
  state, as noted above).
- **`core/math/core_math.py`**'s `check_conservation_pre_decay` and
  `check_shadow_non_creation` (documented in
  [`corners/core_math_contract.md`](../corners/core_math_contract.md)) are
  conceptually adjacent invariant checks that live closer to the propagation
  math itself rather than in the Sigma/Gamma/Theta triad — Hesperia's
  invariant-checking discipline is distributed across at least three separate
  locations (`sphere/guards/`, `core/guards/`, `core/math/core_math.py`), each
  guarding a different layer of the system.
