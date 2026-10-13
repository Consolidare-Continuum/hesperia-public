# Corner: Core Math Contract (`core/math/core_math.py` — pre-v0.4, still load-bearing)

**Provenance:** `22_SPEC__V0_3_Core_Math_Contract_v1_0.md` (v0.3 era, on `backup/hesperia-mrt-fork`,
not mirrored into the main line's `docs/` tree). `core/math/core_math.py`'s own docstring states the
relationship directly: **"HESPERIA v0.3 — minimal reference implementation of 22_SPEC (Core Math
Contract v1.0)."** This is not historical-only material — it is live, current code, imported by
`runtime/pipeline/analyze.py`. It predates, and is the actual computational substrate underneath,
several modules described elsewhere in this package (`corners/propagation_dynamics.md`,
`corners/shadow_correction.md`, `corners/guards.md`) at the level of "why this layer exists" without
previously naming the exact formulas. This file closes that gap.

## The architectural law this corner enforces: math lives in exactly one place

`tests/architecture/test_no_math_in_sphere.py` is a CI-enforced rule, not a convention: **`sphere/*`
must not implement math; it must call `core.math`.** The test greps `sphere/` for forbidden
patterns — `np.sum`, `np.dot`, `np.matmul`/`@`, `np.argmax`, `math.log`/`log2` — and fails the build
if any appear outside `core/math/`. This is the same single-source-of-truth discipline as Sigma's
guard verdicts being carried forward rather than recomputed (`corners/fpf_bridge.md`), applied one
level deeper: not just "don't recompute a verdict," but "don't even have a *second place capable of*
computing a number that should only ever be computed one way." Every entropy, every sum, every
matrix multiply in the entire structural pipeline traces back to this one module.

## §3–§7: fusion, centroid selection, diffusion, shadow propagation, aggregation

| Term | Formula | Constants (defaults) |
|---|---|---|
| **Fusion** (`fusion`, §3) | `E0[i] = clamp(α·S'[i] + (1−α)·L'[i], 0, E_cap)`, where `S'`, `L'` are `S`, `L` each normalized to sum to 1 | `alpha = 0.65`, `E_cap = 1.0` |
| **Centroid selection** (`centroid_indices`, §4) | Top-`K` indices of `E0` above threshold `η`, tie-broken by smaller index | `eta = 0.02`, `K_max = 5` |
| **Base traversal step** (`base_step`, §5) | `D = (1−λ)·E + λ·(E·W)`; `E_next = clamp(D·(1−decay), 0, E_cap)` — a row-stochastic transition matrix `W` blended with self-retention, then decayed | `lambda = 0.55`, `decay = 0.04` |
| **Shadow step** (`shadow_step`, §6) | `E_shadow = E·Ws` — propagation through a *separate* shadow transition matrix `Ws` | — |
| **Aggregation** (`aggregate_dominant_family_area`, §7) | Rolls per-side energy up to dominant family/area, the same area/family coordinate system as `corners/topology_geometry.md` | — |

`E0`/`S`/`L` is the precise pre-v0.4 name for what later corners call Dict A / Dict B activation
fused into a single energy vector (`corners/lexicon_resolver.md`) — same concept, earlier
terminology. `base_step`'s `(1−λ)E + λ(EW)` is mathematically a discrete-time relative of the
continuous graph-Laplacian diffusion (`dc/dt = −αLc`) documented in `corners/propagation_dynamics.md`
— both blend a node's own value with its neighbors' via a fixed, versioned weight, both are
deterministic, but they are not the same equation: one is an explicit row-stochastic matrix step,
the other a continuous-time Laplacian. Whether the current production propagation path computes
through this exact function or an equivalent reimplementation in `sphere/propagation/` was not
fully traceable from this read; what is certain (per the architecture test above) is that whichever
path runs, it is required to delegate the underlying arithmetic to `core.math`, not reimplement it.

## §8–§11: the four penalties

Each penalty is an independent, named failure mode, summed (not multiplied) into a single
governance score — additive penalties so each can be reasoned about and tuned in isolation:

