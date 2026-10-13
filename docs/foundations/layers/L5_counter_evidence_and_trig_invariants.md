# Layer 5 — Counter-Evidence Pressure & Trigonometric/Metric Invariants (38_SPEC)

Source: `core/layers/layer_5.py`, function `compute_L5`. Module docstring labels it
"v0.4.x" as a legacy SPEC-era name only — the live spec id is 38_SPEC. 25 variables,
split into two unrelated halves that share nothing but a layer number: **5A**
(counter-evidence / contradiction pressure, 12 variables) and **5B** (trigonometric
and metric-space axiom residuals, 13 variables). Downstream consumers: L7, L8, L9.

This is the first layer in the documented set whose two halves are not a single
coherent measurement — 5A is a live computation over retrieved evidence, 5B is a
**self-test of geometric axioms**, largely independent of the actual pipeline input.
Both are documented in full, and the difference is called out explicitly rather than
smoothed over, per the project's standing provenance discipline: don't make code look
more uniform or more "alive" than it is.

## What L5 receives

- `l1_B`: Layer 1 output for the baseline run — only `DOMINANT_AREA_ID` is used.
- `l4`: Layer 4 output — only `INTEGRITY_CHECK_PASS_RATIO` and
  `EVIDENCE_SUPPORT_INDEX_BASELINE` are used.
- `R_pos`: the same positive-evidence retrieval set already computed for L4
  (`meta["R_B"]`) — L5 does not re-retrieve it.
- `R_neg`: a **separately retrieved** negative-evidence set (`meta["R_neg"]`) —
  chunks retrieved against a negation/contradiction query, independent of `R_pos`.
- `anti_families`: an optional set of family IDs flagged as semantically
  contradictory to the dominant attribution (defaults to empty set if absent).
- `v`, `w`: two real-valued vectors for the 5B self-test, defaulting to the
  orthonormal basis vectors `[1,0]` and `[0,1]` when not supplied.

## Part 5A — Counter-evidence / contradiction pressure (12 variables)

### Conceptual frame: falsification, not confirmation

L4 asks "does the *supporting* evidence for the dominant attribution hold up?" L5
asks the structurally opposite question: "does evidence that should **contradict**
the dominant attribution actually exist, and how much of it is there?" This is the
same shift in stance that separates verificationism from **falsificationism**
(Popper, *The Logic of Scientific Discovery*, 1934/1959) — a hypothesis is tested
not by piling up confirming instances but by actively trying to find what would
refute it. `R_neg` is Hesperia's mechanism for actively searching for refuting
evidence rather than only accumulating supporting evidence, mirrored against the
`anti_families` set (the explicit list of "this would contradict the claim"
categories).

Mechanically, 5A is an exact structural mirror of L4's retrieval-quality logic,
re-run against `R_neg` instead of `R_pos`, reusing the same `_area_of` and
`_jaccard` helpers already documented in
[`L4_evidence_retrieval.md`](L4_evidence_retrieval.md). No new retrieval-theory
lineage needs restating here — what is new is the object being measured
(absence/presence of counter-evidence) and the resulting **pressure** score.

### Variables

