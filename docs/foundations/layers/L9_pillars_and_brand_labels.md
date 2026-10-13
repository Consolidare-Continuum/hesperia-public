# Layer 9 — Pillars, Bands & Human-Facing Labels (42_SPEC)

Source: `core/layers/layer_9.py`, function `compute_L9`. 25 variables: 6 ordinal
confidence bands, 2 directionalization-convention strings, 6 weighted "pillar"
scores, 5 categorical brand-word labels, and 4 boolean workflow-action triggers.
This is the **terminal layer** of the L1–L9 chain. The module docstring states
its role precisely: *"Final layer: L1–L9 metrics become human-facing labels (no
locale here; i18n can wrap L9 output)."* L9 produces no text — only fixed,
named, language-agnostic categories and booleans that a separate
internationalization/templating layer is expected to render into actual
sentences in a given locale.

## What L9 receives

`l3` (only `SHADOW_ENABLED`, `SHADOW_ACCEPTABILITY_GATE`), `l4` (only
`INTEGRITY_CHECK_PASS_RATIO`, `RETRIEVAL_SHORTFALL_BASELINE`), `l7` (only
`DECISION_STATUS_CODE`, `SHADOW_JUSTIFICATION_SCORE`), and `l8` (ten `SI_*_U1000`
/ `SI_TRIG_REALITY_FLAG` fields). Notably, L9 reads two raw (non-standardized)
fields directly from L4 rather than going through L8's unit layer — see
`ACTION_REQUIRE_EVIDENCE_REBUILD` below.

## Group I — Confidence bands (6 variables)

```
u = SI_SYSTEM_CONFIDENCE_U1000
BAND_0_CRITICAL:   u <  200
BAND_1_WEAK:    200 ≤ u <  400
BAND_2_FAIR:    400 ≤ u <  600
BAND_3_GOOD:    600 ≤ u <  800
BAND_4_STRONG:  800 ≤ u <  950
BAND_5_EXCELLENT:    u ≥  950
```

Six mutually-exclusive, collectively-exhaustive boolean bands over the
already-standardized `[0,1000]` confidence score — a direct discretization of a
continuous measurement into ordinal categories. Converting an interval/ratio
scale into ordinal bands for reporting is standard measurement-theory practice
(Stevens, *On the Theory of Scales of Measurement*, 1946, established the
nominal/ordinal/interval/ratio taxonomy this kind of band conversion moves
*down* within); the specific six-band structure and its boundary values (200,
400, 600, 800, 950 — non-uniform near the top, giving a narrower top band) are a
Hesperia-native cutoff choice, the same kind of asymmetric-near-the-extreme
banding used in many real rating systems (e.g., credit-score bands, severity
scales) where most of the discriminative interest is concentrated near the high
end.

## Group II — Directionalization convention (2 variables)

`DIRECTIONALIZE_HIGH_IS_GOOD = "clamp(u,0,1000)"` and
`DIRECTIONALIZE_LOW_IS_GOOD = "1000-clamp(u,0,1000)"` are not computed scores —
they are **declared formula strings**, the same "policy as data" pattern already
seen in L8's `CLAMP_POLICY`/`ROUNDING_POLICY` fields. They document, in a form a
downstream reporting/i18n layer can read programmatically, the two possible
conventions for turning a raw U1000 number into a "higher is better" semantic:
most metrics (coverage, evidence, stability, confidence) are already
high-is-good; a few (area leakage, contradiction pressure) are naturally
low-is-good and must be inverted before banding or color-coding them the same
way. `AREA_CONTAINMENT_U1000` and `CONSISTENCY_U1000` below are the two concrete
applications of the `LOW_IS_GOOD` inversion.

## Group III — Inverted framing scores (2 variables)

