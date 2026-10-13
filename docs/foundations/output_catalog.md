# Output catalog — every aggregated variable that reaches a consumer, ground up from L1 to the LLM

`parameter_catalog.md` answers "which constant produced this output and why does it have that
value." This file answers the other half of the same question: **once those constants have done
their work, what are the actual named variables a consumer — an operator reading `/analyze`, the
`/product/interpret` HTTP caller, or the LLM sitting behind `fpf_bridge` — receives?** These are not
raw measurements in most cases; from L7 up they are aggregations of aggregations (a `PILLAR_*`
score is a weighted blend of an `SI_*` value that is itself a rescaled `L1`–`L6` composite). They
are still parameters in the sense this package uses the word: named, typed, bounded values whose
exact composition a reader needs traceable, not just their existence.

**Every name and formula below was read directly from the implementing source** —
`core/layers/layer_1.py` through `layer_9.py`, `core/domain/derived_metrics.py`,
`sphere/fpf_bridge/constants.py`, `runtime/services/product_interpret_service.py` — not paraphrased
from the layer docs in `layers/*.md`. Where the layer's own docstring claim ("25 variables") didn't
match the literal key count returned, the original per-layer specs (`34_SPEC` through `42_SPEC`)
were recovered from an archived full-repo snapshot and are now restored into this repo at
`docs/specs/history/` (see `provenance.md` for the recovery chain) — cross-checked against
each layer's code, every apparent discrepancy resolved cleanly against the spec's own numbered
list (see each layer section below for the specific resolution), with one genuine exception: L7's
`STABILITY_ANOMALY_SCORE` and profile-conformance fields are real, code-only additions made after
`40_SPEC` was written, not spec omissions. See `provenance.md` for how these specs were located and
what that means for citing them.

## 0. Two live product surfaces, not one

- **`/analyze` (frozen HSPR-01/02, `docs/ENGINE-ANALYZE-CONTRACT.md`)** — 9 mandatory top-level
  fields: `trace[]` (per-step `area_id`/`family_id`/`concept_id`/`label`/`activation`/
  `confidence`), `dominant_area_id`, `dominant_family_id`, `dominant_concept_id`, `governance`,
  `loopability`, `tension_energy`, `obstacle_score`, `contradiction_flags[]`, `weak_signals[]`.
  This is the contract `HesperiaPublicSnapshot.from_engine_result()` parses against; still frozen.
- **`/product/interpret` (FPF-V7-12, `runtime/services/product_interpret_service.py`)** — always
  returns `schema`, `mode`, `router_envelope` (the L1–L9 + fpf_bridge compile), `interpretation`
  (`mode`, `structural_summary`, `dominant_activation`, `dominant_label`, `router_fingerprint`,
  `trace_steps`), `engine_trace_hash`, `router_fingerprint`, `evidence_ids`
  (`input_hash`/`corpus_snapshot_id`/`policy_snapshot_id`), `decision`, `router_mode`. Adds
  `cobalt_retrieval` when COBALT is enabled. When `mode="llm"`, adds `llm`, `prompt_envelope`,
  `router_output_audit`, `router_decision`, `governed_decision`, `evidence_ids.output_hash`, and,
  strict-mode-only, `governance_warning`/`governance_block` (which also collapses `interpretation`
  to a `"blocked"` stub and drops `llm` entirely). **`field_dynamics` output never appears here** —
  see §13.

## 1. L1 — structural activation census (`core/layers/layer_1.py`, 34_SPEC)

Docstring claims "25 variables base"; `compute_L1`'s base return dict literally has **27 keys**.
Resolved against the recovered spec
(`docs/specs/history/34_SPEC__V0_4_Layer1_Instrumentation_25_Variables_v1_0.txt`, restored from
archive — see `provenance.md`): the spec's own numbered list has exactly 25 entries,
but item 18 ("`UNIQUE_AREAS_HIT` / `AREA_SPREAD`") bundles two variable names into one numbered
entry — 25 spec entries → 26 actual variables. The 27th key, `PROFILE_MODE_ACTIVE`, is a code-only
metadata flag outside the spec's numbered list entirely (not present in `34_SPEC` at all — added
later as an explicit, never-inferred flag per the code's own comment "never infer from PCS
presence"). Plus, only when a `profile` argument is supplied, 6 more `34_SPEC N1` profile-conformance
keys (3 always present, 3 conditional on which profile fields are set) — up to **33 keys total**.

| # | Variable | Type/Range | Meaning |
|---|---|---|---|
| 1 | `PROFILE_MODE_ACTIVE` | bool | Whether a structure profile was supplied for this run |
| 2 | `TOTAL_TOKENS` | int | Token count of the input |
| 3 | `ATTRIBUTED_TOKENS` | int | Tokens matched to Dict A/B |
| 4 | `COVERAGE_RATIO` | float [0,1] | `ATTRIBUTED_TOKENS / TOTAL_TOKENS` |
| 5 | `UNIQUE_FAMILIES_HIT` | int [0,288] | Count of distinct families with ≥1 hit |
| 6 | `FAMILY_ACTIVATION_DENSITY` | float [0,1] | `UNIQUE_FAMILIES_HIT / F` |
| 7 | `FAMILY_HIT_VECTOR_L1` | float | L1 norm of hit vector (= `ATTRIBUTED_TOKENS`) |
| 8 | `FAMILY_HIT_VECTOR_L2` | float | L2 norm of hit vector (concentration) |
| 9 | `MAX_FAMILY_HITS` | int | Peak single-family hit count |
| 10 | `DOMINANT_FAMILY_ID` | int [0,287] | Argmax family (first index on ties) |
| 11 | `DOMINANT_AREA_ID` | int [0,11] | `DOMINANT_FAMILY_ID // FAMILIES_PER_AREA` |
| 12 | `DOMINANCE_RATIO` | float [0,1] | `MAX_FAMILY_HITS / ATTRIBUTED_TOKENS` |
| 13 | `MEAN_ALTITUDE_GLOBAL` | float [0,1] | Hit-weighted mean altitude, all families |
| 14 | `MEAN_ALTITUDE_DOMINANT` | float [0,1] | Mean altitude within the dominant family only |
| 15 | `ALTITUDE_VARIANCE_GLOBAL` | float | Hit-weighted variance of per-family mean altitude |
| 16 | `FAMILY_ENTROPY` | float [0, ln F] | Shannon entropy of the family hit distribution |
| 17 | `NORMALIZED_FAMILY_ENTROPY` | float [0,1] | `FAMILY_ENTROPY / ln(F)`, clamped |
| 18 | `GINI_COEFFICIENT` | float [0,1] | Inequality of hit distribution across families |
| 19 | `UNIQUE_AREAS_HIT` | int [0,12] | Count of distinct areas with ≥1 hit |
| 20 | `AREA_SPREAD` | float [0,1] | `UNIQUE_AREAS_HIT / A` |
| 21 | `AREA_DOMINANCE_RATIO` | float [0,1] | Hits in dominant area / attributed |
| 22 | `SECONDARY_FAMILY_RATIO` | float [0,1] | Runner-up family hits / max hits |
| 23 | `SIGNAL_TO_NOISE_RATIO` | float ≥0 | Max hits / (attributed − max hits) |
| 24 | `SPARSITY_INDEX` | float [0,1] | `1 − FAMILY_ACTIVATION_DENSITY` |
| 25 | `TOKEN_REDUNDANCY_RATIO` | float [0,1] | `1 − (unique_families / attributed)` |
| 26 | `ALTITUDE_WEIGHTED_MASS` | float ≥0 | Σ over families of hits × mean altitude |
| 27 | `STRUCTURAL_STABILITY_INDEX` | float [0,1] | `DOMINANCE_RATIO × (1 − NORMALIZED_FAMILY_ENTROPY)` — feeds L7 `SYSTEM_CONFIDENCE_SCORE` |

