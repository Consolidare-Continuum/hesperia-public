# Parameter catalog — every explicit constant in the system, ground up, and what it means for the output

`parameter_synergies.md` explains which parameters combine and why. The corner docs explain why
each module exists. `parameter_rationale_and_theory.md` answers the academic companion question:
why each parameter is there, why its value/range makes sense, and what theory family it belongs to.
This file is the flat reference neither of those is: every named, explicit math constant currently
live in the system, in pipeline order from geometry up to the final LLM-facing output, with
**what specific meaning it contributes to the output** — not "what it is," but "what changes in
the final artifact if this number changes." Values are read directly from the canon YAMLs and
`core/math/core_math.py`'s `DEFAULT_CONFIG`, not paraphrased.

## 0. Geometry constants — the fixed shape everything else is computed over

| Parameter | Value | Source | Meaning it gives the output |
|---|---|---|---|
| `AREAS` | 12 | `21_MATH` formalization; `SIGMA_001` (`area_vector` length 12) | Every area-level output (dominant area, area entropy, area vector) is a 12-slot structure — changing this would invalidate every Sigma shape check at once. |
| `FAMILIES_PER_AREA` × `AREAS` | 24 × 12 = 288 | same; `SIGMA_002` (`family_counts` length 288) | The resolution of "which family" an output can name — 288 distinct family-level answers. |
| `HEXES_PER_FAMILY` × `TOTAL_FAMILIES` | 250 × 288 = 72,000 (72,240 in the GCS pentagon-defect variant) | `corners/hex_substrate.md` | The finest grain at which a concept hit can be located before rollup to family/area. |
| `SIDES_PER_HEX` | 6 | same | Determines `TOTAL_SIDES`, the dimensionality of the energy vector `E` that `core/math/core_math.py` operates on. |

## 1. Activation / calibration thresholds — what counts as "active" at all

| Parameter | Value | Source | Meaning it gives the output |
|---|---|---|---|
| `activation_threshold` | 0.01 | `assets/specs/canon/activation_calibration.yaml` → `hesperia.engine.calibration.activation_calibration` → live gate `hesperia.engine.kme.clinical_bridge` (CHI-B16-02) | The floor below which a concept hit is treated as noise, not signal — directly determines `active_sides`/`activeSides`, the denominator of nearly every downstream ratio (coherence, fragmentation). |
| `area_active_threshold` | 0.05 | same chain | Same floor, one level up — determines whether an *area* counts as touched at all in coverage (`Φ`, `NodeCoverage`) calculations. |

## 2. Propagation weights — how far and how strongly a signal spreads

| Parameter | Value | Source | Meaning it gives the output |
|---|---|---|---|
| `center_to_inner` | 0.25 | `assets/specs/canon/propagation_weights.yaml` | How much of a concept's activation reaches the next ring out within the same family — the strongest single edge weight in the system. |
| `inner_to_middle` / `middle_to_inner` | 0.18 | same | Second-ring spread, symmetric in both directions. |
| `middle_to_outer` / `outer_to_middle` | 0.12 | same | Outermost-ring spread — the weakest in-area edge, meaning activation thins fastest at the periphery. |
| `bridge_weight` | 0.22 | same | Cross-*area* spread — deliberately close to the strongest in-area weight (0.25), not suppressed; directly controls how much a text's activation in one area "leaks" into a thematically adjacent one in the final area vector. |
| `decay_factor` | 1.0 (no decay) | same | Per-hop attenuation for future multi-hop propagation — currently a no-op, meaning today's single-hop spread is not yet discounted by distance. |

## 3. Core Math Contract constants (`core/math/core_math.py`, `DEFAULT_CONFIG`)

