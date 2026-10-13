# Requirements specification (ISO/IEC/IEEE 29148 form)

Requirements below are extracted from what the system's own guards and canon already enforce
(`specs/canon/*.yaml`, `core/math/core_math.py`, `VERSION.yaml`) — not invented for this document.
Each requirement cites the exact invariant, constant, or code path that satisfies it, verified
directly against source. This is a **traceability document**: its purpose is to make each
requirement checkable against a named artifact, per `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`'s
verification discipline.

## 1. Functional requirements

| ID | Requirement | Traced to |
|---|---|---|
| FR-1 | The system MUST convert raw text into a bounded, deterministic structural read before any LLM involvement. | `sphere/pipeline/pipeline_runner.py` (L1–L10 canonical entrypoint); `docs/iso/ARCHITECTURE_DESCRIPTION.md` §3 |
| FR-2 | The system MUST produce exactly one canonical structural read per input, not one per calling context (CLI, API, tests, calibration). | `layer_registry.py`, `contract_validation.py`, `isolation_validation.py` (`corners/sphere_pipeline.md`) |
| FR-3 | The system MUST NOT allow an LLM to narrate outside a fixed menu of legal next states. | `sphere/fpf_bridge/` (Layer 11), 5 structural states verified in `sphere/fpf_bridge/constants.py` (`output_catalog.md` §12) |
| FR-4 | The system MUST re-measure an LLM's own output against the structural read that produced its prompt and issue a verdict. | `sphere/router/audit.py`, `runtime/services/product_interpret_service.py`'s `mode="llm"` path |
| FR-5 | The system MUST support at least three governance strictness modes for how a verdict affects the served response. | `HESPERIA_ROUTER_MODE` ∈ `{observe, warn, strict}`, `product_interpret_service.py::_router_mode()` |
| FR-6 | The system MUST expose two independently-versioned response contracts (legacy and current-governed) without silently merging their shapes. | `docs/ENGINE-ANALYZE-CONTRACT.md` (`/analyze`) vs. `runtime/services/product_interpret_service.py` (`/product/interpret`) — see `output_catalog.md` §0 |
| FR-7 | The system MUST NOT allow raw wording to activate families/areas directly unless routed through resolved concept evidence or an explicitly marked fallback path. | Dict A (surface span matching, no family/area authority) → Dict B (disambiguated resolution) freeze discipline (`corners/lexicon_resolver.md`); the founding memo's load-bearing sentence, restated in `NOVELTY_AND_POSITIONING.md` |
| FR-8 | The system MUST cap, not merely measure, any entropy increase diffusion introduces relative to the pre-propagation read. | `max_entropy_increase = 0.1` (`sphere/shadow/entropy_correction.py`, verified against source) |
| FR-9 | The system MUST consolidate per-layer outputs into one versioned fingerprint object before Theta's "required artifacts present" check runs, rather than requiring Theta to enumerate every layer's sub-output dict by hand. | USF (`specs/canon/usf_schema.json`), `corners/interpretation_usf.md`, `corners/schemas_contracts.md` |

## 2. Non-functional requirements

### 2.1 Determinism

