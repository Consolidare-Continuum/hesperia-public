# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for Prolog-style rule parser (sphere.prolog_logic).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_rule_parsing() -> None:
    """parse_rule returns type rule with head and body."""
    from sphere.prolog_logic import parse_rule
    parsed = parse_rule("a :- b, c.")
    assert parsed["type"] == "rule"
    assert parsed["head"]["predicate"] == "a"
    assert len(parsed["body"]) == 2


def test_fact_parsing() -> None:
    """parse_fact returns type fact with predicate and args."""
    from sphere.prolog_logic import parse_fact
    parsed = parse_fact("entropy_low(true).")
    assert parsed["type"] == "fact"
    assert parsed["predicate"] == "entropy_low"
    assert isinstance(parsed["args"], list)
    assert len(parsed["args"]) == 1
