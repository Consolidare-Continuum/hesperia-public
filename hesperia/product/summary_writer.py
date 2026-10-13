# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Deterministic short summaries; tone modes: technical | executive | media."""

from __future__ import annotations

from typing import Any, Literal

from hesperia.product.schemas.innovation_radar_schema import InnovationRadarReport
from hesperia.product.schemas.narrative_monitor_schema import NarrativeMonitorReport
from hesperia.product.schemas.policy_detector_schema import PolicyDetectorReport

ToneMode = Literal["technical", "executive", "media"]


def _fmt(x: float, nd: int = 2) -> str:
    return f"{float(x):.{nd}f}"


def write_policy_summary(report: PolicyDetectorReport, mode: ToneMode = "executive") -> str:
    g = report.global_tension_score
    clusters = report.top_conflict_clusters or []
    triz = report.dominant_triz_patterns or []
    ca, cb = "n/a", "n/a"
    if clusters:
        c0 = clusters[0]
        ca = str(c0.get("family_a", c0.get("concept_a", "n/a")))
        cb = str(c0.get("family_b", c0.get("concept_b", "n/a")))
    top_triz = str(triz[0].get("triz_class", "parameter_change")) if triz else "parameter_change"
    if mode == "technical":
        return (
            f"Global tension index {_fmt(g)}. "
            f"Primary conflict locus: {ca} vs {cb}. "
            f"Dominant TRIZ resolution class: {top_triz}."
        )
    if mode == "media":
        return (
            f"Tension level {_fmt(g)} on a 0–1 scale. "
            f"Strongest clash involves {ca} and {cb}. "
            f"Main response pattern: {top_triz}."
        )
    return (
        f"Global tension score is {_fmt(g)}. "
        f"Top conflict cluster appears between {ca} and {cb}. "
        f"Dominant solution pattern: {top_triz}."
    )


def write_innovation_summary(report: InnovationRadarReport, mode: ToneMode = "executive") -> str:
    p = report.innovation_pressure_score
    rare = report.rare_clusters[:1]
    rc = len(report.rare_clusters)
    if mode == "technical":
        return (
            f"Innovation pressure (max cluster score) {_fmt(p)}. "
            f"Rare-structure clusters enumerated: {rc}."
        )
    if mode == "media":
        return (
            f"Novelty signal strength {_fmt(p)}. "
            f"{rc} unusual concept groupings flagged."
        )
    return (
        f"Innovation pressure score {_fmt(p)}. "
        f"{rc} rare combination clusters identified for review."
    )


def write_narrative_summary(report: NarrativeMonitorReport, mode: ToneMode = "executive") -> str:
    n0 = report.narratives[0] if report.narratives else {}
    pen = float(n0.get("penetration", 0))
    vel = float(n0.get("velocity", 0))
    stab = float(n0.get("stability", 0))
    blk = len(report.blocked_routes or [])
    if mode == "technical":
        return (
            f"Penetration {_fmt(pen)}, spread velocity {_fmt(vel)}, stability {_fmt(stab)}. "
            f"Blocked route endpoints: {blk}."
        )
    if mode == "media":
        return (
            f"Narrative reach {_fmt(pen)}; spread speed {_fmt(vel)}. "
            f"{blk} blockage points detected."
        )
    return (
        f"Narrative penetration {_fmt(pen)}, spread velocity {_fmt(vel)}, stability {_fmt(stab)}. "
        f"Blockage pressure appears at {blk} route endpoints."
    )


def apply_summaries(
    policy: PolicyDetectorReport | None,
    innovation: InnovationRadarReport | None,
    narrative: NarrativeMonitorReport | None,
    mode: ToneMode = "executive",
) -> None:
    if policy:
        policy.summary_text = write_policy_summary(policy, mode)
    if innovation:
        innovation.summary_text = write_innovation_summary(innovation, mode)
    if narrative:
        narrative.summary_text = write_narrative_summary(narrative, mode)
