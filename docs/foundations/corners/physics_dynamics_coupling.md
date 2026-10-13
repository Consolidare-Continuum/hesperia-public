# Cross-cutting: physics, dynamics, propagation, activation, and traversal mathematics

This corner sits beside [`geometry_math_coupling.md`](geometry_math_coupling.md) as
the same kind of document for a different axis: where that file traces how
*shape* (icosahedral topology, hex substrate) constrains the math, this file
traces how *motion* — energy flow, mass diffusion, sequence-level traversal
dynamics — is actually computed, layer by layer, down to the named formula and
its external scientific lineage. It exists because the numbered-layer
documentation (`layers/L1`–`L9`) and the guard documentation
(`layers/GUARDS_sigma_gamma_theta.md`) each treat dynamics-adjacent material
(L6's stability scaffold, Gamma's execution-order checks) only as far as their
own layer's variables go. The actual physics — the functions that move mass,
energy, and trajectory state through the system — live one level down, in
`core/dynamics/`, `core/math/`, `sphere/propagation/`, and
`sphere/dynamism/`, and nothing in the layer docs traces them end to end. This
document is that trace.

## Why "physics" is the right word and not just a metaphor

Three of the four conserved-quantity disciplines a physical system obeys show
up here as *literal, checked* invariants, not loose analogy:

- **Mass/probability conservation** — `core/math/conservation.py`'s
  `check_mass_conservation` asserts `sum(after) ≈ sum(before)` within a
  relative tolerance (default `1e-6` at the math layer, `1e-5` at the
  propagation call site). This is the discrete analogue of a continuity
  equation: total activation mass is a conserved quantity across a diffusion
  step unless something explicitly declares a loss.
- **Energy conservation with named, audited loss terms** —
  `core/dynamics/operator.py`'s `compute_h_total` doesn't just compute an
  update, it computes `total_energy_before`, `total_energy_after`,
  `expected_decay_loss`, `actual_loss`, `forbidden_loss`, and an
  `energy_conservation_ok` boolean within a tolerance. A "forbidden loss" is
  energy that disappeared *for a reason the model doesn't account for* — the
  function distinguishes accounted-for decay from unaccounted-for leakage
  exactly the way a physics simulation distinguishes dissipation from a bug.
- **Boundedness via clamping, not by construction** —
  `core/dynamics/numeric.py`'s `clamp_energy` explicitly handles `NaN`/`Inf`
  (`math.isnan`/`math.isinf`) before bounding into `[0, 1]`. This is a
  numerical-physics discipline (a simulation that lets state escape into
  non-finite values is no longer simulating anything), applied here to a
  non-physical, Hesperia-native quantity ("activation energy").

That last point is the one to hold onto throughout this document:
**Hesperia borrows the conservation/clamping discipline of physics
simulation, not actual physical units.** "Energy," "mass," and "decay" below
are Hesperia-native quantities (concept-attribution weight, in effect) that
are *modeled with* the mathematics of physical conservation laws because that
mathematics is exactly the right tool for "a bounded quantity must not
silently leak or explode across a multi-step computation" — which is precisely
Hesperia's actual requirement.

## Layer 1 of the physics: the per-node energy update law

`core/dynamics/operator.py`, function `compute_h_total`:

```
H_total = H_self + H_coupling − H_inhibition

H_self       = v · (1 − decay)
H_coupling   = coupling_alpha · mean(all v)
H_inhibition = inhibition_alpha · v
```

Three named terms, three different physical lineages:

- **`H_self` (self-decay term)** — exponential-style decay of a node's own
  prior value. The discrete-time form `v·(1−decay)` is the first-order
  (Euler) discretization of the canonical decay ODE `dv/dt = −decay·v`, the
  same equation that governs radioactive decay, RC-circuit discharge, and
  every leaky-memory model in computational neuroscience.
- **`H_coupling` (mean-field coupling term)** — every node is pulled toward
  the *global mean* of all node values, scaled by `coupling_alpha`. Coupling a
  unit to the population average rather than to its literal neighbors only is
  the defining move of **mean-field theory** (Weiss, 1907, the original
  mean-field treatment of ferromagnetism — the Curie–Weiss model) — each spin
  feels an effective field that stands in for the influence of every other
  spin, rather than computing all pairwise interactions directly. Hesperia
  uses the identical simplification for tractability: an O(1) "feel the
  crowd" term instead of an O(n²) all-pairs interaction term.
- **`H_inhibition` (linear inhibition term)** — `inhibition_alpha · v`, i.e. a
  node's own value subtracted in proportion to itself. This is structurally
  the leak term of a **leaky integrate-and-fire neuron** (Lapicque, 1907, the
  founding model of integrate-and-fire dynamics): a membrane potential that
  decays toward rest proportionally to its own magnitude, the same
  self-damping shape reused here for activation rather than voltage.

