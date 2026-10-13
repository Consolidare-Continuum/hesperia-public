# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Internal metric keys → product-safe display names and per-product subsets."""

from __future__ import annotations

INTERNAL_TO_PRODUCT: dict[str, str] = {
    "contradiction_score": "Policy Tension Score",
    "contradiction_density": "Structural Tension Density",
    "innovation_score": "Innovation Pressure Score",
    "propagation_penetration": "Narrative Penetration Score",
    "spread_velocity": "Narrative Spread Velocity",
    "hex_pressure": "Semantic Pressure Index",
    "locality_score": "Conflict Locality Index",
    "hotspot_score": "Tension Hotspot Score",
    "path_score": "Route Strength",
    "contradiction_pressure": "Blockage Pressure",
    "stability": "Signal Stability",
    "rarity": "Combination Rarity",
    "propagation_reach": "Cross-Area Reach",
}

POLICY_DETECTOR_METRICS: frozenset[str] = frozenset(
    {
        "contradiction_score",
        "contradiction_density",
        "locality_score",
        "hotspot_score",
    }
)

POLICY_DETECTOR_LABELS: dict[str, str] = {
    "policy_tension": "Policy Tension Score",
    "conflict_cluster_count": "Conflict Cluster Count",
    "cross_domain_friction": "Cross-Domain Friction",
    "resolution_pattern_class": "Resolution Pattern Class",
}

INNOVATION_RADAR_LABELS: dict[str, str] = {
    "innovation_pressure": "Innovation Pressure Score",
    "rare_combination_rank": "Rare Combination Rank",
    "cross_area_reach": "Cross-Area Reach",
    "stability_over_time": "Stability Over Time",
}

NARRATIVE_MONITOR_LABELS: dict[str, str] = {
    "narrative_penetration": "Narrative Penetration Score",
    "spread_velocity": "Spread Velocity",
    "route_strength": "Route Strength",
    "blockage_pressure": "Blockage Pressure",
}


def product_name(internal_key: str) -> str:
    return INTERNAL_TO_PRODUCT.get(internal_key, internal_key.replace("_", " ").title())
