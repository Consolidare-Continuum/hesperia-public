# Layer 6 — Dynamical Stability Scaffold (39_SPEC)

Source: `core/layers/layer_6.py`, function `compute_L6`. 25 variables, named after five
distinct branches of applied mathematics — sensitivity analysis, differential
geometry, linear algebra, growth-curve fitting, and dynamical-systems/Lyapunov
stability theory. Downstream consumers, per the module docstring: L7 reads
`CONSIST_STABILITY_REGIME_VALID`-adjacent facts and `MAX_CHAOS_LEVEL`; L8 reads
`SI_GLOBAL_STABILITY`; L9 also consumes L6 output.

**This is the most stub-heavy layer documented so far, and it is documented as such
without softening.** The module docstring states the operating mode plainly: *"when
no perturbation, stub with 0/1.0."* As implemented today, only 2 of the 25 variables
are computed from live upstream data (`DEPTH_GROWTH_RATIO`,
`FIBONACCI_DEVIATION_SCORE`); two more are computed but only from those two plus a
constant (`GLOBAL_STABILITY_SCORE`, `CONCEPTUAL_COHERENCE_INDEX`); the remaining 21
are hardcoded identity or neutral-element constants assigned under the comment
`# I. No perturbation → 0 or identity`. This document treats the constants honestly
as a **scaffold** — a fixed, well-typed contract awaiting a live perturbation/Jacobian
source — not as completed measurements.

## What L6 receives

- `l1`: Layer 1 output — only `NORMALIZED_FAMILY_ENTROPY` is used.
- `l2`: Layer 2 output — `MASS_AT_DEPTH` (the per-BFS-depth mass profile documented
  in [`L2_topology_traversal.md`](L2_topology_traversal.md)) is the sole live input.
- `mass_at_depth`: optional override of L2's `MASS_AT_DEPTH`; falls back to
  `l2.get("MASS_AT_DEPTH")` then `[0.0]`.

No perturbation vector, Jacobian, or second baseline/shadow run is passed into
`compute_L6` at all — which is exactly why the sensitivity- and curvature-named
variables cannot be computed live: the data they would be computed *from* is not
part of this function's signature yet.

## Group I — Sensitivity analysis stubs (6 variables, all constant)

`INPUT_PERTURBATION_RESPONSE=0.0`, `DOMINANT_FAMILY_STABILITY=True`,
`COVERAGE_GRADIENT=0.0`, `ENTROPY_GRADIENT=0.0`, `STABILITY_RADIUS=1.0`,
`SECOND_ORDER_RESPONSE=0.0`.

The naming follows classical **sensitivity analysis** / perturbation theory: a
gradient is a first-derivative response to an input perturbation, a "second-order
response" is the next term in a Taylor expansion (Taylor, 1715) of system output
around an operating point. `STABILITY_RADIUS=1.0` reads as "radius of perturbation
the system can absorb before the dominant family changes" — set to its maximal/safe
default (1.0) in the no-perturbation path. None of these can be anything but their
declared constants without an actual perturbed input being run through the
pipeline a second time, the way L3 does for its baseline/shadow comparison.

**HES-MATH-BEHAV-54..57 (2026-08-05):** Gradient / curvature / Group-IV Newtonian
slots remain PARTIAL with `39_SPEC` formula notes in `layer_6.py` and
`L6_PARTIAL_*_SLOTS` inventory constants. Fill deferred until `E(x±ε)` is wired —
do not invent finite differences from `MASS_AT_DEPTH` alone.

## Group II — Curvature & rank stubs (6 variables, all constant)

`DOMINANCE_CURVATURE=0.0`, `ENTROPY_CURVATURE=0.0`, `HIT_VECTOR_RANK=1`,
`PRINCIPAL_COMPONENT_ENERGY_RATIO=1.0`, `CONDITION_NUMBER=1.0`, `SPECTRAL_GAP=0.0`.

These name four more distinct mathematical concepts, each with real lineage even
though none is computed here yet:

- **Curvature** (`DOMINANCE_CURVATURE`, `ENTROPY_CURVATURE`) — second-derivative
  shape of a response surface, differential geometry (Gauss, *Disquisitiones
  generales circa superficies curvas*, 1827).
