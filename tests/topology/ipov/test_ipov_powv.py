"""
IPoV-07 — Gold tests: fixed surface path → expected r, distances.

Tests use deterministic, no-external-dependency inputs.
All assertions are against analytically known values.
"""
from __future__ import annotations

import math
import pytest

from sphere.topology.ipov.anchor_map import (
    ANCHOR_MAP,
    ANCHOR_MAP_ID,
    AREA_RING,
    GeodesicConstants,
    GCS,
    build_anchor_map,
    geodesic_hex_count_for_family,
)
from sphere.topology.ipov.powv import (
    PoWVState,
    InteriorPointOfWorldView,
    compute_powv_step,
    powv_point_zero,
)
from sphere.topology.ipov.surface_events import (
    SurfaceEvent,
    SurfaceEventType,
    EventBatch,
)
from sphere.topology.ipov.session_export import (
    powv_to_pov_block,
    PoWVSessionExport,
)


# ---------------------------------------------------------------------------
# GeodesicConstants invariants
# ---------------------------------------------------------------------------

class TestGeodesicConstants:
    def test_hex_count_formula(self):
        gcs = GeodesicConstants()
        assert gcs.hex_count == 10 * gcs.frequency_nu ** 2 - 10

    def test_total_faces(self):
        gcs = GeodesicConstants()
        assert gcs.total_faces == gcs.hex_count + gcs.pentagon_count

    def test_delta_hex(self):
        gcs = GeodesicConstants()
        assert gcs.delta_hex == gcs.hex_count - gcs.semantic_hex_count

    def test_family_split_check(self):
        # 240×251 + 48×250 = 72,240
        gcs = GeodesicConstants()
        assert gcs.families_251 * 251 + gcs.families_250 * 250 == gcs.hex_count

    def test_scale_factor_sigma(self):
        gcs = GeodesicConstants()
        assert abs(gcs.scale_factor_sigma - 72240 / 72000) < 1e-9

    def test_sides_count(self):
        gcs = GeodesicConstants()
        assert gcs.sides_count == gcs.hex_count * 6


# ---------------------------------------------------------------------------
# AnchorMap invariants
# ---------------------------------------------------------------------------

class TestAnchorMap:
    def test_anchor_map_id_matches_metric_registry(self):
        assert ANCHOR_MAP_ID == "anchor_map_v1"

    def test_area_ring_length(self):
        assert len(AREA_RING) == 12

    def test_area_ring_contains_known_areas(self):
        for area in ["GOOD", "HARM", "TRUTH", "FREEDOM", "ORDER", "CHAOS"]:
            assert area in AREA_RING

    def test_area_directions_unit_vectors(self):
        for i, d in enumerate(ANCHOR_MAP.area_directions):
            n = math.sqrt(sum(x ** 2 for x in d))
            assert abs(n - 1.0) < 1e-9, f"area {i} not unit: {n}"

    def test_area_directions_equatorial(self):
        # All area anchors on equatorial ring → z ≈ 0
        for d in ANCHOR_MAP.area_directions:
            assert abs(d[2]) < 1e-9

    def test_family_directions_unit_vectors(self):
        for i in range(12):
            for j in range(24):
                d = ANCHOR_MAP.family_directions[i][j]
                n = math.sqrt(sum(x ** 2 for x in d))
                assert abs(n - 1.0) < 1e-9, f"family ({i},{j}) not unit: {n}"

    def test_family_count(self):
        total = sum(len(ANCHOR_MAP.family_directions[i]) for i in range(12))
        assert total == 288

    def test_pentagon_directions_unit_vectors(self):
        for p, d in enumerate(ANCHOR_MAP.pentagon_directions):
            n = math.sqrt(sum(x ** 2 for x in d))
            assert abs(n - 1.0) < 1e-9, f"pentagon {p} not unit: {n}"

    def test_pentagon_count(self):
        assert len(ANCHOR_MAP.pentagon_directions) == 12

    def test_geodesic_hex_count_family_rule(self):
        # indices 0,6,12,18 → 250; all others → 251
        for j in range(24):
            expected = 250 if j % 6 == 0 else 251
            assert geodesic_hex_count_for_family(j) == expected

    def test_family_split_total(self):
        count_250 = sum(1 for i in range(12) for j in range(24) if geodesic_hex_count_for_family(j) == 250)
        count_251 = sum(1 for i in range(12) for j in range(24) if geodesic_hex_count_for_family(j) == 251)
        assert count_250 == 48
        assert count_251 == 240
        assert count_250 * 250 + count_251 * 251 == GCS.hex_count

    def test_global_family_id_roundtrip(self):
        for i in range(12):
            for j in range(24):
                gid = ANCHOR_MAP.global_family_id(i, j)
                ai, fi = ANCHOR_MAP.area_family_from_global(gid)
                assert ai == i
                assert fi == j

    def test_area_directions_evenly_spaced(self):
        # Adjacent area anchors should be separated by 30° (π/6)
        dirs = ANCHOR_MAP.area_directions
        expected_angle = 2 * math.pi / 12
        for i in range(12):
            a = dirs[i]
            b = dirs[(i + 1) % 12]
            dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
            angle = math.acos(max(-1.0, min(1.0, dot)))
            assert abs(angle - expected_angle) < 1e-9, f"areas {i},{(i+1)%12}: angle={math.degrees(angle):.3f}°"


