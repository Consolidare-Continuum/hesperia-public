# HESPERIA — FPF-BUII bottom-up inspect constants.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Layer ids, L6 live allowlist, GapReport schema id, provisional ADR tags."""

from __future__ import annotations

GAP_REPORT_SCHEMA = "hesperia.fpf_gap_report.v0_1"
INSPECT_SLICE_SCHEMA = "hesperia.fpf_inspect_slice.v0_1"
FPF_PIN_EXPECTED = "fpf-thinking-map==1.9.3"

# Dig order (SPEC §4) — climb emits slices in this sequence.
CLIMB_ORDER: tuple[str, ...] = (
    "L0",
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "L7",
    "L8",
    "L9",
    "GTP",
    "Guards",
    "Router",
)

# output_catalog.md §6 — only these may appear as EvidencePrimitive ids from L6.
L6_LIVE_FIELDS: frozenset[str] = frozenset(
    {
        "DEPTH_GROWTH_RATIO",
        "FIBONACCI_DEVIATION_SCORE",
        "LYAPUNOV_ESTIMATE",
        "GLOBAL_STABILITY_SCORE",
        "CONCEPTUAL_COHERENCE_INDEX",
    }
)

# Documented stubs — hard-excluded from evidence wrapping.
L6_STUB_FIELDS: frozenset[str] = frozenset(
    {
        "INPUT_PERTURBATION_RESPONSE",
        "DOMINANT_FAMILY_STABILITY",
        "COVERAGE_GRADIENT",
        "ENTROPY_GRADIENT",
        "STABILITY_RADIUS",
        "SECOND_ORDER_RESPONSE",
        "DOMINANCE_CURVATURE",
        "ENTROPY_CURVATURE",
        "HIT_VECTOR_RANK",
        "PRINCIPAL_COMPONENT_ENERGY_RATIO",
        "CONDITION_NUMBER",
        "SPECTRAL_GAP",
        "EXPONENTIAL_FIT_ERROR",
        "POWER_LAW_FIT_ERROR",
        "POTENTIAL_GRADIENT",
        "ESCAPE_ENERGY_THRESHOLD",
        "FORCE_ANALOG_MAGNITUDE",
        "MONOTONICITY_CHECK",
        "FIXED_POINT_DETECTION",
        "CYCLE_DETECTION_FUNCTIONAL",
    }
)

# Ethan ADRs FPF-HSR-02/03/04 — named provisional gaps (BUII-G3).
PROVISIONAL_HEX_ROTATION_R0 = "hex_rotation_r0_interim"
PROVISIONAL_40_POLICY = "40_policy_v0_placeholder"
PROVISIONAL_ANCHOR_MAP = "anchor_map_provisional"
