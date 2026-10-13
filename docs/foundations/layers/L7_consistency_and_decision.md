# Layer 7 — Cross-Layer Consistency Gates & Decision Synthesis (40_SPEC)

Source: `core/layers/layer_7.py`, function `compute_L7`. 25 variables: 10 boolean
consistency gates, a trust tier, three limit/within-limits pairs plus one bare
limit, four alignment/justification/support scores, and the three terminal
decision facts `SYSTEM_CONFIDENCE_SCORE`, `DECISION_STATUS_CODE`,
`OUTPUT_TRUST_TAG`. This is the first layer whose entire job is to **read** L1–L6
rather than compute new structural measurements — it is a synthesis/decision
layer, sitting one step before the formal Sigma/Gamma/Theta guards documented
separately in [`corners/guards.md`](../corners/guards.md) and
[`corners/logic_guards.md`](../corners/logic_guards.md). L7 is part of the
numbered layer pipeline, not one of those guards — it produces the **inputs**
several of those guards and L8/L9 consume.

## What L7 receives

The full L1–L6 result dictionaries, plus `visited_B` (defaulting to L2's
`VISITED_IDS`), `F`, `A`, and a set of named thresholds with defaults baked into
the function signature (`MIN_COVERAGE_RATIO=0.10`, `SHADOW_MAX_DEVIATION=0.25`,
`MAX_CONTRADICTION=0.50`, `MAX_CROSS_AREA_RATIO=0.50`, `MAX_LYAPUNOV=2.0`,
`HIGH_CONF=0.70`, `MED_CONF=0.40`, `EVIDENCE_SUPPORT_INDEX_SHADOW=0.0`,
`MIN_PCS=0.0`). `run()` also reads an optional `meta["stability"]` dict, produced
by a separate module (`core/stability/stability_delta.py`), used for a post-hoc
trust-tag demotion described below.

## Group I — The 10 boolean consistency gates (CONSIST_*)

Each gate is a direct cross-check between facts that two different layers
computed independently — the same role unit tests play for code, but run live on
every pipeline execution against real data instead of fixtures.

| Gate | Check | What it catches |
|---|---|---|
| `CONSIST_COVERAGE_MIN_GATE` | `l1.COVERAGE_RATIO ≥ MIN_COVERAGE_RATIO` (default 0.10) | Attribution found too little of the input to trust anything downstream. |
| `CONSIST_ATTRIBUTION_MASS_EQUALITY` | `\|l1.FAMILY_HIT_VECTOR_L1 − l1.ATTRIBUTED_TOKENS\| ≤ EPS_INT` | L1's own internal mass accounting is self-consistent (an L1-norm vs. raw-count agreement check, floating-point tolerance `1e-6`). |
| `CONSIST_TRAVERSAL_NONEMPTY_WHEN_ATTRIBUTED` | `(ATTRIBUTED_TOKENS=0 ⟺ TOTAL_REACHABLE_NODES=0)` | L1 (attribution) and L2 (BFS traversal) agree on whether there was anything to traverse at all — a biconditional, not just an implication. |
| `CONSIST_DOMINANT_FAMILY_IN_TRAVERSAL` | `l1.DOMINANT_FAMILY_ID ∈ visited_B` | The family L1 says is dominant was actually reached by L2's BFS — catches a disagreement between the census and the traversal about which family matters. |
| `CONSIST_AREA_MAPPING` | `l1.DOMINANT_AREA_ID == l1.DOMINANT_FAMILY_ID // FPA` | L1's own area assignment is arithmetically consistent with the family→area mapping (`FPA = F/A` families per area) — a self-consistency check on L1's output, not a cross-layer one. |
| `CONSIST_EVIDENCE_INTEGRITY_HARD` | `l4.INTEGRITY_CHECK_PASS_RATIO == 1.0` | Hard requirement, no tolerance: every retrieved chunk passed its checksum. |
| `CONSIST_SHADOW_DELTA_ONLY_IF_SHADOW` | `(not l3.SHADOW_ENABLED AND l3.SHADOW_DEVIATION_SCORE==0.0) OR l3.SHADOW_ENABLED` | If no shadow run happened, the deviation score must be exactly zero — guards against a stale/leftover nonzero deviation being read as real. |
| `CONSIST_TRIG_REQUIRED_FOR_ANGLE_METRICS` | `l5.REALITY_GATE_TRIG` | Passes through L5's trig/metric-axiom self-test (documented in [`L5_counter_evidence_and_trig_invariants.md`](L5_counter_evidence_and_trig_invariants.md)) as a precondition for trusting any angle-based metric elsewhere in the pipeline. |
| `CONSIST_COUNTER_EVIDENCE_VALID` | `l5.REALITY_GATE_COUNTER_EVIDENCE` | Passes through L5's counter-evidence gate. |
| `CONSIST_STABILITY_REGIME_VALID` | `lyap == lyap AND \|lyap\| ≠ ∞` | A **NaN/Inf sanity check** on L6's `LYAPUNOV_ESTIMATE`, using the classic IEEE-754 idiom `x == x` being false exactly when `x` is NaN (IEEE 754-1985 floating-point standard; the self-inequality property of NaN is a designed consequence of the standard's comparison semantics, not a numerical coincidence). |