# ---------------------------------------------------------------------------
# PoWV — point zero state
# ---------------------------------------------------------------------------

class TestPoWVPointZero:
    def test_point_zero_position(self):
        state, snap = powv_point_zero()
        assert snap.r_x == 0.0
        assert snap.r_y == 0.0
        assert snap.r_z == 0.0
        assert snap.point_zero is True

    def test_point_zero_step_is_one(self):
        _, snap = powv_point_zero()
        # First step increments step counter to 1 (from initial 0)
        assert snap.step == 1

    def test_point_zero_all_area_distances_equal(self):
        # At r=(0,0,0) on unit sphere all areas at distance 1.0
        _, snap = powv_point_zero()
        for e in snap.area_distances:
            assert abs(e.d - 1.0) < 1e-9, f"area {e.area_id}: d={e.d}"

    def test_point_zero_uniform_relative_distances(self):
        _, snap = powv_point_zero()
        expected = 1.0 / 12.0
        for e in snap.area_distances:
            assert abs(e.d_relative - expected) < 1e-9

    def test_point_zero_barycentric_uniform(self):
        _, snap = powv_point_zero()
        assert len(snap.barycentric_areas) == 12
        for w in snap.barycentric_areas:
            assert abs(w - 1.0 / 12.0) < 1e-6

    def test_point_zero_all_family_distances_present(self):
        _, snap = powv_point_zero()
        assert len(snap.family_distances) == 288

    def test_point_zero_all_pentagon_distances_present(self):
        _, snap = powv_point_zero()
        assert len(snap.pentagon_distances) == 12

    def test_point_zero_provenance(self):
        _, snap = powv_point_zero()
        assert snap.provenance.update_mode == "point_zero"


# ---------------------------------------------------------------------------
# PoWV — deterministic step
# ---------------------------------------------------------------------------

class TestComputePoWVStep:
    def _good_direction(self):
        """Unit direction toward GOOD area (area index 0, angle=0)."""
        return ANCHOR_MAP.area_directions[0]

    def test_single_event_moves_toward_area(self):
        state = PoWVState(lambda_gain=0.10)
        s = self._good_direction()
        new_state, snap = compute_powv_step(state, [(s, 1.0)])
        # After one step toward (1,0,0): r should have positive x
        assert new_state.x > 0.0
        assert snap.point_zero is False

    def test_no_events_preserves_position(self):
        state = PoWVState(x=0.3, y=0.0, z=0.0, lambda_gain=0.10)
        new_state, snap = compute_powv_step(state, [])
        assert abs(new_state.x - 0.3) < 1e-9
        assert abs(new_state.y) < 1e-9

    def test_position_stays_in_unit_ball(self):
        state = PoWVState(lambda_gain=0.9)  # aggressive gain
        s = self._good_direction()
        for _ in range(20):
            state, snap = compute_powv_step(state, [(s, 1.0)])
        assert state.norm() <= 1.0 + 1e-9

    def test_step_counter_increments(self):
        state = PoWVState()
        state, snap = compute_powv_step(state, [])
        assert state.step == 1
        state, snap = compute_powv_step(state, [])
        assert state.step == 2

    def test_deterministic_same_inputs(self):
        s = self._good_direction()
        state1 = PoWVState(lambda_gain=0.10)
        state2 = PoWVState(lambda_gain=0.10)
        ns1, snap1 = compute_powv_step(state1, [(s, 0.5)])
        ns2, snap2 = compute_powv_step(state2, [(s, 0.5)])
        assert abs(ns1.x - ns2.x) < 1e-12
        assert abs(snap1.r_x - snap2.r_x) < 1e-12

    def test_opposite_pull_moves_away(self):
        # Start near GOOD (positive x), pull toward HARM (area 1, angle=30°)
        state = PoWVState(x=0.5, y=0.0, z=0.0, lambda_gain=0.5)
        # HARM direction is at 30° from x-axis
        harm_dir = ANCHOR_MAP.area_directions[1]
        new_state, _ = compute_powv_step(state, [(harm_dir, 1.0)])
        # x should decrease slightly (HARM pulls from +x toward (cos30°, sin30°,0))
        assert new_state.y > 0.0  # HARM has positive y component

    def test_area_distances_at_moved_position(self):
        # Pull strongly toward GOOD area → GOOD should have smallest distance
        state = PoWVState(lambda_gain=0.5)
        s = ANCHOR_MAP.area_directions[0]  # GOOD
        for _ in range(10):
            state, snap = compute_powv_step(state, [(s, 1.0)])
        # GOOD (area 0) should be closest area
        min_entry = min(snap.area_distances, key=lambda e: e.d)
        assert min_entry.area_id == "GOOD"

    def test_update_mode_set_on_event(self):
        state = PoWVState()
        s = self._good_direction()
        new_state, snap = compute_powv_step(state, [(s, 1.0)])
        assert snap.provenance.update_mode == "surface_event"


