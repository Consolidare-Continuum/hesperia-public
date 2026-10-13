# CHIRON-126 address map (agentic)

**Brain twin (same map):** `/data/altitudine/CC_.com/operational/assignments/chiron-inventory/CHIRON-126-ACCOMMODATED-OPERATIONAL-LIST-2026-08-21.md`

**Date:** 2026-08-21  
**Purpose (agentic):** numbered 1–126 with **define** / **calibrate** / **live consumer** / **tweakable** addresses. Use this before any `PC-*` recipe or numeric retune.  
**Repo root (dev):** `/data/workspaces/hesperia` → push `igareosh/hesperia`  
**Hesperia mirror:** `docs/recipes/chiron_tweaks/CHIRON-126-ADDRESS-MAP-2026-08-21.md`  
**Pack SoT:** `docs/recipes/chiron_tweaks/CANDIDATE-REGISTRY.md` · snapshot `STATUS-SNAPSHOT-2026-08-21.md`  
**Catalog / ranges:** `docs/foundations/parameter_catalog.md` · `assets/calibration/dynamics_parameter_registry.yaml` · synergies `docs/foundations/parameter_synergies.md`

**Counts:** 92 operational (default-live) + 34 accommodated (`HESPERIA_TFP_FIELD_DYNAMICS`, default **off**) = **126**.

### Column legend

| Column | Meaning |
|--------|---------|
| **Define** | Source of default / formula (edit here = change meaning) |
| **Calibrate** | Preferred knob (YAML / env / dataclass field agents should touch) |
| **Live** | What actually reads the value on a real path today |
| **Tweak** | `yaml` / `env` / `dataclass` / `module-const` / `formula` / `gated-envelope` / `no-op` / `offline-only` |

**Do not** retune packs that must move together without `parameter_synergies.md` (B2, B5, B3/B4). Tier C: gate on + Class B consumer only — not sealed-core merge.

**Gate (Tier C):** env `HESPERIA_TFP_FIELD_DYNAMICS=1` · binder `hesperia/modules/tfp/field_dynamics_consumer.py` · `build_tfp_fd_param_envelope()`.

---

## Tier A — 60 (closed/calibrated, operational)

### KME primitives (6) — items 1–6

Computed metrics (not YAML knobs). Formula SoT + live rollup.

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 1 | `LD` | `core/domain/primitive_metrics.py` → `compute_ld` | grain / graph inputs (not a scalar knob) | `hesperia/engine/kme/clinical_bridge.py` · `core/domain/pipeline.py` · fingerprint | formula |
| 2 | `COH` | `primitive_metrics.py` → `compute_coh` | same | same | formula |
| 3 | `NC` | `primitive_metrics.py` (NodeCoverage) | same | same | formula |
| 4 | `PR` | `primitive_metrics.py` (PropagationRadius) | same | same | formula |
| 5 | `PV` | `primitive_metrics.py` (PropagationVolume) | same | same | formula |
| 6 | `CI` | `primitive_metrics.py` (ConcentrationIndex) | same | same | formula |

Docs: `docs/foundations/corners/kme.md` · wiki layer `hesperia_wiki` / `docs/brain-export/colombo/hesperia-wiki/pages/KME-Primitives-and-Derived-Metrics.md`. Evidence: CHI-002 (`4fe53ca`).

### KME derived metrics (35) — items 7–41

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 7–41 | `KDI`…`KVI` (see list below) | `core/domain/derived_metrics.py` → `compute_derived_metrics` | change formula only (architecture) | `clinical_bridge` / fingerprint / `to_derived_vector` | formula |

Ordered symbols (7→41): `KDI`, `CSI`, `SPI`, `TDS`, `SSS`, `KCI`, `CCI`, `SPS`, `DCI`, `CSI2`, `KEF`, `ASS`, `CDR`, `KCR`, `TCI`, `PEI`, `KE`, `SCS`, `CRI`, `KNS`, `CII`, `TEP`, `KSI`, `CDD`, `SSR`, `TER`, `CPC`, `KBS`, `TRI`, `IDE`, `KPS`, `TBI`, `KDI2`, `CDI`, `KVI`.

