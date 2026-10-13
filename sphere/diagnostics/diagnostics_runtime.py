# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Diagnostics runtime: run all detectors in deterministic order and aggregate.
Execution order: anomaly → monotony → instability. No fuzzy deduplication.
"""

from __future__ import annotations

from typing import Any

from . import anomaly_detector, monotony_detector, instability_detector


def run_diagnostics(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Run anomaly, monotony, and instability detectors in order.
    Returns diagnostics list, diagnostic_codes, and registry (count, by_code, by_severity).
    """
    diagnostics: list[dict[str, Any]] = []
    # Deterministic order: anomaly, monotony, instability
    diagnostics.extend(anomaly_detector.detect_structural_anomalies(metrics, config))
    diagnostics.extend(monotony_detector.detect_structural_monotony(metrics, config))
    diagnostics.extend(instability_detector.detect_rhetorical_instability(metrics, config))

    diagnostic_codes = [d.get("diagnostic_code", "") for d in diagnostics]
    by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    by_code: dict[str, int] = {}
    for d in diagnostics:
        sev = d.get("severity", "medium")
        if sev in by_severity:
            by_severity[sev] += 1
        code = d.get("diagnostic_code", "")
        by_code[code] = by_code.get(code, 0) + 1

    return {
        "diagnostics": diagnostics,
        "diagnostic_codes": diagnostic_codes,
        "registry": {
            "count": len(diagnostics),
            "by_code": by_code,
            "by_severity": by_severity,
        },
    }
