# HESPERIA v0.7.0 — consolidated (METRIC + HRES research wave)

**Codename:** `v7_consolidated`  
**Baseline:** v0.6.0 sealed release  
**Authority:** `24_SPEC__Hesperia_Metric_and_Distance_v0_1.md`, Ethan Minkowski–IPoW SPEC §14

## What this release consolidates

Research → product wiring from the 2026-06-22 METRIC/HRES waves:

| Track | Deliverables in v0.7.0 |
|-------|------------------------|
| **METRIC** | Frozen `anchor_map_v1`, `hesperia_metric` emit, `metric_layer` contract, env flags |
| **HRES** | 24_SPEC §14 iteration geometry (`I²_n`, `powv_step`) on dev specs |
| **IPoV reconcile** | Single `anchor_map_id` across IPoV-01 code and METRIC registry |
| **Pedagogy** | Brain `physics_cosmology/` + `METRIC_research/` — docs only, not runtime physics |

## Include (incremental over v0.6.0)

- `schemas/anchor_map_v1.json` (FROZEN option A)
- `schemas/hesperia_metric_v01.json` + pytest
- `runtime/services/hesperia_metric_emit.py` with `HESPERIA_METRIC_EMIT=1`
- `docs/specs/24_SPEC__*`, `ENGINE-ANALYZE-CONTRACT.md` metric_layer sections
- `docs/specs/ANCHOR_MAP_IPOV_METRIC_RECONCILE.md`

## Deferred to follow-on rows (not blocking v0.7.0 scope doc)

- `HESPERIA_GCS_EMIT=1` static metric-geometry block (METRIC-22)
- Full `meta.interior_point_of_world_view` live emit (METRIC-23, HRES-04) — **implementation
  landed** internally (2026-08-04, drained from a Tersagor vendored copy that had it built but
  never merged upstream — same pattern as the KSI-Inspector drain). Full
  `InteriorPointOfWorldView` (ellipsoid geometry, geodesic distances, barycentric weights,
  coupling, provenance), distinct from the deliberately narrow PointZero-only stub already in
  the sealed GTP path. Still not wired into the live `/analyze` emit path — that wiring is the
  remaining METRIC-23 scope, tracked separately from this code landing.
- `path_metric_cost` on traversal (METRIC-24/25)

## Pin

- System version target: **0.7.0**
- `anchor_map_id`: **anchor_map_v1**
- Dict pack: inherit v0.6.0 external policy until calibration wave opens

**SIGNED: Developer (Gena) | v7_consolidated scope | 2026-06-23 | release planning**
