# HSR-V7 Core Import Convergence Report

Date: 2026-07-06
Repo: `igareosh/hesperia`
Baseline before pass: `f216ab220cf22174480694a6e1c2a30e23cd679c`
Pass: Core Import Convergence

## 1. Purpose

Converge active implementation and non-compat test imports onto canonical `core.*` paths after the completed core fusion pass, while preserving old import surfaces as compatibility shims.

## 2. Search Baseline

Searches were run against the repo for:

- `from hesperia.engine.kme`
- `import hesperia.engine.kme`
- `from hesperia.modules.core`
- `import hesperia.modules.core`
- `from hesperia.modules.metrics`
- `import hesperia.modules.metrics`
- `from hesperia.modules.topology`
- `import hesperia.modules.topology`
- `core.domain`
- `core.runtime`

Classification rule used:

- Replace old imports in live implementation under `hesperia/`, `runtime/`, and non-compat tests.
- Retain old imports in shim surfaces, explicit compatibility tests, and archive docs.

## 3. Old Import Paths Found

### Replaced with canonical imports

- `hesperia/extensions/dynamics/xi_proxy.py`
- `hesperia/extensions/triz/pipeline.py`
- `hesperia/extensions/triz/report_extractors.py`
- `hesperia/extensions/triz/propagation_engine.py`
- `hesperia/extensions/triz/kme_bridge.py`
- `runtime/pipeline/run_e2e_all.py`
- `runtime/pipeline/run_tfp_file_pipeline.py`
- `tests/domain/test_kme_triz_integration.py`
- `tests/triz/test_signal_stabilization.py`
- `tests/triz/test_commercial_intelligence.py`
- `tests/triz/test_family_clustering.py`
- `tests/triz/test_contradiction_engine.py`
- `tests/triz/test_propagation_topology.py`
- `tests/test_field_dynamics_xi_proxy.py`

### Intentionally retained old imports

- `hesperia/engine/kme/*`
  Compatibility shim surface by design.
- `hesperia/modules/core/*`
  Compatibility shim surface by design.
- `hesperia/modules/metrics/*`
  Compatibility shim surface by design.
- `hesperia/modules/topology/*`
  Compatibility shim surface by design.
- `hesperia/extensions/dynamics/triz_signal.py`
  Retained runtime import of `hesperia.engine.kme.clinical_bridge` because `clinical_bridge` was explicitly kept outside canonical `core.domain`.
- `runtime/pipeline/run_e2e_all.py`
  Retained runtime imports of `hesperia.engine.kme.clinical_bridge` for the same reason.
- `runtime/pipeline/run_tfp_file_pipeline.py`
  Retained runtime imports of `hesperia.engine.kme.clinical_bridge` for the same reason.
- `tests/domain/test_clinical_bridge.py`
  Tests the preserved `clinical_bridge` surface.
- `tests/engine/kme/test_clinical_bridge.py`
  Tests the preserved `hesperia.engine.kme` compatibility surface.
- `tests/test_core_import_convergence.py`
  Compatibility proof test; intentionally imports old shim paths.
- `docs/archive/*`
  Historical/archive record, not active code.

## 4. Imports Converted to Canonical `core.*`

Canonical import targets used in this pass:

- `core.domain.models`
- `core.domain.active_graph`
- `core.domain.pipeline`

No new architecture layers were introduced.

## 5. Compatibility Shims Verified

Compatibility surfaces preserved:

- `hesperia.engine.kme`
- `hesperia.modules.core`
- `hesperia.modules.metrics.base`
- `hesperia.modules.topology.core`

Focused import test added:

- `tests/test_core_import_convergence.py`

## 6. Dynamic Aliases Reviewed

Reviewed:

- `hesperia/engine/module_aliases.py`

Status:

- already aligned from the previous fusion pass;
- aliases point to canonical `core.runtime.*` implementations;
- no changes needed in this pass.

## 7. Tests Run

- `python3 -m py_compile hesperia/extensions/dynamics/xi_proxy.py hesperia/extensions/dynamics/triz_signal.py hesperia/extensions/triz/pipeline.py hesperia/extensions/triz/report_extractors.py hesperia/extensions/triz/propagation_engine.py hesperia/extensions/triz/kme_bridge.py runtime/pipeline/run_e2e_all.py runtime/pipeline/run_tfp_file_pipeline.py`
- `python3 -m pytest tests/test_core_import_convergence.py tests/domain/test_kme_triz_integration.py tests/triz/test_signal_stabilization.py tests/triz/test_commercial_intelligence.py tests/triz/test_family_clustering.py tests/triz/test_contradiction_engine.py tests/triz/test_propagation_topology.py tests/test_field_dynamics_xi_proxy.py tests/domain/test_clinical_bridge.py tests/engine/kme/test_clinical_bridge.py -q`

## 8. Failures or Skipped Checks

- No files were deleted.
- No payloads were pruned.
- No archive cleanup was performed.
- No version or calibration authority changed.

## 9. Final Status

PASS.

Active implementation code now imports canonical `core.*` surfaces where canonical owners exist, while compatibility-facing legacy paths remain importable and explicitly tested.

## Historical Note

Later on 2026-07-06, the core-expulsion delete pass removed obsolete shim files under
`hesperia/modules/core`, `hesperia/modules/metrics`, `hesperia/modules/topology`, and selected
leaf shim files under `hesperia/engine/kme/` once live code and tests no longer required them.
Protected legacy bridge behavior under `hesperia.engine.kme.clinical_bridge` remained.