**Profile metrics** (only when `profile` supplied; `PROFILE_MODE_ACTIVE=True`):

| # | Variable | Always present? | Meaning |
|---|---|---|---|
| 28 | `PROFILE_ID` | always (with profile) | Name/version string identifying the active profile |
| 29 | `PROFILE_VERSION` | always | Profile's own version tag |
| 30 | `PROFILE_CHECKSUM` | always | Content hash of the profile, for audit trail |
| 31 | `FAMILY_PROFILE_DEVIATION` | always | L2 distance, observed vs. expected family distribution, `/√2` normalized |
| 32 | `AREA_PROFILE_DEVIATION` | always | Same, at area grain |
| 33 | `PROFILE_CONFORMANCE_SCORE` | always | `1 − weighted_penalty`; hard-gates L7 decision code 75 |
| — | `FORBIDDEN_MASS_PENALTY` | only if profile has `DENY_FAMILIES` | Hit mass landing in denied families |
| — | `ALTITUDE_DEVIATION` | only if profile has `ALT_BAND`/`ALT_TARGET` | Distance from altitude band/target |
| — | `BUDGET_VIOLATION_SCORE` | only if profile has any `MAX_*`/`MIN_*` cap | Worst single budget-cap breach (max, not averaged) |

**Total L1: 27 base + up to 6 profile keys = 33 max.**

## 2. L2 — topology traversal (`core/layers/layer_2.py`, 35_SPEC)

Docstring says "25 variables"; the return dict has those 25 plus 2 explicit downstream handoffs
(`VISITED_IDS`, `MASS_AT_DEPTH`) the code comments flag as feeding L3/L6 rather than being
independent measurements — **27 keys total**.

| # | Variable | Type/Range | Meaning |
|---|---|---|---|
| 1 | `TRAVERSAL_START_FAMILY` | int | BFS root (= L1 `DOMINANT_FAMILY_ID`) |
| 2 | `BASE_NEIGHBOR_COUNT` | int | Degree of the start family |
| 3 | `ACTIVE_NEIGHBOR_COUNT` | int | Neighbors of start with ≥1 hit |
| 4 | `NEIGHBOR_ACTIVATION_RATIO` | float [0,1] | `ACTIVE_NEIGHBOR_COUNT / BASE_NEIGHBOR_COUNT` |
| 5 | `TRAVERSAL_DEPTH_REACHED` | int | Deepest BFS depth with nonzero mass |
| 6 | `TOTAL_REACHABLE_NODES` | int | Count of families visited within `MAX_ALLOWED_DEPTH` |
| 7 | `REACH_RATIO` | float [0,1] | `TOTAL_REACHABLE_NODES / F` |
| 8 | `MEAN_TRAVERSAL_DISTANCE` | float | Average BFS hop distance over visited set |
| 9 | `MAX_TRAVERSAL_DISTANCE` | int | Deepest single hop reached |
| 10 | `TRAVERSAL_RADIUS_RATIO` | float [0,1] | `MAX_TRAVERSAL_DISTANCE / MAX_ALLOWED_DEPTH` |
| 11 | `PATH_COUNT` | int | BFS tree edges (`TOTAL_REACHABLE_NODES − 1`) |
| 12 | `BRANCHING_FACTOR_MEAN` | float | Mean degree over the visited set |
| 13 | `LOCAL_CLUSTERING_COEFFICIENT` | float [0,1] | Watts-Strogatz clustering at the start family |
| 14 | `PROPAGATION_MASS_DECAY` | float | Mass ratio between the two deepest populated depths |
| 15 | `MASS_RETENTION_RATIO` | float | Total mass in visited set / start family's own mass |
| 16 | `CROSS_AREA_TRAVERSAL_COUNT` | int | Visited families outside the dominant area |
| 17 | `CROSS_AREA_RATIO` | float [0,1] | `CROSS_AREA_TRAVERSAL_COUNT / TOTAL_REACHABLE_NODES` — feeds L9 area-containment |
| 18 | `AREA_BOUNDARY_CROSSINGS` | int | BFS tree edges that cross an area boundary |
| 19 | `TRAVERSAL_COMPACTNESS` | float | `TOTAL_REACHABLE_NODES / (MAX_TRAVERSAL_DISTANCE + 1)` |
| 20 | `LOOP_COUNT` | int | Induced-subgraph edges beyond the BFS tree (cycles) |
| 21 | `LOOP_DENSITY` | float [0,1] | `LOOP_COUNT / TOTAL_REACHABLE_NODES` |
| 22 | `CENTRALITY_SHIFT` | float | \|degree(start) − mean degree over visited set\| |
| 23 | `EDGE_UTILIZATION_RATIO` | float [0,1] | BFS tree edges / total induced-subgraph edges |
| 24 | `TRAVERSAL_SYMMETRY_INDEX` | float | Variance of BFS distance from start, over visited set |
| 25 | `GEOMETRIC_STABILITY_INDEX` | float [0,1] | `MASS_RETENTION × (1−CROSS_AREA_RATIO) × (1−LOOP_DENSITY)` — feeds L7/L9 `PILLAR_GEOMETRY` |
| 26 | `VISITED_IDS` | list[int] | Family IDs reached — internal handoff to L3 (Jaccard) and L7 (`g4` gate) |
| 27 | `MASS_AT_DEPTH` | list[float] | Per-depth mass profile — internal handoff to L6 (`DEPTH_GROWTH_RATIO`) |