- **Rank** / **principal component energy ratio** — linear algebra rank and PCA's
  explained-variance ratio (Pearson, 1901; Hotelling, 1933). `HIT_VECTOR_RANK=1`
  and `PRINCIPAL_COMPONENT_ENERGY_RATIO=1.0` are the trivial values for a
  single-vector/no-decomposition case — they assert "rank-1, 100% energy in one
  component" by default rather than computing an actual eigendecomposition.
- **Condition number** — numerical linear algebra's measure of how much a small
  input change can be amplified by a linear operator (Turing, 1948; Wilkinson,
  *Rounding Errors in Algebraic Processes*, 1963). `CONDITION_NUMBER=1.0` is the
  identity-operator value — perfectly well-conditioned.
- **Spectral gap** — the difference between the largest and second-largest
  eigenvalues of a graph's adjacency/Laplacian matrix, used in spectral graph
  theory to bound mixing rate and algebraic connectivity (Fiedler, 1973). `0.0`
  here is the neutral/undefined default, not a computed gap from L2's adjacency
  structure.

## Group III — Depth-growth curve fitting (4 variables, 2 live)

| Variable | Formula | Status |
|---|---|---|
| `DEPTH_GROWTH_RATIO` | `mass_at_depth[1] / (mass_at_depth[0] + eps)` if `len ≥ 2` and `mass_at_depth[0] > 0`, else `0.0` | **Live.** Ratio of L2's BFS mass at depth 1 to depth 0 — a discrete growth-rate measure, the simplest member of the exponential-growth-model family (cf. Malthus, 1798; Verhulst, 1838 for the continuous analogue). |
| `FIBONACCI_DEVIATION_SCORE` | `\|mass_at_depth[2] − (mass_at_depth[1] + mass_at_depth[0])\|` if `len ≥ 3`, else `0.0` | **Live.** Tests how far the depth-mass sequence deviates from the **Fibonacci recurrence** `F(n) = F(n-1) + F(n-2)` (Fibonacci, *Liber Abaci*, 1202). A zero score means the propagation mass at successive BFS depths happens to add like a Fibonacci sequence; this is a deviation-from-a-named-recurrence test, not a claim that propagation *should* be Fibonacci-shaped — it is one specific, falsifiable growth-shape hypothesis among the family fitted here. |
| `EXPONENTIAL_FIT_ERROR` | `0.0` (constant) | Reserved slot for a real exponential-curve least-squares fit error against `mass_at_depth`; not computed. |
| `POWER_LAW_FIT_ERROR` | `0.0` (constant) | Reserved slot for a power-law fit error (Zipf/Pareto-family curve fitting); not computed. |

The four together represent the standard toolkit for characterizing a discrete
growth/branching sequence by trying competing parametric shapes (linear ratio,
recurrence-based, exponential, power-law) — but only the two cheapest checks
(ratio and recurrence deviation) are actually evaluated against `mass_at_depth`
today.

## Group IV — Potential-field / dynamical-systems analogy (6 variables, all constant)

`POTENTIAL_GRADIENT=0.0`, `ESCAPE_ENERGY_THRESHOLD=1.0`,
`FORCE_ANALOG_MAGNITUDE=0.0`, `MONOTONICITY_CHECK=True`,
`FIXED_POINT_DETECTION=True`, `CYCLE_DETECTION_FUNCTIONAL=False`.

This group borrows classical-mechanics and dynamical-systems vocabulary as an
analogy for propagation behavior, consistent with the "potential landscape"
framing of zone weights already established in
[`geometry_math_coupling.md`](../corners/geometry_math_coupling.md):

- `POTENTIAL_GRADIENT` / `FORCE_ANALOG_MAGNITUDE` — the classical-mechanics
  relation force `= −∇U` (potential gradient), here named as an analogy for
  whatever "pushes" activation mass between zones, not a literal physical force.
- `ESCAPE_ENERGY_THRESHOLD` — analogous to activation energy / escape velocity:
  the energy needed to leave a local potential well. Default `1.0` is the
  maximal/no-escape-yet value.
- `MONOTONICITY_CHECK`, `FIXED_POINT_DETECTION`, `CYCLE_DETECTION_FUNCTIONAL` —
  qualitative dynamical-systems-theory questions about a trajectory (does it
  move monotonically, does it converge to a fixed point, does it enter a cycle),
  the discrete-system analogues of concepts from Poincaré's qualitative theory of
  differential equations (1881–1886). All three default to the "boring/stable"
  answer (monotone, fixed-point reached, no cycle) in the no-perturbation path.