Model types: `core/domain/models.py` (`PrimitiveMetrics`, `DerivedMetrics`).

### Phase1Theta (9, CHI-003) — items 42–50

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 42 | `lambda_a` | `hesperia/extensions/dynamics/state.py` `Phase1Theta` | `assets/calibration/dynamics_parameter_registry.yaml` `parameters.lambda_a` | `hesperia/extensions/dynamics/phase1.py` (FD path) | dataclass + registry |
| 43 | `gamma_f` | same | registry `gamma_f` | phase1 | dataclass + registry |
| 44 | `gamma_q` | same | registry | phase1 | dataclass + registry |
| 45 | `gamma_p` | same | registry | phase1 | dataclass + registry |
| 46 | `mu_a` | same | registry | phase1 | dataclass + registry |
| 47 | `delta_a` | same | registry | phase1 | dataclass + registry |
| 48 | `rho_a` | same | registry | phase1 | dataclass + registry |
| 49 | `lambda_c` | same | registry | phase1 | dataclass + registry |
| 50 | `alpha_in` | same | registry | phase1 | dataclass + registry |

**Note:** CHI-003 / Colombo verdict — dual-signal `areas_working`; **do not** adopt FD Phase1 defaults as TFP theme model. Defaults remain calibratable for Field Dynamics research / gated paths. Evidence: `02623ad`.

### Phase2Theta (9, CHI-003) — items 51–59

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 51 | `lambda_f` | `state.py` `Phase2Theta` | `dynamics_parameter_registry.yaml` | `hesperia/extensions/dynamics/phase2.py` | dataclass + registry |
| 52 | `beta_x` | same | registry | phase2 | dataclass + registry |
| 53 | `beta_intra` | same | registry | phase2 | dataclass + registry |
| 54 | `beta_area` | same | registry | phase2 | dataclass + registry |
| 55 | `beta_pf` | same | registry | phase2 | dataclass + registry |
| 56 | `mu_f` | same | registry | phase2 | dataclass + registry |
| 57 | `delta_f` | same | registry | phase2 | dataclass + registry |
| 58 | `rho_f` | same | registry | phase2 | dataclass + registry |
| 59 | `area_hit_weight` | same | registry (`w_hit` symbol) | phase2 | dataclass + registry |

### CHI-004 (1) — item 60

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 60 | `dlcr_alpha` | `hesperia/extensions/dynamics/e2e_bridge.py` (literal `alpha = 0.22`) | same site + env gate `HESPERIA_FIELD_DYNAMICS_DLCR` | DLCR blend into family injection on FD e2e | module-const + env gate |

Evidence: CHI-004 (`a75bc5b`). Lexical pipeline: `core/engine/lexical_concept/pipeline.py`.

---

## Tier B — 32 operational — items 61–92

### B1 — Activation floor (2)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 61 | `activation_threshold` | `assets/specs/canon/activation_calibration.yaml` | YAML → `hesperia/engine/calibration/activation_calibration.py` getters | `hesperia/engine/kme/clinical_bridge.py` (`get_activation_threshold`) | yaml |
| 62 | `area_active_threshold` | same YAML | same getters | clinical_bridge area gate | yaml |

Evidence: CHI-012 → CHI-B16-02 (`b29aab4`). Tests: `tests/engine/kme/test_activation_calibration_sot.py`.

### B2 — Propagation weights (6)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 63 | `center_to_inner` | `assets/specs/canon/propagation_weights.yaml` `zone_weights` | YAML | `sphere/topology/activation_propagation.py` via `propagation_weights_loader.py` | yaml |
| 64 | `inner_to_middle` / `middle_to_inner` | same | YAML | same | yaml |
| 65 | `middle_to_outer` / `outer_to_middle` | same | YAML | same | yaml |
| 66 | `bridge_weight` | same (`bridge_weight`) | YAML | same | yaml |
| 67 | `decay_factor` | same | YAML | **no live multi-hop consumer** (reserved) | no-op |
| 68 | `concept_to_family_multiplier` | same | YAML | **no-op by design** | no-op |

