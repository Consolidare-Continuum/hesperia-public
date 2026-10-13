# GTP-02/GTP-07 — Pydantic schema classes (gtp_v0_1 registry, iteration bundle blocks).
# Ported from tersagor_agent.hesperia.gtp.schemas' TestGTPSchemas 2026-08-04 (HWIKI/core-domain drain).
# Complementary to test_gtp_schema.py, which validates the raw JSON Schema file against a fixture —
# this file tests the Pydantic model classes in sphere/topology/gtp/schemas.py directly.

from __future__ import annotations

from sphere.topology.gtp.schemas import (
    GTP_FIXTURE,
    GtpIterationBundle,
    GtpSideSpecSchema,
    GtpV0_1,
)
from sphere.topology.gtp.side_operators import SIDE_SPECS as GTP_SIDE_TABLE


class TestGTPSchemas:
    def test_fixture_has_six_side_specs(self):
        assert len(GTP_FIXTURE.side_specs) == 6

    def test_fixture_fara_reserved(self):
        assert len(GTP_FIXTURE.semantic_reserved) == 1
        assert GTP_FIXTURE.semantic_reserved[0].id == "FARA"
        assert GTP_FIXTURE.semantic_reserved[0].stateless is True
        assert GTP_FIXTURE.semantic_reserved[0].side_id is None

    def test_fixture_point_zero_delta_zero(self):
        d = GTP_FIXTURE.point_zero_delta
        assert d["x"] == 0.0
        assert d["y"] == 0.0
        assert d["z"] == 0.0

    def test_fixture_side_ids_match(self):
        for spec in GTP_FIXTURE.side_specs:
            assert 0 <= spec.side_id <= 5

    def test_fixture_logical_matches_table(self):
        for spec in GTP_FIXTURE.side_specs:
            table_spec = GTP_SIDE_TABLE[spec.side_id]
            assert spec.logical == table_spec.logical.value

    def test_fixture_semantic_matches_table(self):
        for spec in GTP_FIXTURE.side_specs:
            table_spec = GTP_SIDE_TABLE[spec.side_id]
            assert spec.semantic_ro == table_spec.semantic.ro

    def test_gtp_iteration_bundle_defaults(self):
        bundle = GtpIterationBundle()
        assert bundle.schema_name == "gtp_iteration_bundle_v0_1"
        assert bundle.psi_scalar == 0.0
        assert bundle.chosen_area_id == ""