| Penalty | Formula | What it punishes | Constants |
|---|---|---|---|
| **Ambiguity** `P_amb` (§8) | `gap = (e1−e2)/(e1+ε)`; `P_amb = k_amb·(1−gap)²` | the top-1 and top-2 activated sides being too close in energy — no clear winner | `k_amb = 0.35`, degraded if `gap < delta_gap = 0.08` |
| **Thin-core** `P_thin` (§9) | `CoreShare = sumS/(sumS+sumL+ε)`; `P_thin = k_thin·(1−CoreShare)` | too much of the fused energy coming from `L` (Dict B) relative to `S` (Dict A) — a "thin" surface-evidence core | `k_thin = 0.30`, degraded if `CoreShare < tau_core = 0.25` |
| **Dispersion** `P_disp` (§10) | normalized Shannon entropy of `E_end` over active sides: `P_disp = k_disp·H_norm`, `H_norm = H/ln(M)` | energy spreading too thin across too many sides instead of concentrating | `k_disp = 0.25` — **the same Shannon-entropy tool documented in `provenance.md`**, reused here rather than reinvented |
| **Guard** `P_guard` (§11) | `P_guard = clamp(k_guard·(sigma_fail+gamma_violation+theta_reject), 0, 1)` | any Sigma/Gamma/Theta failure directly taxes the governance score — guard failures aren't just gates, they're penalized inputs to the composite metric | `k_guard = 0.30` |
| **Shadow** `P_shadow` | `k_shadow·(shadow_hops/max_shadow_hops)` | how many shadow-propagation hops were needed — more hops, more penalty | `k_shadow = 0.40`, `max_shadow_hops = 2` |

## §12: the composite metrics, and the clearest "parameters combined" example in the repo

```
metric_governance = clamp(1 − (P_amb + P_thin + P_shadow + P_disp + P_guard), 0, 1)
```

This is a single number — **1 minus the sum of five independent penalty signals** — meant to answer
"how healthy is this structural read, overall." It is the pre-v0.4 ancestor of the same instinct
behind KME's composite metrics (`corners/kme.md`) and TRIZ's `innovation_score`
(`corners/triz_extension.md`): take several orthogonal, individually-meaningful signals and combine
them into one number a downstream consumer can threshold on, while keeping every contributing term
inspectable.

`metric_obstacle_score` is an even more explicit worked example of weighted parameter combination:

```
obstacle_score = w_decay·Loss + w_guard_obs·clamp(GuardCount,0,1) + w_shadow_obs·(shadow_hops/max_shadow_hops)
```

with `w_decay=0.50`, `w_guard_obs=0.30`, `w_shadow_obs=0.20` — **a convex combination whose weights
are required, by `validate_config` (§16), to sum to exactly 1.0 ± 1e-6.** This is not a soft
convention; building a config where the three obstacle weights don't sum to 1 fails CI. Three
different failure signals — energy loss, guard pressure, shadow-hop cost — are deliberately
proportioned (half from decay loss, three-tenths from guard pressure, two-tenths from shadow cost)
rather than weighted equally, encoding a judgment about which failure mode matters most to an
"obstacle" reading.

`metric_tension_energy` (`F = family energies`; `tension_energy = 1 − gapF`, gap between the top two
family energies) is the direct, name-preserved ancestor of `tension_energy` as it appears today in
17 files across `hesperia/engine/output_trace.py` and `core/propagation/{guard_pipeline,
invariant_enforcer, output_contracts, shadow_layer}.py` — one of the few v0.3-era metric names that
survived essentially unchanged into the current pipeline.

## How and why "Markov" — and the honest terminology boundary

`base_step`'s diffusion equation has the literal shape of a Markov chain step. `make_demo_W`'s own
docstring states it plainly: **"Row-stochastic n × n (uniform outflow)"** — a row-stochastic matrix
is precisely the transition-probability matrix of a finite-state Markov chain (each row sums to 1,
describing where a unit of "mass" at state `i` redistributes to on the next step). `base_step`
applies `D = (1−λ)E + λ(EW)` — a **lazy Markov chain** formulation: instead of fully transitioning
via `W` each step, a `(1−λ)` fraction stays put and only `λ` actually moves along the transition
matrix. This "laziness" is a standard, well-known technique (not a Hesperia invention) for keeping
a chain aperiodic and well-behaved under iteration — and `core/math/core_math.py` does iterate it,
`T_steps = 8` times per run, exactly as one would iterate a Markov chain forward from an initial
distribution `E0` to see where mass ends up after a fixed number of steps.

