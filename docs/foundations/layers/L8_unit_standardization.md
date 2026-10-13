# Layer 8 — Unit Standardization & Interpretation Policy (41_SPEC)

Source: `core/layers/layer_8.py`, function `compute_L8`. Unlike every layer
documented so far, L8's docstring does **not** claim a fixed "25 variables" count
— its job is structurally different: it is a **re-expression layer**, taking
already-computed scores from L1–L7 and rendering each one into a small, fixed
taxonomy of report units. No new measurement is performed here; every `SI_*`
field is a deterministic, invertible transform of a single upstream value. The
module docstring states the scope plainly: *"SI_* report units from L1..L7...
All 9 layers flow to i18n via L8→L9."*

**Naming note**: the `SI_` prefix here is a Hesperia internal convention
(plausibly "Standard Interface" or "Standardized Indicator") and should not be
read as the Système International d'Unités (SI units — meters, kilograms,
seconds). None of these fields carry physical-unit dimensions; they are
dimensionless ratios, percentages, counts, and per-mille scores. This
distinction is worth stating explicitly so the name is not over-interpreted.

## What L8 receives

The full L1–L7 result dictionaries. No independent inputs, no thresholds, no
randomness — `compute_L8` is a pure, total function of its seven dictionary
arguments.

## The taxonomy (5 policy/meta fields)