**Total L2: 27.**

## 3. L3 — baseline/shadow comparison (`core/layers/layer_3.py`, 36_SPEC)

**25 keys, exactly matching the docstring.**

| # | Variable | Type/Range | Meaning |
|---|---|---|---|
| 1 | `SHADOW_ENABLED` | bool | Always `True` when L3 runs at all (a shadow pair was supplied) |
| 2 | `DOMINANT_FAMILY_CHANGED` | bool | Baseline vs. shadow dominant family differ |
| 3 | `DOMINANT_AREA_CHANGED` | bool | Baseline vs. shadow dominant area differ |
| 4 | `DOMINANT_FAMILY_DELTA_HITS` | int | Hit-count delta at (each run's own) dominant family |
| 5 | `DOMINANCE_RATIO_DELTA` | float | Shadow − baseline `DOMINANCE_RATIO` |
| 6 | `COVERAGE_RATIO_DELTA` | float | Shadow − baseline `COVERAGE_RATIO` |
| 7 | `UNIQUE_FAMILIES_HIT_DELTA` | int | Shadow − baseline unique family count |
| 8 | `AREA_SPREAD_DELTA` | float | Shadow − baseline `AREA_SPREAD` |
| 9 | `ENTROPY_DELTA` | float | Shadow − baseline `NORMALIZED_FAMILY_ENTROPY` |
| 10 | `GINI_DELTA` | float | Shadow − baseline `GINI_COEFFICIENT` |
| 11 | `ALTITUDE_MEAN_DELTA` | float | Shadow − baseline `MEAN_ALTITUDE_GLOBAL` |
| 12 | `ALTITUDE_DOMINANT_DELTA` | float | Shadow − baseline `MEAN_ALTITUDE_DOMINANT` |
| 13 | `TRAVERSAL_DEPTH_DELTA` | int | Shadow − baseline `TRAVERSAL_DEPTH_REACHED` |
| 14 | `REACHABLE_NODES_DELTA` | int | Shadow − baseline `TOTAL_REACHABLE_NODES` |
| 15 | `MAX_DISTANCE_DELTA` | int | Shadow − baseline `MAX_TRAVERSAL_DISTANCE` |
| 16 | `CROSS_AREA_RATIO_DELTA` | float | Shadow − baseline `CROSS_AREA_RATIO` |
| 17 | `LOOP_DENSITY_DELTA` | float | Shadow − baseline `LOOP_DENSITY` |
| 18 | `EDGE_UTILIZATION_DELTA` | float | Shadow − baseline `EDGE_UTILIZATION_RATIO` |
| 19 | `VISITED_JACCARD_SIMILARITY` | float [0,1] | Jaccard of baseline vs. shadow `VISITED_IDS` |
| 20 | `VISITED_SYMMETRIC_DIFFERENCE_RATIO` | float [0,1] | `1 − Jaccard`, i.e. symmetric-difference share |
| 21 | `FAMILY_HIT_VECTOR_L1_DELTA` | float | Shadow − baseline L1 norm of hit vector |
| 22 | `HIT_VECTOR_COSINE_SIMILARITY` | float [−1,1] | Cosine similarity, baseline vs. shadow hit vectors |
| 23 | `TOP_K_OVERLAP_RATIO` | float [0,1] | Overlap of top-K families, baseline vs. shadow |
| 24 | `SHADOW_DEVIATION_SCORE` | float | `0.35·(1−cosine) + 0.35·sym_diff + 0.30·|dominance_delta|` — feeds L7/L9 |
| 25 | `SHADOW_ACCEPTABILITY_GATE` | bool | Deviation, cross-area delta, and area-flip all within policy caps |

**Total L3: 25.**

## 4. L4 — evidence retrieval (`core/layers/layer_4.py`, 37_SPEC)

**25 keys, exactly matching the docstring.**

| # | Variable | Type/Range | Meaning |
|---|---|---|---|
| 1 | `RETRIEVAL_MODE_ID` | string | Retrieval engine identifier (`"LEX_BM25_V1"`) |
| 2 | `TOP_K` | int | Target retrieval count (default 20) |
| 3 | `RETRIEVED_COUNT_BASELINE` | int | Chunks actually retrieved, baseline |
| 4 | `RETRIEVED_COUNT_SHADOW` | int | Chunks actually retrieved, shadow |
| 5 | `RETRIEVAL_SHORTFALL_BASELINE` | int | `max(0, TOP_K − retrieved)` — gates L9 `ACTION_REQUIRE_EVIDENCE_REBUILD` |
| 6 | `RETRIEVAL_SHORTFALL_SHADOW` | int | Same, shadow run |
| 7 | `UNIQUE_BOOKS_BASELINE` | int | Distinct source books in baseline retrieval |
| 8 | `UNIQUE_BOOKS_SHADOW` | int | Same, shadow |
| 9 | `DUPLICATE_BOOK_RATIO_BASELINE` | float [0,1] | `1 − unique_books/retrieved` |
| 10 | `DUPLICATE_BOOK_RATIO_SHADOW` | float [0,1] | Same, shadow |
| 11 | `FAMILY_MATCH_COUNT_BASELINE` | int | Retrieved chunks tagged with the dominant family |
| 12 | `FAMILY_MATCH_RATIO_BASELINE` | float [0,1] | `FAMILY_MATCH_COUNT / retrieved` — 0.45 weight in support index |
| 13 | `AREA_MATCH_RATIO_BASELINE` | float [0,1] | Retrieved chunks in dominant area / retrieved — 0.35 weight |
| 14 | `TOP_K_FAMILY_COVERAGE_BASELINE` | float [0,1] | Distinct families represented in retrieval / F |
| 15 | `EVIDENCE_ENTROPY_BASELINE` | float [0,1] | Normalized Shannon entropy of retrieved-chunk family distribution |
| 16 | `EVIDENCE_GINI_BASELINE` | float [0,1] | Gini of same distribution |
| 17 | `RANK_WEIGHTED_ALIGNMENT_BASELINE` | float [0,1] | Rank-weighted (`1/(r+1)`) share of retrieved chunks in dominant area |
| 18 | `HIT_EVIDENCE_OVERLAP_BASELINE` | float [0,1] | Jaccard: active (hit) families vs. retrieved-chunk families |
| 19 | `HIT_EVIDENCE_OVERLAP_SHADOW` | float [0,1] | Same, shadow |
| 20 | `EVIDENCE_JACCARD_BS` | float [0,1] | Jaccard of baseline vs. shadow retrieved chunk IDs |
| 21 | `BOOKSET_JACCARD_BS` | float [0,1] | Jaccard of baseline vs. shadow book sets |
| 22 | `EVIDENCE_SHIFT_SCORE` | float [0,1] | `1 − EVIDENCE_JACCARD_BS` |
| 23 | `INTEGRITY_CHECK_PASS_RATIO` | float [0,1] | Fraction of retrieved chunks with a valid checksum — gates L7 `g6` (hard) |
| 24 | `EVIDENCE_SUPPORT_INDEX_BASELINE` | float [0,1] | `0.45·family_match + 0.35·area_match + 0.20·hit_overlap` — the single most load-bearing L4 output |
| 25 | `EVIDENCE_ACCEPTABILITY_GATE` | bool | Integrity, shortfall, support, and duplication all within policy caps |

**Total L4: 25.**

## 5. L5 — counter-evidence & trig invariants (`core/layers/layer_5.py`, 38_SPEC)

**25 keys, exactly matching the docstring**, in two unrelated halves.

**5A — counter-evidence / contradiction pressure:**

| # | Variable | Type/Range | Meaning |
|---|---|---|---|
| 1 | `ANTI_REGION_SIZE` | int | Count of families flagged as "anti" (contradicting) the dominant read |
| 2 | `RETRIEVED_COUNT_NEG` | int | Counter-evidence chunks retrieved |
| 3 | `NEG_SHORTFALL` | int | `max(0, TOP_K − retrieved_neg)` |
| 4 | `NEG_UNIQUE_BOOKS` | int | Distinct books in counter-evidence set |
| 5 | `NEG_DUPLICATE_BOOK_RATIO` | float [0,1] | `1 − unique/retrieved`, counter-evidence |
| 6 | `NEG_AREA_MATCH_RATIO` | float [0,1] | Counter-evidence chunks in dominant area / retrieved |
| 7 | `POS_NEG_BOOKSET_JACCARD` | float [0,1] | Book overlap, positive vs. negative evidence — 0.20 weight in pressure score |
| 8 | `POS_NEG_CHUNK_JACCARD` | float [0,1] | Chunk overlap, positive vs. negative |
| 9 | `POS_SUPPORT_INDEX` | float [0,1] | `= EVIDENCE_SUPPORT_INDEX_BASELINE` passthrough from L4 |
| 10 | `NEG_SUPPORT_INDEX` | float [0,1] | Fraction of counter-evidence chunks tagged to an anti-family — 0.55 weight |
| 11 | `CONTRADICTION_PRESSURE_SCORE` | float | `0.55·neg_support + 0.25·(1−pos_support) + 0.20·bookset_jaccard` — feeds L9 `CONSISTENCY_U1000` |
| 12 | `REALITY_GATE_COUNTER_EVIDENCE` | bool | Integrity, shortfall, and pressure all within policy caps — gates L7 `g9` |

**5B — trig/metric-space axiom self-test** (all 13 residuals live from `(v,w,θ)` per `38_SPEC`
as of HES-MATH-BEHAV-60..62, 2026-08-05; default orthonormal pair still yields near-zero residuals):

| # | Variable | Live or hardcoded-0 | Meaning |
|---|---|---|---|
| 13 | `DOT_SYMMETRY_RESIDUAL` | live | \|dot(v,w) − dot(w,v)\| |
| 14 | `DOT_SELF_NONNEG_RESIDUAL` | live | `max(0, −dot(v,v))` — non-negativity check |
| 15 | `NORM_CONSISTENCY_RESIDUAL` | live | \|‖v‖² − dot(v,v)\| |
| 16 | `COSI_CLAMP_VIOLATION_COUNT` | live | 1 if raw cosine falls outside [−1,1], else 0 |
| 17 | `ANGLE_RANGE_VIOLATION_COUNT` | live | 1 if arccos angle falls outside [0,π], else 0 |
| 18 | `LAW_OF_COSINES_RESIDUAL` | **live** | \|c² − (a²+b²−2ab cos θ)\| with a=‖v‖, b=‖w‖, c=‖v−w‖ |
| 19 | `SIN_COS_IDENTITY_RESIDUAL` | live | \|sin²θ + cos²θ − 1\| |
| 20 | `ROTATION_NORM_PRESERVATION_RESIDUAL` | **live** | \|‖R(θ)·v₂‖ − ‖v₂‖\| for 2×2 rotation by θ |
| 21 | `ORTHONORMALITY_RESIDUAL_FROBENIUS` | **live** | Frobenius ‖RᵀR − I‖ |
| 22 | `TRIANGLE_INEQUALITY_VIOLATION_COUNT` | **live** | 1 if triangle sides a,b,c violate inequality else 0 |
| 23 | `METRIC_SYMMETRY_RESIDUAL` | **live** | \|d(v,w) − d(w,v)\| |
| 24 | `METRIC_IDENTITY_RESIDUAL` | **live** | max(\|d(v,v)\|, \|d(w,w)\|) |
| 25 | `REALITY_GATE_TRIG` | live (AND of all 13 above) | Gates L7 `g8` and L9 `ACTION_ALLOW_HUMAN_SUMMARY` |

**Total L5: 25 (12 counter-evidence + 13 live trig/metric self-tests including AND-gate).**

## 6. L6 — dynamical stability scaffold (`core/layers/layer_6.py`, 39_SPEC)

**25 keys, exactly matching the docstring.** Only 4 are live/derived; the other 21 are documented
no-perturbation identity constants (`0.0`/`1.0`/`True`/`False`), a named scaffold reserved for a
future perturbation-analysis pass — not an oversight. **HES-MATH-BEHAV-54..57 (2026-08-05):**
gradient / curvature / Group-IV Newtonian+functional slots stay PARTIAL with explicit `39_SPEC`
formula notes in `layer_6.py` — do not invent finite differences without `E(x±ε)`.

| # | Variable | Live or stub | Value if stub | Meaning |
|---|---|---|---|---|
| 1 | `INPUT_PERTURBATION_RESPONSE` | stub | 0.0 | Sensitivity to input delta |
| 2 | `DOMINANT_FAMILY_STABILITY` | stub | True | Whether dominant family survives perturbation |
| 3 | `COVERAGE_GRADIENT` | stub | 0.0 | Rate of change of coverage |
| 4 | `ENTROPY_GRADIENT` | stub | 0.0 | Rate of change of entropy |
| 5 | `STABILITY_RADIUS` | stub | 1.0 | Perturbation tolerance — feeds `CONCEPTUAL_COHERENCE_INDEX` |
| 6 | `SECOND_ORDER_RESPONSE` | stub | 0.0 | Curvature of stability response |
| 7 | `DOMINANCE_CURVATURE` | stub | 0.0 | Curvature of dominance over perturbation |
| 8 | `ENTROPY_CURVATURE` | stub | 0.0 | Curvature of entropy over perturbation |
| 9 | `HIT_VECTOR_RANK` | stub | 1 | Rank of the hit vector |
| 10 | `PRINCIPAL_COMPONENT_ENERGY_RATIO` | stub | 1.0 | Energy concentration in top principal component |
| 11 | `CONDITION_NUMBER` | stub | 1.0 | Matrix condition number — feeds `GLOBAL_STABILITY_SCORE` |
| 12 | `SPECTRAL_GAP` | stub | 0.0 | Eigenvalue spread |
| 13 | `DEPTH_GROWTH_RATIO` | **live** | — | `mass_at_depth[1] / mass_at_depth[0]` from L2's BFS |
| 14 | `FIBONACCI_DEVIATION_SCORE` | **live** | — | \|mass[2] − (mass[1]+mass[0])\| — Fibonacci-growth deviation test |
| 15 | `EXPONENTIAL_FIT_ERROR` | stub | 0.0 | Fit error against exponential mass falloff |
| 16 | `POWER_LAW_FIT_ERROR` | stub | 0.0 | Fit error against power-law mass falloff |
| 17 | `POTENTIAL_GRADIENT` | stub | 0.0 | Potential-field gradient analog |
| 18 | `ESCAPE_ENERGY_THRESHOLD` | stub | 1.0 | Energy needed to leave current structural basin |
| 19 | `FORCE_ANALOG_MAGNITUDE` | stub | 0.0 | Force-like quantity analog |
| 20 | `MONOTONICITY_CHECK` | stub | True | Whether mass decay is monotonic |
| 21 | `FIXED_POINT_DETECTION` | stub | True | Whether a fixed point exists |
| 22 | `CYCLE_DETECTION_FUNCTIONAL` | stub | False | Whether a dynamical cycle was detected |
| 23 | `LYAPUNOV_ESTIMATE` | **live** (constant 0.0 today) | — | Lyapunov exponent estimate — gates L7 `g10`/`MAX_CHAOS_LEVEL` |
| 24 | `GLOBAL_STABILITY_SCORE` | **live** | — | `1/(1+CONDITION_NUMBER+|LYAPUNOV_ESTIMATE|)` — feeds L7/L8/L9 `PILLAR_STABILITY` |
| 25 | `CONCEPTUAL_COHERENCE_INDEX` | **live** | — | `STABILITY_RADIUS × (1−entropy) × GLOBAL_STABILITY_SCORE` |

**Total L6: 25 (4 genuinely live, 21 scaffold constants).**

## 7. L7 — consistency and decision (`core/layers/layer_7.py`, 40_SPEC)

**25 base keys, exactly matching the docstring and the recovered spec** — `40_SPEC`
(`docs/specs/history/40_SPEC__V0_4_Layer7_Cross_Layer_Interactions_Limits_Aggregates_25_Variables_v1_0.txt`,
restored from archive — see `provenance.md`) confirms `OUTPUT_TRUST_TAG` is its
item 25, closing what an earlier pass of this file miscounted as "24 base." Plus, only when a
profile is active, `CONSIST_PROFILE_CONFORMANCE` and (conditionally)
`PROFILE_CHECKSUM`; plus, only when a `stability` anomaly score is supplied to `run()` and exceeds
threshold, `STABILITY_ANOMALY_SCORE` (which also demotes `OUTPUT_TRUST_TAG` to `"LOW_CONFIDENCE"`
post-hoc — this demotion path is not visible in `compute_L7` itself, only in the `run()` wrapper).

| # | Variable | Type | Meaning |
|---|---|---|---|
| 1 | `CONSIST_COVERAGE_MIN_GATE` (`g1`) | bool | `COVERAGE_RATIO ≥ MIN_COVERAGE_RATIO` |
| 2 | `CONSIST_ATTRIBUTION_MASS_EQUALITY` (`g2`) | bool | L1 norm of hit vector ≈ attributed tokens |
| 3 | `CONSIST_TRAVERSAL_NONEMPTY_WHEN_ATTRIBUTED` (`g3`) | bool | Traversal is empty iff attribution is empty |
| 4 | `CONSIST_DOMINANT_FAMILY_IN_TRAVERSAL` (`g4`) | bool | Dominant family appears in L2's visited set |
| 5 | `CONSIST_AREA_MAPPING` (`g5`) | bool | Dominant area correctly derives from dominant family |
| 6 | `CONSIST_EVIDENCE_INTEGRITY_HARD` (`g6`) | bool | L4 integrity pass ratio is exactly 1.0 |
| 7 | `CONSIST_SHADOW_DELTA_ONLY_IF_SHADOW` (`g7`) | bool | Shadow delta is zero unless a shadow run actually happened |
| 8 | `CONSIST_TRIG_REQUIRED_FOR_ANGLE_METRICS` (`g8`) | bool | `= L5 REALITY_GATE_TRIG` |
| 9 | `CONSIST_COUNTER_EVIDENCE_VALID` (`g9`) | bool | `= L5 REALITY_GATE_COUNTER_EVIDENCE` |
| 10 | `CONSIST_STABILITY_REGIME_VALID` (`g10`) | bool | Lyapunov estimate is finite and not NaN |
| 11 | `TRUST_TIER` | int [0,3] | 0 if `g1` fails, 1 if `g6` fails, 2 if `g8` fails, else 3 |
| 12 | `MAX_ALLOWABLE_SHADOW_DEVIATION` | float | Echoed policy constant |
| 13 | `SHADOW_WITHIN_LIMITS` | bool | `= L3 SHADOW_ACCEPTABILITY_GATE` |
| 14 | `MAX_ALLOWABLE_CONTRADICTION` | float | Echoed policy constant |
| 15 | `CONTRADICTION_WITHIN_LIMITS` | bool | `L5 CONTRADICTION_PRESSURE_SCORE ≤` policy cap |
| 16 | `MAX_AREA_LEAKAGE` | float | Echoed policy constant |
| 17 | `AREA_LEAKAGE_WITHIN_LIMITS` | bool | `L2 CROSS_AREA_RATIO ≤` policy cap |
| 18 | `MAX_CHAOS_LEVEL` | float | Echoed policy constant (Lyapunov cap) |
| 19 | `STRUCTURE_EVIDENCE_ALIGNMENT` | float [0,1] | `0.60·L4 support + 0.40·L2 geometric_stability` |
| 20 | `SHADOW_EVIDENCE_ALIGNMENT_DELTA` | float | Shadow support − baseline support |
| 21 | `SHADOW_JUSTIFICATION_SCORE` | float [0,1] | Nonzero only if shadow gate passed **and** shadow improved support |
| 22 | `CONTRADICTION_ADJUSTED_SUPPORT` | float [0,1] | `L4 support × (1 − L5 pressure)` |
| 23 | **`SYSTEM_CONFIDENCE_SCORE`** | float [0,1] | `(tier/3) × L1.stability × L2.geometric × contradiction_adjusted_support × L6.global_stability` — the single most-aggregated number in the system |
| 24 | **`DECISION_STATUS_CODE`** | int | `0` pass; else `10/20/30/40/50/60/70` by which gate failed first, `75` reserved for profile-conformance failure |
| 25 | `OUTPUT_TRUST_TAG` | string | `HIGH`/`MED`/`LOW` from code+confidence thresholds — spec item 25 |
| cond. | `CONSIST_PROFILE_CONFORMANCE` | bool | Only present when a profile is active — not in `40_SPEC`'s original 25, a later profile-mode addition |
| cond. | `PROFILE_CHECKSUM` | hash | Only present when a profile is active and supplies a checksum — same, later addition |
| cond. | `STABILITY_ANOMALY_SCORE` | float | Only present when `run()` receives a `stability` dict; also demotes `OUTPUT_TRUST_TAG` to `"LOW_CONFIDENCE"` — code-only, post-spec addition |

**Total L7: 25 base (spec-exact) + up to 3 conditional, code-only additions beyond the original spec = 28 max.**

## 8. L8 — unit standardization (`core/layers/layer_8.py`, 41_SPEC)

**30 keys**: 5 policy/metadata constants (always identical text), 22 `SI_*` metrics computed by
`compute_L8`, and 3 more always added by the `run()` wrapper (`POLICY_MODE`,
`INTERPRETATION_CONSTRAINTS`, `INTERPRETATION_SCOPE`) regardless of whether a policy was supplied.

| # | Variable | Meaning |
|---|---|---|
| 1 | `UNIT_TYPE_ENUM` | Fixed reference string: `"COUNT,RATIO,PERCENT,U1000,RADIANS,SECONDS,BYTES,HASH,BOOLEAN,CODE"` |
| 2 | `SCALE_POLICY_ENUM` | Fixed reference string: `"RAW,CLAMP_0_1,CLAMP_0_100,CLAMP_0_1000,ZSCORE,LOG10"` |
| 3 | `EPSILON_POLICY` | `1e-12` |
| 4 | `CLAMP_POLICY` | Fixed formula string: `"max(lo,min(hi,v))"` |
| 5 | `ROUNDING_POLICY` | Fixed string: `"DECIMALS_RATIO=6,DECIMALS_PCT=2,DECIMALS_U1000=0"` |
| 6 | `SI_TOTAL_TOKENS_COUNT` | int, `= L1 TOTAL_TOKENS` |
| 7 | `SI_COVERAGE_PCT` | `L1 COVERAGE_RATIO → [0,100]` |
| 8 | `SI_COVERAGE_U1000` | `L1 COVERAGE_RATIO → [0,1000]` — feeds L9 bands |
| 9 | `SI_DOMINANCE_PCT` | `L1 DOMINANCE_RATIO → [0,100]` |
| 10 | `SI_DOMINANCE_U1000` | `L1 DOMINANCE_RATIO → [0,1000]` |
| 11 | `SI_ENTROPY_U1000` | `L1 NORMALIZED_FAMILY_ENTROPY → [0,1000]` |
| 12 | `SI_ENTROPY_PCT` | Same, `[0,100]` |
| 13 | `SI_GEOMETRIC_STABILITY_U1000` | `L2 GEOMETRIC_STABILITY_INDEX → [0,1000]` |
| 14 | `SI_GEOMETRIC_STABILITY_PCT` | Same, `[0,100]` |
| 15 | `SI_AREA_LEAKAGE_PCT` | `L2 CROSS_AREA_RATIO → [0,100]` |
| 16 | `SI_AREA_LEAKAGE_U1000` | Same, `[0,1000]` — L9 inverts to `AREA_CONTAINMENT_U1000` |
| 17 | `SI_SHADOW_DEVIATION_U1000` | `L3 SHADOW_DEVIATION_SCORE → [0,1000]` |
| 18 | `SI_SHADOW_DEVIATION_PCT` | Same, `[0,100]` |
| 19 | `SI_EVIDENCE_SUPPORT_U1000` | `L4 EVIDENCE_SUPPORT_INDEX_BASELINE → [0,1000]` |
| 20 | `SI_EVIDENCE_SUPPORT_PCT` | Same, `[0,100]` |
| 21 | `SI_CONTRADICTION_PRESSURE_U1000` | `L5 CONTRADICTION_PRESSURE_SCORE → [0,1000]` |
| 22 | `SI_CONTRADICTION_PRESSURE_PCT` | Same, `[0,100]` |
| 23 | `SI_TRIG_REALITY_FLAG` | bool, `= L5 REALITY_GATE_TRIG` passthrough |
| 24 | `SI_GLOBAL_STABILITY_U1000` | `L6 GLOBAL_STABILITY_SCORE → [0,1000]` |
| 25 | `SI_GLOBAL_STABILITY_PCT` | Same, `[0,100]` |
| 26 | `SI_SYSTEM_CONFIDENCE_U1000` | `L7 SYSTEM_CONFIDENCE_SCORE → [0,1000]` — feeds L9 confidence bands |
| 27 | `SI_SYSTEM_CONFIDENCE_PCT` | Same, `[0,100]` |
| 28 | `POLICY_MODE` | string, default `"STRUCTURE_PLUS_CONTEXT"` — always present |
| 29 | `INTERPRETATION_CONSTRAINTS` | dict `{allow_text, allow_context, allow_structure}` — always present |
| 30 | `INTERPRETATION_SCOPE` | `"structure_only"` or `"structure_and_context"` — the Π gate limiting what L9/LLM may claim |

**Total L8: 30.**

## 9. L9 — pillars, brand labels, and action triggers (`core/layers/layer_9.py`, 42_SPEC) — the terminus

**25 keys, exactly matching the docstring and the recovered spec** — verified directly against
`compute_L9`, and cross-checked against `42_SPEC`
(`docs/specs/history/42_SPEC__V0_4_Layer9_Human_Reference_Brand_Treatment_25_Variables_v1_0.txt`,
restored from archive — see `provenance.md`), whose own numbered list resolves the
numbering below — item order follows the spec, not the code's dict-literal order. Every one of
these 25 is user-facing by construction; there is no further "internal-only" tier above this layer.

| Group | # (per `42_SPEC`) | Variable | Rule |
|---|---|---|---|
| Bands | 1–6 | `BAND_0_CRITICAL` … `BAND_5_EXCELLENT` | Mutually exclusive on `SI_SYSTEM_CONFIDENCE_U1000`: `<200 / 200–400 / 400–600 / 600–800 / 800–950 / ≥950` |
| Reference strings | 7–8 | `DIRECTIONALIZE_HIGH_IS_GOOD`, `DIRECTIONALIZE_LOW_IS_GOOD` | Fixed formula strings (`"clamp(u,0,1000)"` / `"1000-clamp(u,0,1000)"`) documenting the i18n/reporting directionalization convention, not values |
| Directional reframes | 9–10 | `AREA_CONTAINMENT_U1000`, `CONSISTENCY_U1000` | `1000 − SI_AREA_LEAKAGE_U1000`; `1000 − SI_CONTRADICTION_PRESSURE_U1000` — genuine spec-numbered outputs, not internal-only scratch values; pillars 8 and 10 below consume them directly |
| Pillars | 11 | `PILLAR_INPUT_QUALITY_U1000` | `round(0.60·SI_COVERAGE + 0.40·SI_DOMINANCE)`, clamped |
| Pillars | 12 | `PILLAR_GEOMETRY_U1000` | `round(0.70·SI_GEOMETRIC_STABILITY + 0.30·AREA_CONTAINMENT_U1000)`, clamped |
| Pillars | 13 | `PILLAR_EVIDENCE_U1000` | `= SI_EVIDENCE_SUPPORT_U1000` (direct passthrough) |
| Pillars | 14 | `PILLAR_CONSISTENCY_U1000` | `round(0.60·CONSISTENCY_U1000 + 0.40·(1000−SI_ENTROPY))`, clamped |
| Pillars | 15 | `PILLAR_STABILITY_U1000` | `= SI_GLOBAL_STABILITY_U1000` (direct passthrough) |
| Pillars | 16 | `PILLAR_GOVERNANCE_U1000` | `1000` if `DECISION_STATUS_CODE==0`, else `clamp(1000 − 10·code, 0, 1000)` |
| Brand words | 17 | `BRAND_WORD_TRUST` | Trust ladder (exact thresholds in `layer_9.py` lines 61–66) |
| Brand words | 18 | `BRAND_WORD_EVIDENCE` | `SUPPORTED ≥800 / BACKED ≥600 / THIN ≥400 / else UNSUPPORTED` on `SI_EVIDENCE_SUPPORT_U1000` |
| Brand words | 19 | `BRAND_WORD_CONTRADICTION` | `CONSISTENT ≥800 / MIXED ≥600 / CONTESTED ≥400 / else CONTRADICTED` on `CONSISTENCY_U1000` |
| Brand words | 20 | `BRAND_WORD_GEOMETRY` | `CONTAINED ≥800 / STABLE ≥600 / DIFFUSE ≥400 / else CHAOTIC` on `PILLAR_GEOMETRY_U1000` |
| Brand words | 21 | `BRAND_WORD_SHADOW` | Stateful: `OFF` (no shadow) → `REJECTED`/`JUSTIFIED`/`NEUTRAL` (see `layer_9.py` lines 70–75) |
| Actions | 22 | `ACTION_REQUIRE_MORE_INPUT` | `SI_COVERAGE_U1000 < 500` |
| Actions | 23 | `ACTION_REQUIRE_EVIDENCE_REBUILD` | `L4 INTEGRITY_CHECK_PASS_RATIO < 1.0` or `L4 RETRIEVAL_SHORTFALL_BASELINE > MAX_SHORTFALL` |
| Actions | 24 | `ACTION_REQUIRE_GOVERNANCE_REVIEW` | `L7 DECISION_STATUS_CODE != 0` or `SI_SYSTEM_CONFIDENCE_U1000 < 450` |
| Actions | 25 | `ACTION_ALLOW_HUMAN_SUMMARY` | `code==0` **and** `confidence≥650` **and** `SI_TRIG_REALITY_FLAG` — the release gate |

**Total L9: 25 (spec-exact).**

## 10. KME — six primitives, 35 pure-algebra derived metrics (`core.domain`, compat facade in `hesperia.engine.kme/`)

Six bounded primitives (`LD, COH, NC, PR, PV, CI`, each `[0,1]`) feed
`derived/calculator.py::compute_derived_metrics`, which computes **exactly 35** named
ratios/products — verified letter-for-letter against source:

`KDI, CSI, SPI, TDS, SSS, KCI, CCI, SPS, DCI, CSI2, KEF, ASS, CDR, KCR, TCI, PEI, KE, SCS, CRI, KNS,
CII, TEP, KSI, CDD, SSR, TER, CPC, KBS, TRI, IDE, KPS, TBI, KDI2, CDI, KVI`

Each is strictly `clamp01(product-or-safe_div of primitives only)` — no re-access to the underlying
graph (see `corners/kme.md`). `to_full_fingerprint` concatenates primitives + derived into a fixed
41-element vector, hashed for cross-run/cross-document comparison. **Total KME: 6 + 35 = 41.** Not
part of `/analyze` or `/product/interpret`'s response body — reaches consumers only via
`clinical_bridge.py` and TRIZ's read-only `kme_bridge.py`.

## 11. TRIZ — three named decision-intelligence exports (`corners/triz_extension.md`)

Read-only against everything above; not part of either HTTP contract.

- **Policy Contradiction Detector** — per item: `contradiction_score`, `contradiction_density`,
  `area_id`, `family_ids`, `triz_principle` (`segmentation`/`counterbalance`/`parameter_change`/
  `dynamic_adaptation`).
- **Innovation Radar** — per cluster: `innovation_score`, `rarity`, `contradiction_density`,
  `propagation_reach`; aggregate: `cluster_count`, `max_innovation_score`, `mean_innovation_score`.
- **Narrative Propagation Monitor** — per narrative: `penetration`, `velocity`, `stability`;
  aggregate versions of the same three.

## 12. `fpf_bridge` (Layer 11) — the state machine the LLM actually sees

`sphere/fpf_bridge/constants.py` defines exactly **5** structural states — verified against source:

| State constant | String value | Risk level |
|---|---|---|
| `STATE_FOCUSED_DOMINANT` | `"focused_dominant"` | normal |
| `STATE_DISTRIBUTED_BALANCED` | `"distributed_balanced"` | low |
| `STATE_UNSTABLE_TRANSITION` | `"unstable_transition"` | high |
| `STATE_TENSION_ELEVATED` | `"tension_elevated"` | high |
| `STATE_DIFFUSE_SPREAD` | `"diffuse_spread"` | normal |

The LLM does not receive L1–L9's ~190 raw variables at all; `bridge_to_llm_prompt()`'s envelope is
a **projection**: one active state, its legal next transitions with evidence requirements,
pre-evaluated Sigma/Gamma/Theta guard verdicts as closures, and FGR-calibrated evidence primitives
(`parameter_catalog.md` §5's "permission to narrate at a given confidence level," not a number).

**Evidence surface, as of `fpf_bridge_v7_2` (2026-07-04, flag-gated off by default, ratification
pending — `assets/specs/canon/fpf_bridge_v7_2_evidence_expansion.md`):** the original 7 signal types (5
rule types, raw area activations, one stability score) are joined by, when
`HESPERIA_FPF_EVIDENCE_EXPANSION`/`HESPERIA_FPF_CONTRADICTION_GATE`/`HESPERIA_FPF_KME_EVIDENCE` are
set — L5's `contradiction_pressure`/`counter_evidence_gate` (with the native `contradicts` field
finally populated, naming which evidence a contradiction is actually in tension with), L7's
`trust_tier`/`system_confidence`/`decision_status`, L4's `evidence_support_baseline`, KME's 6
primitives + `kme_ksi`, and TRIZ's `triz_contradiction_*` (explicitly namespaced apart from
`contradiction_pressure` — two independently-computed contradiction mechanisms, never averaged).
KME and TRIZ evidence defaults to the same core bounded context as everything else — both are
general-purpose Hesperia mechanisms, not TFP-/COBALT-exclusive, a correction made mid-build to the
spec that introduced them. None of this changes the projection discipline above: still a menu of
FGR-scored evidence and legal transitions, never the raw L1–L9 dict.

