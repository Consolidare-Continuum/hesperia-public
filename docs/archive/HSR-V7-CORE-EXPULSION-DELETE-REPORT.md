# HSR-V7 Core Expulsion Delete Report

Date: 2026-07-06
Repo: `igareosh/hesperia`
Pass: Core Expulsion Trash Pass
Baseline before deletion: `67f9e668027347d0e9d4a7c321eb4bf9c8bfb07d`

## 1. Purpose

Remove obsolete post-core-fusion shim files that no longer belong in the live repository after
canonical ownership had already converged to `core.domain` and `core.runtime`.

This was a destructive pass, but limited to explicit core-expulsion leftovers.

## 2. Deleted Files

- `hesperia/modules/core/__init__.py`
- `hesperia/modules/core/dict_a.py`
- `hesperia/modules/core/dict_b.py`
- `hesperia/modules/metrics/__init__.py`
- `hesperia/modules/metrics/base.py`
- `hesperia/modules/topology/__init__.py`
- `hesperia/modules/topology/core.py`
- `hesperia/engine/kme/active_graph.py`
- `hesperia/engine/kme/bridge.py`
- `hesperia/engine/kme/execution_flow.py`
- `hesperia/engine/kme/extractor.py`
- `hesperia/engine/kme/loader.py`
- `hesperia/engine/kme/models.py`
- `hesperia/engine/kme/pipeline.py`
- `hesperia/engine/kme/derived/__init__.py`
- `hesperia/engine/kme/derived/calculator.py`
- `hesperia/engine/kme/fingerprint/__init__.py`
- `hesperia/engine/kme/fingerprint/builder.py`
- `hesperia/engine/kme/primitives/__init__.py`
- `hesperia/engine/kme/primitives/calculator.py`
- `hesperia/engine/kme/profiling/__init__.py`
- `hesperia/engine/kme/profiling/profiler.py`

## 3. Kept Files

- `hesperia/engine/kme/__init__.py`
- `hesperia/engine/kme/clinical_bridge.py`
- `hesperia/engine/kme/fingerprint_distance.py`
- `hesperia/engine/kme/validation/__init__.py`
- all of `core/*`
- all of `runtime/*`
- all of `hesperia/modules/tfp/*`

## 4. Protected Legacy Files

- `hesperia/engine/kme/clinical_bridge.py`
  Kept by explicit policy and confirmed still live in runtime code and tests.

## 5. Canonical Replacements

- `hesperia/modules/core/dict_a.py` → `core/runtime/dict_a_module.py`
- `hesperia/modules/core/dict_b.py` → `core/runtime/dict_b_module.py`
- `hesperia/modules/metrics/base.py` → `core/runtime/metrics_module.py`
- `hesperia/modules/topology/core.py` → `core/runtime/topology_module.py`
- `hesperia/engine/kme/active_graph.py` → `core/domain/active_graph.py`
- `hesperia/engine/kme/bridge.py` → `core/domain/bridge.py`
- `hesperia/engine/kme/execution_flow.py` → `core/domain/pipeline.py`
- `hesperia/engine/kme/extractor.py` → `core/domain/extractor.py`
- `hesperia/engine/kme/loader.py` → `core/domain/loader.py`
- `hesperia/engine/kme/models.py` → `core/domain/models.py`
- `hesperia/engine/kme/pipeline.py` → `core/domain/pipeline.py`
- `hesperia/engine/kme/derived/*` → `core/domain/derived_metrics.py`
- `hesperia/engine/kme/fingerprint/*` → `core/domain/fingerprint.py`
- `hesperia/engine/kme/primitives/*` → `core/domain/primitive_metrics.py`
- `hesperia/engine/kme/profiling/*` → `core/domain/profile.py`

## 6. Imports Searched

Searches were run for:

- `hesperia.engine.kme`
- `hesperia.modules.core`
- `hesperia.modules.metrics`
- `hesperia.modules.topology`
- `clinical_bridge`

Classification outcome:

- `clinical_bridge` remains live and protected.
- package-level `hesperia.engine.kme` remains intentionally preserved.
- deleted leaf shims had no live imports outside compatibility tests, archive docs, or already-updated source-truth wording.

## 7. Tests Updated

- `tests/test_core_import_convergence.py`
  - removed assertions for deleted `hesperia.modules.*` shim imports
  - kept proof for canonical imports
  - kept proof for intentionally preserved `hesperia.engine.kme` and `hesperia.engine.kme.clinical_bridge`

## 8. Docs Updated

- `README.md`
- `docs/HSR-V7-SOURCE-TRUTH.md`
- `docs/HSR-V7-CONSOLIDATION-REPORT.md`
- `docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md`
- `docs/foundations/corners/core_math_contract.md`
- `docs/archive/HSR-V7-CORE-IMPORT-CONVERGENCE-REPORT.md`
- `docs/archive/HSR-V7-CORE-FUSION-CONSOLIDATION-REPORT.md`
- `docs/archive/HSR-V7-CORE-EXPULSION-DELETE-INVENTORY.md`

## 9. Verification Commands Run

- `python3 tools/validate_version_consistency.py`
- `python3 tools/check_calibration_pack_integrity.py`
- `python3 -m pytest tests/test_calibration_dict_version_loader.py tests/test_provenance_metadata.py -q`
- `python3 -m pytest tests -q -k "kme or domain or fingerprint or primitive or derived or profile or topology or modules or import or clinical_bridge"`
- `python3 -m py_compile $(find core hesperia runtime -name "*.py")`
- `git status --short`
- `git diff --stat`

## 10. Verification Results

- `validate_version_consistency.py`: PASS
- `check_calibration_pack_integrity.py`: PASS
- targeted pytest (`test_calibration_dict_version_loader.py`, `test_provenance_metadata.py`): PASS
- broad `pytest -k ...`: one unrelated failure outside this delete surface
  - `tests/architecture/test_layer_dependencies.py::test_sphere_does_not_import_runtime`
  - reported violations in:
    - `sphere/router/pre_llm_compiler.py`
    - `sphere/router/audit.py`
- repo-wide `py_compile`: one unrelated existing syntax error outside this delete surface
  - `hesperia/visualization/session_graph.py:55`

Neither failing location was touched by this pass.

## 11. Scope Statement

Deletion was limited to explicit core-expulsion leftovers listed in the inventory.

No active `core.*` implementation was deleted.
No active `runtime/*` implementation was deleted.
No TFP domain extension files were deleted.
No calibration metadata changed.
No version metadata changed.

## 12. Final Status

PASS for the intended core-expulsion cleanup surface, with unrelated pre-existing repo failures
documented separately above.
