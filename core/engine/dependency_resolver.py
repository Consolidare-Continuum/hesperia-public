"""Capability-based dependency resolution for modules."""

from __future__ import annotations

from typing import Any


def resolve_execution_order(modules: list[Any]) -> list[Any]:
    remaining = list(modules)
    available: set[str] = {"input.text", "input.signals"}
    ordered: list[Any] = []
    while remaining:
        progressed = False
        for module in list(remaining):
            requires = set(getattr(module, "requires", []))
            if requires.issubset(available):
                ordered.append(module)
                available.update(set(getattr(module, "provides", [])))
                remaining.remove(module)
                progressed = True
        if not progressed:
            missing = {
                getattr(m, "name", "unknown"): sorted(set(getattr(m, "requires", [])) - available) for m in remaining
            }
            raise ValueError(f"module_capability_unmet:{missing}")
    return ordered

