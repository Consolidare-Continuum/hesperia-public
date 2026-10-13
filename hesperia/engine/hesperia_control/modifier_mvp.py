# Modifier MVP (HC-03) — pre-CD weight adjustment. Copyright © 2026 igareosh.com.
from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from hesperia.engine.hesperia_control.readonly_guard import assert_lexical_readonly


def apply_modifier_mvp_pre_cd(
    concept_weights: MutableMapping[str, float],
    *,
    negation_targets: Mapping[str, float] | None = None,
    damping_factor: float = 0.85,
) -> dict[str, Any]:
    """
    Pre-CD MVP: apply negation suppression and uniform damping to listed targets.

    negation_targets: concept_id -> suppression factor in [0, 1] (1 = full zero-out intent).
    Deterministic: sorted iteration by concept_id.
    """
    assert_lexical_readonly()
    negation_targets = negation_targets or {}
    trace: list[str] = []
    for cid in sorted(negation_targets.keys()):
        if cid not in concept_weights:
            continue
        sup = float(negation_targets[cid])
        sup = max(0.0, min(1.0, sup))
        old = float(concept_weights[cid])
        concept_weights[cid] = old * (1.0 - sup)
        trace.append(f"negation:{cid}:{old:.6f}->{concept_weights[cid]:.6f}")
    for cid in sorted(concept_weights.keys()):
        concept_weights[cid] = float(concept_weights[cid]) * damping_factor
        trace.append(f"damp:{cid}:{damping_factor}")
    return {"trace": trace, "damping_factor": damping_factor}
