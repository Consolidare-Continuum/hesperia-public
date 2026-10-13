# Era 6: The Metric Wave — v0.7.0 (2026-06-22, in-flight)

## Evidence

This era is not yet a tagged release — it is recorded in `release/v0.7.0/RELEASE_SCOPE.md`
(committed) and realized as uncommitted working-tree files:

```
$ git status --short | grep -E 'metric|anchor|gcs|path_metric'
?? docs/specs/
?? release/v0.7.0/
?? runtime/services/anchor_map_registry.py
?? runtime/services/gcs_lookup.py
?? runtime/services/hesperia_metric_emit.py
?? runtime/services/path_metric.py
?? schemas/anchor_map_v1.json
?? schemas/hesperia_metric_v01.json
?? tests/schemas/
?? tests/test_anchor_map_reconcile.py
?? tests/test_metric_22_26.py
 M docs/ENGINE-ANALYZE-CONTRACT.md
```

`release/v0.7.0/RELEASE_SCOPE.md` (committed, dated 2026-06-23) names this work `v7_consolidated`,
explicitly baselined on "v0.6.0 sealed release," consolidating two parallel research tracks —
**METRIC** (frozen `anchor_map_v1`, `hesperia_metric` emit, `metric_layer` contract, env flags) and
**HRES** (`24_SPEC §14` iteration geometry: `I²_n`, `powv_step`) — plus an "IPoV reconcile" task
(single `anchor_map_id` across IPoV-01 code and the METRIC registry) and a pedagogy track
explicitly marked "docs only, not runtime physics."

## What this era actually is

This is the era where Hesperia formalizes its own vocabulary for "distance" and "position" after
several independent geometric notions (area-sphere geodesics, family zone costs, hex hop counts,
the as-yet-unimplemented "Interior Point of World View" / IPoW position in a unit ball) had
accumulated across prior eras without a shared registry. `docs/specs/24_SPEC__Hesperia_Metric_and_Distance_v0_1.md`
is the spec; the working-tree files are its incremental, flag-gated implementation.

The scope document is unusually explicit about what is *not* included: "Deferred to follow-on rows
(not blocking v0.7.0 scope doc): `HESPERIA_GCS_EMIT=1` static geodesic_sphere block, Full
`meta.interior_point_of_world_view` live emit, `path_metric_cost` on traversal." This deferral list
is direct evidence of the same restraint pattern seen in every prior era (lexicon freeze stops
short of full WSD; contradiction track centralizes rather than sprawls; sealing strips narrative
but preserves config) — applied here to a brand new geometric vocabulary that could easily have
expanded into a much larger physics-flavored rewrite (the spec itself explicitly disclaims Einstein
field equations and a Poisson solver, §1 and §9).

## Why this ordering was the minimal right move

Shipping the registry and naming discipline (`metric_layer` enum, the "no bare distance" rule) and
the frozen `anchor_map_v1` artifact *before* shipping any live emit of GCS or IPoW data means the
naming discipline is locked in and testable (`tests/test_anchor_map_reconcile.py`,
`tests/test_metric_22_26.py`) before any consumer (including the LLM bridge, era 7, which would be
the most likely eventual consumer of a `path_metric_cost`) can depend on a half-finished emit
format. Gating everything behind `HESPERIA_METRIC_EMIT` / `HESPERIA_GCS_EMIT` env flags — both
defaulting to off — means the new vocabulary can be exercised in CI and tests without it ever
becoming part of the default `/analyze` contract until it is proven, the same incremental rollout
discipline as the v0.5.x calibration era's task-by-task sealing.

See [`corners/metric_registry.md`](../corners/metric_registry.md), [`corners/topology_geometry.md`](../corners/topology_geometry.md).