| Parameter | Value | Formula it appears in | Meaning it gives the output |
|---|---|---|---|
| `alpha` | 0.65 | `fusion`: `E0 = α·S' + (1−α)·L'` | How much the fused energy vector trusts Dict A (surface) evidence vs. Dict B (lexical/concept) evidence — 65/35 split toward surface evidence. |
| `eta` | 0.02 | `centroid_indices` | Minimum `E0` value to be eligible as a centroid — controls how many sides count as "active enough to matter" for traversal. |
| `K_max` | 5 | same | Caps how many centroids (dominant sides) the traversal step considers — bounds the output's "how many distinct things were active" answer. |
| `lambda` | 0.55 | `base_step`: `D = (1−λ)E + λ(EW)` | The diffusion/self-retention balance — at 0.55, the next-step energy leans slightly toward "what neighbors had" over "what this side already had." |
| `decay` | 0.04 | `base_step` | Per-step energy loss — over `T_steps=8` steps, compounds to a meaningful overall attenuation, shaping how much signal survives to the final read. |
| `E_cap` | 1.0 | fusion, base_step clamp | The ceiling every energy value is held under — guarantees no output value can report "activation" above 1.0 regardless of upstream magnitude. |
| `k_amb` | 0.35 | `P_amb = k_amb·(1−gap)²` | How heavily an unclear top-1-vs-top-2 winner penalizes the governance score — quadratic in the closeness of the gap, so near-ties are penalized disproportionately more than slight gaps. |
| `delta_gap` | 0.08 | ambiguity `degraded` flag | The gap below which the output is flagged "ambiguity-degraded" as a discrete fact, independent of the continuous `P_amb` penalty. |
| `tau_core` | 0.25 | thin-core `degraded` flag | The `CoreShare` floor below which the output is flagged "thin-core-degraded" — i.e., too little of the read came from surface (Dict A) evidence. |
| `k_thin` | 0.30 | `P_thin = k_thin·(1−CoreShare)` | How heavily a Dict-B-dominated (lexical-only) read is penalized in governance. |
| `k_disp` | 0.25 | `P_disp = k_disp·H_norm` | How heavily a too-spread-out (high-entropy) final energy distribution is penalized. |
| `k_guard` | 0.30 | `P_guard` | How heavily each Sigma/Gamma/Theta failure directly taxes the governance score, independent of the guard's own pass/fail gating elsewhere. |
| `k_shadow` | 0.40 | `P_shadow_value` | How heavily shadow-hop usage is penalized — the single largest penalty coefficient, reflecting that shadow correction is treated as a necessary but costly fallback. |
| `max_shadow_hops` | 2 | `P_shadow`, `metric_obstacle_score` | The ceiling on how many shadow hops are tolerated before the penalty saturates at its maximum. |
| `w_decay`, `w_guard_obs`, `w_shadow_obs` | 0.50, 0.30, 0.20 | `metric_obstacle_score` (convex combination, CI-enforced to sum to 1.0) | Exact proportional attribution of the final "obstacle score" to energy loss vs. guard pressure vs. shadow cost — half the obstacle reading is always about energy loss, never less. |
| `energy_conservation_tolerance` | 1e-6 | `check_conservation_pre_decay` | How strict the conservation-of-energy check is before an output is allowed to be trusted as a valid diffusion step at all. |

## 4. Diagnostic / logic rule thresholds — what the output is allowed to call itself

**Live (canonical):** `assets/specs/canon/logic_rules.yaml` via `sphere/logic/rule_engine.py`
(Layer-9), on `/product/tfp`, `/product/fingerprint`, `/product/llm-audit` — **not**
`/product/interpret`. CHI-B16-03 / CHI-006.

**Deprecated (do not tune as Tier B):** `assets/specs/canon/diagnostic_rules.yaml` +
`sphere/diagnostics/` — unwired everywhere; see `sphere/diagnostics/README.md`.

Live Layer-9 concepts (representative; declarative rules, not all former B6 keys):

| Concept | Live rule (approx) | Meaning |
|---|---|---|
| Low entropy → monotony | `RULE_001`: `entropy < 0.35` | Structurally narrow discourse |
| High curvature → instability | `RULE_003`: `curvature > 1.20` | Trajectory instability |
| Low coverage | `RULE_004`: `coverage < 0.60` | Sparse / low-coverage flag |
| Low stability | `RULE_005`: `stability_index < 0.25` | Volatile movement |

Historical `diagnostic_rules.yaml` numeric table (orphaned — kept for archaeology only):

