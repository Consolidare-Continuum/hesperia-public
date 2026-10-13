"""Deterministic text segmentation and trajectory helpers for DLCR (L4+)."""

from .segmentation import segment_by_newlines
from .trajectory import trajectory_over_segments

__all__ = ["segment_by_newlines", "trajectory_over_segments"]
