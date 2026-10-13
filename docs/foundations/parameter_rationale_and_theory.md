# Parameter rationale and theory map — why these values exist, and what scientific family they belong to

`parameter_catalog.md` tells you **what each explicit constant changes in the output**. This file
answers the adjacent academic question: **why is that parameter here at all, why is its value in
this range or at this magnitude, and what theory family is it borrowing from?**

Two honesty rules govern this file:

1. **Verified** means the reason is stated directly in a spec, code comment, range registry, or
   existing foundations/publication doc.
2. **Inferred** means the reason is reconstructed from current wiring, neighboring constants, and
   the subsystem's role. This is still useful, but it is not passed off as an author quote.

For raw values, use `parameter_catalog.md`. For cross-citation of named external science, use
`references.md` and `docs/publication/SCIENCE.md`. This file is the bridge between them.

## 0. Geometry constants

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `AREAS = 12` | Not tuned as a free scalar; 12 is forced by the chosen icosahedral area sphere. The point is uniform closed-surface coverage with a fixed area vector shape Sigma can check. | Platonic-solid geometry, geodesic/icosahedral tessellation | Verified | `references.md`, `corners/topology_geometry.md`, `parameter_catalog.md` |
| `FAMILIES_PER_AREA × AREAS = 24 × 12 = 288` | Fixes semantic resolution at a stable ontology grain: fine enough to distinguish families, still bounded enough for a fixed vector contract and tractable propagation. | Engine ontology design over fixed graph resolution | Inferred | `parameter_catalog.md`, `output_catalog.md`, `corners/topology_geometry.md` |
| `HEXES_PER_FAMILY × TOTAL_FAMILIES = 250 × 288` | Chooses a much finer landing substrate below family level so diffusion has room to move before rollup; 250 is the local-resolution budget per family. | Hex-grid discretization, graph-based field resolution | Inferred | `parameter_catalog.md`, `corners/hex_substrate.md` |
| `SIDES_PER_HEX = 6` | Comes from the hex substrate itself: six equal-distance neighbors is exactly the adjacency regularity Hesperia wants before aggregation. | Hexagonal lattice geometry | Verified | `references.md`, `corners/hex_substrate.md` |

## 1. Activation and calibration thresholds

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `activation_threshold = 0.01` | Keeps very weak lexical/concept hits from counting as active while staying low enough not to erase weak-but-real evidence. It is a noise floor, not a confidence statement. | Thresholded sparse activation, calibration discipline | Inferred | `parameter_catalog.md`, `specs/canon/activation_calibration.yaml` |
| `area_active_threshold = 0.05` | Stricter than the raw hit floor because an area should not count as genuinely touched by a few crumbs of activation. Area-level claims are intentionally harder to trigger than side-level activity. | Aggregated-state thresholding, coverage control | Inferred | `parameter_catalog.md`, `output_catalog.md` |

## 2. Propagation weights

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `center_to_inner = 0.25` | Strongest local edge weight: preserves the intuition that nearest semantic neighborhood should receive the largest share of spread. | Graph diffusion on layered local neighborhoods | Verified | `parameter_catalog.md`, `references.md`, `parameter_synergies.md` |
| `inner_to_middle = 0.18` and `middle_to_inner = 0.18` | Lower than center-to-inner to make outward spread decay with distance while preserving reversibility/symmetry within the ring model. | Distance-sensitive diffusion | Inferred | `parameter_catalog.md` |
| `middle_to_outer = 0.12` and `outer_to_middle = 0.12` | Lowest in-area weight so the perimeter remains reachable but diluted; this keeps the far ring from dominating the read by simple connectivity alone. | Distance decay in local diffusion fields | Inferred | `parameter_catalog.md` |
| `bridge_weight = 0.22` | Deliberately high enough to allow meaningful cross-area leakage, but still below the strongest local edge. This is the parameter that lets Hesperia represent "semantic bleed" instead of a sealed area silo. | Cross-region coupling on a semantic graph | Verified | `parameter_catalog.md`, `parameter_synergies.md` |
| `decay_factor = 1.0` | A conscious no-op today: the architecture leaves room for explicit multi-hop attenuation, but current single-hop propagation is documented as undamped by hop distance. | Diffusion architecture with deferred distance attenuation | Verified | `parameter_catalog.md` |

