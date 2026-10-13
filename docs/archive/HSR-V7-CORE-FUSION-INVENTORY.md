# HSR-V7 core fusion inventory

Date: 2026-07-06

## Repository state

- Branch: `main`
- Commit: `0fb1f17`

## No deletion or pruning

This pass moves canonical core-grade code into `core/` and replaces legacy paths with compatibility shims. No files are deleted and no payloads are pruned.

## Inventory

Current path: `hesperia/engine/kme/models.py`
Proposed canonical path: `core/domain/models.py`
Action: `MOVE`
Reason: domain models are canonical structural/core data types.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/active_graph.py`
Proposed canonical path: `core/domain/active_graph.py`
Action: `MOVE`
Reason: deterministic active-graph construction is core-grade measurement logic.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/bridge.py`
Proposed canonical path: `core/domain/bridge.py`
Action: `MOVE`
Reason: generic pipeline-to-domain mapping is reusable structural logic.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/extractor.py`
Proposed canonical path: `core/domain/extractor.py`
Action: `MOVE`
Reason: frozen domain-constant extraction is core structural measurement.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/loader.py`
Proposed canonical path: `core/domain/loader.py`
Action: `MOVE`
Reason: domain graph loading and canonicalization are core-domain authority.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/pipeline.py`
Proposed canonical path: `core/domain/pipeline.py`
Action: `MOVE`
Reason: reusable KME pipeline execution is the canonical structural pipeline surface.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/primitives/calculator.py`
Proposed canonical path: `core/domain/primitive_metrics.py`
Action: `MOVE`
Reason: primitive metrics are deterministic core-domain computation.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/derived/calculator.py`
Proposed canonical path: `core/domain/derived_metrics.py`
Action: `MOVE`
Reason: derived metrics are deterministic core-domain computation.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/fingerprint/builder.py`
Proposed canonical path: `core/domain/fingerprint.py`
Action: `MOVE`
Reason: canonical fingerprint construction belongs to core-domain authority.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/profiling/profiler.py`
Proposed canonical path: `core/domain/profile.py`
Action: `MOVE`
Reason: domain profiling and classification are core-domain computation.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/engine/kme/execution_flow.py`
Proposed canonical path: `hesperia/engine/kme/execution_flow.py`
Action: `SHIM`
Reason: keep legacy execution-flow import surface but point it at canonical `core.domain.pipeline`.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: no
Authority level: `ENGINE-COMPATIBILITY`

Current path: `hesperia/modules/core/dict_a.py`
Proposed canonical path: `core/runtime/dict_a_module.py`
Action: `MOVE`
Reason: generic deterministic loader wrapper should not stay under optional module authority.
Runtime affected: yes
Tests affected: maybe
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/modules/core/dict_b.py`
Proposed canonical path: `core/runtime/dict_b_module.py`
Action: `MOVE`
Reason: generic deterministic loader wrapper should not stay under optional module authority.
Runtime affected: yes
Tests affected: maybe
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/modules/metrics/base.py`
Proposed canonical path: `core/runtime/metrics_module.py`
Action: `MOVE`
Reason: generic runtime wrapper for core metrics should not remain canonical under optional modules.
Runtime affected: yes
Tests affected: maybe
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/modules/topology/core.py`
Proposed canonical path: `core/runtime/topology_module.py`
Action: `MOVE`
Reason: generic runtime wrapper for topology normalization should not remain canonical under optional modules.
Runtime affected: yes
Tests affected: maybe
Compatibility shim required: yes
Authority level: `CURRENT-CORE-AUTHORITY`

Current path: `hesperia/modules/tfp/*`
Proposed canonical path: `hesperia/modules/tfp/*`
Action: `KEEP`
Reason: TFP remains a domain extension, not generic core.
Runtime affected: no
Tests affected: no
Compatibility shim required: no
Authority level: `DOMAIN-EXTENSION`

Current path: `hesperia/engine/kme/clinical_bridge.py`
Proposed canonical path: `hesperia/engine/kme/clinical_bridge.py`
Action: `KEEP`
Reason: clinical bridge is a domain-specific adapter layered on top of core-domain primitives.
Runtime affected: yes
Tests affected: yes
Compatibility shim required: no
Authority level: `ENGINE-COMPATIBILITY`

