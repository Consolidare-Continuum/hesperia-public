# HESPERIA — Invariant TFP activation (compat entry point).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Canonical implementation lives in ``hesperia.nlp.invariant_activation`` (engine runtime bundle).
# This module re-exports ``build_invariant_tfp_activation`` for legacy imports and tests.

from __future__ import annotations

from hesperia.nlp.invariant_activation import build_invariant_activation as build_invariant_tfp_activation

__all__ = ["build_invariant_tfp_activation"]