## 3. Core Math Contract constants

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `alpha = 0.65` | Favors surface evidence (`S'`) over lexical/concept evidence (`L'`) so the fused energy field stays anchored in observable wording instead of drifting into a purely derived concept cloud. | Weighted fusion over normalized evidence channels | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `eta = 0.02` | Prunes negligible energy before centroid selection; the point is to keep traversal from chasing numerical dust. | Sparse centroid selection under bounded energy | Inferred | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `K_max = 5` | Hard cap on how many centroids can define the read; this prevents the "everything was active" failure mode from expanding traversal breadth without bound. | Bounded multi-centroid graph traversal | Inferred | `parameter_catalog.md` |
| `lambda = 0.55` | Slightly favors redistributed neighbor mass over pure self-retention, which makes diffusion real rather than decorative while keeping the update close to a lazy Markov-like step. | Row-stochastic/lazy-chain-style diffusion | Verified | `parameter_catalog.md`, `corners/core_math_contract.md`, `provenance.md` |
| `decay = 0.04` | Small enough that an 8-step run still preserves meaningful signal, large enough that stale energy does not circulate forever. | Damped discrete-time propagation | Inferred | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `E_cap = 1.0` | Makes energy a bounded normalized quantity everywhere; after that choice, comparisons and guards can assume a closed unit interval. | Bounded normalized field values | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `k_amb = 0.35` | Ambiguity matters, but does not dominate the governance score by itself; the coefficient is large enough to punish near-ties while remaining one term in an additive penalty set. | Additive penalty composition | Inferred | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `delta_gap = 0.08` | Discrete "ambiguity-degraded" threshold below which the top two energies are too close to narrate a clear winner, even if the continuous penalty is modest. | Decision-boundary thresholding | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `tau_core = 0.25` | Requires at least a quarter of the evidence mass to come from the surface side before the read is considered to have a healthy surface anchor. | Evidence-anchor sufficiency threshold | Inferred | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `k_thin = 0.30` | Thin-core reads are penalized materially, but slightly less than ambiguity. This keeps the model wary of over-derived readings without making them automatically fatal. | Additive governance penalties | Inferred | `parameter_catalog.md` |
| `k_disp = 0.25` | Dispersion penalty is meaningful but lower than ambiguity and shadow. The system tolerates some spread as long as it is not the dominant pathology. | Shannon-entropy-based dispersion penalty | Verified | `parameter_catalog.md`, `references.md`, `corners/core_math_contract.md` |
| `k_guard = 0.30` | Guard failures should hurt both categorically and numerically; this makes shape/order/governance failures visible inside the composite score, not only as booleans. | Composite penalty fed by certification failures | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `k_shadow = 0.40` | Highest penalty coefficient because shadow correction is explicitly a costly fallback, not a normal happy-path mechanism. | Fallback-cost penalization | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `max_shadow_hops = 2` | Very short leash on correction depth; if shadow propagation needs more than two hops, the system treats that as saturation-level cost. | Bounded corrective traversal | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `w_decay = 0.50` | Makes energy loss the largest contributor to `metric_obstacle_score`; half the obstacle reading is about signal attrition itself. | Convex-weighted diagnostic aggregation | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `w_guard_obs = 0.30` | Keeps guard pressure as the second-largest obstacle component: important, but not more important than actual energy loss. | Convex-weighted diagnostic aggregation | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `w_shadow_obs = 0.20` | Shadow cost influences obstacle score, but least of the three obstacle terms. It is a downstream correction cost, not the first explanatory lens. | Convex-weighted diagnostic aggregation | Verified | `parameter_catalog.md`, `corners/core_math_contract.md` |
| `energy_conservation_tolerance = 1e-6` | Numerical strictness threshold: tight enough to catch genuine conservation drift, loose enough to avoid false positives from floating-point residue. | Numerical-analysis tolerance for conservation laws | Verified | `parameter_catalog.md`, `corners/core_math_contract.md`, `REPRODUCIBILITY_PACKAGE.md` |

