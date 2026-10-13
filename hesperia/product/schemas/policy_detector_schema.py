# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PolicyDetectorReport:
    corpus_id: str
    generated_at: str
    global_tension_score: float
    top_conflict_clusters: list[dict]
    top_cross_domain_conflicts: list[dict]
    dominant_triz_patterns: list[dict]
    summary_text: str = ""
