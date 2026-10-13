# HESPERIA agentic-bridge — get_hesperia_bridge_state (spec: fpf_bridge_v7_3 §1.1, Phase 1).
#
# In-process function only. Not yet an MCP tool — deploying it as one (Phase 2) means adding a
# launcher + registry entry in Olga's own repo, per her existing colombo-library MCP convention
# (spec §5). That's a separate-account, separate-repo step and stays out of this module's scope.
#
# Read-only against sphere: this wraps sphere.fpf_bridge.bridge.bridge_to_llm_prompt directly,
# no second implementation (same "no duplicate client" rule COBALT-10 established).

from __future__ import annotations

from typing import Any, Literal

from sphere.fpf_bridge.bridge import bridge_to_llm_prompt

from runtime.agentic_bridge.flags import bridge_enabled

Branch = Literal["tfp", "cobalt"]
VALID_BRANCHES = ("tfp", "cobalt")


class BridgeDisabledError(RuntimeError):
    """Raised when HESPERIA_MCP_BRIDGE_ENABLED is not set — no default fallback behavior."""


def get_hesperia_bridge_state(
    result: dict[str, Any],
    *,
    branch: Branch,
) -> dict[str, Any]:
    """Return bridge_to_llm_prompt()'s state for an external agent (Cursor) to reason over.

    `result` is a sphere pipeline result dict (same shape bridge_to_llm_prompt already expects).
    Phase 1 accepts a pre-built result rather than raw text + an engine call — wiring this to a
    live `/analyze` call is part of the Phase 2 deployment step, not this function's job.

    `branch` is required, no default, so a caller can never silently mix TFP/COBALT context.

    NOTE (known gap, not yet closed): v7.2 §3's per-evidence `context_scope` tagging is not yet
    implemented — EvidencePrimitive has no native field for it, and adding one needs either a
    wrapper/subclass over the library's frozen dataclass or reusing `context_id` with a
    branch-suffixed value. Until that lands, `branch` here labels the call as a whole, not each
    individual evidence item — do not read the returned evidence as already branch-tagged.
    """
    if branch not in VALID_BRANCHES:
        raise ValueError(f"branch must be one of {VALID_BRANCHES}, got {branch!r}")
    if not bridge_enabled():
        raise BridgeDisabledError(
            "HESPERIA_MCP_BRIDGE_ENABLED is not set — this tool is off by default (spec §6)."
        )

    state = bridge_to_llm_prompt(result)
    return {
        "branch": branch,
        "context_scope_note": "not yet per-evidence tagged — see module docstring",
        **state,
    }
