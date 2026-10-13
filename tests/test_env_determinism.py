# HESPERIA — TFP-GATE-A0: strict determinism preconditions when CI sets HESPERIA_STRICT_DETERMINISM=1.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import os


def test_pythonhashseed_zero_when_strict_determinism() -> None:
    """PYTHONHASHSEED must be 0 before interpreter start; CI/job must export it."""
    if os.environ.get("HESPERIA_STRICT_DETERMINISM") != "1":
        return
    assert os.environ.get("PYTHONHASHSEED") == "0", (
        "Set PYTHONHASHSEED=0 for deterministic str hash / dict order in strict runs "
        "(see docs/governance/TFP_ENV_DETERMINISM.md)."
    )