| Variable | Formula | Reading |
|---|---|---|
| `ANTI_REGION_SIZE` | `len(anti_families)` | How large the contradiction-category set is. |
| `RETRIEVED_COUNT_NEG` | `len(R_neg)` | Raw count of negative-evidence chunks retrieved. |
| `NEG_SHORTFALL` | `max(0, TOP_K - retrieved_neg)` | Same shortfall pattern as L4 — retrieval-completeness deficit, applied to the negative set. |
| `NEG_UNIQUE_BOOKS` | distinct `bookId` count in `R_neg` | Source diversity of counter-evidence. |
| `NEG_DUPLICATE_BOOK_RATIO` | `1 - NEG_UNIQUE_BOOKS / retrieved_neg` | Same duplication-concentration measure as L4, on the negative set. |
| `NEG_AREA_MATCH_RATIO` | fraction of `R_neg` chunks whose `_area_of(familyId)` equals `dominant_area_B` | How much of the counter-evidence still falls in the *same* geometric area as the dominant claim — high values mean the contradiction is local/internal rather than from an unrelated area. |
| `POS_NEG_BOOKSET_JACCARD` | Jaccard(`pos_books`, `neg_books`) | Source overlap between supporting and contradicting evidence pools. |
| `POS_NEG_CHUNK_JACCARD` | Jaccard(`pos_chunks`, `neg_chunks`) | Chunk-level overlap — non-zero values flag chunks retrieved on both sides. |
| `POS_SUPPORT_INDEX` | passthrough of `EVIDENCE_SUPPORT_INDEX_BASELINE` from L4 | Reuses L4's already-computed support index rather than recomputing it — avoids redundant work and guarantees consistency between layers. |
| `NEG_SUPPORT_INDEX` | fraction of `R_neg` whose `familyId ∈ anti_families` | How much of the retrieved counter-evidence is *actually* in a flagged contradiction category (vs. just being topically unrelated noise). |
| `CONTRADICTION_PRESSURE_SCORE` | `0.55·NEG_SUPPORT_INDEX + 0.25·(1 − POS_SUPPORT_INDEX) + 0.20·POS_NEG_BOOKSET_JACCARD` | Convex combination (weights sum to 1.0), same multi-attribute-scoring pattern as L1/L3/L4's composites — see [`core_math_contract.md`](../corners/core_math_contract.md). Three independent signals of "the claim is under pressure": real anti-evidence found, supporting evidence weak, and source pools overlapping (suggesting ambiguity rather than a clean separation). |
| `REALITY_GATE_COUNTER_EVIDENCE` | `INTEGRITY_CHECK_PASS_RATIO == 1.0 AND NEG_SHORTFALL ≤ MAX_SHORTFALL AND CONTRADICTION_PRESSURE_SCORE ≤ MAX_CONTRADICTION` | Hard AND-gate, same pattern as `SHADOW_ACCEPTABILITY_GATE` (L3) and `EVIDENCE_ACCEPTABILITY_GATE` (L4): all conditions must hold, no averaging masks a single failure. |

Governance constants: `TOP_K=20` (shared default with L4), `MAX_SHORTFALL=2`,
`MAX_CONTRADICTION=0.50`.

## Part 5B — Trigonometric and metric-space invariant residuals (13 variables)

### What this actually is

This half does **not** operate on pipeline data at all by default. `v` and `w`
default to `[1.0, 0.0]` and `[0.0, 1.0]` — a fixed orthonormal pair — and the
module docstring calls this "deterministic pass." Read plainly: 5B is a **runtime
self-test of linear-algebra and metric-space axioms**, not a measurement of
anything about the document, the attribution, or the geometry sphere. It exists to
assert, on every pipeline run, that the basic mathematical identities the rest of
the system relies on (dot-product symmetry, the Cauchy–Schwarz bound, the
Pythagorean trig identity, metric-space axioms) still hold for whatever vector
inputs are in play — a property test, not a content test.

As of **HES-MATH-BEHAV-60..62 (2026-08-05)** the six formerly hardcoded residuals are
**live** from `(v, w, θ)` per `38_SPEC`: law of cosines on the `‖v‖/‖w‖/‖v−w‖`
triangle, 2×2 rotation-by-θ norm preservation + Frobenius orthonormality, triangle
inequality on those sides, and Euclidean metric symmetry/identity. Default
`[1,0]`/`[0,1]` still yields near-zero residuals — sealed `REALITY_GATE_TRIG`
behavior is preserved.

The residuals computed from `v`/`w`/`theta` are genuine, and
each corresponds to a named, centuries-old algebraic identity:

| Variable | Formula | Axiom / identity being tested | Origin |
|---|---|---|---|
| `DOT_SYMMETRY_RESIDUAL` | `\|v·w − w·v\|` | Commutativity of the inner product | Inner-product-space axiom (formalized in Hilbert/Banach-era functional analysis, early 20th c.; the dot product itself traces to Gibbs/Heaviside vector algebra, 1880s) |
| `DOT_SELF_NONNEG_RESIDUAL` | `max(0, −v·v)` | Positive-definiteness of the inner product (`v·v ≥ 0`) | Same inner-product-space axiom set |
| `NORM_CONSISTENCY_RESIDUAL` | `\|‖v‖² − v·v\|` | Definition of the induced norm from the inner product | Same axiom set |
| `COSI_CLAMP_VIOLATION_COUNT` | `1` if `cos θ = (v·w)/(‖v‖‖w‖)` falls outside `[-1, 1]` | Cauchy–Schwarz inequality | Cauchy (1821), Schwarz (1888) |
| `ANGLE_RANGE_VIOLATION_COUNT` | `1` if `θ = arccos(cos θ)` falls outside `[0, π]` | Range of the arccosine / definition of angle between vectors | Classical trigonometry; arccos range convention |
| `SIN_COS_IDENTITY_RESIDUAL` | `\|sin²θ + cos²θ − 1\|` | Pythagorean trigonometric identity | Pythagoras (geometric form, c. 500 BCE); algebraic trig identity, classical |
| (clamping of `cosi_raw` before `acos`) | `max(-1, min(1, cosi_raw))` | Numerical guard so floating-point drift just outside `[-1,1]` doesn't crash `acos` | Standard numerical-analysis practice, not a named theorem |

`REALITY_GATE_TRIG` is the AND of all 13 live residual checks — the same hard-gate
pattern as `REALITY_GATE_COUNTER_EVIDENCE` above and the other layers' acceptability
gates. As of HES-MATH-BEHAV-60..62 every conjunct is computed from `(v, w, θ)`
(default orthonormal pair still passes).

### Why a trig self-test sits inside the pipeline at all

Hesperia's geometry (the icosahedral sphere, area/family embeddings — see
[`geometry_math_coupling.md`](../corners/geometry_math_coupling.md)) depends on
ordinary Euclidean vector-space properties holding: norms behave like norms, angles
behave like angles, cosine similarity (used live in L3's
`HIT_VECTOR_COSINE_SIMILARITY`) stays bounded in `[-1,1]`. L5's 5B half is a
defensive check that those properties have not been silently violated — by a future
refactor, a numerical edge case, or a different vector source than the
fixed-default pair — rather than a measurement specific to any one document or
attribution. It is best read as **infrastructure self-verification**, parallel in
spirit to `core_math.py`'s `check_conservation_pre_decay` and
`check_shadow_non_creation` (documented in
[`core_math_contract.md`](../corners/core_math_contract.md)), but for the
trigonometric/metric layer rather than the energy-conservation layer.

## Relationship to neighboring layers and corners

- **L1 → L5**: only `DOMINANT_AREA_ID` is consumed, to anchor `NEG_AREA_MATCH_RATIO`
  against the same area used throughout L1–L4.
- **L4 → L5**: `INTEGRITY_CHECK_PASS_RATIO` and `EVIDENCE_SUPPORT_INDEX_BASELINE`
  are passed through directly — L5 does not recompute evidence-support, it reuses
  L4's number as `POS_SUPPORT_INDEX` and gates on L4's integrity ratio. This is the
  same "don't duplicate upstream work" pattern as L3 passing area assignments
  through rather than re-deriving them.
- **L5 → L7, L8, L9**: per the module docstring, `compute_L5`'s output is consumed
  by three downstream layers (not yet documented in this series). `REALITY_GATE_COUNTER_EVIDENCE`
  and `REALITY_GATE_TRIG` are the two boolean facts most likely to be read as
  hard pipeline gates by those layers, following the same gate-reading convention
  established at L3/L4.
- **Naming overlap check**: L5's "counter-evidence" (5A) is unrelated to L3's
  "Baseline vs. Shadow" duality or L8's "shadow correction" — three different
  uses of an adversarial/comparative pattern in this pipeline, each structurally
  distinct. Tracked here to prevent conflation, consistent with the L3 doc's
  similar callout for the word "shadow."
- **Reused helpers**: `_area_of` and `_jaccard` are re-implemented locally in
  `layer_5.py` rather than imported from `layer_4.py` — functionally identical to
  L2/L3/L4's versions, confirmed by direct comparison of the source.
