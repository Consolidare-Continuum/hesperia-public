from __future__ import annotations

from hesperia.product.compression import compress_product_output


def test_compression_has_compact_fields() -> None:
    out = compress_product_output({"tension": 0.8, "stability": 0.2, "loopability": 0.9})
    assert set(out.keys()) == {"risk", "stability", "pattern", "confidence", "decision_basis"}
    assert out["risk"] == "high"

