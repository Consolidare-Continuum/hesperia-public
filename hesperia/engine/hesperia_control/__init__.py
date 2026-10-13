# Hesperia control layer (HC program) — deterministic helpers. Copyright © 2026 igareosh.com.
"""MVP modules for HC-01 … HC-10 tasking. Ref: cursor ETHAN-HESPERIA-CONTROL-LAYER-V1-TASKING."""

from hesperia.engine.hesperia_control.dominance import classify_segment_dominance
from hesperia.engine.hesperia_control.modifier_mvp import apply_modifier_mvp_pre_cd
from hesperia.engine.hesperia_control.readonly_guard import assert_lexical_readonly
from hesperia.engine.hesperia_control.unmapped_diagnostics import UnmappedDiagnosticsReport, rank_unmapped_tokens

__all__ = [
    "apply_modifier_mvp_pre_cd",
    "assert_lexical_readonly",
    "classify_segment_dominance",
    "rank_unmapped_tokens",
    "UnmappedDiagnosticsReport",
]
