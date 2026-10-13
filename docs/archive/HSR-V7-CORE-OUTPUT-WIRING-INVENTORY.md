# HSR-V7 Core Output Wiring Inventory

## Scope

Inventory of live core output parameter families after core fusion and output wiring convergence.

## Parameter Inventory

### 1. domain_graph

- Parameter: `domain_graph`
- Canonical name: `domain_graph`
- Produced by: loaders/bridge helpers such as `load_domain_graph_from_dict_b`, `synthetic_domain_graph_for_topology`
- Canonical module: `core.domain.models`, loaders in `core.domain` and `hesperia.engine.kme`
- Type: `DomainGraph`
- Range / allowed values: graph with node/edge collections
- Optional or required: required
- Current downstream consumers: `build_active_graph`, pipeline runners, compatibility bridge
- Serialized in: not serialized directly in canonical report JSON
- Test coverage: indirect
- Status: IMPLEMENTED-NOT-DOCUMENTED
- Action: keep internal; do not expose as report JSON field

### 2. active_graph

- Parameter: `active_graph`
- Canonical name: `active_graph`
- Produced by: `core.domain.active_graph.build_active_graph`, `build_clinical_active_graph`
- Canonical module: `core.domain.active_graph`
- Type: `ActiveGraph`
- Range / allowed values: bounded weights, concept graph only
- Optional or required: required intermediate
- Current downstream consumers: primitive metrics, TRIZ bridge/topology helpers
- Serialized in: not serialized directly in canonical report JSON
- Test coverage: `tests/domain/test_kme_triz_integration.py`
- Status: CANONICAL-WIRED
- Action: retain as internal computation artifact

### 3. primitive_metrics

- Parameter: `primitive_metrics`
- Canonical name: `primitives` in report JSON, `primitiveMap` in fingerprint JSON
- Produced by: `compute_primitives`
- Canonical module: `core.domain.primitive_metrics`
- Type: `dict[str, float]`
- Range / allowed values: six normalized floats in `[0, 1]`
- Optional or required: required
- Current downstream consumers: derived metrics, fingerprint builder, runtime report writers
- Serialized in: `metric_report_to_dict`, `DomainFingerprint.to_dict`
- Test coverage: `tests/domain/test_e2e_pipeline.py`, `tests/test_core_output_wiring.py`
- Status: CANONICAL-WIRED
- Action: keep fingerprint map as single source of truth after fingerprint build

### 4. derived_metrics

- Parameter: `derived_metrics`
- Canonical name: `derived` in report JSON, `derivedMap` in fingerprint JSON
- Produced by: `compute_derived_metrics`
- Canonical module: `core.domain.derived_metrics`
- Type: `dict[str, float]`
- Range / allowed values: 35 normalized floats in `[0, 1]`
- Optional or required: required
- Current downstream consumers: fingerprint builder, runtime report writers, marketable subsets
- Serialized in: `metric_report_to_dict`, `DomainFingerprint.to_dict`
- Test coverage: `tests/domain/test_e2e_pipeline.py`, `tests/test_core_output_wiring.py`
- Status: CANONICAL-WIRED
- Action: keep fingerprint map as single source of truth after fingerprint build

### 5. fingerprint

- Parameter: `fingerprint`
- Canonical name: `fingerprint`
- Produced by: `build_fingerprint`
- Canonical module: `core.domain.fingerprint`
- Type: `DomainFingerprint`
- Range / allowed values: ordered 41-value bounded vector plus metadata/hash
- Optional or required: required
- Current downstream consumers: report JSON, profile builder, runtime pipelines
- Serialized in: `DomainFingerprint.to_dict`
- Test coverage: `tests/domain/test_fingerprint.py`, `tests/domain/test_e2e_pipeline.py`, `tests/test_core_output_wiring.py`
- Status: CANONICAL-WIRED
- Action: preserve as authority for report metric maps and metadata

### 6. profile

