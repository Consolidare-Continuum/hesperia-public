"""Noise sensitivity harness for bounded deviation checks."""

from __future__ import annotations

from typing import Any, Callable


def perturbations(text: str) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    variants = [text]
    # word order noise
    if len(words) >= 3:
        variants.append(" ".join(words[:1] + words[2:3] + words[1:2] + words[3:]))
    # local synonym-style swap (light deterministic substitution)
    repl = text.replace("good", "fine").replace("bad", "poor")
    variants.append(repl)
    # punctuation/noise
    variants.append(text + " ...")
    return variants


def output_deviation(base: dict[str, Any], other: dict[str, Any]) -> float:
    keys = ("tension", "loopability", "stability")
    dev = 0.0
    for key in keys:
        dev += abs(float(base.get(key, 0.0)) - float(other.get(key, 0.0)))
    return dev / max(1, len(keys))


def run_noise_sensitivity(text: str, runner: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    variants = perturbations(text)
    baseline = runner(variants[0])
    deviations: list[float] = []
    for candidate in variants[1:]:
        out = runner(candidate)
        deviations.append(output_deviation(baseline, out))
    max_dev = max(deviations) if deviations else 0.0
    return {
        "variant_count": len(variants),
        "deviations": deviations,
        "max_deviation": max_dev,
        "stable": max_dev <= 0.35,
    }

