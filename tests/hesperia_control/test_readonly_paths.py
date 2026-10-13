# HC-10 — control modules do not enable lexical write by default. Copyright © 2026 igareosh.com.
from __future__ import annotations

import os

from hesperia.engine.hesperia_control.readonly_guard import assert_lexical_readonly


def test_readonly_default() -> None:
    os.environ.pop("HESPERIA_LEXICAL_WRITE_ALLOWED", None)
    assert_lexical_readonly()  # no-op path