| Variable | Formula | Purpose |
|---|---|---|
| `AREA_CONTAINMENT_U1000` | `clamp(1000 − SI_AREA_LEAKAGE_U1000, 0, 1000)` | Reframes "how much leaked across areas" (bad-when-high) as "how well-contained" (good-when-high), so it can be combined additively with other good-when-high pillar inputs without sign confusion. |
| `CONSISTENCY_U1000` | `clamp(1000 − SI_CONTRADICTION_PRESSURE_U1000, 0, 1000)` | Same inversion applied to L5's contradiction pressure (passed through L8) — "how consistent" rather than "how contradicted." |

## Group IV — Six governance pillars (6 variables)

| Pillar | Formula | Composition style |
|---|---|---|
| `PILLAR_INPUT_QUALITY_U1000` | `round(0.60·SI_COVERAGE_U1000 + 0.40·SI_DOMINANCE_U1000)`, clamped | Convex combination (weights sum to 1.0) — same multi-attribute-scoring pattern used throughout L1–L7's composites. |
| `PILLAR_GEOMETRY_U1000` | `round(0.70·SI_GEOMETRIC_STABILITY_U1000 + 0.30·AREA_CONTAINMENT_U1000)`, clamped | Convex combination of L2's structural stability and the inverted leakage score. |
| `PILLAR_EVIDENCE_U1000` | `= SI_EVIDENCE_SUPPORT_U1000` | Direct passthrough — no combination needed, L4's evidence-support figure already stands alone as a pillar. |
| `PILLAR_CONSISTENCY_U1000` | `round(0.60·CONSISTENCY_U1000 + 0.40·(1000 − SI_ENTROPY_U1000))`, clamped | Convex combination of the inverted-contradiction score and inverted entropy — low dispersion (concentrated attribution) treated as contributing to consistency. |
| `PILLAR_STABILITY_U1000` | `= SI_GLOBAL_STABILITY_U1000` | Direct passthrough of L6's stability score. |
| `PILLAR_GOVERNANCE_U1000` | `1000` if `DECISION_STATUS_CODE==0`, else `clamp(1000 − 10·DECISION_STATUS_CODE, 0, 1000)` | A linear penalty proportional to the *numeric value* of L7's decision code — this makes the decision-code registry's magnitudes do double duty as severity weights (code 70 → penalty 700, score 300; code 75 → penalty 750, score 250), not just as a lookup key. Worth knowing if the decision-code numbering in L7 is ever renumbered: this formula's severity ordering depends on the current code values, not just their relative order. |

Six named pillars condensing nine-layers'-worth of internal metrics into a small,
fixed reporting vocabulary (input quality, geometry, evidence, consistency,
stability, governance) is structurally the same idea as a **balanced
scorecard** (Kaplan & Norton, *The Balanced Scorecard*, 1992) — translating many
raw measurements into a handful of named strategic/operational dimensions for
oversight. The specific six pillars chosen and their weights are Hesperia-native
engineering decisions; the *pattern* of "many raw metrics → few named pillar
scores for governance reporting" is the borrowed structural idea.

## Group V — Brand-word categorical labels (5 variables)

Each is a threshold ladder mapping a pillar/score onto a small ordered set of
named categories — the same style as L7's `OUTPUT_TRUST_TAG`, generalized across
five separate dimensions:

- `BRAND_WORD_TRUST`: `"BLOCKED"` (decision code ≠ 0, hard override) →
  `"TRUSTED"` (≥850) → `"USABLE"` (≥650) → `"TENTATIVE"` (≥450) → `"FRAGILE"`.
- `BRAND_WORD_EVIDENCE`: `"SUPPORTED"` (≥800) → `"BACKED"` (≥600) → `"THIN"`
  (≥400) → `"UNSUPPORTED"`.
- `BRAND_WORD_CONTRADICTION`: `"CONSISTENT"` (≥800) → `"MIXED"` (≥600) →
  `"CONTESTED"` (≥400) → `"CONTRADICTED"`, based on `CONSISTENCY_U1000`.