| ID | Requirement | Traced to |
|---|---|---|
| NFR-D1 | Same input + same pinned calibration/corpus state MUST produce byte-identical output. | `VERSION.yaml`'s `active_calibration_dict_pack` pin (`corners/calibration.md`); `core/guards/determinism.py` |
| NFR-D2 | Energy/mass conservation across a propagation step MUST hold within a fixed numerical tolerance. | `energy_conservation_tolerance = 1e-6` (`core/math/core_math.py`'s `DEFAULT_CONFIG`, `check_conservation_pre_decay`) — `parameter_catalog.md` §3 |
| NFR-D3 | Layer execution order MUST be a checkable, singular fact, not an emergent property of caller code. | `GAMMA_001 layer_order_valid` (`specs/canon/gamma_invariants.yaml`, verified) |
| NFR-D4 | The number of registered layers/rules MUST match the number actually triggered in a run. | `GAMMA_007 registry_count_matches_triggered_rules` (`specs/canon/gamma_invariants.yaml`, verified) |

### 2.2 Reproducibility

| ID | Requirement | Traced to |
|---|---|---|
| NFR-R1 | Graph-clustering steps that would otherwise be order-dependent MUST be seeded for run-to-run reproducibility. | `LOUVAIN_SEED = 42` (`hesperia/extensions/triz/`, `parameter_catalog.md` §7) |
| NFR-R2 | A release's exact calibration data MUST be mechanically checkable against what the version claims to run. | `validate_version_consistency` (`release/vX.Y.Z/RELEASE_SCOPE.md`, `corners/calibration.md`) |
| NFR-R3 | The per-layer canonical specs a release's math traces to MUST be locatable in the repository, not only in code comments. | `docs/specs/history/34_SPEC`–`42_SPEC` (restored; `docs/foundations/provenance.md`) |

### 2.3 Structural shape invariants

| ID | Requirement | Traced to |
|---|---|---|
| NFR-S1 | Every area-level output MUST be a fixed 12-slot structure. | `SIGMA_001` (`area_vector` length 12) — `specs/canon/sigma_invariants.yaml`, verified |
| NFR-S2 | Every family-level output MUST be a fixed 288-slot structure. | `SIGMA_002` (`family_counts` length 288) — `specs/canon/sigma_invariants.yaml`, verified |

### 2.4 Governance

| ID | Requirement | Traced to |
|---|---|---|
| NFR-G1 | An interpretation that does not derive from the canonical L1–L10 chain MUST be flaggable as non-canonical, not silently accepted. | `THETA_004 flag_non_canonical_interpretation` (`specs/canon/theta_governance_rules.yaml`, verified) |
| NFR-G2 | A release MUST NOT ship proprietary calibration-dictionary or corpus payloads even when shipping the engine logic. | `release/v0.6.0/RELEASE_SCOPE.md`: "Do not ship calibration dict payloads. Do not ship corpus payloads." (`corners/release_governance.md`) |
| NFR-G3 | A new analytical/evidence capability added to the LLM boundary (Layer 11 and its consumers) MUST default to disabled and change no existing behavior until explicitly enabled via a dedicated environment flag. | `HESPERIA_FPF_EVIDENCE_EXPANSION`/`HESPERIA_FPF_CONTRADICTION_GATE`/`HESPERIA_FPF_KME_EVIDENCE`/`HESPERIA_MCP_BRIDGE_ENABLED`/`HESPERIA_MCP_BRIDGE_ACT_ENABLED` (`sphere/fpf_bridge/bridge.py`, `runtime/agentic_bridge/flags.py`) — verified by `tests/test_fpf_bridge.py::TestContradictionEvidenceExpansion::test_flags_off_by_default_no_behavior_change` and sibling tests, all passing with flags unset |

### 2.5 Analytical-layer isolation

| ID | Requirement | Traced to |
|---|---|---|
| NFR-I1 | Layer 11 (`sphere/fpf_bridge/`) and any consumer built on top of it MUST NOT mutate the sphere pipeline result it reads. | `tests/test_fpf_bridge.py::TestBridge::test_read_only` — asserts the input `result` dict is byte-identical (via `json.dumps` comparison) before and after `bridge_pipeline_result()` runs. Same discipline TRIZ already states against KME's active graph (`corners/triz_extension.md`: "No mutation of ontology files, dict A/B, topology adjacency" — cited here as prior art, not independently re-verified by this pass) |

## 3. What is explicitly out of scope for this requirements set

- **Performance/latency requirements** (throughput, response-time SLAs) are not currently
  documented anywhere in `docs/foundations/` as enforced, measured invariants — do not invent
  numbers here. If/when such requirements exist as enforced checks, add them as NFR-P* rows with
  the same citation discipline used above.
- **`hesperia/extensions/dynamics/`'s requirements** are intentionally absent from this document —
  the subsystem has no wiring into either product surface (FR-6), so no functional requirement
  here can currently reference it without overclaiming (`corners/field_dynamics.md`).

## Maintenance note

This document is registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. Any new guard
invariant, canon YAML rule, or `VERSION.yaml` field that changes the truth of a row above must
update that row in the same commit, per the traceability matrix's LTS discipline.

## Navigation

← [`docs/README.md`](../README.md) (start here) · [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`ARCHITECTURE_DESCRIPTION.md`](ARCHITECTURE_DESCRIPTION.md) (components these requirements trace to) · [`QUALITY_MODEL.md`](QUALITY_MODEL.md) (quality characteristics these requirements support) · [`../foundations/parameter_catalog.md`](../foundations/parameter_catalog.md) §3 (Core Math Contract constants underlying NFR-D2)
