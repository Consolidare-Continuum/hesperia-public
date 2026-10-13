# HSR-V7 Core Output Contract

## Objective

This document defines the current canonical output contract for HESPERIA structural computation after core fusion and output wiring convergence.

## Canonical Authority

- Structural computation authority: `core/domain/`
- Canonical document-output producer: `core/domain/pipeline.py`
- Canonical fingerprint serializer: `core/domain/models.py::DomainFingerprint.to_dict`
- Compatibility adapter retained: `hesperia/engine/kme/clinical_bridge.py`

## Canonical Document Output

`core.domain.pipeline.metric_report_to_dict(report)` is the canonical JSON shape for document-level KME output.

Required top-level keys:

- `sourceId`: string
- `primitives`: object with 6 bounded metrics
- `derived`: object with 35 bounded metrics
- `fingerprint`: object with fingerprint metadata and ordered vectors
- `triz`: object, present when TRIZ signals are available

## Primitive Metrics Contract

- Canonical producer: `core.domain.primitive_metrics.compute_primitives`
- Canonical names: `LD`, `COH`, `NC`, `PR`, `PV`, `CI`
- Type: `float`
- Range: normalized to `[0, 1]`
- Canonical serialized names:
  - report scope: `primitives`
  - fingerprint scope: `primitiveMap`

## Derived Metrics Contract

- Canonical producer: `core.domain.derived_metrics.compute_derived_metrics`
- Canonical names: the 35-key derived map emitted by `core.domain.fingerprint.to_derived_map`
- Type: `float`
- Range: normalized to `[0, 1]`
- Canonical serialized names:
  - report scope: `derived`
  - fingerprint scope: `derivedMap`

## Fingerprint Contract

- Canonical producer: `core.domain.fingerprint.build_fingerprint`
- Canonical JSON keys:
  - `fingerprintVersion`
  - `domainRelease`
  - `sourceId`
  - `metricNames`
  - `metricValues`
  - `primitiveMap`
  - `derivedMap`
  - `vectorHash`
- Type notes:
  - `metricNames`: ordered `list[str]`
  - `metricValues`: ordered `list[float]`
  - `vectorHash`: lowercase SHA-256 hex string

## Wiring Rule

`MetricReport.primitive_map` and `MetricReport.derived_map` must mirror `MetricReport.fingerprint.primitive_map` and `MetricReport.fingerprint.derived_map`.

This is the current source-of-truth rule for both:

- canonical core pipeline path: `core.domain.pipeline.run_document`
- compatibility bridge path: `hesperia.engine.kme.clinical_bridge.run_kme_from_activation`

No adapter should recompute or rename these maps once the fingerprint exists.

## Topology And TRIZ

- Topology is optional document-run context, not a required top-level KME report field.
- TRIZ signals are attached under `triz` when available.
- Current document output does not serialize a standalone top-level `topology` or `provenance` field.

Status:

- `topology`: IMPLEMENTED-NOT-DOCUMENTED at intermediate runtime level, not part of canonical KME report JSON
- `provenance`: DOCUMENTED-NOT-IMPLEMENTED as a dedicated top-level KME field

## Profile And Classification

- Canonical profile producer: `core.domain.profile.build_profile`
- Canonical profile serializer: `core.domain.models.DomainProfile.to_dict`
- Profile output is a corpus-level contract, not part of document-level `metric_report_to_dict`
- Classification currently exists via `core.domain.profile.classify_document`

Status:

- `profile`: CANONICAL-WIRED for corpus-level APIs, absent by design from document report JSON
- `classification`: IMPLEMENTED-NOT-DOCUMENTED for core helper output, not part of document report JSON

## Version And Calibration

- Fingerprint version authority: `core/domain/fingerprint.py::FINGERPRINT_VERSION`
- Domain release authority: pipeline input `domain_release`
- This pass does not change calibration pack or system version authority.

## Runtime Consumers

Current runtime/report consumers that must treat this contract as canonical:

- `runtime/pipeline/run_e2e_all.py`
- `runtime/pipeline/run_tfp_file_pipeline.py`
- `hesperia/engine/multiscale_product_bridge.py`

## Tests

Direct contract coverage:

- `tests/domain/test_e2e_pipeline.py`
- `tests/domain/test_kme_triz_integration.py`
- `tests/test_core_output_wiring.py`
