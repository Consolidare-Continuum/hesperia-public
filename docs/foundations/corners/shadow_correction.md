# Corner: Shadow Correction (`sphere/shadow/`, Layer 8)

## Why this corner exists at all

Diffusion-based propagation (see `corners/propagation_dynamics.md`) is
mathematically correct but operationally noisy: it spreads weak, possibly
spurious activation just as readily as it spreads strong, well-evidenced
activation, and it monotonically increases entropy relative to the original
sparse signal. Left unmitigated, a single ambiguous lexical match could, after
diffusion, look indistinguishable from a strongly and repeatedly evidenced
theme. Shadow correction exists to restore the distinction between "this
region of meaning is genuinely dominant" and "this region got some diffuse
spillover," without touching the propagation math itself (the propagated
artifact stays separate from the corrected one — this is exactly what Gamma
invariant `GAMMA_003 raw_propagated_separation` enforces).

## Why three distinct sub-mechanisms (suppression, dominance reinforcement, entropy correction) instead of one blended formula

Each mechanism corrects a different, independent failure mode of diffusion,
and conflating them into a single tunable parameter would make it impossible
to diagnose which failure mode is dominating a given anomalous result:

- **Tail suppression** (`suppression.py`) removes activation below a
  structural noise floor — diffusion's tendency to leave a faint trace
  everywhere, including areas with no real lexical support.
- **Dominance reinforcement** (`dominance_filter.py`) counteracts diffusion's
  tendency to flatten a genuinely concentrated signal toward uniformity, by
  re-boosting whichever area was already dominant before correction.
- **Entropy correction** (`entropy_correction.py`) is the most structurally
  interesting of the three: it explicitly measures entropy before and after
  diffusion and, if entropy rose above a fixed bound
  (`max_entropy_increase=0.1`), blends the corrected vector back toward a more
  peaked distribution. This is a direct, bounded counter-measure against
  diffusion's known mathematical side effect (heat-equation-style smoothing
  always increases entropy on a connected graph unless the input was already
  uniform) — it does not try to prevent the side effect, it caps it.

Keeping these as three separately testable functions, each consuming only
`core.math` primitives, means a regression in any one of them is locally
attributable rather than buried inside one large heuristic.

## Why this had to be a deterministic, rule-bounded correction rather than a learned denoiser

A learned denoising model would need training data defining "correct" shadow
correction, which doesn't exist independent of the system's own outputs
(there is no external ground truth for "how much should entropy be allowed to
rise"). More importantly, a learned correction would reintroduce exactly the
opacity problem the whole architecture exists to avoid — Hesperia would no
longer be able to explain a downstream interpretation by tracing it through a
chain of explicit transformations. The fixed thresholds
(`structural_threshold=0.01`, `dominance_boost_factor=0.2`,
`entropy_blend_strength=0.2`) are visible, versioned constants precisely so
that any output can be reproduced and explained from the formula alone.

## Relationship to neighboring corners

- Sits directly between `corners/propagation_dynamics.md` (input) and
  `corners/logic_guards.md`'s Layer-9 rule engine plus `corners/interpretation_usf.md`'s
  state classifier (consumers — both read `shadow_metrics.corrected_area_vector`
  and `shadow_diagnostics` as their primary structural facts).
- Its diagnostics (`shadow_diagnostics`, including `entropy_before`/`entropy_after`)
  are what later layers — including, eventually, fpf_bridge's evidence mapper
  — use to calibrate confidence (FGR) per piece of evidence, since a result
  that needed heavy shadow correction is structurally less crisp than one that
  needed none.