The `H_total = self + coupling − inhibition` composition is additive (a
direct field superposition, the same structural move as superposing forces in
classical mechanics), which is why the energy-accounting fields
(`expected_decay_loss` etc.) can be computed in closed form from the same
three terms rather than needing a separate accounting pass.

## Layer 2 of the physics: diffusion as a lazy random walk

`core/math/diffusion.py`'s `diffuse_step` (re-exported as `diffuse_once` at
`sphere/propagation/diffusion.py`):

```
v' = (1 − alpha)·v + alpha·(v @ W)
```

This is not an arbitrary blend — it is the textbook **lazy random walk**
update, and with `W` row-stochastic it is exactly the **personalized
PageRank** iteration (Page & Brin, *The PageRank Citation Ranking*, 1998):
with probability `(1−alpha)` mass stays put, with probability `alpha` it
takes one step along the graph according to `W`'s transition probabilities.
`alpha` here plays the role PageRank calls the "teleportation"/"damping"
parameter, just inverted in convention (Hesperia's `alpha` is the
*move* probability; PageRank's `d` is usually quoted as the *stay-on-link*
probability) — same mechanism, opposite-labeled knob.

`core/math/normalization.py`'s `normalize_l1` (sum-to-1 normalization) and
`core/math/matrix_utils.py`'s `row_normalize` (each row of `W` sums to 1) are
what make `W` row-stochastic in the first place — without them `v @ W` would
not conserve mass, and the lazy-random-walk reading above would not hold
mathematically, only resemble it cosmetically. `sphere/propagation/
weighting.py`'s `build_edge_weight_matrix` builds `W` from the geometry's
adjacency so that "mass flows only along edges (no adjacency → no
diffusion)" — i.e., `W`'s support is exactly the icosahedral adjacency
structure documented in `geometry_math_coupling.md`; this document and that
one describe the same matrix from two different angles (this one: what
operation is performed with it; that one: where its entries come from
geometrically).

### Multi-step diffusion: Markov-chain power iteration

`core/math/transition_matrix.py` builds the **discrete-time Markov chain**
machinery directly: `compute_transition_matrix` counts raw `a_t → a_{t+1}`
transitions (Markov, 1906, the original finite-state stochastic-process
formalism), and `compute_transition_probabilities` row-normalizes those
counts into an actual stochastic transition matrix. `sphere/propagation/
multi_step_diffusion.py`'s `propagate_k_steps`:

```
v_k = v @ W^k          (np.linalg.matrix_power)
```

is the **Chapman–Kolmogorov equation** (Chapman, 1928; Kolmogorov, 1931) in
its simplest discrete form: the k-step transition distribution is the
single-step transition matrix raised to the k-th power. `iterative_diffusion`
computes the same quantity by repeated single-step application instead of
matrix exponentiation — the docstring is explicit that the two are
mathematically equivalent at `alpha`-weighted single steps, exposed as two
APIs (closed-form power vs. iterative) for different callers' convenience,
not two different physical models.

`propagation_depth_metric` tracks the sequence `v, vW, vW², ...` and computes
consecutive L1 distances plus an entropy sequence — i.e., it watches *how
fast the walk mixes toward its stationary distribution* and how disordered it
becomes while doing so, the standard diagnostic pairing (distance-to-previous
+ entropy trend) used to characterize Markov chain mixing behavior.

### Feedback control on the diffusion rate itself

`sphere/propagation/weighting.py` does not treat `alpha` as fixed; it
modulates it by two opposing feedback rules:

```
effective_alpha (stability) = base_alpha · (1 − k_stability · stability_index)   [k_stability = 0.5]
effective_alpha (jump)      = base_alpha · (1 + k_jump · jump_rate)              [k_jump = 0.3]
```

applied in a fixed, documented order (stability modulation first, then
jump-rate modulation, per `compute_effective_diffusion_rate`). These are
literal **negative and positive feedback loops** in the cybernetic sense
(Wiener, *Cybernetics: Or Control and Communication in the Animal and the
Machine*, 1948, the founding text distinguishing stabilizing/negative from
amplifying/positive feedback in any control system, biological or
mechanical): high `stability_index` *suppresses* diffusion (a structurally
stable trajectory doesn't need to keep spreading mass), while high
`jump_rate` *amplifies* diffusion (a volatile trajectory gets more mixing,
not less). The deterministic application order means the two feedback terms
are not symmetric — stability damping is computed against the base rate,
then jump amplification is computed against the already-damped rate, not
against the original base rate independently.

`build_meta_filtered_edge_weights` applies a third, purely structural
modulation: the icosahedron's two pole/meta vertices (indices 5 and 11 — A6
and A12, per `geometry_math_coupling.md`) get a flat `scale=0.5` reduction on
incident edge weight. This is a static geometric correction (pole vertices
have a different local degree/curvature than the ten equatorial vertices),
not a feedback term — it does not depend on run-time state the way the
stability/jump modulations do.