## 4. Diagnostic rule thresholds

These are best read as **classification boundaries**, not physical constants. Their main rationale
is interpretive honesty: when does a metric become strong enough to deserve a label?

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `ultra_sparse_coverage_threshold = 0.02` | Reserves the "real structure" labels for non-trivial coverage; below this, the system treats the read as near-zero signal. | Sparse-activation anomaly gating | Inferred | `parameter_catalog.md`, `specs/canon/diagnostic_rules.yaml` |
| `excessive_jump_threshold = 0.60` | A large single-step trajectory change should be explicitly abnormal, not just "dynamic." | State-sequence change-point thresholding | Inferred | `parameter_catalog.md` |
| `transition_concentration_threshold = 0.75` | Flags when most transition mass is collapsing into one route, which suggests an artifact-like pattern rather than distributed structural motion. | Transition-matrix concentration diagnostics | Inferred | `parameter_catalog.md` |
| `entropy_threshold = 0.35` | Low enough to truly mean narrowness, high enough not to call every focused read monotonous. The rationale is Shannon entropy over a bounded categorical distribution, not Kolmogorov machinery. | Shannon-entropy-based narrowness detection | Verified | `parameter_catalog.md`, `references.md`, `provenance.md` |
| `coverage_threshold = 0.20` | Monotony should mean both narrow spread and limited reach, not just low entropy by itself. | Joint thresholding over breadth and concentration | Verified | `parameter_catalog.md` |
| `dominant_area_share_threshold = 0.65` | High bar for saying an area truly dominates structurally; this is stricter than the bridge's trust-tier threshold because structural labeling is a stronger claim than evidence grading. | Dominance classification thresholding | Verified | `parameter_catalog.md` |
| `unique_areas_max = 2` | More than two touched areas is too distributed to call monotonous, even if entropy is low. | Cardinality-based regime labeling | Inferred | `parameter_catalog.md` |
| `curvature_threshold = 1.20` and `severe_curvature_threshold = 1.50` | Two-tier instability scale: one for notable bending, one for severe bending. | Trajectory-shape diagnostics | Inferred | `parameter_catalog.md` |
| `jump_rate_threshold = 0.30` and `severe_jump_rate_threshold = 0.50` | Same two-tier design for frequent structural jumps across turns. | State-transition volatility diagnostics | Inferred | `parameter_catalog.md` |
| `low_stability_threshold = 0.15` | Keeps the "unstable" label for genuinely weak stability values, not any mild imperfection. | Stability-floor thresholding | Inferred | `parameter_catalog.md` |

## 5. FGR and freshness thresholds

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `DOMINANT_SHARE_HIGH = 0.35` | At this point a dominant-area rule has enough local strength to merit the higher FGR tier, even though that is still below the stronger structural-label threshold of 0.65. | Trust-calibrated evidence grading (FPF FGR applied to Hesperia evidence) | Verified | `parameter_synergies.md`, `fpf_bridge` docs |
| `ENTROPY_DROP_SIGNIFICANT = 0.15` | Sets the cutoff for when an entropy drop is strong enough to upgrade trust tier instead of being treated as a mild fluctuation. | Trust-calibrated evidence grading | Inferred | `parameter_synergies.md` |
| `STABILITY_CURRENT_THRESHOLD = 0.7` | Only clearly stable runs are marked `CURRENT`; the bridge does not equate middling stability with freshness. | Stability-to-freshness mapping for evidence recency | Verified | `parameter_catalog.md`, `parameter_synergies.md` |
| `STABILITY_STALE_THRESHOLD = 0.3` | Below this the run is too unstable to count as even stale; it is `EXPIRED` for bridge purposes. | Stability-to-freshness mapping for evidence recency | Verified | `parameter_catalog.md`, `parameter_synergies.md` |

