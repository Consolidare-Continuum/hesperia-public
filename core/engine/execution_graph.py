"""Execution graph construction and cycle detection."""

from __future__ import annotations

from typing import Any

PHASES = ("preprocess", "project", "postprocess")


def _requires_for_phase(module: Any, phase: str) -> set[str]:
    req = getattr(module, "requires", {})
    if isinstance(req, dict):
        return set(req.get(phase, []))
    if isinstance(req, list):
        return set(req)
    return set()


def _provides_for_phase(module: Any, phase: str) -> set[str]:
    prov = getattr(module, "provides", {})
    if isinstance(prov, dict):
        return set(prov.get(phase, []))
    if isinstance(prov, list):
        return set(prov)
    return set()


def topological_sort_phase(modules: list[Any], phase: str, seed_available: set[str] | None = None) -> list[Any]:
    remaining = list(modules)
    ordered: list[Any] = []
    available = set(seed_available or {"input.text", "input.signals"})
    while remaining:
        progressed = False
        for m in list(remaining):
            if not bool(getattr(m, "capabilities", {}).get(phase, False)):
                ordered.append(m)
                remaining.remove(m)
                progressed = True
                continue
            req = _requires_for_phase(m, phase)
            if req.issubset(available):
                ordered.append(m)
                available.update(_provides_for_phase(m, phase))
                remaining.remove(m)
                progressed = True
        if not progressed:
            missing = {getattr(m, "name", "?"): sorted(_requires_for_phase(m, phase) - available) for m in remaining}
            raise ValueError(f"execution_graph_cycle_or_unmet:{phase}:{missing}")
    return ordered


def build_execution_graph(modules: list[Any]) -> dict[str, list[Any]]:
    graph: dict[str, list[Any]] = {}
    available = {"input.text", "input.signals"}
    for phase in PHASES:
        ordered = topological_sort_phase(modules, phase, seed_available=available)
        graph[phase] = ordered
        for m in ordered:
            if bool(getattr(m, "capabilities", {}).get(phase, False)):
                available.update(_provides_for_phase(m, phase))
    return graph