Evidence: CHI-007. Synergy: `bridge_weight` × shadow — see `parameter_synergies.md` §2 (lanes may not co-occur).

### B3 — Core Math fusion/traversal (6)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 69 | `alpha` | `core/math/core_math.py` `DEFAULT_CONFIG` | `DEFAULT_CONFIG` (or inject config dict) | `fusion` → `runtime/pipeline/analyze.py` + orchestrators | dataclass/module-const |
| 70 | `eta` | same | same | `centroid_indices` | module-const |
| 71 | `K_max` | same | same | `centroid_indices` | module-const |
| 72 | `lambda` | same | same | `base_step` | module-const |
| 73 | `decay` | same | same | `base_step` | module-const |
| 74 | `E_cap` | same | same | fusion / base_step clamp | module-const |

Evidence: CHI-009. **Not** the same `alpha` as C5 Semantic Field.

### B4 — Core Math governance penalties (8)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 75 | `k_amb` | `core_math.py` `DEFAULT_CONFIG` | same | `ambiguity_penalty` → `metric_governance` | module-const |
| 76 | `delta_gap` | same | same | ambiguity `degraded` | module-const |
| 77 | `tau_core` | same | same | thin-core `degraded` | module-const |
| 78 | `k_thin` | same | same | `thin_core_penalty` | module-const |
| 79 | `k_disp` | same | same | `dispersion_penalty` | module-const |
| 80 | `k_guard` | same | same | `guard_penalty` | module-const |
| 81 | `k_shadow` | same | same | `P_shadow_value` | module-const |
| 82 | `max_shadow_hops` | same | same | `P_shadow` / obstacle | module-const |

Evidence: CHI-010. Tune as a set.

### B5 — Obstacle-score weights (3)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 83 | `w_decay` | `DEFAULT_CONFIG` | same; must sum 1.0 with siblings | `metric_obstacle_score` | module-const (set) |
| 84 | `w_guard_obs` | same | same | same | module-const (set) |
| 85 | `w_shadow_obs` | same | same | same | module-const (set) |

Evidence: CHI-008. `validate_config()` sum check exists; pytest CI not the enforcer.

### B7 — FGR/Freshness calibration (4)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 86 | `DOMINANT_SHARE_HIGH` | **Live:** `sphere/interpretation/state_classifier.py` (0.35). **Doc twin:** `sphere/fpf_bridge/constants.py` | prefer live site for Layer-10 | sealed Layer-10 state classifier | module-const (split SoT) |
| 87 | `ENTROPY_DROP_SIGNIFICANT` | same split (0.15) | same | state_classifier | module-const (split SoT) |
| 88 | `STABILITY_CURRENT_THRESHOLD` | `sphere/fpf_bridge/constants.py` (0.7) | fpf_bridge constants | `evidence_mapper.py` (internal surface) | module-const (internal) |
| 89 | `STABILITY_STALE_THRESHOLD` | same (0.3) | same | evidence_mapper | module-const (internal) |

Evidence: CHI-011. Do not “fix” by editing only the unused twin.

### B8 — TRIZ relation weights (3)

| # | Symbol | Define | Calibrate | Live | Tweak |
|---|--------|--------|-----------|------|-------|
| 90 | `conflict` / `negation` weight | `hesperia/extensions/triz/contradiction_engine.py` `_REL_WEIGHT` (1.0 / 1.0) | `_REL_WEIGHT` dict | contradiction signal build | module-const |
| 91 | `opposition` weight | same (0.85) | same | same | module-const |
| 92 | `LOUVAIN_SEED` | `hesperia/extensions/triz/novelty_engine.py` `LOUVAIN_SEED = 42` | module const | Louvain communities | module-const |

