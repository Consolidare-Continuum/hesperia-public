# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""TRIZ analytics layer — isolated from KME core metrics."""

from hesperia.extensions.triz.exporters import (
    export_innovation_radar,
    export_narrative_monitor,
    export_policy_report,
)
from hesperia.extensions.triz.models import (
    ConceptActivation,
    ConceptRelation,
    Contradiction,
    ContradictionSignal,
    InnovationCluster,
    MatrixCoordinate,
    NarrativeSignal,
    TRIZReport,
    TRIZSignals,
)
from hesperia.extensions.triz.kme_bridge import (
    build_topology_from_activation_trace,
    run_triz_for_kme,
    topology_from_graph_coordinates,
)
from hesperia.extensions.triz.pipeline import (
    active_graph_from_payload,
    run_triz_analysis_complete,
    run_triz_layer,
    triz_report_to_dict,
)
from hesperia.extensions.triz.commercial_intelligence import (
    build_commercial_intelligence_bundle,
    commercial_intelligence_to_dict,
    compare_triz_corpora,
    extract_core_commercial_signals,
    extract_product_slice,
)
from hesperia.extensions.triz.direct_outputs import TRIZDirectMetrics, build_triz_direct_metrics, compare_triz_direct
from hesperia.extensions.triz.triz_pipeline import run_triz_analysis
from hesperia.extensions.triz.report_extractors import extract_triz_from_metric_report, extract_triz_summary
from hesperia.extensions.triz.topology_metrics import get_area_adjacency

__all__ = [
    "ConceptActivation",
    "ConceptRelation",
    "Contradiction",
    "ContradictionSignal",
    "InnovationCluster",
    "MatrixCoordinate",
    "NarrativeSignal",
    "TRIZReport",
    "TRIZSignals",
    "run_triz_analysis",
    "TRIZDirectMetrics",
    "build_triz_direct_metrics",
    "compare_triz_direct",
    "build_commercial_intelligence_bundle",
    "commercial_intelligence_to_dict",
    "compare_triz_corpora",
    "extract_core_commercial_signals",
    "extract_product_slice",
    "active_graph_from_payload",
    "run_triz_analysis_complete",
    "run_triz_layer",
    "triz_report_to_dict",
    "export_policy_report",
    "export_innovation_radar",
    "export_narrative_monitor",
    "build_topology_from_activation_trace",
    "run_triz_for_kme",
    "topology_from_graph_coordinates",
    "extract_triz_from_metric_report",
    "extract_triz_summary",
    "get_area_adjacency",
]
