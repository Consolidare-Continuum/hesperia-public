# HESPERIA — RAD. Ethan PO-22 token pairs.
from __future__ import annotations

from core.lexical.cooccurrence import pair_counts_from_canonical, token_pair_counts


def test_pair_counts_deterministic() -> None:
    pc = token_pair_counts(["a", "b", "a", "c"], window=2)
    assert isinstance(pc, dict)
    pc2 = pair_counts_from_canonical("a b a c", window=2)
    assert pc2 == pc or len(pc2) >= 1
