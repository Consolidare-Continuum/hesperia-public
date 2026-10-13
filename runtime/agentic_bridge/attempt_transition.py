# HESPERIA agentic-bridge — attempt_hesperia_transition (spec: fpf_bridge_v7_3 §1.2, Phase B).
#
# In-process function only — same scope boundary as get_state.py. Deploying as a real MCP tool
# is Phase 2 (Olga's repo/account), not this module's job.
#
# Uses fpf_thinking_map's own ThinkingMapTraversal.attempt_transition directly — no wrapper logic
# re-implementing gate/evidence checks. One honest correction versus the original spec draft:
# GatePrimitive.evaluate() in the installed fpf-thinking-map version never actually returns
# GateDecision.BLOCK (only ABSTAIN/DEGRADE/PASS — verified by reading primitives.py directly).
# attempt_transition() *does* correctly special-case BLOCK if a gate ever produces it, so this
# function is honest about what's real today: ABSTAIN (missing evidence, wrong state, or unknown
# transition) and COLLECT_EVIDENCE (evidence gap) are the two enforcement outcomes you'll actually
# see; BLOCK is wired end-to-end but dormant until some gate implementation actually emits it.

from __future__ import annotations

from typing import Any, Literal

from sphere.fpf_bridge.bridge import bridge_pipeline_result

from runtime.agentic_bridge.flags import act_enabled
from runtime.agentic_bridge.get_state import VALID_BRANCHES, Branch


class BridgeActDisabledError(RuntimeError):
    """Raised when HESPERIA_MCP_BRIDGE_ACT_ENABLED is not set."""


def attempt_hesperia_transition(
    result: dict[str, Any],
    *,
    branch: Branch,
    transition_id: str,
) -> dict[str, Any]:
    """Validate one named transition against its gate/evidence requirements. Never mutates
    anything — re-runs the deterministic bridge on `result` and asks whether `transition_id`
    is currently legal, same computation bridge_pipeline_result already does internally for its
    own `initial_outcome`, just addressable one transition at a time.

    Stateless by construction (spec §2): calling this twice with the same `result` and
    `transition_id` always returns the same outcome — there is no session to drift.
    """
    if branch not in VALID_BRANCHES:
        raise ValueError(f"branch must be one of {VALID_BRANCHES}, got {branch!r}")
    if not act_enabled():
        raise BridgeActDisabledError(
            "HESPERIA_MCP_BRIDGE_ACT_ENABLED is not set — Phase B is off by default (spec §6)."
        )

    traversal, state = bridge_pipeline_result(result)
    outcome = traversal.attempt_transition(state, transition_id)

    return {
        "branch": branch,
        "transition_id": transition_id,
        **outcome.to_dict(),
    }