**Why this shape, specifically:** a Markov-chain-style update is the natural mathematical form for
"redistribute a bounded quantity across a fixed graph in a way that depends only on the current
state, not the full history" — which is exactly what energy propagation needs (`base_step` doesn't
need to remember every prior step, only the current `E`). It also composes cleanly with the
conservation checks below: a row-stochastic matrix step preserves total mass *by construction*
(before decay), which is precisely what `check_conservation_pre_decay` verifies.

**What this is not, and the project's own discipline about saying so:** this is a deterministic
application of a Markov-shaped equation with fixed, hand-set weights — not a fitted statistical
Markov model, and not a Hidden Markov Model with inferred latent states or likelihood estimation.
The project's own internal scientific-alignment guidance (brain repo,
`operational/assignments/reports/ETHAN-HESPERIA-SCIENTIFIC-ALIGNMENT-BOOKS-REDISCOVERY-2026-03-25.md`)
states this exact boundary explicitly: *"session segmentation + transitions are framed as
discrete-time state sequence analysis. Use 'Markov-like' unless a full HMM likelihood model is
implemented."* The same discipline applies here: `base_step` and the dynamics-layer `state_sequence`/
`transitions` machinery (`corners/propagation_dynamics.md`, `corners/interpretation_usf.md`) are
correctly described as **Markov-like** — they have the structural property (next state depends
only on current state plus a fixed transition rule) — but calling them "a Markov chain model" would
overclaim a probabilistic apparatus (stationary-distribution analysis, estimated transition
probabilities, likelihood-based inference) that was never built. The same overclaim discipline
`provenance.md` applies to Kolmogorov applies here: name the real mathematical shape, don't borrow
the prestige of the fuller statistical framework that isn't actually implemented.

## Conservation invariants: physics-style laws, enforced as code

- `check_conservation_pre_decay`: after a base step's diffusion (`E·W`) but before decay is applied,
  total energy must be conserved within `energy_conservation_tolerance = 1e-6` — diffusion
  redistributes energy across sides, it does not create or destroy it.
- `check_shadow_non_creation`: shadow propagation's total output energy must not exceed total input
  energy (`sum(E_shadow) <= sum(E) + ε`) — the shadow mechanism may move or suppress energy, never
  manufacture it.

These are the literal, code-level realization of the "mathematically honest" framing already used
in `corners/propagation_dynamics.md` for the production diffusion stage — here it's not a framing
choice, it's an assertion checked at runtime.

## What did *not* survive from the earlier (v0.2 / early-v0.3) math exploration

A separate, richer formalization exists on `backup/hesperia-mrt-fork` at
`21_MATH__HESPERIA_formalization_v1_1_java.txt` (394 lines), predating or running parallel to
22_SPEC, defining: bipolar activation axes and tension energy as `Σ B[k]²` (a *different* tension
formula than the one that survived), KL divergence and cosine similarity between distributions,
a four-constant exponential decay model for "context integrity" (`ALPHA=0.35, BETA=0.30,
GAMMA=0.25, DELTA=0.20`), turn-to-turn coherence and cumulative drift via cosine similarity, and
**Fourier/DFT-based "ring smoothness"** over a 12-area ring. A direct `grep` check against the
current codebase: `fragIndex`, `areaEntropy` (as a named function), `bipolar`, `ringSmoothness`,
`decayRate`/`contextIntegrity`, `turn_coherence`, `cumulative_drift`, and `kl_divergence` — **zero
matches anywhere in `.py`.** Only `tension_energy` (renamed formula) and `cosine_similarity` (now
living in `core/domain/fingerprint.py`, repurposed for fingerprint comparison rather
than turn-to-turn drift) persisted. The honest reading: 21_MATH was a broader exploratory
formalization than what 22_SPEC actually committed to building — the DFT ring-smoothness idea in
particular never got an implementation to grep for. Record it here as real, dated intention that
did not become the shipped contract, per the same discipline `provenance.md` applies to BELL/`path_mass`.

## Relationship to neighboring corners

- Is the computational substrate `corners/propagation_dynamics.md` and `corners/shadow_correction.md`
  describe at the level of intent — this corner supplies the exact formulas and constants.
- `P_guard`'s direct dependence on Sigma/Gamma/Theta failure counts is a second, earlier-era
  instance of guard verdicts feeding a downstream composite score, alongside `corners/fpf_bridge.md`'s
  FGR-gated evidence (`parameter_synergies.md` §3–4).
- `provenance.md` and `references.md` should be read alongside this file for the Shannon-entropy
  sourcing of `P_disp` and the explicit Kolmogorov non-adoption finding.
