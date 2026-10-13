# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from core.engine.output_readout import band_for_value, format_scalar_readout


def test_band_for_value_unit_interval_edges() -> None:
    assert band_for_value(0.0) == "very_low"
    assert band_for_value(0.14) == "very_low"
    assert band_for_value(0.15) == "low"
    assert band_for_value(0.5) == "moderate"
    assert band_for_value(0.85) == "very_high"


def test_format_scalar_readout_stable() -> None:
    r = format_scalar_readout(0.370376, precision=2)
    assert r["value_raw"] == 0.370376
    assert r["display_value"] == 0.37
    assert r["band"] == "moderate"
