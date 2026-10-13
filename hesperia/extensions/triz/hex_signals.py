# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Hex-level pressure from contradictions; peaks; temporal volatility."""

from __future__ import annotations

from typing import Any

from hesperia.extensions.triz.topology_binding import bind_concept_to_matrix


def aggregate_hex_pressure(
    active_hexes: dict[int, float] | None,
    contradictions: list[Any],
    concept_mapping: dict[str, Any],
) -> dict[int, float]:
    """
    hex_pressure[hex] = Σ contradiction_scores where concept endpoint touches hex.
    active_hexes optional baseline (added to pressure sum).
    """
    pressure: dict[int, float] = {}
    if active_hexes:
        for h, v in sorted(active_hexes.items()):
            pressure[int(h)] = float(v)
    for c in contradictions:
        for cid in (c.concept_a, c.concept_b):
            m = bind_concept_to_matrix(cid, concept_mapping)
            h = m.hex_id
            if h is None or h < 0:
                continue
            pressure[h] = pressure.get(h, 0.0) + float(c.score)
    return dict(sorted(pressure.items(), key=lambda x: x[0]))


def detect_hex_pressure_peaks(
    pressure: dict[int, float],
    concept_mapping: dict[str, Any],
    *,
    top_k: int = 32,
    min_pressure: float = 0.01,
) -> list[dict[str, Any]]:
    """Rank hexes by pressure; attach area/family from first concept mapping match for hex."""
    hex_to_af: dict[int, tuple[int, int]] = {}
    for cid, raw in sorted(concept_mapping.items()):
        m = bind_concept_to_matrix(cid, concept_mapping)
        hid = m.hex_id
        if hid is not None and hid >= 0 and hid not in hex_to_af and m.area_id >= 0:
            hex_to_af[hid] = (m.area_id, m.family_id)

    rows: list[dict[str, Any]] = []
    for hex_id, pr in sorted(pressure.items(), key=lambda x: (-x[1], x[0])):
        if pr < min_pressure:
            continue
        af = hex_to_af.get(hex_id, (-1, -1))
        rows.append(
            {
                "area": af[0],
                "family": af[1],
                "hex": int(hex_id),
                "pressure": round(float(pr), 6),
            }
        )
    return rows[:top_k]


def hex_volatility_index(
    pressure_prev: dict[int, float],
    pressure_curr: dict[int, float],
) -> dict[int, float]:
    """volatility = |current - previous| per hex (corpus batch delta)."""
    keys = sorted(set(pressure_prev) | set(pressure_curr))
    return {
        h: round(abs(float(pressure_curr.get(h, 0.0)) - float(pressure_prev.get(h, 0.0))), 6)
        for h in keys
        if abs(float(pressure_curr.get(h, 0.0)) - float(pressure_prev.get(h, 0.0))) > 1e-9
    }