# ---------------------------------------------------------------------------
# SurfaceEvent → EventBatch → event_vectors
# ---------------------------------------------------------------------------

class TestSurfaceEventBatch:
    def test_traversal_event_generates_vector(self):
        ev = SurfaceEvent(event_type=SurfaceEventType.TRAVERSAL, step=1, area_id="GOOD")
        batch = EventBatch(events=[ev])
        vecs = batch.to_event_vectors()
        assert len(vecs) >= 1
        # All directions are unit vectors
        for s, w in vecs:
            n = math.sqrt(sum(x ** 2 for x in s))
            assert abs(n - 1.0) < 1e-9

    def test_guard_block_negative_weight(self):
        ev = SurfaceEvent(
            event_type=SurfaceEventType.GUARD_BLOCK,
            step=1,
            area_id="HARM",
            guard_events=["guard_1"],
        )
        batch = EventBatch(events=[ev])
        vecs = batch.to_event_vectors()
        assert len(vecs) >= 1
        assert any(w < 0 for _, w in vecs)

    def test_unknown_area_ignored(self):
        ev = SurfaceEvent(event_type=SurfaceEventType.TRAVERSAL, step=1, area_id="UNKNOWN_AREA")
        batch = EventBatch(events=[ev])
        vecs = batch.to_event_vectors()
        assert len(vecs) == 0

    def test_empty_batch_empty_vectors(self):
        batch = EventBatch(events=[])
        assert batch.to_event_vectors() == []

    def test_activation_event_weights(self):
        ev = SurfaceEvent(
            event_type=SurfaceEventType.ACTIVATION,
            step=1,
            activation_slice={"GOOD": 0.8, "HARM": 0.2},
        )
        batch = EventBatch(events=[ev])
        vecs = batch.to_event_vectors()
        assert len(vecs) == 2
        weights = {round(w, 1) for _, w in vecs}
        assert 0.8 in weights
        assert 0.2 in weights

    def test_traversal_payload_path_metric_on_area_crossing(self):
        batch = EventBatch(
            events=[
                SurfaceEvent(
                    event_type=SurfaceEventType.TRAVERSAL,
                    step=1,
                    area_id="GOOD",
                    global_id=0,
                ),
                SurfaceEvent(
                    event_type=SurfaceEventType.TRAVERSAL,
                    step=2,
                    area_id="HARM",
                    global_id=24,
                ),
            ]
        )
        payload = batch.to_traversal_payload()
        assert payload["path_metric_cost"] > 0.0
        assert "area_sphere" in payload["path_metric_layers"]
        assert payload["path_action_version"] == "0.1"

    def test_empty_batch_zero_path_metric(self):
        payload = EventBatch(events=[]).to_traversal_payload()
        assert payload["path_metric_cost"] == 0.0
        assert payload["path_metric_layers"] == []


# ---------------------------------------------------------------------------
# Session export
# ---------------------------------------------------------------------------

class TestSessionExport:
    def test_pov_block_from_point_zero(self):
        _, snap = powv_point_zero()
        block = powv_to_pov_block(snap)
        assert block.r_x == 0.0
        assert block.point_zero is True
        assert len(block.barycentric_areas) == 12
        assert len(block.nearest_areas) == 3

    def test_session_export_accumulates(self):
        export = PoWVSessionExport()
        state = PoWVState()
        for _ in range(3):
            state, snap = compute_powv_step(state, [])
            export.record(snap)
        assert len(export.steps) == 3

    def test_inspector_strip_is_list_of_dicts(self):
        export = PoWVSessionExport()
        state, snap = powv_point_zero()
        export.record(snap)
        strip = export.to_inspector_strip()
        assert isinstance(strip, list)
        assert isinstance(strip[0], dict)
        assert "r_x" in strip[0]

    def test_latest_returns_last(self):
        export = PoWVSessionExport()
        state = PoWVState(lambda_gain=0.3)
        s = ANCHOR_MAP.area_directions[0]
        for _ in range(3):
            state, snap = compute_powv_step(state, [(s, 1.0)])
            export.record(snap)
        latest = export.latest()
        assert latest is not None
        assert latest.step == 3

    def test_reset_clears_steps(self):
        export = PoWVSessionExport()
        _, snap = powv_point_zero()
        export.record(snap)
        export.reset()
        assert export.steps == []
        assert export.latest() is None
