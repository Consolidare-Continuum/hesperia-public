# HESPERIA — GTP-06: path-discovery pipeline (wording -> surface).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Single deterministic entrypoint tying GTP-01..05 together per spec §10.3 flowchart:

    W -> phi -> L -> I -> D
    delta_powv -> Psi
    I, Psi, D -> G (GTPA)

This is the "path-discovery pipeline stub" GTP-06 calls for, and the function GTP-07
wires into the router envelope (sphere/router/pre_llm_compiler.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from sphere.topology.gtp.coherence import CoherenceField, compute_coherence_field
from sphere.topology.gtp.gtpa import GTPAResult, gtpa_next_hex
from sphere.topology.gtp.imprint import ImprintDifference, ThoughtImprint, build_thought_imprint, imprint_difference
from sphere.topology.gtp.ipow import POINT_ZERO, Vec3, point_zero_delta
from sphere.topology.gtp.neighbors import HexCell
from sphere.topology.gtp.rotation import input_features, select_hex_rotation


@dataclass(frozen=True)
class GtpStepResult:
    imprint: ThoughtImprint
    difference: ImprintDifference
    psi: CoherenceField
    gtpa: GTPAResult
    rotation_scores: dict[int, float]


def run_gtp_step(
    text: str,
    h: HexCell,
    *,
    powv_position: Vec3 = POINT_ZERO,
    baseline_area_id: int | None = None,
    baseline_global_id: int | None = None,
    prior_imprint: ThoughtImprint | None = None,
    path_template: dict[str, float] | None = None,
) -> GtpStepResult:
    """One deterministic GTP step for HexCell `h` given input wording `text`."""
    phi = input_features(text)
    hex_rotation, rotation_scores = select_hex_rotation(text)
    imprint = build_thought_imprint(h, phi, hex_rotation)
    diff = imprint_difference(
        imprint,
        baseline_area_id=baseline_area_id if baseline_area_id is not None else h.area_id,
        baseline_global_id=baseline_global_id if baseline_global_id is not None else h.global_id,
        prior=prior_imprint,
    )
    delta_powv = point_zero_delta(powv_position)
    psi = compute_coherence_field(delta_powv)
    gtpa_result = gtpa_next_hex(h, psi=psi, phi=phi, hex_rotation=hex_rotation, path_template=path_template)
    return GtpStepResult(
        imprint=imprint,
        difference=diff,
        psi=psi,
        gtpa=gtpa_result,
        rotation_scores=rotation_scores,
    )


def gtp_step_to_dict(result: GtpStepResult) -> dict:
    """Serialize for the `gtp_v0_1` registry block (schemas/gtp/gtp_v0_1.schema.json) and envelope wiring."""
    h = result.imprint.hex
    next_h = result.gtpa.next_hex
    return {
        "schema": "hesperia.gtp_v0_1",
        "hex_rotation": result.imprint.hex_rotation,
        "current_hex": {"area_id": h.area_id, "global_id": h.global_id, "hex_index": h.hex_index},
        "thought_imprint": {
            "fired_sides": list(result.imprint.fired_sides),
            "fired_operators": [op.value for op in result.imprint.fired_operators],
        },
        "imprint_difference": {
            "area_shifted": result.difference.area_shifted,
            "family_shifted": result.difference.family_shifted,
            "new_fired_sides": list(result.difference.new_fired_sides),
        },
        "coherence": {
            "psi_abs": result.psi.psi_abs,
            "psi_ent": result.psi.psi_ent,
            "psi_align": result.psi.psi_align,
            "vector_dim": len(result.psi.vector),
        },
        "gtpa": {
            "next_hex": {
                "area_id": next_h.area_id,
                "global_id": next_h.global_id,
                "hex_index": next_h.hex_index,
            },
            "exit_side": result.gtpa.exit_side,
            "hex_rotation": result.gtpa.hex_rotation,
            "score": result.gtpa.score,
        },
    }
