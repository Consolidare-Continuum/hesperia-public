# Hesperia consolidation report

Date: 2026-07-06

## Completed

- Synced root `VERSION.yaml` and `hesperia/VERSION.yaml`.
- Moved active calibration default to `v0_6_0_clr_v052_5`.
- Marked `archive_063_minimal` as archive-only placeholder metadata.
- Updated version loaders to resolve from repo root first and packaged copy second.
- Replaced hardcoded `0.6.0` fallbacks in runtime/package metadata with `0.6.5`.
- Renamed pipeline metadata constant away from `ENGINE_VERSION`.
- Added metrics-file resolution with fallback support for baseline metrics files.
- Added repository truth navigation docs.
- Updated stale v7 source-truth verification text.
- Renamed `docs/SOURCE_OF_TRUTH.md` to `docs/HSR-V7-SOURCE-TRUTH.md`.
- Renamed `docs/CONSOLIDATION_REPORT.md` to `docs/HSR-V7-CONSOLIDATION-REPORT.md`.
- Moved `docs/brain-export/README.md` to `docs/archive/brain-export/README.md`.
- Added `docs/archive/ARCHIVE-MANIFEST.md` and `docs/archive/HSR-V7-CONSOLIDATION-INVENTORY.md`.
- Fused shared KME/domain implementation into canonical `core.domain`.
- Fused generic runtime modules into canonical `core.runtime`.
- Preserved `hesperia.engine.kme` as a compatibility facade during fusion, with protected legacy bridge behavior.
- Recreated `hesperia.modules.core` / `metrics` / `topology` as transitional compatibility shims during fusion.
- Converged live imports onto canonical `core.domain.*` paths where canonical owners exist.
- Updated non-archive source-truth docs to reflect post-core-fusion architecture.
- Removed obsolete core-expulsion shim files where no live code or tests still required them.

## Notes

- Historical payloads under `docs/brain-export/archive/` remain in place for a later prune/move pass.
- The repo now prefers the complete calibration pack for active development; archive placeholder remains explicitly labeled.
- Current architectural authority:
  - `core.domain` = canonical shared KME/domain computation
  - `core.runtime` = canonical generic runtime module layer
  - `hesperia.engine.kme` = narrowed compatibility package surface; protected legacy bridge remains
  - former `hesperia.modules.core` / `metrics.base` / `topology.core` shim files were removed after convergence
  - `hesperia.modules.tfp` = domain extension