- Parameter: `profile`
- Canonical name: `profile`
- Produced by: `build_profile`
- Canonical module: `core.domain.profile`
- Type: `DomainProfile`
- Range / allowed values: 41-value aggregate vectors and hash
- Optional or required: optional, corpus-level only
- Current downstream consumers: domain comparison and classification helpers
- Serialized in: `DomainProfile.to_dict`
- Test coverage: `tests/domain/test_domain_profile.py`
- Status: CANONICAL-WIRED
- Action: document as corpus-level contract, not document report JSON

### 7. classification

- Parameter: `classification`
- Canonical name: classification result from `classify_document`
- Produced by: `classify_document`
- Canonical module: `core.domain.profile`
- Type: `str | None`
- Range / allowed values: chosen `domain_id` or `None`
- Optional or required: optional
- Current downstream consumers: callers of profile matching
- Serialized in: not serialized in canonical report JSON
- Test coverage: indirect via profile tests
- Status: IMPLEMENTED-NOT-DOCUMENTED
- Action: keep out of document report JSON until a dedicated public contract exists

### 8. topology

- Parameter: `topology`
- Canonical name: `topology`
- Produced by: `build_topology_from_activation_trace`, `topology_from_graph_coordinates`
- Canonical module: `hesperia.extensions.triz.kme_bridge`
- Type: `dict`
- Range / allowed values: topology payload when available
- Optional or required: optional
- Current downstream consumers: `run_triz_for_kme`
- Serialized in: not serialized in canonical report JSON
- Test coverage: `tests/domain/test_kme_triz_integration.py`
- Status: IMPLEMENTED-NOT-DOCUMENTED
- Action: document as intermediate wiring only

### 9. triz

- Parameter: `triz_signals`
- Canonical name: `triz`
- Produced by: `run_triz_for_kme`
- Canonical module: `hesperia.extensions.triz.kme_bridge`
- Type: object with `.to_dict()`
- Range / allowed values: TRIZ analysis payload
- Optional or required: optional
- Current downstream consumers: report extractors, runtime reports
- Serialized in: `metric_report_to_dict`
- Test coverage: `tests/domain/test_kme_triz_integration.py`, `tests/test_core_output_wiring.py`
- Status: CANONICAL-WIRED
- Action: preserve optional top-level `triz` field

### 10. provenance

- Parameter: `provenance`
- Canonical name: none in current document report contract
- Produced by: no dedicated document-level producer in current core KME path
- Canonical module: none
- Type: n/a
- Range / allowed values: n/a
- Optional or required: n/a
- Current downstream consumers: docs discuss provenance more broadly than current KME report exposes
- Serialized in: not serialized in canonical report JSON
- Test coverage: none
- Status: DOCUMENTED-NOT-IMPLEMENTED
- Action: document absence explicitly; do not invent field in this pass

### 11. calibration_pack

- Parameter: `calibration_pack`
- Canonical name: none in current document report contract
- Produced by: external system/version authority outside current KME report
- Canonical module: external to `core.domain` report path
- Type: n/a in document report
- Range / allowed values: n/a
- Optional or required: n/a
- Current downstream consumers: system/runtime layers, not current KME report JSON
- Serialized in: not serialized in canonical report JSON
- Test coverage: external integrity checks only
- Status: DOCUMENTED-NOT-IMPLEMENTED
- Action: leave unchanged

### 12. version_metadata

- Parameter: `version_metadata`
- Canonical name: `fingerprintVersion`, `domainRelease`
- Produced by: `build_fingerprint`, pipeline input
- Canonical module: `core.domain.fingerprint`, `core.domain.pipeline`
- Type: `str`
- Range / allowed values: non-empty version strings when provided
- Optional or required: required for `fingerprintVersion`, optional for `domainRelease`
- Current downstream consumers: runtime reports and validation tests
- Serialized in: `DomainFingerprint.to_dict`
- Test coverage: `tests/domain/test_fingerprint.py`, `tests/test_core_output_wiring.py`
- Status: CANONICAL-WIRED
- Action: keep fingerprint metadata as version authority inside document report JSON