## 6. KME and derived metrics

KME introduces **no extra tunable scalar constants** in the same sense as §§0–5. Its six primitive
measures and 35 derived ratios/products are structural measurements over bounded `[0,1]` inputs.
The key academic reason for this design is comparability: Hesperia wants cross-document structural
comparison without reopening the deterministic measurement pipeline.

| Item | Why it is shaped this way | Theory family | Confidence | Main support |
|---|---|---|---|---|
| Six primitives `LD, COH, NC, PR, PV, CI` | Small basis set that separates density, coherence, coverage, spread radius, spread volume, and concentration before any composite score is built. | Bounded graph-structural comparability metrics | Verified | `corners/kme.md`, `parameter_catalog.md` |
| 35 derived metrics | Pure algebra over the six primitives so every composite can be decomposed and audited. | Ratio/product metric engineering under bounded inputs | Verified | `corners/kme.md`, `parameter_synergies.md`, `SCIENCE.md` |
| `clamp01` / `safe_div` discipline | Keeps every derived metric numerically safe and publication-honest under sparse or degenerate cases. | Numerical robustness for bounded comparability measures | Verified | `corners/kme.md`, `NOVELTY_AND_POSITIONING.md` |

## 7. TRIZ relation weights and seed

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `conflict = 1.0` and `negation = 1.0` | These are treated as full-strength contradiction relations, so they carry the maximum contradiction signal by design. | Narrow deterministic slice of TRIZ contradiction analysis | Verified | `parameter_catalog.md`, `corners/triz_extension.md` |
| `opposition = 0.85` | Opposition is real tension, but slightly softer than direct conflict/negation. The discount preserves rank order instead of flattening all contradiction types. | Weighted contradiction semantics | Verified | `parameter_catalog.md` |
| `LOUVAIN_SEED = 42` | Pure reproducibility choice: Louvain clustering otherwise depends on tie-breaking and can drift run-to-run. | Seeded community detection for deterministic analytics | Verified | `parameter_catalog.md`, `SCIENCE.md`, `REPRODUCIBILITY_PACKAGE.md` |

## 8. Field Dynamics extension (`hesperia/extensions/dynamics/`)

This subsystem has the weakest documentation provenance because its cited canonical spec is missing.
Where possible, reasons below are drawn directly from the registry meanings/ranges; otherwise they
are explicit inferences from current code structure. None of these parameters currently affect the
live product surface.

### 8.1 Phase 1 Theta

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `lambda_a = 0.35` | Moderate area-state decay: enough persistence for temporal continuity, enough decay to avoid inertial lock-in. | Discrete-time damped state dynamics | Verified | `dynamics_parameter_registry.yaml`, `field_dynamics.md` |
| `gamma_f = 0.4` | Injection from the pipeline snapshot is slightly stronger than raw decay, meaning fresh measured structure can actively steer the area state. | Measurement-driven state injection | Verified | same |
| `gamma_q = 0.15` | Neighbor diffusion is present but notably weaker than direct injection, so area coupling does not wash out local evidence. | Icosahedral neighbor diffusion | Verified | same |
| `gamma_p = 0.08` | Contradiction pressure penalizes the area state, but less strongly than injection or diffusion. | Pressure-penalized state evolution | Verified | same |
| `mu_a = 0.4` | Contradiction state itself decays at a moderate rate, preventing permanent memory of tension spikes. | Damped contradiction dynamics | Verified | same |
| `delta_a = 0.12` | TRIZ-driven contradiction gain is noticeable but not dominant; contradiction can influence the state without becoming the only signal. | TRIZ-to-area contradiction coupling | Verified | same |
| `rho_a = 0.02` | Very small bleed/resolution term, consistent with its own "stub" status in the registry. | Weak regularization / bleed term | Verified | same |
| `lambda_c = 0.3` | Concept-mass decay is moderate, keeping concept mass as a short-memory contributor. | Damped concept-mass state | Verified | same |
| `alpha_in = 0.25` | Injection gain below `gamma_f`, so concept-mass injection supports rather than overrides area-state dynamics. | Controlled concept-mass injection | Verified | same |