| Parameter | Value | Meaning it gives the output |
|---|---|---|
| `ultra_sparse_coverage_threshold` | 0.02 | Below this coverage, the output is flagged a zero-signal/anomalous read rather than a substantive structural state. |
| `excessive_jump_threshold` | 0.60 | Above this, a single-step change is flagged anomalous rather than a normal trajectory shift. |
| `transition_concentration_threshold` | 0.75 | Above this, the output's transition pattern is flagged as suspiciously concentrated (possible artifact rather than genuine structure). |
| `entropy_threshold` (monotony) | 0.35 | Below this entropy, the output is classified `structural_monotony` — "structurally narrow discourse" — the exact number this report's earlier analysis traced back to Shannon entropy, not Kolmogorov complexity. |
| `coverage_threshold` (monotony) | 0.20 | Combined with the entropy check, low coverage below this is part of what makes a read count as monotonous rather than merely focused. |
| `dominant_area_share_threshold` | 0.65 | Above this share, an output is eligible to be called "dominant-area" structurally — this is a *different* threshold from `DOMINANT_SHARE_HIGH=0.35` in the FGR table (§5), which gates trust in a *rule event*, not the structural classification itself; the two numbers answer different questions despite both being about area dominance. |
| `unique_areas_max` | 2 | Caps how many distinct areas a read can touch and still be called monotonous. |
| `curvature_threshold` / `severe_curvature_threshold` | 1.20 / 1.50 | Two-tier thresholds for when a trajectory's curvature is flagged instability vs. severe instability in the output. |
| `jump_rate_threshold` / `severe_jump_rate_threshold` | 0.30 / 0.50 | Same two-tier pattern for how often the structural state jumps between turns. |
| `low_stability_threshold` | 0.15 | Below this, `stability_index` itself is low enough to flag the output as unstable independent of curvature/jump metrics. |

## 5. FGR / Freshness calibration — what the LLM is told to trust, per evidence item

(Full numeric table already in `parameter_synergies.md` §4 — restated here only for catalog
completeness.) `DOMINANT_SHARE_HIGH=0.35`, `ENTROPY_DROP_SIGNIFICANT=0.15`,
`STABILITY_CURRENT_THRESHOLD=0.7`, `STABILITY_STALE_THRESHOLD=0.3` gate which of two FGR tiers
(both encoded as `(formality, scope, reliability)` triples, e.g. `dominant_area` high tier =
`(0.9, 0.7, 0.9)`) and which `Freshness` enum value (`CURRENT`/`STALE`/`EXPIRED`) get attached to
each `EvidencePrimitive` the LLM substrate receives. This is the only parameter group in this
catalog whose "output" is not a number in a report but **permission for the LLM to narrate at a
given confidence level.**

## 6. KME primitives and derived metrics — comparability output

The six bounded primitives (`LD, COH, NC, PR, PV, CI`, each `[0,1]`) and the 35 derived ratio/product
metrics (`corners/kme.md`) are parameters in a different sense: not fixed constants but
*computed* values whose meaning is entirely relational — `KSI = clamp01(safe_div(COH·LD, PR))`
means nothing as a raw number except in comparison to another document's `KSI`. Their output
contribution is comparability itself: the fingerprint hash (`fingerprint/builder.py`) exists so
that two of these vectors can be diffed, which is the one thing none of the constants in §0–§5
provide on their own (each of those describes a single run, not a comparison between runs).

## 7. TRIZ relation weights and clustering seed

| Parameter | Value | Meaning it gives the output |
|---|---|---|
| `conflict` / `negation` relation weight | 1.0 | Full-strength contradiction signal — these relation types are treated as unambiguous tension. |
| `opposition` relation weight | 0.85 | Slightly discounted — opposition is treated as real but slightly less certain tension than direct conflict/negation. |
| `LOUVAIN_SEED` | 42 | Makes innovation-cluster membership in the output reproducible run-to-run; without it, the same input could produce different cluster assignments. |

## 8. Field Dynamics extension (`hesperia/extensions/dynamics/`) — internal, not yet on the output path

Full account in `corners/field_dynamics.md`. Listed here for catalog completeness only: these ~47
constants currently produce a separate, optional E2E artifact
(`run_output_e2e_field_dynamics.json`) that `runtime/services/product_interpret_service.py` never
reads — `EXTENSION_STATUS.yaml` classifies this extension's product surface as `internal`, not
`optional`/shipped. None of the rows below change anything in `/product/interpret` output today;
they are catalogued because they are live, tested, environment-gated code, not because they are
reachable.

