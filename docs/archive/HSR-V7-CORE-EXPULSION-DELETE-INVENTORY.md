# HSR-V7 Core Expulsion Delete Inventory

Date: 2026-07-06
Repo: `igareosh/hesperia`
Baseline before delete: `67f9e668027347d0e9d4a7c321eb4bf9c8bfb07d`

## Candidate Inventory

### 1. `hesperia/modules/core/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: package marker for obsolete runtime-module shim surface
- Canonical replacement: none; canonical runtime modules live under `core.runtime.*`
- Live imports found: `tests/test_core_import_convergence.py`, current docs only
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: `docs/HSR-V7-SOURCE-TRUTH.md`, `docs/HSR-V7-CONSOLIDATION-REPORT.md`, `docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md`
- Action: `DELETE`

### 2. `hesperia/modules/core/dict_a.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only module; implementation moved to `core.runtime.dict_a_module`
- Canonical replacement: `core/runtime/dict_a_module.py`
- Live imports found: none outside compatibility test/docs
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 3. `hesperia/modules/core/dict_b.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only module; implementation moved to `core.runtime.dict_b_module`
- Canonical replacement: `core/runtime/dict_b_module.py`
- Live imports found: none outside compatibility test/docs
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 4. `hesperia/modules/metrics/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: package marker for obsolete runtime-module shim surface
- Canonical replacement: none; canonical runtime module lives under `core.runtime.metrics_module`
- Live imports found: compatibility test/docs only
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: `docs/HSR-V7-SOURCE-TRUTH.md`, `docs/HSR-V7-CONSOLIDATION-REPORT.md`
- Action: `DELETE`

### 5. `hesperia/modules/metrics/base.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only module; implementation moved to `core.runtime.metrics_module`
- Canonical replacement: `core/runtime/metrics_module.py`
- Live imports found: none outside compatibility test/docs
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 6. `hesperia/modules/topology/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: package marker for obsolete runtime-module shim surface
- Canonical replacement: none; canonical runtime module lives under `core.runtime.topology_module`
- Live imports found: compatibility test/docs only
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: `docs/HSR-V7-SOURCE-TRUTH.md`, `docs/HSR-V7-CONSOLIDATION-REPORT.md`
- Action: `DELETE`

### 7. `hesperia/modules/topology/core.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only module; implementation moved to `core.runtime.topology_module`
- Canonical replacement: `core/runtime/topology_module.py`
- Live imports found: none outside compatibility test/docs
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 8. `hesperia/engine/kme/active_graph.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.active_graph`
- Canonical replacement: `core/domain/active_graph.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 9. `hesperia/engine/kme/bridge.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.bridge`
- Canonical replacement: `core/domain/bridge.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 10. `hesperia/engine/kme/execution_flow.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.pipeline`
- Canonical replacement: `core/domain/pipeline.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 11. `hesperia/engine/kme/extractor.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.extractor`
- Canonical replacement: `core/domain/extractor.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 12. `hesperia/engine/kme/loader.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.loader`
- Canonical replacement: `core/domain/loader.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 13. `hesperia/engine/kme/models.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.models`
- Canonical replacement: `core/domain/models.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 14. `hesperia/engine/kme/pipeline.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.pipeline`
- Canonical replacement: `core/domain/pipeline.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 15. `hesperia/engine/kme/derived/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only subpackage facade; canonical implementation already lives in `core.domain.derived_metrics`
- Canonical replacement: `core/domain/derived_metrics.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 16. `hesperia/engine/kme/derived/calculator.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.derived_metrics`
- Canonical replacement: `core/domain/derived_metrics.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 17. `hesperia/engine/kme/fingerprint/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only subpackage facade; canonical implementation already lives in `core.domain.fingerprint`
- Canonical replacement: `core/domain/fingerprint.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 18. `hesperia/engine/kme/fingerprint/builder.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.fingerprint`
- Canonical replacement: `core/domain/fingerprint.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: `docs/foundations/corners/core_math_contract.md`
- Action: `DELETE`

### 19. `hesperia/engine/kme/primitives/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only subpackage facade; canonical implementation already lives in `core.domain.primitive_metrics`
- Canonical replacement: `core/domain/primitive_metrics.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 20. `hesperia/engine/kme/primitives/calculator.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.primitive_metrics`
- Canonical replacement: `core/domain/primitive_metrics.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 21. `hesperia/engine/kme/profiling/__init__.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only subpackage facade; canonical implementation already lives in `core.domain.profile`
- Canonical replacement: `core/domain/profile.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 22. `hesperia/engine/kme/profiling/profiler.py`

- Classification: `CORE-EXPULSION-DELETE`
- Reason: shim-only leaf; canonical implementation already lives in `core.domain.profile`
- Canonical replacement: `core/domain/profile.py`
- Live imports found: none in live code/tests/docs outside archive
- Tests affected: none
- Docs affected: archive traceability docs only
- Action: `DELETE`

### 23. `hesperia/engine/kme/__init__.py`

- Classification: `COMPATIBILITY-STILL-NEEDED`
- Reason: package-level compatibility facade still intentionally preserved
- Canonical replacement: package-level canonical exports come from `core.domain.*`
- Live imports found: `tests/test_core_import_convergence.py`
- Tests affected: `tests/test_core_import_convergence.py`
- Docs affected: current source-truth docs
- Action: `KEEP`

### 24. `hesperia/engine/kme/clinical_bridge.py`

- Classification: `LEGACY-BRIDGE-KEEP`
- Reason: explicitly protected legacy bridge; still imported by live runtime code and covered by tests
- Canonical replacement: none yet; intentionally left outside canonical `core.domain`
- Live imports found: `hesperia/extensions/dynamics/triz_signal.py`, `runtime/pipeline/run_e2e_all.py`, `runtime/pipeline/run_tfp_file_pipeline.py`
- Tests affected: `tests/domain/test_clinical_bridge.py`, `tests/engine/kme/test_clinical_bridge.py`
- Docs affected: current source-truth and foundation docs
- Action: `KEEP`

### 25. `hesperia/engine/kme/fingerprint_distance.py`

- Classification: `COMPATIBILITY-STILL-NEEDED`
- Reason: still exported by preserved package-level compatibility facade
- Canonical replacement: none in `core.domain`; file is still the active home for extra distance helpers
- Live imports found: indirect through `hesperia.engine.kme.__init__`
- Tests affected: package import proof only
- Docs affected: none
- Action: `KEEP`

### 26. `hesperia/engine/kme/validation/__init__.py`

- Classification: `UNKNOWN-REVIEW-NEEDED`
- Reason: validation namespace reservation; not a moved implementation shim
- Canonical replacement: none
- Live imports found: none
- Tests affected: none
- Docs affected: none
- Action: `KEEP`

### 27. `tests/test_core_import_convergence.py`

- Classification: `COMPATIBILITY-STILL-NEEDED`
- Reason: should remain as focused convergence proof, but old module-shim assertions must be removed after deletion
- Canonical replacement: canonical proof via `core.domain` and `core.runtime`, plus kept compatibility proof for `hesperia.engine.kme` / `hesperia.engine.kme.clinical_bridge`
- Live imports found: direct test only
- Tests affected: this file
- Docs affected: delete report
- Action: `KEEP`