### 8.2 Phase 2 Theta

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `lambda_f = 0.35` | Same moderate decay pattern as Phase 1, but now at family-grain dynamics. | Discrete-time damped family field | Verified | `dynamics_parameter_registry.yaml`, `field_dynamics.md` |
| `beta_x = 0.42` | Family-hit injection is one of the strongest terms, making current observed hits the main driver of family-state updates. | Hit-driven family-field injection | Verified | same |
| `beta_intra = 0.08` | Mild mean-reversion inside the area; enough to smooth without collapsing family distinctions. | Intra-area regularization | Verified | same |
| `beta_area = 0.10` | Area feedback informs families, but the family field is not simply re-imposed from above. | Cross-scale top-down coupling | Verified | same |
| `beta_pf = 0.06` | Family contradiction penalty is deliberately smaller than hit injection so tension moderates but does not dominate family evidence. | Contradiction-penalized family field | Verified | same |
| `mu_f = 0.4` | Family contradiction memory decays at the same moderate pace as area contradiction memory. | Damped contradiction dynamics | Verified | same |
| `delta_f = 0.1` | Area-level TRIZ signal affects family pressure, but less strongly than direct family-hit injection. | Cross-level TRIZ pressure transfer | Verified | same |
| `rho_f = 0.002` | Extremely small bleed term: regularization exists, but family identity is meant to stay sharp. | Very weak regularization | Verified | same |
| `area_hit_weight = 0.52` | Slightly favors hit-area evidence over aggregate area-state contribution in the blend to L6. | Cross-scale blend weighting | Verified | same |

### 8.3 Phase 3 Theta

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `hex_cap = 128` | Keeps the active subgraph sparse and computationally bounded, well below the full 288-family proxy ceiling. | Sparse active-subgraph truncation | Verified | `dynamics_parameter_registry.yaml`, `field_dynamics.md` |
| `lambda_h = 0.32` | Moderate hex-field decay, slightly less than the area/family decay terms. | Damped sparse-cell dynamics | Verified | same |
| `theta_c = 0.45` | Strongest Phase 3 coefficient because direct hex injection is the main point of this layer. | Sparse-cell injection gain | Verified | same |
| `theta_d = 0.18` | Neighbor diffusion is meaningful but clearly secondary to direct injection. | Local diffusion on active proxy cells | Verified | same |
| `theta_p = 0.06` | Pressure penalty is present but modest, mirroring Phase 2's moderation pattern. | Pressure-penalized sparse-cell dynamics | Verified | same |
| `mu_h = 0.38` | Contradiction decay is again moderate, close to the Phase 1/2 pattern. | Damped contradiction dynamics | Verified | same |
| `delta_h = 0.08` | Area TRIZ signal reaches the hex level softly rather than dominating it. | Cross-level contradiction coupling | Verified | same |
| `rho_h = 0.001` | Tiny bleed term: the hex field is meant to remain highly localized. | Minimal regularization | Verified | same |
| `hex_hit_blend = 0.48` | Keeps downstream injection nearly balanced between direct hits and hex-field state, with a slight bias away from the hex proxy. | Cross-level blend weighting | Verified | same |

### 8.4 Phase 4 Theta

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `gravity_epsilon = 0.055` | Small coupling term so cluster gravity nudges, rather than overrides, L6/L5 injection. | Weak cluster-gravity coupling | Verified | `dynamics_parameter_registry.yaml`, `field_dynamics.md` |
| `tau_front = 0.085` | Front-edge threshold tuned as a small but non-trivial delta, so only clear narrative edge changes register. | Edge-detection thresholding in state sequences | Verified | same |
| `ephemeral_cap = 96` | Limits the number of top families when Phase 3 is off, preserving bounded cluster work. | Bounded surrogate active-set selection | Verified | same |

### 8.5 Xi proxy, calibration index, semantic field, and bridge terms

