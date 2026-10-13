# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3 / v0.3.1 — failure classification.
19_SPEC Release v0.3 Structural Enforcement; 20_SPEC Runtime Guards and Failure Classes.
No free-form error logic; use only these classes.
"""

from enum import Enum, auto


class FailureClass(Enum):
    HARD_STOP = auto()
    DATA_REJECT = auto()
    DEGRADED_STATE = auto()
    WARN = auto()
