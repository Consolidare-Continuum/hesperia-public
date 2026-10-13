# HESPERIA — Public schema validation. Fail if internal-revealing key appears before serialization.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Re-export shim — moved to core.projection.schema_guard 2026-07-31 (core/engine graduation:
core/engine/projection/schema_enforcer.py couldn't reach this from here without violating "core
must not import runtime"). Kept so existing runtime/tools/tests callers don't break, and so the
sealed-file-manifest tools that check for this literal path still find it."""

from __future__ import annotations

from core.projection.schema_guard import (
    AMBIGUOUS_EXACT_KEYS,
    FORBIDDEN_KEY_SUBSTRINGS,
    FORBIDDEN_RESPONSE_SUBSTRINGS,
    LEGACY_COMPAT_KEYS,
    load_public_output_top_level_allowlist,
    validate_against_public_schema,
    validate_public_schema_strict,
    validate_public_top_level_keys_allowlisted,
)

__all__ = [
    "AMBIGUOUS_EXACT_KEYS",
    "FORBIDDEN_KEY_SUBSTRINGS",
    "FORBIDDEN_RESPONSE_SUBSTRINGS",
    "LEGACY_COMPAT_KEYS",
    "load_public_output_top_level_allowlist",
    "validate_against_public_schema",
    "validate_public_schema_strict",
    "validate_public_top_level_keys_allowlisted",
]