| Field | Value | Meaning |
|---|---|---|
| `UNIT_TYPE_ENUM` | `"COUNT,RATIO,PERCENT,U1000,RADIANS,SECONDS,BYTES,HASH,BOOLEAN,CODE"` | The declared closed set of unit kinds this layer (and downstream consumers) are allowed to express values in. Of these ten, only `COUNT`, `PERCENT`, `U1000`, and `BOOLEAN` are actually produced by `compute_L8`'s own fields — `RATIO`, `RADIANS`, `SECONDS`, `BYTES`, `HASH`, and `CODE` are declared as part of the enum but not exercised by any field in this layer, the same "declared-but-not-yet-live" honesty pattern already documented for L6's stub variables. They presumably cover unit kinds used by other parts of the system (e.g. `RADIANS` for the L5 trig layer's `theta`, `CODE` for L7's `DECISION_STATUS_CODE`) that L8 does not itself re-express. |
| `SCALE_POLICY_ENUM` | `"RAW,CLAMP_0_1,CLAMP_0_100,CLAMP_0_1000,ZSCORE,LOG10"` | Likewise a declared closed set of six scaling policies; `compute_L8`'s own fields use only the clamp-based ones (effectively `CLAMP_0_1` then percent/per-mille rescaling). `ZSCORE` (standard-score normalization, Karl Pearson's standardization of a variable by its mean and standard deviation, late 19th/early 20th c.) and `LOG10` (logarithmic compression, useful for heavy-tailed distributions) are reserved scale kinds, not used by any field computed here. |
| `EPSILON_POLICY` | `1e-12` | The floating-point tolerance constant this layer's policy declares as standard — matches the `eps` used in L5's `compute_L5` and several other layers' divide-by-zero guards, documented for consistency across the pipeline. |
| `CLAMP_POLICY` | `"max(lo,min(hi,v))"` | The literal clamp formula as a declared string — the exact same two-sided clamp implemented as `_clamp(v, lo, hi)` here and as `_c(x, lo, hi)` in L7 and `_clamp01` in L1: `max(lo, min(hi, v))`. Stating it as policy text (not just code) makes the convention explicit and auditable independent of any one layer's implementation. |
| `ROUNDING_POLICY` | `"DECIMALS_RATIO=6,DECIMALS_PCT=2,DECIMALS_U1000=0"` | Declared decimal precision per unit kind — ratios to 6 decimal places, percentages to 2, U1000 scores to integers (0 decimals, matching `_ratio_to_u1000`'s `round()` call). |

## The U1000 scale: a per-mille convention

`_ratio_to_u1000(r) = round(clamp(r, 0, 1) × 1000)` produces an integer in
`[0, 1000]`. This is the same idea as the historical **per mille** (‰) unit —
parts per thousand rather than parts per hundred — used historically for
shipping/salinity measurements and still standard today for blood-alcohol
concentration and some financial interest-rate quoting. Hesperia's motivation is
practical rather than historical: representing a `[0,1]` confidence/stability
score as an integer with three significant digits of resolution avoids floating-
point representation noise in logs, reports, and any downstream system that
prefers integers — the same reasoning that leads credit-scoring systems and some
probability-display UIs to use a 0–1000 or 0–100 integer scale rather than a raw
float.

## The SI_* re-expressed fields (22 fields, 11 source values × ~2 units each)

Each pair below takes one upstream `[0,1]`-ratio value and renders it as both a
percentage and a U1000 score (two views of the same number, for different
consumer needs — human-readable percent vs. integer-friendly per-mille):

| Source (layer.field) | SI_*_PCT | SI_*_U1000 |
|---|---|---|
| `l1.COVERAGE_RATIO` | `SI_COVERAGE_PCT` | `SI_COVERAGE_U1000` |
| `l1.DOMINANCE_RATIO` | `SI_DOMINANCE_PCT` | `SI_DOMINANCE_U1000` |
| `l1.NORMALIZED_FAMILY_ENTROPY` | `SI_ENTROPY_PCT` | `SI_ENTROPY_U1000` |
| `l2.GEOMETRIC_STABILITY_INDEX` | `SI_GEOMETRIC_STABILITY_PCT` | `SI_GEOMETRIC_STABILITY_U1000` |
| `l2.CROSS_AREA_RATIO` | `SI_AREA_LEAKAGE_PCT` | `SI_AREA_LEAKAGE_U1000` |
| `l3.SHADOW_DEVIATION_SCORE` (re-clamped to `[0,1]` before conversion) | `SI_SHADOW_DEVIATION_PCT` | `SI_SHADOW_DEVIATION_U1000` |
| `l4.EVIDENCE_SUPPORT_INDEX_BASELINE` | `SI_EVIDENCE_SUPPORT_PCT` | `SI_EVIDENCE_SUPPORT_U1000` |
| `l5.CONTRADICTION_PRESSURE_SCORE` | `SI_CONTRADICTION_PRESSURE_PCT` | `SI_CONTRADICTION_PRESSURE_U1000` |
| `l6.GLOBAL_STABILITY_SCORE` | `SI_GLOBAL_STABILITY_PCT` | `SI_GLOBAL_STABILITY_U1000` |
| `l7.SYSTEM_CONFIDENCE_SCORE` | `SI_SYSTEM_CONFIDENCE_PCT` | `SI_SYSTEM_CONFIDENCE_U1000` |

Plus two fields with no dual unit: `SI_TOTAL_TOKENS_COUNT` (plain `int(l1.TOTAL_TOKENS)`,
unit `COUNT`) and `SI_TRIG_REALITY_FLAG` (passthrough of `l5.REALITY_GATE_TRIG`,
unit `BOOLEAN`).

Note that `l3.SHADOW_DEVIATION_SCORE` is the only source value explicitly
re-clamped to `[0,1]` before conversion (`_clamp(l3["SHADOW_DEVIATION_SCORE"], 0.0, 1.0)`)
— a defensive measure, since L3's deviation score is a weighted combination of
deltas that is not contract-guaranteed to stay within `[0,1]` the way the other
nine source ratios are by construction.

## The Π interpretation policy (added in `run()`, not `compute_L8`)

After `compute_L8` returns, `run()` reads an optional `meta["policy"]` dict and
attaches three more fields to the result:

- `POLICY_MODE` — defaults to `"STRUCTURE_PLUS_CONTEXT"` if no policy is supplied.
- `INTERPRETATION_CONSTRAINTS` — a passthrough copy of the policy's constraint
  dict (`allow_text`, `allow_context`, `allow_structure`), defaulting to all-true.
- `INTERPRETATION_SCOPE` — derived: `"structure_only"` if either `allow_text` or
  `allow_context` is explicitly disallowed, else `"structure_and_context"`.

This is a **governance gate on interpretation**, not a mathematical
transformation — it records, alongside the standardized scores, what kind of
downstream reasoning (structure-only vs. structure-plus-surrounding-context) is
permitted to act on them. The function docstring's phrase "Respects Π
interpretation policy" names this mechanism Π (the policy function), and the
comment explains its purpose: *"If text/input_context disallowed, interpretation
must ignore raw text."* This is the layer where a policy decision made elsewhere
in the system (what the caller is allowed to read into the result) becomes part
of the structured output itself, so L9 and any reporting layer downstream can
honor it without needing access to the original policy object.

## Relationship to neighboring layers and corners

- **L1–L7 → L8**: every `SI_*` field is sourced directly from one specific
  upstream layer's field — L8 introduces no new measurement, only
  re-expression. This makes L8 the natural place to verify, by inspection, that
  every important L1–L7 score has a standardized external-facing form.
- **L8 → L9**: per the module docstring, "all 9 layers flow to i18n via L8→L9"
  — L8 is the normalization step that makes the raw pipeline output safe and
  consistent to hand to L9's internationalization/reporting logic (not yet
  documented in this series), since L9 can rely on a fixed unit taxonomy instead
  of needing to know each upstream layer's native scale.
- **Cross-layer convention reuse**: the clamp formula (`max(lo, min(hi, v))`) and
  the `1e-12` epsilon constant declared here as policy are the same conventions
  already seen implemented independently in L1 (`_clamp01`), L5 (`eps`), and L7
  (`_c`) — L8's `EPSILON_POLICY`/`CLAMP_POLICY` fields make explicit, as
  declared data, a convention that was previously only implicit/duplicated
  across the codebase.
