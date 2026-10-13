# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""TRIZ layer — shared dataclasses (matrix coordinates, signals, unified output)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MatrixCoordinate:
    area_id: int
    family_id: int
    hex_id: int | None = None


@dataclass
class ConceptActivation:
    concept_id: str
    activation: float
    coordinate: MatrixCoordinate


@dataclass
class ConceptRelation:
    source: str
    target: str
    relation_type: str
    weight: float = 1.0


@dataclass
class ContradictionSignal:
    concept_a: str
    concept_b: str
    score: float
    triz_class: str
    coord_a: MatrixCoordinate
    coord_b: MatrixCoordinate

    @property
    def area_cluster(self) -> list[int]:
        s: set[int] = set()
        if self.coord_a.area_id >= 0:
            s.add(self.coord_a.area_id)
        if self.coord_b.area_id >= 0:
            s.add(self.coord_b.area_id)
        return sorted(s)


# Legacy alias: code expecting .area_cluster as field uses property above
Contradiction = ContradictionSignal


@dataclass
class InnovationCluster:
    cluster_id: str
    concepts: list[str]
    rarity: float
    contradiction_density: float
    propagation_reach: float
    innovation_score: float


@dataclass
class NarrativeSignal:
    narrative_id: str
    activated_areas: list[int]
    penetration: float
    velocity: float
    stability: float


@dataclass
class TRIZSignals:
    """Single structured object for KME / pipeline attachment."""

    contradictions: list[ContradictionSignal]
    innovation_clusters: list[InnovationCluster]
    narratives: list[NarrativeSignal]
    narrative_routes: list[dict[str, Any]] = field(default_factory=list)
    direct_metrics: Any = None  # TRIZDirectMetrics — atomic numeric/structural outputs

    def to_dict(self) -> dict[str, Any]:
        def coord(c: MatrixCoordinate) -> dict[str, Any]:
            return {
                "area_id": c.area_id,
                "family_id": c.family_id,
                "hex_id": c.hex_id,
            }

        out: dict[str, Any] = {
            "contradictions": [
                {
                    "concept_a": c.concept_a,
                    "concept_b": c.concept_b,
                    "score": round(float(c.score), 6),
                    "triz_class": c.triz_class,
                    "coord_a": coord(c.coord_a),
                    "coord_b": coord(c.coord_b),
                    "area_cluster": list(c.area_cluster),
                }
                for c in sorted(
                    self.contradictions,
                    key=lambda x: (-x.score, x.concept_a, x.concept_b),
                )
            ],
            "innovation_clusters": [
                {
                    "cluster_id": cl.cluster_id,
                    "concepts": list(cl.concepts),
                    "rarity": round(float(cl.rarity), 6),
                    "contradiction_density": round(float(cl.contradiction_density), 6),
                    "propagation_reach": round(float(cl.propagation_reach), 6),
                    "innovation_score": round(float(cl.innovation_score), 6),
                }
                for cl in sorted(
                    self.innovation_clusters,
                    key=lambda x: (-x.innovation_score, x.cluster_id),
                )
            ],
            "narratives": [
                {
                    "narrative_id": n.narrative_id,
                    "activated_areas": list(n.activated_areas),
                    "penetration": round(float(n.penetration), 6),
                    "velocity": round(float(n.velocity), 6),
                    "stability": round(float(n.stability), 6),
                }
                for n in sorted(self.narratives, key=lambda x: x.narrative_id)
            ],
            "narrative_routes": list(self.narrative_routes),
        }
        if self.direct_metrics is not None:
            dm = self.direct_metrics
            out["atomic_metrics"] = dm.to_dict()
            out["primary_signals"] = {
                "contradiction_score_peak": round(max(dm.contradiction_scores), 6)
                if dm.contradiction_scores
                else 0.0,
                "contradiction_count": dm.contradiction_count,
                "contradiction_density": round(dm.contradiction_density, 6),
                "innovation_score": round(dm.innovation_score, 6),
                "innovation_pressure": round(dm.innovation_pressure, 6),
                "narrative_penetration": round(dm.narrative_penetration, 6),
                "propagation_velocity": round(dm.propagation_velocity, 6),
                "semantic_pressure": round(dm.semantic_pressure, 6),
                "domain_coupling_aggregate": round(
                    float(dm.domain_coupling.get("aggregate_cross_area_edge_rate", 0.0)), 6
                ),
                "area_activation": dict(dm.area_activation),
                "activation_energy": round(dm.activation_energy, 6),
            }
        return out


# Backward compat: run_triz_layer historically returned TRIZReport
TRIZReport = TRIZSignals