## Group V — Lyapunov estimate & composite stability (3 variables, 2 derived)

| Variable | Formula | Status |
|---|---|---|
| `LYAPUNOV_ESTIMATE` | `0.0` (constant) | Reserved slot for a Lyapunov exponent estimate — the rate of divergence of nearby trajectories under iteration, the standard scalar measure of chaos (Lyapunov, *The General Problem of the Stability of Motion*, 1892; popularized for discrete/chaotic systems by Oseledec, 1968). `0.0` asserts neutral/stable (no exponential divergence) since no trajectory pair is available to estimate it from. |
| `GLOBAL_STABILITY_SCORE` | `1.0 / (1.0 + CONDITION_NUMBER + \|LYAPUNOV_ESTIMATE\|)` | **Derived**, but currently from two constants (`CONDITION_NUMBER=1.0`, `LYAPUNOV_ESTIMATE=0.0`), so it evaluates to a fixed `0.5` today. The functional form itself is meaningful and durable: stability decreases as ill-conditioning (`CONDITION_NUMBER`) and chaos (`|LYAPUNOV_ESTIMATE|`) increase, bounded in `(0, 1]` via a reciprocal — the same shape as classical robustness indices built from a reciprocal condition number. When real values are wired into `CONDITION_NUMBER`/`LYAPUNOV_ESTIMATE` (e.g. by L7/L8 supplying perturbed-run data), this formula starts producing a genuine composite without needing to change. |
| `CONCEPTUAL_COHERENCE_INDEX` | `STABILITY_RADIUS · (1 − NORMALIZED_FAMILY_ENTROPY) · GLOBAL_STABILITY_SCORE` | **Live**, the one fully computed composite in this layer (using L1's real `NORMALIZED_FAMILY_ENTROPY`). Unlike the additive convex-combination composites seen in L1/L3/L4/L5 (weighted sums to 1.0), this is a **multiplicative** combination of three factors each intended to lie in `[0,1]`: any one weak factor (high entropy, low stability radius, low global stability) pulls the whole index down disproportionately — a soft-AND rather than a weighted-average. This is a Hesperia-native composition choice; the multiplicative-conjunction pattern itself is the standard way to combine independent `[0,1]`-bounded confidence/quality factors (used broadly in reliability engineering, e.g. series-system reliability = product of component reliabilities). |

## Why ship a layer that is mostly constants

Documented honestly rather than silently treated as "done": the value of L6 in its
current form is the **stable 25-key contract** it gives to L7, L8, and L9. Those
downstream layers can already read `GLOBAL_STABILITY_SCORE`,
`CONCEPTUAL_COHERENCE_INDEX`, `DEPTH_GROWTH_RATIO`, and
`FIBONACCI_DEVIATION_SCORE` as real signals today, and can read the remaining 21
keys as safe, conservative defaults (no perturbation detected, system assumed
stable) without needing a code change in this layer once real perturbation/Jacobian
data becomes available. The naming was chosen up front to span sensitivity
analysis, differential geometry, linear algebra, growth-curve fitting, and
Lyapunov stability theory specifically so that the eventual live values have an
unambiguous, already-named mathematical home — this is forward scaffolding, not
filler picked for cosmetic completeness.

## Relationship to neighboring layers and corners

- **L1 → L6**: `NORMALIZED_FAMILY_ENTROPY` feeds `CONCEPTUAL_COHERENCE_INDEX`
  directly.
- **L2 → L6**: `MASS_AT_DEPTH` (documented in
  [`L2_topology_traversal.md`](L2_topology_traversal.md)) is the only live
  structural input, driving `DEPTH_GROWTH_RATIO` and
  `FIBONACCI_DEVIATION_SCORE`.
- **L6 → L7, L8, L9**: per the module docstring, L7 reads chaos/stability-regime
  facts, L8 reads `SI_GLOBAL_STABILITY` (presumably sourced from
  `GLOBAL_STABILITY_SCORE`), and L9 also consumes L6's output — not yet
  documented in this series.
- **Energy/propagation potential framing**: Group IV's potential-gradient
  language is the same conceptual register as the zone-weight "potential
  landscape" already documented in
  [`geometry_math_coupling.md`](../corners/geometry_math_coupling.md) — L6 names
  the dynamical-systems vocabulary for that landscape even though it does not yet
  compute live values from it.