Evidence: CHI-005.

---

## Tier C — 34 accommodated — items 93–126

**Gate:** `HESPERIA_TFP_FIELD_DYNAMICS` · **Envelope:** `hesperia/modules/tfp/field_dynamics_consumer.py` · Offline FD: `e2e_bridge.run_field_dynamics_e2e_artifact` / `runtime/pipeline/run_e2e_all.py`. Evidence: CHI-013 → CHI-015 (`1215569`).

### C1 — Phase3Theta / hex grain (9)

| # | Symbol | Define | Calibrate | Live (gated) | Tweak |
|---|--------|--------|-----------|--------------|-------|
| 93 | `hex_cap` | `state.py` `Phase3Theta` | dataclass + env `HESPERIA_FIELD_DYNAMICS_HEX_CAP` (`phase3.field_dynamics_hex_cap_from_env`) | envelope `c1_phase3` + phase3 | dataclass + env |
| 94 | `lambda_h` | same | registry + dataclass | envelope / phase3 | dataclass + registry |
| 95 | `theta_c` | same | same | same | dataclass + registry |
| 96 | `theta_d` | same | same | same | dataclass + registry |
| 97 | `theta_p` | same | same | same | dataclass + registry |
| 98 | `mu_h` | same | same | same | dataclass + registry |
| 99 | `delta_h` | same | same | same | dataclass + registry |
| 100 | `rho_h` | same | same | same | dataclass + registry |
| 101 | `hex_hit_blend` | same | same | same | dataclass + registry |

### C2 — Phase4Theta / cluster gravity (3)

| # | Symbol | Define | Calibrate | Live (gated) | Tweak |
|---|--------|--------|-----------|--------------|-------|
| 102 | `gravity_epsilon` | `state.py` `Phase4Theta` | registry + dataclass | envelope `c2_phase4` · e2e_bridge gravity | dataclass + registry |
| 103 | `tau_front` | same | same | same | dataclass + registry |
| 104 | `ephemeral_cap` | same | same | same | dataclass + registry |

### C3 — Ξ tension proxy (4)

| # | Symbol | Define | Calibrate | Live (gated) | Tweak |
|---|--------|--------|-----------|--------------|-------|
| 105 | `xi_scale` | `xi_proxy._xi_scale_from_env` default **0.14** | env `HESPERIA_FIELD_DYNAMICS_XI_SCALE` | `xi_proxy.apply_xi_to_contradiction_signal` · envelope `c3_xi` | env |
| 106 | `xi_kme_weight` | `xi_proxy._xi_kme_weight_from_env` default **0.55** | env `HESPERIA_FIELD_DYNAMICS_XI_KME_WEIGHT` (+ `HESPERIA_FIELD_DYNAMICS_XI_KME`) | same | env |
| 107 | blend `0.35` | `xi_proxy.py` (`boost = xs * (0.35 * g + …)`) **and** `field_dynamics_consumer.XI_BLEND_G` | module const (keep both in sync) | apply path + envelope honesty | module-const |
| 108 | blend `0.65` | same (`0.65 * per`) · `XI_BLEND_PER` | same | same | module-const |

### C4 — HSPR Calibration Index (7, offline-only)

Live weight SoT is **`HSPRWeights`** in `hesperia/engine/calibration/hspr_field.py` (defaults: `w_sigma/w_Q/w_E=0.20`, `w_K/w_R=0.15`, `w_D=0.10`). Catalog prose `0.25/0.25/…` is **stale vs code** — agents trust the dataclass. `source_alignment_kappa` is envelope-bound (`1.0`), not a field on `HSPRWeights`.

