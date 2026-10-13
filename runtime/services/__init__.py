# HESPERIA — Runtime service façades.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Runtime service façades. Structural measurement entry point; calls sphere + core."""

from runtime.services.analysis_service import run_structural_analysis, run_structural_analysis_batch

__all__ = [
    "run_structural_analysis",
    "run_structural_analysis_batch",
]
