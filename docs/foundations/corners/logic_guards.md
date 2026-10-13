# Corner: Logic Rules, Prolog Inference, and Guards — Sigma/Gamma/Theta (`sphere/logic/`, `sphere/prolog_logic/`, `sphere/guards/`, `specs/canon/*_rules.yaml`, `*_invariants.yaml`)

## Why this corner exists at all

Everything below this layer (lexicon, hex substrate, geometry, propagation,
shadow correction) produces *measurements*. Measurements alone are not a
verdict — something has to decide, from those measurements, whether a
structural pattern is meaningful (logic rules), whether deeper symbolic
relationships hold (Prolog inference), and whether the entire run is even
trustworthy enough to certify as canonical (guards). Without this corner,
Hesperia would be a sophisticated metrics calculator with no mechanism for
ever saying "this output is valid" or "this output is not" — which is
precisely the authority the system exists to produce.

## Why logic rules live in YAML, not in Python conditionals

`specs/canon/logic_rules.yaml`'s own header states the discipline directly:
"Edit rules here; no thresholds in Python." A rule like `structural_monotony`
(entropy below 0.35 indicates structurally narrow discourse) is a *claim about
the domain*, not an implementation detail of the rule engine. Putting it in
code would conflate two things that need to change independently and be
reviewed by different people: the rule *evaluator* (an engineering concern —
does the AND/OR/IMPLIES logic execute correctly) and the rule *content* (a
domain/clinical/governance concern — is entropy 0.35 actually the right
cutoff for "narrow"). Versioning rules as data also means a rule-set change is
a diffable, reviewable artifact rather than a buried code change, which is a
prerequisite for `THETA_001`-style governance ("canonical output requires
Sigma and Gamma pass") to mean anything stable over time.

## Why Prolog inference is a separate stage from the rule engine

The Layer-9 rule engine evaluates declarative conditions against scalar
metrics (entropy, governance area share, curvature) — it is good at
threshold-style reasoning. But some Hesperia claims are relational/symbolic
("if X derived AND Y not yet evidenced, the propagation pattern indicates Z")
and are more naturally expressed and proven in a logic-programming substrate
than encoded as nested boolean rule conditions. `sphere/prolog_logic/` exists
to host exactly that class of reasoning, with its own knowledge base, rule
compiler, and explanation graph — keeping it distinct from the YAML rule
engine means each system is asked to do only the kind of inference it's
suited for, rather than stretching the simpler rule engine into recursive
symbolic logic it wasn't designed for.

## Why Sigma, Gamma, and Theta are three separate guards rather than one validation pass

Each guard checks a categorically different kind of failure, and conflating
them would hide *which class* of problem caused a rejection:

- **Sigma** (static invariants — `sigma_invariants.yaml`) checks shape and
  structural bounds that should hold for *any* valid output regardless of how
  it was computed: vector lengths, matrix symmetry, value ranges. These are
  checks you could run on a single artifact in isolation, with no knowledge of
  how the pipeline executed.
- **Gamma** (dynamic invariants — `gamma_invariants.yaml`) checks properties
  of the *execution* itself: layer order, no illegal mutation of upstream
  artifacts, raw/propagated separation, determinism flags. These require
  knowledge of the run, not just the artifact.
- **Theta** (governance rules — `theta_governance_rules.yaml`) checks release
  eligibility: does this output qualify as *canonical* given Sigma/Gamma
  results and artifact completeness. Theta is downstream of, and depends on,
  both of the others (`THETA_001`).

This three-way split means a failure can be localized immediately: a Sigma
failure means the artifact itself is malformed; a Gamma failure means the
*process* that produced it was unsound even if the artifact looks fine; a
Theta failure means everything was sound but the output still doesn't meet
the bar for "safe to certify as canonical." `guard_runtime.py`'s explicit
sequencing (Sigma → Gamma → Theta, "orchestration only; no policy logic
here") encodes this dependency order directly: governance is meaningless to
evaluate over data that's already known to violate structural shape or
execution invariants.

## Why guards are "no free-form eval" (data-driven conditions, not arbitrary code)

`theta_governance_rules.yaml`'s header — "Gates release/build state; no
free-form eval" — exists for the same reason logic rules are YAML: a
governance gate that could run arbitrary code would itself need to be audited
for correctness on every change, defeating the purpose of having a fixed,
reviewable gate. Expressing conditions as `{fact, op, value}` triples keeps
the entire governance surface small enough to review exhaustively.

## Exhaustive invariant enumeration

For the full invariant-by-invariant treatment of Sigma/Gamma/Theta (every ID,
its actual implemented check, and its formal/scientific lineage), see
[`layers/GUARDS_sigma_gamma_theta.md`](../layers/GUARDS_sigma_gamma_theta.md) —
written as the direct continuation of the L1-L9 layer documentation series, at
the same level of detail. That document also confirms and traces the "Layer-9
rule engine" named above is a distinct system from `core/layers/layer_9.py`
(the numbered pipeline's final layer, documented in
[`layers/L9_pillars_and_brand_labels.md`](../layers/L9_pillars_and_brand_labels.md)) —
both happen to be labeled `layer_9` in different output dictionaries.

## Relationship to neighboring corners

- Reads from `corners/shadow_correction.md` and `corners/propagation_dynamics.md`
  as its primary fact sources.
- Its verdicts are what `corners/interpretation_usf.md` packages into the USF
  artifact, and what `corners/fpf_bridge.md` later treats as pre-evaluated,
  read-only closures (the bridge never re-runs Sigma/Gamma/Theta — it consumes
  their already-computed verdicts, which is only safe because this corner
  already made those verdicts deterministic and complete).