## Layer 3 of the physics: trajectory-level dynamics (the L6 engine)

`sphere/dynamism/dynamism_engine.py`'s `compute_dynamism` is explicitly
labeled in its own docstring as the **Layer-6 entrypoint** — it is the real
computational engine behind the L6 variables that
[`L6_dynamical_stability_scaffold.md`](../layers/L6_dynamical_stability_scaffold.md)
documents as "live" (as opposed to the 21 no-perturbation constants in that
same layer). `sphere/dynamism/{curvature,jump_rate,stability,trajectory,
transition_matrix}.py` are all thin re-export shims; the actual formulas live
in `core/math/`:

| Quantity | Formula (`core/math/...`) | Lineage |
|---|---|---|
| `compute_curvature` | mean step-score over transitions: same-area → 0, adjacent move → 1, non-adjacent move → 2 | A coarse discrete proxy for path curvature — *not* a rigorous Ricci/Ollivier-Ricci discrete curvature (no edge-weight or neighborhood-overlap computation involved); the term names the *intent* (how sharply a trajectory bends relative to the graph's adjacency structure), not a literal instance of discrete differential geometry. Worth being precise about: this is a Hesperia-native heuristic borrowing the *name* "curvature" for a 3-level adjacency-aware step score. |
| `compute_jump_rate` | `jump_count / total_transitions`, jump = non-adjacent transition | Simple ratio/frequency statistic — no external lineage beyond elementary probability (relative frequency as probability estimate). |
| `compute_stability_index` | `repeated_stays / total_transitions` (self-loop frequency) | Same elementary-frequency lineage as jump rate; structurally the complement of "how often does the trajectory move at all." |
| `compute_structural_tension` | `1 − max(area_vector)/sum(area_vector)` | A **dominance/concentration** measure — the complement of the largest-share-of-total statistic used in concentration indices (the same family as the Herfindahl–Hirschman Index's underlying "share of total" building block, though Hesperia uses max-share rather than HHI's sum-of-squared-shares). Low tension = one area dominates; high tension = balanced competition across areas. |
| `compute_transition_matrix` / `compute_transition_probabilities` | raw count matrix, then row-normalized | Same Markov transition-matrix construction described above, applied here at trajectory-analysis time rather than diffusion time — one formula, two call sites. |
| `build_trajectory` / `compress_trajectory` | identity passthrough; run-length-encode consecutive repeats (optionally into `{area, length}` segments) | Standard run-length encoding — a lossless compression of "stayed in area X for N steps" into one record, the same technique used in basic data compression and in describing piecewise-constant signals. |

`compute_dynamism` validates `area_sequence` values lie in `[0, 11]` (the
12-area structure) and orchestrates all five sub-computations from one
ordered sequence and one adjacency matrix; a length-1 sequence deterministically
zeroes every metric (no transitions exist to measure), and an empty sequence
is a hard `ValueError` rather than a silent zero — the same "fail loud on
genuinely undefined input, fail quiet (to zero) on merely degenerate input"
discipline seen elsewhere in the numbered layers.

## Activation: where mass enters the dynamical system

"Activation" in this corner refers to the same concept-attribution weight
that `corners/lexicon_resolver.md` and `corners/hex_substrate.md` describe as
entering the system through controlled-lexicon matching — this document picks
up exactly where those leave off: once an area/hex vector has non-zero mass,
`core/math/vector_ops.py`'s `detect_dominant_area`/`detect_dominant_family`
(`argmax`, lower-index tie-break) and `detect_family_peaks` (top-k by count,
stable `(-count, index)` sort) are the deterministic primitives that turn a
raw activation vector into "which area/family actually carries this signal" —
tie-breaking by lower index rather than, say, by random choice or insertion
order is itself a determinism-preserving design decision, consistent with
every other tie-break rule already documented across L1–L9.

`core/math/entropy_metrics.py`'s `compute_entropy` (Shannon entropy, base 2 —
Shannon, *A Mathematical Theory of Communication*, 1948) and
`compute_normalized_entropy` (entropy divided by `log2(N)`, bounding the
result to `[0,1]` regardless of vector length) are the activation-side
counterpart to the propagation-side entropy tracking in
`propagation_depth_metric` above: the same formula, applied once to a raw
activation distribution (how concentrated is attribution before any
diffusion happens) and once to a sequence of post-diffusion states (how does
concentration change as mass spreads). This is the same entropy machinery
[`L1_structural_activation_census.md`](../layers/L1_structural_activation_census.md)
already documents as computed at the L1 census stage — confirming L1's
entropy figure and the propagation engine's entropy tracking are the same
formula reused at two different points in the pipeline, not two independently
invented entropy measures.

