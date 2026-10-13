# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Per-run_id signal history, smoothing, persistence filters (in-memory store)."""

from __future__ import annotations

from typing import Any

_HISTORY: dict[str, dict[str, list[Any]]] = {}


def update_signal_history(run_id: str, triz_report_dict: dict[str, Any]) -> None:
    """Append contradiction / innovation / narrative snapshots for run_id."""
    if run_id not in _HISTORY:
        _HISTORY[run_id] = {
            "contradictions": [],
            "innovation_scores": [],
            "narrative_penetration": [],
        }
    h = _HISTORY[run_id]
    h["contradictions"].append(triz_report_dict.get("contradictions") or [])
    cl = triz_report_dict.get("innovation_clusters") or []
    h["innovation_scores"].append(
        [float(x.get("innovation_score", 0)) for x in cl if isinstance(x, dict)]
    )
    nar = triz_report_dict.get("narratives") or []
    h["narrative_penetration"].append(
        [float(x.get("penetration", 0)) for x in nar if isinstance(x, dict)]
    )


def exponential_smooth_series(series: list[float], alpha: float = 0.3) -> list[float]:
    if not series:
        return []
    out = [series[0]]
    a = min(1.0, max(1e-9, alpha))
    for x in series[1:]:
        out.append(a * x + (1.0 - a) * out[-1])
    return out


def persistent_contradictions(
    run_id: str,
    *,
    min_runs: int = 3,
    key_fn: Any = None,
) -> list[str]:
    """Contradiction keys seen in >= min_runs snapshots."""
    if run_id not in _HISTORY:
        return []
    runs = _HISTORY[run_id]["contradictions"]
    if len(runs) < min_runs:
        return []
    from collections import Counter

    ctr: Counter[str] = Counter()
    for snap in runs[-32:]:
        if not isinstance(snap, list):
            continue
        keys: set[str] = set()
        for c in snap:
            if not isinstance(c, dict):
                continue
            k = f"{c.get('concept_a')}|{c.get('concept_b')}"
            keys.add(k)
        for k in keys:
            ctr[k] += 1
    return sorted([k for k, v in ctr.items() if v >= min_runs])


def persistent_narrative(
    run_id: str,
    *,
    threshold: float = 0.15,
    min_runs: int = 3,
) -> bool:
    if run_id not in _HISTORY:
        return False
    pens = _HISTORY[run_id]["narrative_penetration"]
    if len(pens) < min_runs:
        return False
    tail = pens[-min_runs:]
    return all(
        pens and all(float(p) >= threshold for p in (row or [0])) for row in tail if row
    )


def persistent_innovation_cluster(
    run_id: str,
    cluster_id: str,
    *,
    tolerance: float = 0.05,
    min_runs: int = 3,
) -> bool:
    if run_id not in _HISTORY:
        return False
    series_list = _HISTORY[run_id]["innovation_scores"]
    if len(series_list) < min_runs:
        return False
    # Without cluster id per score, use global mean stability
    flat = [s for row in series_list[-min_runs:] for s in (row or [])]
    if len(flat) < 2:
        return True
    mx, mn = max(flat), min(flat)
    return (mx - mn) <= tolerance


def clear_history(run_id: str) -> None:
    _HISTORY.pop(run_id, None)
