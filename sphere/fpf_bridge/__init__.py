# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Layer 11 — fpf-thinking-map bridge for LLM-bounded structural interpretation."""

from sphere.fpf_bridge.bridge import bridge_pipeline_result, bridge_to_llm_prompt
from sphere.fpf_bridge.llm_integration import (
    LlmInterpretConfig,
    MockLlmClient,
    interpret_prompt_state,
    interpret_structural_state,
)

__all__ = [
    "LlmInterpretConfig",
    "MockLlmClient",
    "bridge_pipeline_result",
    "bridge_to_llm_prompt",
    "interpret_prompt_state",
    "interpret_structural_state",
]