## Traversal: BFS structure vs. diffusion — two distinct "movement" models

It is worth being explicit that Hesperia has **two unrelated notions of
movement** that this corner's title groups together but that must not be
conflated:

1. **Traversal (L2, `layers/L2_topology_traversal.md`)** — a one-shot,
   deterministic **breadth-first search** from the dominant family to depth
   8, used to assess topology risk (reachability, clustering coefficient,
   circuit rank) *before* any diffusion happens. This is discrete graph
   search — no mass, no probability, no iteration count beyond a fixed depth
   bound.
2. **Propagation/diffusion (this document, Layers 1–3 above)** — a
   continuous-valued, iterative mass-redistribution process governed by the
   diffusion/PageRank/Markov-chain mathematics above, which happens *after*
   traversal has already characterized the graph's shape.

BFS traversal answers "what is reachable, and how is it shaped"; diffusion
answers "given that shape, how does mass actually move through it
quantitatively." The two are sequenced (traversal informs L2's risk
variables before L6's dynamism, propagation, and shadow correction ever
touch the graph) but are mathematically unrelated techniques — BFS has no
notion of conserved mass or stochastic transition probability, and diffusion
has no notion of "depth" in the BFS sense (`propagation_depth_metric`'s
"depth" is the diffusion step index `k` in `v @ W^k`, an entirely different
quantity from L2's BFS hop-depth, despite the name overlap — a naming
collision worth flagging in the same spirit as the `layer_9` collision
documented in `logic_guards.md`).

## Relationship to neighboring corners

- **[`geometry_math_coupling.md`](geometry_math_coupling.md)** — that
  document explains where `W`'s entries (the adjacency-derived edge weights)
  come from geometrically; this document explains what is computed *with*
  `W` once it exists (diffusion, k-step propagation, feedback-modulated
  diffusion rates). Read together they give the complete picture: geometry
  fixes the matrix, dynamics defines the operator applied to it.
- **[`propagation_dynamics.md`](propagation_dynamics.md)** — the pre-existing
  conceptual framing of propagation (`dc/dt = −αLc`, Laplacian dynamics) and
  the propagation/shadow-correction split. This document is the
  implementation-level continuation of that framing: every formula here
  (`diffuse_step`, `propagate_k_steps`, the feedback-modulated `alpha`,
  `compute_dynamism`) is the literal code computing the dynamics that
  document describes architecturally, now traced to its exact source
  location and named scientific lineage.
- **[`layers/L6_dynamical_stability_scaffold.md`](../layers/L6_dynamical_stability_scaffold.md)** —
  confirms that L6's four "live" variables
  (`DEPTH_GROWTH_RATIO`, `FIBONACCI_DEVIATION_SCORE`,
  `GLOBAL_STABILITY_SCORE`, `CONCEPTUAL_COHERENCE_INDEX`) are computed
  upstream of, and fed by, `compute_dynamism`'s curvature/jump-rate/
  stability/trajectory outputs documented here — L6's own source file is the
  scaffold; `sphere/dynamism/` + `core/math/` is where the numbers it
  scaffolds around actually come from.
- **[`layers/GUARDS_sigma_gamma_theta.md`](../layers/GUARDS_sigma_gamma_theta.md)** —
  Sigma's matrix/vector shape checks (`SIGMA_003`/`004`: 12×12 symmetric
  adjacency) are preconditions this document's `W`-construction code assumes
  hold; Gamma's execution-order and no-illegal-mutation checks are what make
  it safe to assume a diffusion step actually ran on unmutated upstream
  state before its conservation check (`check_mass_conservation`) is
  evaluated.
- **`core/dynamics/constants.py`'s `get_constant`** — both `compute_h_total`
  and the propagation-weighting functions read tunable constants (decay
  rates, `coupling_alpha`, `inhibition_alpha`, `k_stability`, `k_jump`) from
  `assets/config/engine_constants.json` through this single accessor rather
  than hardcoding them in the formula modules — the same "policy/threshold as
  data, not as code" discipline already established for `logic_rules.yaml`
  and `theta_governance_rules.yaml` in `logic_guards.md`, applied here to
  physical-dynamics tuning constants instead of governance thresholds.
