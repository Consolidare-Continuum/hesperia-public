# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Extract TRIZ slice from MetricReport for exports and downstream consumers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.domain.models import MetricReport


def extract_triz_from_metric_report(report: "MetricReport") -> dict[str, Any]:
    if report.triz_signals is None:
        return {}
    return {"triz": report.triz_signals.to_dict()}


def extract_triz_summary(report: "MetricReport") -> dict[str, Any]:
    """Counts only — minimal payload."""
    if report.triz_signals is None:
        return {"triz_enabled": False}
    t = report.triz_signals
    return {
        "triz_enabled": True,
        "contradiction_count": len(t.contradictions),
        "innovation_cluster_count": len(t.innovation_clusters),
        "narrative_count": len(t.narratives),
        "narrative_route_steps": len(t.narrative_routes),
    }
