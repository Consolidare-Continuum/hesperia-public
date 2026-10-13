# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NarrativeMonitorReport:
    corpus_id: str
    generated_at: str
    narratives: list[dict]
    top_routes: list[dict]
    blocked_routes: list[dict]
    spillovers: list[dict]
    stability_summary: list[dict]
    summary_text: str = ""
