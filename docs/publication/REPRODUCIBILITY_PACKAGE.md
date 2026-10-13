# Reproducibility package

Everything a reader needs to reproduce a specific numeric claim from `docs/publication/METHODS.md`
or `docs/foundations/`. All values below were read directly from `VERSION.yaml` and
`parameter_catalog.md` at commit `63a2295b` — treat any earlier-circulated figure that disagrees
with this document as stale, not this document as wrong.

In productization language, this is part of what lets Hesperia speak about an **audit trace** with
technical seriousness: version pins, deterministic seeds, and numeric tolerances are what make a
claimed validation artifact reproducible instead of merely presentable.

## 1. System version pins (`VERSION.yaml`)

| Field | Value |
|---|---|
| `system_version` | `0.6.5` |
| `release_stage` | `v7_router_fusion` |
| `components.core_engine` | `0.6.5` |
| `components.dynamics` | `0.6.3` |
| `components.triz` | `0.6.3` |
| `components.clinical` | `0.6.3-modular` |
| `components.calibration` | `0.6.5` |
| `components.router` | `v7-router-0.1` |
| `schema.public_output` | `v1` |
| `pipelines.e2e` | `e2e_v2` |
| `calibration.profile_bundle` | `v1` |
| `calibration.active_profile` | `default_v1` |
| `defaults.active_calibration_dict_pack` | `archive_063_minimal` |
| `tfp_module_v1.pinned_calibration_dict_pack` | `archive_063_minimal` |

**Cross-check:** `defaults.active_calibration_dict_pack` and
`tfp_module_v1.pinned_calibration_dict_pack` match (`archive_063_minimal`), confirming
`validate_version_consistency`'s enforced invariant holds as of this commit
(`docs/iso/LIFECYCLE_PROCESS.md` §3).

**Live discrepancy note:** `docs/foundations/corners/calibration.md` illustrates this pin
mechanism with the example value `"v0_6_0_clr_v052_2"` — that was accurate at some prior commit but
no longer matches the current `archive_063_minimal` pin verified above. This is not a contradiction
in the reproducibility claim (the *mechanism* — a single pinned name checked for consistency — is
what's being verified, not that specific string) but is flagged here as exactly the kind of
drift the seal-checklist addendum in `docs/iso/LIFECYCLE_PROCESS.md` (Addendum) exists to catch.
Do not silently propagate the older example value in future documents; cite this file's live value
instead.

## 2. Deterministic seeds

| Constant | Value | Purpose | Source |
|---|---|---|---|
| `LOUVAIN_SEED` | `42` | Makes TRIZ innovation-cluster membership reproducible run-to-run | `parameter_catalog.md` §7, verified |

## 3. Numerical tolerances

| Constant | Value | Purpose | Source |
|---|---|---|---|
| `energy_conservation_tolerance` | `1e-6` | Strictness of the pre-decay conservation-of-energy check (`check_conservation_pre_decay`) | `core/math/core_math.py` `DEFAULT_CONFIG`, `parameter_catalog.md` §3 |
| `eps` (Layer 1–9 division-by-zero guard) | `1e-9` (L1–L4), `1e-12` (L3 cosine similarity, L6, L7 `EPS_INT`) | Prevents division-by-zero without biasing results; exact value varies by layer per the recovered specs | `34_SPEC`–`40_SPEC`, `docs/specs/history/` |

## 4. Core Math Contract constants (full set)

The complete, source-verified list of `core/math/core_math.py`'s `DEFAULT_CONFIG` (`alpha=0.65`,
`eta=0.02`, `K_max=5`, `lambda=0.55`, `decay=0.04`, `E_cap=1.0`, `k_amb=0.35`, `delta_gap=0.08`,
`tau_core=0.25`, `k_thin=0.30`, `k_disp=0.25`, `k_guard=0.30`, `k_shadow=0.40`,
`max_shadow_hops=2`, `w_decay/w_guard_obs/w_shadow_obs = 0.50/0.30/0.20`) is not repeated here to
avoid a second copy drifting from the first — the authoritative table is
`docs/foundations/parameter_catalog.md` §3. If the publication needs the *reason* or theory lineage
for a value instead of just the value itself, cite
`docs/foundations/parameter_rationale_and_theory.md` alongside it.

## 5. Restored canonical specs (for reproducing the layer-level math independently of this code)

`docs/specs/history/34_SPEC__V0_4_Layer1_Instrumentation_25_Variables_v1_0.txt` through
`42_SPEC__V0_4_Layer9_Human_Reference_Brand_Treatment_25_Variables_v1_0.txt` (plus
`34_SPEC_N1__L1_Normative_Structure_Profile_Extension_v0_4.txt`) — each independently implementable
from the spec text alone, per `docs/foundations/provenance.md`'s recovery-and-verification note.

## 6. What is not yet reproducible from this package

- Any performance/latency claim (no benchmark exists — `docs/iso/QUALITY_MODEL.md`).
- `hesperia/extensions/dynamics/`'s own parameter set (`parameter_catalog.md` §8) is fully
  catalogued but its canonical spec (`ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md`) remains unrecoverable
  from every source checked — a reader can reproduce the *code's* behavior from
  `hesperia/extensions/dynamics/` directly, but not cross-check it against an independent spec text
  the way §5's specs allow for L1–L9.

## Maintenance note

Registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. Re-read `VERSION.yaml` directly (not
from memory of a prior read) before citing any value in §1 in a new document — this file's own
discovery of the `corners/calibration.md` drift is the demonstration of why.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`METHODS.md`](METHODS.md) (what these constants parameterize) · [`VALIDATION_EVIDENCE.md`](VALIDATION_EVIDENCE.md) (what's proven using these pins) · [`../foundations/parameter_catalog.md`](../foundations/parameter_catalog.md) (the full constant table §4 defers to) · [`../foundations/corners/calibration.md`](../foundations/corners/calibration.md) (the drift this document caught and fixed there)
