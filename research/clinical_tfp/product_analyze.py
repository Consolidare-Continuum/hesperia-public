# HESPERIA — Spec path alias for product analysis (v0.5.8 task5).
# Canonical implementation: ``runtime/pipeline/analyze.py`` (``analyze()``).
# Extended output may include ``release_conflict_readiness`` (v0.5.8 task9); authoritative gating remains bundle inspect.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from runtime.pipeline.analyze import analyze

__all__ = ["analyze"]
