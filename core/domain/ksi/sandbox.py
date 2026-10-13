# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from typing import Mapping

from .expected_j import IncomingEdge, compute_expected_j, compute_residual


def replay_concept_residuals(
    concept_ids: list[str],
    incoming_edges: list[IncomingEdge],
    activations: Mapping[str, float],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for cid in concept_ids:
        expected = compute_expected_j(cid, incoming_edges, activations)
        observed = float(activations.get(cid, 0.0))
        out[cid] = compute_residual(expected, observed)
    return out


def sandbox_residual_improved(
    residual_before: float,
    residual_after: float,
    *,
    incident_concept: str,
    all_before: Mapping[str, float],
    all_after: Mapping[str, float],
    tau_sandbox: float = 0.25,
) -> bool:
    if residual_after >= residual_before:
        return False
    for cid, before in all_before.items():
        if cid == incident_concept:
            continue
        after = float(all_after.get(cid, before))
        if abs(after - float(before)) > tau_sandbox:
            return False
    return True