- `BRAND_WORD_GEOMETRY`: `"CONTAINED"` (≥800) → `"STABLE"` (≥600) →
  `"DIFFUSE"` (≥400) → `"CHAOTIC"`, based on `PILLAR_GEOMETRY_U1000`.
- `BRAND_WORD_SHADOW`: not a threshold ladder but a small **state machine** —
  `"OFF"` if no shadow run happened, else `"REJECTED"` if the shadow
  acceptability gate failed, else `"JUSTIFIED"` if L7's
  `SHADOW_JUSTIFICATION_SCORE > 0`, else `"NEUTRAL"` (shadow ran, passed its
  gate, but didn't demonstrably improve evidence support).

These five labels are the concrete instance of what the module docstring calls
"human-facing labels" — fixed English-language tokens, deliberately
locale-agnostic (a wrapping i18n layer is expected to map `"TRUSTED"` to its
translated equivalent rather than this layer producing prose).

## Group VI — Action triggers (4 variables)

| Variable | Condition | Workflow meaning |
|---|---|---|
| `ACTION_REQUIRE_MORE_INPUT` | `SI_COVERAGE_U1000 < 500` | Less than half the input was attributable — ask for more text/context before trusting any output. |
| `ACTION_REQUIRE_EVIDENCE_REBUILD` | `l4.INTEGRITY_CHECK_PASS_RATIO < 1.0 OR l4.RETRIEVAL_SHORTFALL_BASELINE > MAX_SHORTFALL` | Reads L4's **raw** fields directly rather than an `SI_*` standardized form — `RETRIEVAL_SHORTFALL_BASELINE` is a count, not a ratio, so L8 never gave it a U1000/percent rendering; L9 reaches past L8 for this one check rather than waiting for a unit it doesn't have. |
| `ACTION_REQUIRE_GOVERNANCE_REVIEW` | `l7.DECISION_STATUS_CODE != 0 OR SI_SYSTEM_CONFIDENCE_U1000 < 450` | Either an explicit gate failure or sub-"FAIR" confidence triggers a human governance look. |
| `ACTION_ALLOW_HUMAN_SUMMARY` | `l7.DECISION_STATUS_CODE == 0 AND SI_SYSTEM_CONFIDENCE_U1000 ≥ 650 AND SI_TRIG_REALITY_FLAG` | A three-way AND gate — the explicit "go" signal for generating a human-readable summary at all. Notably requires L5's trig/metric self-test (`REALITY_GATE_TRIG`, passed through L8 as `SI_TRIG_REALITY_FLAG`) to have passed, tying a foundational geometry self-check directly to the final human-facing release decision. |

## Relationship to neighboring layers and corners

- **L3, L4, L7, L8 → L9**: L9 is the only layer that reads from four
  non-contiguous upstream layers simultaneously (skipping L1, L2, L5, L6
  directly — their contributions arrive already folded into L7's gates/scores
  and L8's standardized fields).
- **End of the L1–L9 chain**: per the module docstring, no numbered layer
  consumes L9's output — it is rendered to a human-facing report or wrapped by
  a separate i18n/templating system, outside the scope of the numbered-layer
  pipeline documented in this series.
- **Decision-code coupling**: `PILLAR_GOVERNANCE_U1000`'s linear penalty formula
  creates a direct numeric dependency on L7's `DECISION_STATUS_CODE` registry
  values (documented in
  [`L7_consistency_and_decision.md`](L7_consistency_and_decision.md)) — this is
  the one place in the pipeline where a decision code's literal integer value
  (not just its identity) participates in a downstream formula.
- **Trig-gate coupling**: `ACTION_ALLOW_HUMAN_SUMMARY` is the final pipeline
  consumer of L5's `REALITY_GATE_TRIG` (documented in
  [`L5_counter_evidence_and_trig_invariants.md`](L5_counter_evidence_and_trig_invariants.md)),
  closing the loop from "are basic vector-space axioms intact" all the way to
  "is it safe to show this to a human."
