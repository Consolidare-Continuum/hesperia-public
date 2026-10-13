# HSR-V7 Core Fusion Consolidation Report

Date: 2026-07-06
Repo: `igareosh/hesperia`
Pass: Core Fusion Rename and Module Consolidation

## Outcome

- Promoted `core/domain/*` to the canonical implementation layer for shared structural computation.
- Recreated `hesperia.engine.kme.*` as compatibility shims so existing imports continue to resolve.
- Promoted generic runtime loaders to `core/runtime/*`.
- Recreated `hesperia.modules.core.*`, `hesperia.modules.metrics.base`, and `hesperia.modules.topology.core` as compatibility shims.
- Preserved `hesperia/modules/tfp/*` as a domain extension.
- Updated dynamic module aliases to resolve canonical runtime modules from `core.runtime.*`.
- Updated the current architecture spec to document `core/runtime/*` as the Class A canonical location.

Historical note: later on 2026-07-06, the core-expulsion delete pass removed obsolete shim files
that were no longer needed by live code or tests, while keeping protected legacy bridge behavior.

## Canonical Ownership After Fusion

| Concern | Canonical path | Compatibility path |
|---|---|---|
| Domain models | `core/domain/models.py` | `hesperia/engine/kme/models.py` |
| Active graph | `core/domain/active_graph.py` | `hesperia/engine/kme/active_graph.py` |
| Domain constants | `core/domain/extractor.py` | `hesperia/engine/kme/extractor.py` |
| Domain loading | `core/domain/loader.py` | `hesperia/engine/kme/loader.py` |
| Pipeline | `core/domain/pipeline.py` | `hesperia/engine/kme/pipeline.py`, `hesperia/engine/kme/execution_flow.py` |
| Primitive metrics | `core/domain/primitive_metrics.py` | `hesperia/engine/kme/primitives/calculator.py` |
| Derived metrics | `core/domain/derived_metrics.py` | `hesperia/engine/kme/derived/calculator.py` |
| Fingerprint | `core/domain/fingerprint.py` | `hesperia/engine/kme/fingerprint/builder.py` |
| Profile | `core/domain/profile.py` | `hesperia/engine/kme/profiling/profiler.py` |
| Dict A | `core/runtime/dict_a_module.py` | `hesperia/modules/core/dict_a.py` |
| Dict B | `core/runtime/dict_b_module.py` | `hesperia/modules/core/dict_b.py` |
| Topology | `core/runtime/topology_module.py` | `hesperia/modules/topology/core.py` |
| Metrics | `core/runtime/metrics_module.py` | `hesperia/modules/metrics/base.py` |

## Verification Plan

- `python3 tools/validate_version_consistency.py`
- `python3 tools/check_calibration_pack_integrity.py`
- `pytest tests/test_calibration_dict_version_loader.py tests/test_provenance_metadata.py -q`
- `pytest tests -q -k "kme or domain or fingerprint or primitive or derived or profile or topology or modules"`
