# Corner: Propagation and Dynamism (`sphere/propagation/`, `sphere/dynamism/`, `core/operator/`, `core/dynamics/`)

## Why this corner exists at all

A resolved concept hit is a point event — one span, one moment. But the
quantities Hesperia needs to report (governance, tension, loopability,
structural state) are properties of a whole discourse, not of single spans.
Something has to turn a sparse set of point activations into a continuous-ish
field that can be measured, and something has to turn a sequence of such
fields (across sentences or turns) into trajectory features. Propagation does
the first job; dynamism does the second. Neither can be folded into the
resolver (which only knows about one span at a time) or into interpretation
(which needs the field to already exist before it can classify it).

## Why propagation must be a deterministic diffusion process, not a learned one

The design memo explicitly grounds propagation in graph diffusion: with
adjacency matrix A and degree matrix D, the Laplacian L = D − A defines
dynamics like dc/dt = −αLc. This is the standard formalism for "spread a
signal across a graph's neighbors in proportion to its structure," and it is
chosen specifically *because* it is deterministic and parameterized by fixed,
versioned weights rather than learned ones. `specs/canon/propagation_weights.yaml`
encodes this directly: zone weights (`center_to_inner: 0.25`, etc.), a fixed
`bridge_weight` for cross-area edges, and decay factors — all checked into
canon as data, not inferred at runtime. If propagation weights were learned or
tuned silently inside code, two runs of the same text could diverge for
reasons no one could audit; keeping them in YAML makes every propagation run
reproducible from the weights file alone, and makes weight changes a
reviewable diff rather than a retraining event.

## Why propagation and shadow correction are separate layers (see also `corners/shadow_correction.md`)

Propagation's job is to spread evidence outward along real structural edges.
Left alone, that spreading process introduces a side effect: it raises entropy
(a few sharp activations become many faint ones), which is mathematically
correct but operationally undesirable — it would make every text look "more
diffuse" than its actual lexical evidence supports, purely as an artifact of
the diffusion math. Rather than tune diffusion weights to under-spread (which
would silently reintroduce sparsity problems elsewhere), the system keeps
propagation mathematically honest and adds a distinct, explicitly-named
correction stage afterward. This separation is what lets each stage be tested
and reasoned about independently: propagation's job is "is the diffusion math
correct," shadow correction's job is "is the diffusion's side effect bounded."

## Why dynamism (curvature, jump rate, trajectory, stability) is a distinct module from propagation

Propagation answers "what does the field look like right now." Dynamism
answers "how is the field changing across the sequence of texts/turns
processed so far." These require fundamentally different state: propagation
is stateless per call (same input, same field), while dynamism necessarily
carries history (a trajectory needs at least two points). Mixing the two would
force propagation to become stateful, which would break the per-call
determinism guarantee that downstream invariants (Gamma's
"deterministic_flag_true") depend on. Keeping dynamism as a layer that
*consumes* a sequence of already-deterministic propagation outputs, rather
than computing trajectory inline, is the structural reason curvature and jump
rate can be computed and tested without re-running the underlying pipeline.

## Exhaustive formula-by-formula treatment

For the exact diffusion/energy/trajectory formulas referenced above (the
`(1−alpha)v + alpha·vW` diffusion step, `v@W^k` multi-step propagation, the
`H_total = H_self + H_coupling − H_inhibition` energy law, the
stability/jump-rate feedback modulation of the diffusion rate, and the
curvature/jump-rate/stability/trajectory dynamism metrics), each traced to its
exact source function and named scientific lineage (mean-field theory,
leaky-integrate-and-fire, PageRank, Chapman-Kolmogorov, cybernetic
feedback), see
[`physics_dynamics_coupling.md`](physics_dynamics_coupling.md) — written as
the dynamics-axis counterpart to `geometry_math_coupling.md`'s shape-axis
treatment of the same matrices.

## Relationship to neighboring corners

- Consumes resolved concept evidence projected into hex/family space from
  `corners/hex_substrate.md`.
- Feeds `corners/shadow_correction.md` directly (propagated vectors are the
  shadow engine's only input).
- Feeds `corners/logic_guards.md`'s Layer-9 rule engine and `corners/interpretation_usf.md`'s
  state classifier, both of which read dynamism metrics (`stability_index`,
  curvature, jump rate) as facts rather than recomputing them.
- Its determinism is exactly what Gamma invariants (`GAMMA_006
  propagated_lengths_match_raw`, `GAMMA_008 deterministic_flag_true`) exist to
  check.