| Parameter group | Count | Values / range | Meaning it would give the output, if connected |
|---|---|---|---|
| `Phase1Theta` (L6 area / L7 pressure / L9 stability) | 9 | `lambda_a=0.35, gamma_f=0.4, gamma_q=0.15, gamma_p=0.08, mu_a=0.4, delta_a=0.12, rho_a=0.02, lambda_c=0.3, alpha_in=0.25` | Decay/inject/diffuse/pressure-penalize dynamics for the 12-area state vector across turns. |
| `Phase2Theta` (L5 family) | 9 | `lambda_f=0.35, beta_x=0.42, beta_intra=0.08, beta_area=0.1, beta_pf=0.06, mu_f=0.4, delta_f=0.1, rho_f=0.002, area_hit_weight=0.52` | Same shape one level down, at the 288-family grain; `area_hit_weight` blends direct hits vs. family-aggregate injection. |
| `Phase3Theta` (L4 hex active subgraph) | 9 | `hex_cap=128, lambda_h=0.32, theta_c=0.45, theta_d=0.18, theta_p=0.06, mu_h=0.38, delta_h=0.08, rho_h=0.001, hex_hit_blend=0.48` | Same shape at the hex-cell grain, capped to a sparse active set (env-overridable via `HESPERIA_FIELD_DYNAMICS_HEX_CAP`, clamped `[8, 288]`). |
| `Phase4Theta` (L8 cluster gravity) | 3 | `gravity_epsilon=0.055, tau_front=0.085, ephemeral_cap=96` | Cross-family cluster attraction and narrative-front-edge detection. |
| Ξ tension proxy (`xi_proxy.py`) | 4 | `xi_scale=0.14` (env `HESPERIA_FIELD_DYNAMICS_XI_SCALE`), `xi_kme_weight=0.55`, plus hardcoded (non-env) blend constants `0.35`/`0.65` in `boost = xi_scale·(0.35·global + 0.65·per_area)` | Amplifies `contradiction_signal_12` from TRIZ rows (and optionally KME) — **on by default** (`HESPERIA_FIELD_DYNAMICS_XI` defaults `"1"`) whenever the master gate is on, unlike every other phase. |
| HSPR Calibration Index (`calibration.py`) | 7 | 6 weighted components (`0.25/0.25/0.15/0.15/0.10/0.10` for stability/source-alignment/energy/contradiction/diffusion/resistance) + `source_alignment_kappa=1.0` | Grid-search fitness function for tuning the Phase-N thetas themselves — a meta-calibration score, not a runtime output value. |
| Semantic Field v1 (`equations.py` / `semantic_field_v1.py`) | 11 | `alpha=0.15, beta=0.08, gamma=0.12, delta=0.25, mu=0.01, dt=0.05, epsilon=0.0001, tau=0.02, resistance_uniform=1.0, production_clip=true, signed_source_experimental=false` | A physically-styled diffusion-equation coefficient set (`E = (α/2)FᵀLF + (β/2)FᵀRF + (γ/2)FᵀCF − δSᵀF`) — **not the same constants** as the Phase-N thetas above despite sharing Greek letter names; gated separately behind `HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1`. |
| DLCR blend (`e2e_bridge.py`) | 1 | `dlcr_alpha=0.22` | Weight for lexical-concept-recovery hits blended into family injection; gated behind `HESPERIA_FIELD_DYNAMICS_DLCR`. |
| `profiles_v1.json` hex reference | — | *(removed CHI-014-02)* | Nested `hex_field_reference` deleted — was never loaded; sibling profile keys still live for Semantic Field. |

## How to use this file

This is a lookup table, not an argument. When a number in an output (a governance score, a
monotony flag, an FGR tier, a KSI value) needs tracing back to *which constant produced it and
why that constant has the value it has*, start here, then follow the cited corner doc for the full
reasoning. When tuning any of these values, check `parameter_synergies.md` first — several of them
(propagation weights vs. shadow correction's entropy cap; the three `metric_obstacle_score`
weights) are calibrated as a set, not independently.
