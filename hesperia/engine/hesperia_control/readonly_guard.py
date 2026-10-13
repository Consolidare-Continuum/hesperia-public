# Read-only guard for lexical assets (HC-10). Copyright © 2026 igareosh.com.
from __future__ import annotations

import os
from pathlib import Path


def assert_lexical_readonly() -> None:
    """
    No-op marker: control modules must not open dict A/B paths for write.
    Integration tests may patch env to verify no writes occur.
    """
    _ = os.environ.get("HESPERIA_LEXICAL_WRITE_ALLOWED", "").strip().lower() in {"1", "true", "yes"}


def lexical_paths_for_test() -> tuple[Path | None, Path | None]:
    """Optional paths for CI guard (not used in hot path)."""
    return None, None
