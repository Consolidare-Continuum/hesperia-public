# Corner: HesperiaMetric Registry — `24_SPEC` / `anchor_map_v1`

**Location:** `docs/specs/24_SPEC__Hesperia_Metric_and_Distance_v0_1.md`,
`schemas/anchor_map_v1.json`, `schemas/hesperia_metric_v01.json`,
`runtime/services/anchor_map_registry.py`, `runtime/services/path_metric.py`,
`runtime/services/family_graph.py`, `runtime/services/gcs_lookup.py`,
`runtime/services/hesperia_metric_emit.py` (all uncommitted, v0.7.0 working-tree state).

**Born:** 2026-06-22, "METRIC wave," scoped in `release/v0.7.0/RELEASE_SCOPE.md` as the
`v7_consolidated` track.

## Why this is a distinct concern

Before this corner existed, "distance" appeared in at least four structurally unrelated senses
across the codebase and papers: geodesic distance on the 12-area icosahedral sphere, zone
shortest-path cost on the 288-family lattice, hop count on the 72k hex adjacency graph, and an
ambiguous "KSI" used both as a tool name and a quality score (`docs/DOC_INDEX.md` makes this
collision explicit: "Bare 'KSI' in runtime docs is ambiguous — always qualify"). Ambiguous distance
language is a determinism leak of the same kind the guard triad exists to prevent elsewhere: two
readers (or two code paths) agreeing on a number while disagreeing on what manifold it lives on is
unauditable in exactly the way Sigma/Gamma forbid for structural shape and execution order.

The registry's normative rule is the minimal fix: every distance claim must be written as
`distance(metric_layer=<layer>, from=<id>, to=<id>, value=<float>, units=<string>)`, with
`metric_layer` drawn from a fixed enum (`area_sphere`, `family_graph`, `hex_graph`, `gcs_surface`,
`ipow_volume`, `concept_graph`, `state_gram`). This is the same "name the layer you're operating in"
discipline applied to concept resolution (Dict A vs Dict B) and to hex vs. family vs. area, now
extended to distance vocabulary specifically because it had drifted without anyone formalizing it.

`anchor_map_v1` is the frozen artifact this corner depends on for any cross-layer ("semantic ↔
geodesic") mapping: `runtime/services/anchor_map_registry.py` enforces, at load time, both that the
loaded map's ID matches `anchor_map_v1` *and* that its `status` field is literally `"FROZEN"` —
raising `ValueError` otherwise. This is the same freeze-and-verify pattern the lexicon corner uses
for Dict A/B, applied to the geometry-to-geometry mapping layer instead.

## What would break without it

Without a `metric_layer` qualifier, a path-action computation summing costs across area-sphere
geodesic distance, family zone cost, and hex hop count could silently add incommensurable
quantities (radians, zone-step units, hop counts) as if they were the same kind of number — the
path-action formula `S_path = Σ w(e)·ℓ(e)` only makes sense because each edge type's `ℓ(e)` is
explicitly defined per-layer in `24_SPEC §5`'s table, with layer-specific default weights absorbing
the unit mismatch. Without the frozen `anchor_map_v1` check, a semantic-hex-to-GCS-slot lookup could
run against a map that was mid-edit, silently producing a geometry computation that does not
correspond to any single coherent assignment.

## How it relates to neighbors

This corner is explicitly a thin service layer over geometry that already existed (see
`corners/topology_geometry.md`, `corners/hex_substrate.md`): `24_SPEC §4.1` names
`sphere/topology/embedding.py` directly as the `area_sphere` implementation; `§4.2` builds on
`family_embedding.py`'s zone keys; `§4.3` is the hex substrate's adjacency graph. The spec is
careful to scope out what it is *not*: "Einstein field equations; clinical interpretation of IPoW;
DB migration to 251 semantic hex rows; Poisson solver" — explicitly deferring `HESPERIA_GCS_EMIT=1`,
full `interior_point_of_world_view` live emit, and `path_metric_cost` on traversal to "follow-on
rows," per `release/v0.7.0/RELEASE_SCOPE.md`. It is gated behind `HESPERIA_METRIC_EMIT` /
`HESPERIA_GCS_EMIT` env flags, shipping disabled by default — the same incremental, reversible
rollout discipline the sealed-release era (`corners/release_governance.md`) uses for everything
that touches canonical output.

## Wiring status found 2026-08-03 (Felix, productization gap-surfacing pass)

`tests/test_v7_engine_foundations.py` exercises this corner's four `runtime/services/` modules
end-to-end and, before this pass, 4 of its 6 tests failed — not because the modules were broken
(each is independently real, deterministic, and unit-tested in `tests/test_metric_22_26.py` /
`tests/test_family_graph.py`), but because none of them were ever called from the production
pipeline that owns the shape the test exercises:

- **Fixed this pass.** `meta.hesperia_metric` (§10.1's base block, `HESPERIA_METRIC_EMIT=1`) is
  explicitly listed as in-scope for v0.7.0 in `release/v0.7.0/RELEASE_SCOPE.md`, but
  `attach_hesperia_metric_meta` had **zero callers anywhere in the repo** — `git log` shows
  `hesperia_metric_emit.py` unchanged since the METRIC wave landed (`6596c6cf`); the attach call
  was simply never added at any consumer. It could not be wired from
  `sphere/router/engine_analyze_bridge.py` directly — `hesperia_metric_emit.py` lives in
  `runtime/services/`, and `tests/architecture/test_layer_dependencies.py::test_sphere_does_not_import_runtime`
  forbids that import direction (the same RAD rule this file's own docstring cites for why it was
  graduated to sphere in the first place). Fixed by attaching at `runtime/services/engine_analyze_contract.py`
  instead — the runtime-boundary re-export shim, which *can* import `runtime.services.*` — wrapping
  `build_engine_analyze_from_raw`/`run_engine_analyze` there. `sphere/router/pre_llm_compiler.py`
  and `audit.py`, which call the sphere-local function directly, correctly do **not** get the
  metric block (it is a runtime/external-contract concern, not something the internal LLM bridge
  needs).
- **Left failing on purpose, now `xfail(strict=True)`** with a citation to the scope doc: GCS
  `spacing_factor` into `hex_output_engine.build_sparse_hex_scene`'s distance matrix (METRIC-22),
  `path_metric_cost` on `serialize_hex_outputs` (METRIC-24/25), and IPoW in
  `multiscale_product_bridge`'s output (METRIC-23/HRES-04) — all three are the exact items
  `release/v0.7.0/RELEASE_SCOPE.md` names under "Deferred to follow-on rows (not blocking v0.7.0
  scope doc)." The modules these tests import (`path_metric.py`, `gcs_lookup.py`) are real and
  correct in isolation; only the traversal-time call site is genuinely unbuilt, matching the scope
  doc's own account. `strict=True` means the marker itself will fail loudly (not silently pass) the
  day someone actually builds the follow-on row and forgets to remove it — a live pointer to pick
  this work up, not a permanent excuse to ignore it.
