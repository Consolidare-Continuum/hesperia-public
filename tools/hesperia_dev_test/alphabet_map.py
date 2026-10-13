# HESPERIA — hesperia-dev-test alphabet activation map. Copyright © 2026 igareosh.com.
"""Indexed-not-named activation surface: for each bare Latin letter a-z, calls the same
runtime.services.engine_analyze_contract.run_engine_analyze(...) the sealed /analyze endpoint
itself uses (runtime/shipping/api_main.py) and records only the numeric/opaque
dominant_area_id / dominant_family_id / dominant_concept_id fields it already returns — no
dictionary content, no concept names, no lexicon reads of our own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.hesperia_dev_test.corpus import letters

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_ROOT = _REPO_ROOT / "assets" / "lexicon" / "curated"


def letter_activation(letter: str) -> dict[str, Any]:
    from runtime.services.engine_analyze_contract import run_engine_analyze

    engine = run_engine_analyze(letter, assets_root=_ASSETS_ROOT)
    trace = engine.get("trace") or []
    top_activation = max((float(s.get("activation") or 0.0) for s in trace), default=0.0)
    return {
        "letter": letter,
        "area_id": engine.get("dominant_area_id"),
        "family_id": engine.get("dominant_family_id"),
        "concept_id": engine.get("dominant_concept_id"),
        "trace_len": len(trace),
        "top_activation": top_activation,
    }


def build_alphabet_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in letters():
        try:
            out[entry.token] = letter_activation(entry.token)
        except Exception as exc:  # noqa: BLE001
            out[entry.token] = {"letter": entry.token, "error": f"{type(exc).__name__}: {exc}"}
    return out


def summarize(alphabet_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    areas: dict[str, int] = {}
    for v in alphabet_map.values():
        area_id = v.get("area_id")
        if area_id:
            areas[area_id] = areas.get(area_id, 0) + 1
    return {
        "n_letters": len(alphabet_map),
        "n_errors": sum(1 for v in alphabet_map.values() if v.get("error")),
        "area_distribution": dict(sorted(areas.items())),
    }
