# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# MOVED 2026-07-31: the real implementation now lives in core.math.hci_calibration —
# this module is a first-class dynamics extension of core, not the owner of this math.
# Re-exported for backward compatibility; existing imports from this path keep working.

from __future__ import annotations

from core.math.hci_calibration import (
    CalibrationCandidate,
    calibrate_parameter_grid,
    compute_hspr_calibration_index,
    evaluate_candidate,
    generate_candidate_grid,
)

__all__ = [
    "CalibrationCandidate",
    "compute_hspr_calibration_index",
    "generate_candidate_grid",
    "evaluate_candidate",
    "calibrate_parameter_grid",
]
