# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA Π (Pi) interpretation policy layer.
Defines analysis modes that constrain what interpretation layers (e.g. L8) are allowed to use.
Does not evaluate correctness (Θ does that); only defines interpretation permissions and constraints.
Deterministic.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Canonical mode names
STRUCTURE_ONLY = "STRUCTURE_ONLY"
STRUCTURE_PLUS_CONTEXT = "STRUCTURE_PLUS_CONTEXT"
FULL_INTERPRETATION = "FULL_INTERPRETATION"

POLICY_MODES = (STRUCTURE_ONLY, STRUCTURE_PLUS_CONTEXT, FULL_INTERPRETATION)

# Allowed/forbidden field names per mode (for documentation and downstream filtering)
_STRUCTURE_ONLY_ALLOWED = ["L1", "L2", "L6", "stability", "global_structure"]
_STRUCTURE_ONLY_FORBIDDEN = ["text", "tokens", "contextual_wording", "original_text", "token_sequences"]

_STRUCTURE_PLUS_CONTEXT_ALLOWED = ["L1", "L2", "L6", "L3", "L4", "L5", "L7", "stability", "global_structure", "text", "segment_text", "local_context"]
_STRUCTURE_PLUS_CONTEXT_FORBIDDEN = ["external_information", "narrative_extrapolation"]

_FULL_ALLOWED: List[str] = []  # no restriction list = all allowed
_FULL_FORBIDDEN: List[str] = []


def apply_interpretation_policy(state: Any, mode: str) -> Dict[str, Any]:
    """
    Return policy configuration for the given analysis mode.
    Input: PipelineState (used for consistency; policy is deterministic from mode only), mode string.
    Output: policy configuration for input.metadata["policy"] and L8 interpretation discipline.
    """
    mode = (mode or STRUCTURE_PLUS_CONTEXT).strip().upper()
    if mode not in POLICY_MODES:
        mode = STRUCTURE_PLUS_CONTEXT

    if mode == STRUCTURE_ONLY:
        interpretation_constraints = {
            "allow_text": False,
            "allow_context": False,
            "allow_structure": True,
        }
        allowed_fields = list(_STRUCTURE_ONLY_ALLOWED)
        forbidden_fields = list(_STRUCTURE_ONLY_FORBIDDEN)
    elif mode == STRUCTURE_PLUS_CONTEXT:
        interpretation_constraints = {
            "allow_text": True,
            "allow_context": True,
            "allow_structure": True,
        }
        allowed_fields = list(_STRUCTURE_PLUS_CONTEXT_ALLOWED)
        forbidden_fields = list(_STRUCTURE_PLUS_CONTEXT_FORBIDDEN)
    else:
        # FULL_INTERPRETATION: no restrictions
        interpretation_constraints = {
            "allow_text": True,
            "allow_context": True,
            "allow_structure": True,
        }
        allowed_fields = list(_FULL_ALLOWED) if _FULL_ALLOWED else []
        forbidden_fields = list(_FULL_FORBIDDEN)

    return {
        "policy_mode": mode,
        "allowed_fields": allowed_fields,
        "forbidden_fields": forbidden_fields,
        "interpretation_constraints": interpretation_constraints,
    }