| Parameter | Why this value/shape | Theory family | Confidence | Main support |
|---|---|---|---|---|
| `xi_scale = 0.14` | Keeps TRIZ/KME tension boost noticeable but far below a full replacement signal. | Scaled contradiction amplification | Verified | `dynamics_parameter_registry.yaml`, `field_dynamics.md` |
| `xi_kme_weight = 0.55` | Slightly favors the KME-full-graph contribution over the alternative term when Xi-KME blending is enabled. | Weighted contradiction-source blending | Verified | `parameter_catalog.md`, `field_dynamics.md` |
| Xi blend constants `0.35 / 0.65` | Give more weight to per-area tension than global tension, so local contradiction structure matters more than a single global scalar. | Multi-scale tension blending | Verified | `field_dynamics.md`, `xi_proxy.py` note in `parameter_catalog.md` |
| HCI weights `0.25 / 0.25 / 0.15 / 0.15 / 0.10 / 0.10` | Prioritize stability and source alignment over the three load penalties; the tuning score rewards faithful stable behavior before energetic elegance. | Weighted calibration objective design | Verified | `calibration.py`, `parameter_catalog.md` |
| `source_alignment_kappa = 1.0` | Standard saturating-benefit normalizer scale: a one-unit alignment improvement is the turnover point for diminishing returns. | Benefit normalization in bounded calibration scores | Verified | `calibration.py` |
| Semantic-field `alpha = 0.15` | Moderate diffusion-energy coefficient in the research-only equation set. | Variational/diffusion-style energy functional | Inferred | `parameter_catalog.md`, `field_dynamics.md` |
| Semantic-field `beta = 0.08` | Weaker resistance term than diffusion, implying resistance should shape but not dominate the field. | Resistance-regularized field energy | Inferred | same |
| Semantic-field `gamma = 0.12` | Contradiction coupling is material but below the primary diffusion term. | Contradiction-coupled field energy | Inferred | same |
| Semantic-field `delta = 0.25` | Source term has the strongest direct pull among the semantic-field coefficients, keeping the field tied to explicit source mass. | Source-driven field energy | Inferred | same |
| Semantic-field `mu = 0.01` | Very small decay/regularization constant, consistent with iterative convergence rather than aggressive damping. | Weak dissipative regularization | Inferred | same |
| Semantic-field `dt = 0.05` | Small step size for stable iterative updates. | Explicit time-stepping / numerical stability | Inferred | same |
| Semantic-field `epsilon = 0.0001` | Small numerical guard for safe divisions and convergence math. | Numerical-analysis safeguard | Verified | `parameter_catalog.md` |
| Semantic-field `tau = 0.02` | Small threshold term, likely for convergence/activation gating inside the research solver. | Thresholded convergence control | Inferred | `parameter_catalog.md` |
| `resistance_uniform = 1.0` | Neutral baseline resistance everywhere unless a non-uniform profile is supplied. | Uniform resistance prior | Inferred | `parameter_catalog.md` |
| `production_clip = true` | Hard clipping reflects a safety-first bounded-output policy even in research mode. | Bounded-state numerical safety | Inferred | `parameter_catalog.md` |
| `signed_source_experimental = false` | Conservative default: do not allow signed-source behavior unless explicitly exploring it. | Experimental-feature gating | Inferred | `parameter_catalog.md` |
| `dlcr_alpha = 0.22` | Lexical-concept-recovery blend weight is supportive rather than dominant; DLCR can enrich family injection without replacing the main field terms. | Auxiliary evidence blending | Verified | `parameter_catalog.md`, `field_dynamics.md` |

## How to use this file

- If you need the exact number, start with `parameter_catalog.md`.
- If you need the scientific lineage, jump from the row here to `references.md` or
  `docs/publication/SCIENCE.md`.
- If you need to defend a threshold/value in writing, cite both the parameter row here and the
  neighboring implementation doc it points to.

When a reason here is **inferred**, treat it as the current best reconstruction of the repo's own
logic, not as an operator-approved theorem. That distinction is part of the documentation quality
floor, not a weakness.