| # | Symbol (inventory label) | Define / code key | Calibrate | Live (gated) | Tweak |
|---|--------------------------|-------------------|-----------|--------------|-------|
| 109 | stability weight | `HSPRWeights.w_sigma` | dataclass | envelope `c4_hspr_offline` · `run_tfp_hspr_offline_calib_job` | offline-only |
| 110 | source-alignment weight | `HSPRWeights.w_Q` | dataclass | same | offline-only |
| 111 | energy weight | `HSPRWeights.w_E` | dataclass | same | offline-only |
| 112 | contradiction weight | `HSPRWeights.w_K` | dataclass | same | offline-only |
| 113 | diffusion weight | `HSPRWeights.w_R` | dataclass | same | offline-only |
| 114 | resistance weight | `HSPRWeights.w_D` | dataclass | same | offline-only |
| 115 | `source_alignment_kappa` | `field_dynamics_consumer` bind `1.0` in `c4` | envelope / offline job | offline calib JSON only | offline-only |

**Not** product runtime score (Ethan refusal). Distinct from `core/engine/hspr_index.py` (system HSPR).

### C5 — Semantic Field v1 (11)

| # | Symbol | Define | Calibrate | Live (gated) | Tweak |
|---|--------|--------|-----------|--------------|-------|
| 116 | `alpha` | `hesperia/extensions/dynamics/semantic_field_v1.py` `SemanticFieldParamsV1` (0.15) | dataclass + `assets/calibration/profiles_v1.json` via `load_semantic_field_params_v1` | envelope `c5_semantic_field` · equations path | dataclass + profile JSON |
| 117 | `beta` | same (0.08) | same | same | dataclass + profile JSON |
| 118 | `gamma` | same (0.12) | same | same | dataclass + profile JSON |
| 119 | `delta` | same (0.25) | same | same | dataclass + profile JSON |
| 120 | `mu` | same (0.01) | same | same | dataclass + profile JSON |
| 121 | `dt` | same (0.05) | same | same | dataclass + profile JSON |
| 122 | `epsilon` | same (1e-4) | same | same | dataclass + profile JSON |
| 123 | `tau` | same (0.02) | same | same | dataclass + profile JSON |
| 124 | `resistance_uniform` | same (1.0) | same | same | dataclass + profile JSON |
| 125 | `production_clip` | same (`True`) | same | maps to equations `clip_mode` | dataclass + profile JSON |
| 126 | `signed_source_experimental` | same (`False`) | same | envelope + SF v1 | dataclass + profile JSON |

Equations type: `hesperia/extensions/dynamics/equations.py` `SemanticFieldParams`. Env gate family: `HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1` (research) vs TFP Class B gate above.

---

## Quick agent routes

| Intent | Start here |
|--------|------------|
| “What’s operational vs gated?” | This file header + `STATUS-SNAPSHOT-2026-08-21.md` |
| “Change a Tier B YAML knob” | `assets/specs/canon/*.yaml` → loader → Live column |
| “Change Core Math” | `core/math/core_math.py` `DEFAULT_CONFIG` (B3–B5 as sets) |
| “Change Phase-N theta” | `state.py` + `dynamics_parameter_registry.yaml` |
| “Surface Tier C honestly” | `HESPERIA_TFP_FIELD_DYNAMICS=1` + `build_tfp_fd_param_envelope()` |
| “KME formula” | `primitive_metrics.py` / `derived_metrics.py` (not catalog retune) |
| “Wiki symbol live/dead” | `query_knowledge(layer=hesperia_wiki)` or `colombo_research/hesperia/wiki/CLAUDE.md` |

---

## Out of this 126 (do not confuse)

| Bucket | Count | Where |
|--------|-------|--------|
| Retired B6 diagnostics | 13 | was `diagnostic_rules.yaml` / `sphere/diagnostics/` — use Layer-9 `logic_rules.yaml` |
| Retired C6 hex_field_reference | 5 | removed from `profiles_v1.json` (CHI-014-02) |
| Sealed geometry D | 4 | `AREAS` / 288 / hexes / sides — never Chiron calibrate |

---

SIGNED: Developer (Gena) | address-backwire CHIRON-126 | 2026-08-21 | define/calibrate/live/tweak map for agentic use