`CONSIST_PROFILE_CONFORMANCE` is added conditionally (only when
`l1.PROFILE_MODE_ACTIVE is True`), checking `l1.PROFILE_CONFORMANCE_SCORE ≥
MIN_PCS`. When this conditional gate fails, it triggers the one **permanently
reserved decision code, 75** (`PROFILE_CONFORMANCE_FAILURE`, originally specified
in 34_SPEC's note N1 — the same spec era as L1). The comment `# never reuse`
treats this code as a permanent allocation in a small decision-code registry, the
same discipline as a published API never reusing a deprecated enum value.

## Group II — Limits and within-limits pairs (7 variables)

`TRUST_TIER` is an ordinal computed by short-circuit priority: `0` if the
coverage gate fails, else `1` if the integrity gate fails, else `2` if the trig
gate fails, else `3` (all three passed). This is a **staged gate ladder** —
later, more specific gates only matter once the earlier, more fundamental ones
hold — the same priority-encoding idea used in industrial fault-tree and FMEA
(Failure Mode and Effects Analysis) severity coding, where checks are ordered by
how foundational the failure is.

The remaining six variables are three (limit, within-limits) pairs plus one bare
limit, each simply exposing a threshold alongside the boolean of whether the
relevant upstream score respects it: `MAX_ALLOWABLE_SHADOW_DEVIATION` /
`SHADOW_WITHIN_LIMITS` (reads `l3.SHADOW_ACCEPTABILITY_GATE` directly),
`MAX_ALLOWABLE_CONTRADICTION` / `CONTRADICTION_WITHIN_LIMITS` (`l5.CONTRADICTION_PRESSURE_SCORE
≤ MAX_CONTRADICTION`), `MAX_AREA_LEAKAGE` / `AREA_LEAKAGE_WITHIN_LIMITS`
(`l2.CROSS_AREA_RATIO ≤ MAX_CROSS_AREA_RATIO`), and the bare `MAX_CHAOS_LEVEL`
(`= MAX_LYAPUNOV`, default 2.0, used later for decision code 70).

## Group III — Alignment, justification, support (4 variables)

| Variable | Formula | Reading |
|---|---|---|
| `STRUCTURE_EVIDENCE_ALIGNMENT` | `0.60·l4.EVIDENCE_SUPPORT_INDEX_BASELINE + 0.40·l2.GEOMETRIC_STABILITY_INDEX` | Convex combination (weights sum to 1.0), the same multi-attribute-scoring pattern documented for L1/L3/L4/L5's composites — here fusing the evidence layer's confidence with the topology layer's structural-stability confidence into one cross-pipeline alignment figure. |
| `SHADOW_EVIDENCE_ALIGNMENT_DELTA` | `EVIDENCE_SUPPORT_INDEX_SHADOW − l4.EVIDENCE_SUPPORT_INDEX_BASELINE` | Signed delta — positive means the shadow run's evidence support exceeded the baseline's. `EVIDENCE_SUPPORT_INDEX_SHADOW` defaults to `0.0` (no shadow-evidence figure supplied), so this delta is typically negative/zero unless a caller threads in a real shadow evidence score. |
| `SHADOW_JUSTIFICATION_SCORE` | `[shadow_ok] · max(0, delta_shadow) · (1 − l3.SHADOW_DEVIATION_SCORE)` | A gated, clamped product: only nonzero when the shadow gate passed *and* the shadow run actually improved evidence support *and* the shadow's structural deviation was small. All three conditions must hold simultaneously for the shadow run to be "justified" — another multiplicative soft-AND, same composition style as L6's `CONCEPTUAL_COHERENCE_INDEX`. |
| `CONTRADICTION_ADJUSTED_SUPPORT` | `clamp(l4.EVIDENCE_SUPPORT_INDEX_BASELINE · (1 − l5.CONTRADICTION_PRESSURE_SCORE), 0, 1)` | Evidence support discounted by how much counter-evidence pressure L5 found — high contradiction pressure erodes confidence in supporting evidence even if that evidence's raw score was high. |

## Group IV — Terminal decision (3 variables)

### `SYSTEM_CONFIDENCE_SCORE`

```
conf = clamp( (TRUST_TIER/3) · l1.STRUCTURAL_STABILITY_INDEX · l2.GEOMETRIC_STABILITY_INDEX
              · CONTRADICTION_ADJUSTED_SUPPORT · l6.GLOBAL_STABILITY_SCORE,  0, 1 )
```

A five-factor **product**, not a weighted sum — every factor must be
simultaneously healthy for confidence to be high, the same reliability-style
"series system" composition (overall reliability = product of component
reliabilities, standard in reliability engineering) used by L6's
`CONCEPTUAL_COHERENCE_INDEX` and L7's own `SHADOW_JUSTIFICATION_SCORE`. The
`TRUST_TIER/3` factor means confidence is structurally capped well below 1.0
unless the coverage, integrity, and trig gates all passed (tier 3).

### `DECISION_STATUS_CODE`

A priority-encoded integer, evaluated as a chain of `else if`s in order — first
matching condition wins:

| Code | Condition | Meaning |
|---|---|---|
| 75 | profile mode active, `MIN_PCS>0`, and `CONSIST_PROFILE_CONFORMANCE` fails | `PROFILE_CONFORMANCE_FAILURE` — permanently reserved, never reused (34_SPEC N1). |
| 10 | `CONSIST_COVERAGE_MIN_GATE` fails | Coverage too low. |
| 20 | `CONSIST_EVIDENCE_INTEGRITY_HARD` fails | Integrity check failed. |
| 30 | `AREA_LEAKAGE_WITHIN_LIMITS` fails | Cross-area leakage too high. |
| 40 | `SHADOW_WITHIN_LIMITS` fails | Shadow deviation exceeded its limit. |
| 50 | `CONTRADICTION_WITHIN_LIMITS` fails | Contradiction pressure exceeded its limit. |
| 60 | `CONSIST_TRIG_REQUIRED_FOR_ANGLE_METRICS` fails | Trig/metric self-test failed. |
| 70 | `lyap > MAX_LYAPUNOV` | Chaos estimate exceeded its ceiling. |
| 0 | none of the above | Clean pass. |

This is the same priority-encoding idea as `TRUST_TIER` extended to a full
decision registry — each numeric band (10s, 20s, ... 70, and the permanently
reserved 75) is allocated to one specific failure mode so that a downstream
consumer or log reader can distinguish *which* gate failed from the code alone,
without re-inspecting all ten booleans.

### `OUTPUT_TRUST_TAG`

`"HIGH"` if `code==0` and `conf ≥ HIGH_CONF` (0.70); `"MED"` if `code==0` and
`conf ≥ MED_CONF` (0.40); else `"LOW"`. A simple threshold ladder on the
already-computed confidence score, gated on a clean decision code.

### Post-hoc demotion via the Δ-consistency module

After `compute_L7` returns, `run()` checks `meta["stability"]` — a dict produced
by `core/stability/stability_delta.py`, a separate module not itself one of the
numbered layers. That module computes an `anomaly_score` in `[0,1]` as `min(1.0,
0.28 × n_flags)` where `n_flags` counts how many of five independent instability
signals fired (cross-area ratio, loop density, L6 condition number, L6 curvature,
L6 global-stability-low — each compared against its own fixed threshold). If
`anomaly_score > ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE` (0.50), `run()`
overwrites `OUTPUT_TRUST_TAG` to the literal string `"LOW_CONFIDENCE"` (distinct
from the plain `"LOW"` tag `compute_L7` itself can produce) and records
`STABILITY_ANOMALY_SCORE`. This is a second, independent override layer sitting
between `compute_L7`'s pure decision and the value actually returned — worth
knowing if `"LOW"` vs `"LOW_CONFIDENCE"` is ever pattern-matched downstream, since
they are not interchangeable strings.

## Relationship to neighboring layers and corners

- **L1–L6 → L7**: every one of the six prior layers contributes at least one
  gate or score input — L7 is the first point in the pipeline where all of
  L1–L6's outputs are read together.
- **L7 → L8**: per the module docstring, L8 consumes `SI_SYSTEM_CONFIDENCE`
  (presumably sourced from `SYSTEM_CONFIDENCE_SCORE`) — not yet documented in
  this series.
- **L7 → L9**: per the module docstring, L9 consumes "pillars", `BRAND_WORD_*`,
  and `ACTION_*` facts — not yet documented in this series.
- **Distinct from the formal guards**: L7's `CONSIST_*` gates are structural
  cross-checks between layer outputs, evaluated unconditionally on every run.
  They are conceptually adjacent to, but administratively distinct from, the
  Sigma/Gamma/Theta guard system documented in
  [`corners/guards.md`](../corners/guards.md) and
  [`corners/logic_guards.md`](../corners/logic_guards.md) — the guards pass is
  the next major documentation phase after the numbered layers are complete.
- **`stability_delta.py`**: a separate, non-numbered module that post-processes
  L6's stability metrics into a single anomaly score and feeds a corrective
  signal back into L7's output after `compute_L7` has already returned — an
  example of cross-cutting logic living outside the strict L1→L9 layer chain.
