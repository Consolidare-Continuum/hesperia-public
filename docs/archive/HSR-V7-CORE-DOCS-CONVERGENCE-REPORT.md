# HSR-V7 Core Docs Convergence Report

Date: 2026-07-06
Repo: `igareosh/hesperia`
Pass: Core Source-Truth Documentation Convergence

## 1. Purpose

Update non-archive documentation so post-core-fusion architecture is described correctly without
changing code, tests, version metadata, or calibration metadata.

## 2. Baseline Commits

- Core fusion: `f216ab220cf22174480694a6e1c2a30e23cd679c`
- Core import convergence: `b6452aa52709485a82a5d75e5324a11b49782f54`

## 3. Docs Inspected

- `docs/HSR-V7-SOURCE-TRUTH.md`
- `docs/HSR-V7-CONSOLIDATION-REPORT.md`
- `docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md`
- `docs/foundations/corners/kme.md`
- `docs/foundations/output_catalog.md`
- `docs/foundations/provenance.md`
- `docs/publication/TERMINOLOGY_AND_ABBREVIATIONS.md`
- `docs/iso/ARCHITECTURE_DESCRIPTION.md`
- `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`
- `README.md`

## 4. Old Authority References Found

- `hesperia/engine/kme/` described as the KME implementation location in current docs.
- `hesperia/engine/kme/derived/calculator.py` cited as the canonical implementation source in
  current docs.
- `hesperia.modules.*` described in current architecture docs without always clarifying shim status.

## 5. References Updated

- Declared `core/` as the canonical home for deterministic structural computation.
- Declared `core.domain` as the canonical shared KME/domain computation layer.
- Declared `core.runtime` as the canonical generic runtime module layer.
- Clarified `hesperia.engine.kme` as a compatibility import surface.
- Clarified `hesperia.modules.core`, `hesperia.modules.metrics.base`, and
  `hesperia.modules.topology.core` as compatibility import surfaces.
- Clarified `hesperia.modules.tfp` as the domain extension.
- Repointed documentation references from old KME implementation files to canonical `core.domain`
  files where the docs were describing live implementation authority rather than compatibility.

## 6. References Intentionally Retained

- Archive reports under `docs/archive/*` were not rewritten.
- Historical and brain-export material outside archive was left in place unless a live source-truth
  doc needed clarification; this pass did not rewrite research/history payloads wholesale.
- Compatibility references to `hesperia.engine.kme.clinical_bridge` remain valid where docs discuss
  preserved migration surfaces.

## 7. Docs Not Changed and Why

- Most `docs/specs/*.md` files did not describe canonical implementation location and did not need
  edits.
- `docs/brain-export/*` was not bulk-rewritten because this pass was restricted to current
  source-truth authority, not historical cleanup.
- `docs/iso/*` files unrelated to current architecture authority were left unchanged.

## 8. Verification Commands Run

- `python3 tools/validate_version_consistency.py`
- `python3 tools/check_calibration_pack_integrity.py`
- `python3 -m pytest tests/test_core_import_convergence.py -q`
- `git diff --stat`
- `git status --short`

## 9. Change Boundaries

- No Python implementation code changed.
- No tests changed.
- No files were deleted, moved, or renamed.
- No version metadata changed.
- No calibration metadata changed.

## 10. Final Status

PASS.

Diff is docs-only, non-archive source-truth docs now describe post-core-fusion authority correctly,
and compatibility surfaces remain described as compatibility rather than canonical implementation.
