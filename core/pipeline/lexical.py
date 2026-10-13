"""Pipeline stage: lexical normalization and matching."""

from __future__ import annotations

from core.lexical.analysis_input import prepare_structural_analysis_text
from core.lexical.matcher import match_dict_a
from core.lexical.normalization import normalize_text

__all__ = ["prepare_structural_analysis_text", "normalize_text", "match_dict_a"]

