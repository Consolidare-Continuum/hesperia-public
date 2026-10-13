# HESPERIA agentic-bridge feature flags (spec: fpf_bridge_v7_3_agentic_cursor_interface.md §6).
from __future__ import annotations

import os


def bridge_enabled() -> bool:
    return os.environ.get("HESPERIA_MCP_BRIDGE_ENABLED", "0").strip() in ("1", "true", "yes", "on")


def act_enabled() -> bool:
    """Phase B (attempt_hesperia_transition) — separate, higher-tier flag. Not built yet."""
    return os.environ.get("HESPERIA_MCP_BRIDGE_ACT_ENABLED", "0").strip() in ("1", "true", "yes", "on")


def real_data_enabled() -> bool:
    """Gates whether real (non-synthetic) input may flow through either tool — independent of
    the two flags above being on for dev/synthetic testing. Stays False until the security
    review (spec §3) and, for COBALT-branch queries, fpf_bridge_v7_4's corpus scale-up (spec §7)
    have both passed. Nothing in this module flips it — it is a manual, reviewed switch."""
    return os.environ.get("HESPERIA_MCP_BRIDGE_REAL_DATA", "0").strip() in ("1", "true", "yes", "on")
