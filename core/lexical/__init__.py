"""DLCR lexical transform package."""

from .analysis_input import prepare_structural_analysis_text
from .normalization import normalize_text

__all__ = ["normalize_text", "prepare_structural_analysis_text"]

