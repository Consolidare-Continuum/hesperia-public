# Corner: Interpretation Layer and USF (`sphere/interpretation/`, `sphere/usf/`, Layer 10)

## Why this corner exists at all

Logic rules and Prolog inference (see `corners/logic_guards.md`) produce a set
of discrete triggered facts. Something still has to collapse that set into a
small number of human/governance-legible structural states
(`focused_dominant`, `distributed_balanced`, `unstable_transition`,
`tension_elevated`, `diffuse_spread`) and assemble *all* of a run's artifacts
into one canonical, self-consistent record. State classification and USF
generation are the two halves of that job, and they are deliberately the last
deterministic layer before anything resembling language generation is
permitted to happen.

## Why state classification is rule-based with fixed thresholds, not a learned classifier

`state_classifier.py` is explicit in its own docstring: "Rule-based and
deterministic; no math implementation — uses logic events and diagnostics
only." This is a direct consequence of everything below it already being
deterministic — a learned classifier sitting on top of fully deterministic,
auditable inputs would be the single point where the whole chain's
determinism guarantee breaks, for no real gain (the classification boundaries
— dominant share > 0.35, entropy drop > 0.15, tension delta > 0.10 — are
simple enough that a fixed rule table is both sufficient and fully
explainable). Keeping classification a thin, fixed-threshold function over
already-computed diagnostics means the *only* thing left to govern is whether
the five state definitions and their boundaries are well-chosen — a tractable,
reviewable question — rather than whether an opaque model is doing the right
thing.

## Why USF (Universal Structural Fingerprint) exists as a single consolidated artifact

Layers 3 through 9 each produce their own outputs (topology metrics,
propagation diagnostics, shadow corrections, logic rule triggers, Prolog
facts). If each layer's output were consumed independently by downstream
systems, two problems would follow: (1) there would be no single artifact a
guard, an audit, or a future consumer (like fpf_bridge) could hash and treat
as "the result of this run," and (2) partial or malformed sub-outputs could
slip through to consumers that didn't bother checking every upstream layer
individually. USF's strict validation (`_check_list_length`,
`_check_matrix_12x12` — failing loudly rather than silently coercing
shapes) and deterministic field ordering exist so that USF can serve as the
*one* canonical handle for "this run's full structural state," which is
exactly what `THETA_003` checks for ("required artifacts — USF, raw_metrics,
logic_outputs, provenance — must be present") and exactly what a fingerprint
diff (`sphere/usf/fingerprint_diff.py`) needs in order to detect drift between
two runs at all.

## Why USF generation is described as "Layer 10" and explicitly placeholder/non-canonical in some governance paths (`THETA_004`)

The system distinguishes between USF as a *structural* consolidation (always
canonical — it's just packaging already-validated facts) and any
*interpretive narrative* placed at Layer 10 in earlier eras before
fpf_bridge existed. Marking placeholder Layer-10 interpretation as
non-canonical was the correct minimal stance at the time: it let the team
ship a consolidated structural artifact (USF) without prematurely certifying
an interpretation mechanism (narrative generation) that didn't yet have the
guard rails fpf_bridge later provided. This is the same conservative instinct
visible throughout the canon — ship the deterministic measurement first,
gate anything resembling free-form language behind an explicit, later-built
authority boundary.

## Relationship to neighboring corners

- Consumes facts from `corners/logic_guards.md` (triggered rules, Prolog
  facts) and `corners/shadow_correction.md` (corrected vectors, diagnostics).
- Produces the USF artifact and `structural_state` value that
  `corners/fpf_bridge.md` maps directly onto its 5-state state machine
  (`interpretation_metrics.structural_state` → `ActiveState.current_state`,
  a direct, unmediated mapping specifically because this corner already did
  the work of reducing the space to exactly 5 legible states).
- Is the natural boundary the sealed-runtime release process (see
  `eras/05_sealed_0.6.x.md`) treats as "the product" — everything above
  this corner before fpf_bridge was, by design, not yet language.
