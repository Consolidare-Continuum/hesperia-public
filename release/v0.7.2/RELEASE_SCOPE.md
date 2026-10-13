# HESPERIA v0.7.2 — module boundary consolidation + KSI/IPoV drain

**Codename:** `v7_2_boundary_consolidation`
**Baseline:** v0.7.1 sealed release
**Authority:** Direct operator task (igareosh), 2026-08-04

## What this release consolidates

A one-day pass closing a real architectural boundary gap plus landing two previously-external
capabilities that already had complete implementations, just never merged upstream. No live
request-path behavior changes — everything below is either an internal re-home or new code that
is not yet wired into `/analyze` or `/product/interpret`.

## Include (incremental over v0.7.1)

- **Module registry boundary enforced, not just documented**: `dict_a`, `dict_b`, `topology`,
  `metrics` moved out of `core/runtime/` into `hesperia/modules/default/`, sibling to
  `hesperia/modules/{nlp,tfp}/`. `core/` now holds zero module-registry-shaped code
  (`provides`/`requires`/`capabilities`/`create()`), with no exception carved out for
  "universal" modules. Fixed a real latent bug surfaced by the move: the calibration-dict
  fallback path resolved one directory above the actual repo root whenever no explicit
  calibration version was set (the default case), silently loading zero dictionary entries —
  a depth-relative path bug that only became visible once the files moved to their correct depth.
  `tools/check_core_module_boundary.py` — already present, previously never fully green —
  caught one remaining violation (an unnecessary back-compat re-export) mid-pass; removed.
- **KSI-Inspector landed** (`core/domain/ksi/`): the Φ_e → Expected_j → residual →
  incident-classifier → mirror-deficit → bridge-need pipeline, spec'd and registered DONE
  against this product months ago, but the actual implementation had only ever been built in
  an external agent's vendored copy, never merged into this repo. Ported with a real fix (same
  depth-relative path bug class as above) and its full gold-fixture test suite (41 tests).
- **Point-of-view geometry landed**, closing the v0.7.0-deferred METRIC-23/HRES-04 gap: full
  position/orientation state (ellipsoid geometry, geodesic distances, barycentric weights,
  coupling, provenance) plus the matching output-schema layer for the existing thought-routing
  module. Same story as KSI — a complete implementation existed externally, never merged. Ported
  with its full gold-fixture test suite (47 tests) plus 7 new tests for the schema layer.
- **Docs/wiki structure corrected to match**: architecture references that described the Class A
  module set as "consolidated into core" were stale as of this release — corrected across the
  canonical modular-architecture doc and its wiki cross-references.

## Deferred (unchanged, inherited from v0.7.1)

- Traversal cost metric (METRIC-24/25)

## Post-seal flag-gated wiring (2026-08-10)

- METRIC-22/23 is live on `/analyze` only when `HESPERIA_METRIC_EMIT=1`; the public
  PointZero snapshot emits at `engine_result.meta.interior_point_of_world_view`.
- `HESPERIA_GCS_EMIT=1`, together with metric emit, adds the frozen static
  `geodesic_sphere` descriptor inside `engine_result.meta.hesperia_metric`.
- Both flags default OFF, so the frozen public response and schema snapshot remain unchanged.
- The system seal remains **0.7.2**; this additive opt-in wiring does not create a new seal.

## Verification

- `tools/check_import_boundary.py`: clean.
- `tools/check_forbidden_zone_imports.py`: clean.
- `tools/check_core_module_boundary.py`: clean (one real violation found and fixed this pass).
- `tools/check_engine_projection_boundary.py`: clean.
- `tools/sealing_scan.py`: clean (one release-note wording fix needed to stay clean).
- `tools/verify_public_api_snapshot.py`: clean, snapshot unchanged.
- Targeted regression: architecture, calibration, concept_dictionary, domain, engine,
  lexical_concept, nlp, pipeline, topology, layers, fingerprint, gtp, router suites green
  (372+114 = 486 tests across the two landing passes).

## Pin

- System version: **0.7.2**
- `components.core_engine`, `components.calibration`: **0.7.2**
- All other components (`dynamics`, `triz`, `clinical`, `router`, `fpf_bridge`) unchanged
- `anchor_map_id`: unchanged from v0.7.0

**SIGNED: Developer (Felix) | Claude Code context | 2026-08-04 | v0.7.2 boundary consolidation, direct operator task**
