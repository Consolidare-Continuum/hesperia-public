#!/usr/bin/env python3
# HESPERIA — Main engine conceptual-math workflow runner.
# Canonical scope: main engine executable path only.

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_TEXT = os.environ.get("HESPERIA_MAIN_ENGINE_TEXT", "тест структурного анализа").strip() or "x"
_OUT = Path(
    os.environ.get(
        "HESPERIA_MAIN_ENGINE_OUT",
        str(_REPO / "assets/artifacts/e2e/run_output_main_engine_workflow.json"),
    )
)


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _run_once(text: str) -> dict[str, Any]:
    from runtime.services.analysis_service import run_structural_analysis

    assets = _REPO / "assets" / "lexicon" / "curated"
    return run_structural_analysis(text, assets_root=assets, stages="full")


def main() -> int:
    first = _run_once(_DEFAULT_TEXT)
    second = _run_once(_DEFAULT_TEXT)

    first_payload = first.get("payload") if isinstance(first.get("payload"), dict) else {}
    second_payload = second.get("payload") if isinstance(second.get("payload"), dict) else {}

    hash_first = _stable_hash(first_payload)
    hash_second = _stable_hash(second_payload)
    deterministic_ok = hash_first == hash_second

    out = {
        "run": "main_engine_workflow_v1",
        "canonical_path": [
            "runtime.services.analysis_service.run_structural_analysis",
            "core.engine.multiscale_product_bridge.build_structural_internal_from_multiscale",
            "core.engine.sealed_multiscale_stack.run_sealed_multiscale_stack",
            "core.engine.projection.project_to_public",
        ],
        "determinism": {
            "payload_hash_first": hash_first,
            "payload_hash_second": hash_second,
            "deterministic_payload": deterministic_ok,
        },
        "artifacts": {
            "first": first,
            "second": second,
        },
    }

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    print(f"main_engine_workflow_wrote={_OUT}")
    print(f"deterministic_payload={deterministic_ok}")
    return 0 if deterministic_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