## 13. Excluded on purpose: `field_dynamics`

`hesperia/extensions/dynamics/` produces real, named, tested output variables (`area_a`, `p_a`,
`stab`, `f_f`, `p_family`, `hex_x`, `hex_p`, `l8_clusters`, `fronts_12`, `contradiction_signal_12`,
`injection_12`, …) but reaches neither `/analyze` nor `/product/interpret` — see
`corners/field_dynamics.md` and `parameter_catalog.md` §8. Deliberately excluded from the count
below on the same "no path to a consumer today" grounds, however live and tested the code is.

## Grand total: verified, consumer-reachable output variables

| Source | Count | Reachable via |
|---|---|---|
| `/analyze` legacy contract | 9 top-level (+ 6 per trace step) | `/analyze` only |
| L1 | 27 base + up to 6 profile | `router_envelope` (`/product/interpret`) |
| L2 | 27 | `router_envelope` |
| L3 | 25 | `router_envelope` |
| L4 | 25 | `router_envelope` |
| L5 | 25 | `router_envelope` |
| L6 | 25 | `router_envelope` |
| L7 | 24 base + up to 3 conditional | `router_envelope`; `governance`/confidence surface `/analyze` too |
| L8 | 30 | `router_envelope` |
| L9 | 25 | `router_envelope` — terminal, all user-facing |
| KME | 41 (6 primitive + 35 derived) | `clinical_bridge.py`, TRIZ, fingerprint queries — not either HTTP contract |
| TRIZ | 3 shaped export products (field counts vary per product) | TRIZ exports only |
| `fpf_bridge` | 5 structural states | `prompt_envelope` (`/product/interpret`, `mode="llm"`) |

