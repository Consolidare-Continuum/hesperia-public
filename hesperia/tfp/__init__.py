# HESPERIA — Compatibility shim for ``hesperia.tfp`` (E2E, NLP tests, pipeline).
# Stages/math load eagerly; clinical imports are lazy to avoid heavy chains on ``import hesperia.tfp``.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any

from hesperia.engine.tfp_math import TFP_STAGES, detect_tfp_stage, stage_from_timeline

__all__ = [
    "TFP_STAGES",
    "detect_tfp_stage",
    "detect_transference",
    "interpret_session",
    "run_session_topology",
    "stage_from_timeline",
    "transference_summary",
]


def __getattr__(name: str) -> Any:
    if name == "run_session_topology":
        from research.clinical_tfp.session_topology import run_session_topology as fn

        return fn
    if name == "interpret_session":
        from research.clinical_tfp.interpretation import interpret_session as fn

        return fn
    if name == "detect_transference":
        from research.clinical_tfp.transference_detection import detect_transference as fn

        return fn
    if name == "transference_summary":
        from research.clinical_tfp.transference_detection import transference_summary as fn

        return fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