**~239–248 distinct named L1–L9 variables** (exact figure depends on whether a profile is active
and whether L7's optional anomaly/profile fields fire), **+41 KME + 5 fpf_bridge states + 9
`/analyze`-only fields + 3 TRIZ product shapes**, none of which double-count `field_dynamics`'s
separately-tracked ~47 constants (`parameter_catalog.md` §8), because those never reach a consumer.

## How the aggregation actually chains (two worked examples)

- **Trust:** L4 `EVIDENCE_SUPPORT_INDEX_BASELINE` → (unchanged) L7's alignment term inside
  `SYSTEM_CONFIDENCE_SCORE` → L8 `SI_EVIDENCE_SUPPORT_U1000` (rescale only) → L9
  `PILLAR_EVIDENCE_U1000` (passthrough) and `BRAND_WORD_EVIDENCE` (threshold only) — four layers,
  one rescale, one threshold, zero re-blends.
- **Confidence:** L1 `STRUCTURAL_STABILITY_INDEX` × L2 `GEOMETRIC_STABILITY_INDEX` × L4/L5
  contradiction-adjusted support × L6 `GLOBAL_STABILITY_SCORE` all multiply together at L7 into
  `SYSTEM_CONFIDENCE_SCORE` — a genuine four-factor product — before L8 rescales it and L9 bands it.
  Knowing which of these two shapes a given `PILLAR_*`/`BRAND_WORD_*` is is the difference between
  "trace one upstream cause" and "trace four independent upstream causes."

## Relationship to neighboring references

- `parameter_catalog.md` — the input/calibration-constant counterpart to this file.
- `corners/interpretation_usf.md`, `corners/schemas_contracts.md` — why the USF exists as one
  consolidated fingerprint, and why `/analyze`'s shape is frozen and checked at the boundary.
- `corners/fpf_bridge.md` — the full reasoning for why the LLM gets the §12 projection instead of
  any of §1–§9's raw variables directly.
- `corners/field_dynamics.md` / `parameter_catalog.md` §8 — the field-dynamics precedent this
  file's §13 exclusion follows.
