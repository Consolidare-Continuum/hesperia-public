from hesperia.product.triz_metric_catalog import (
    INTERNAL_TO_PRODUCT,
    product_name,
)


def test_every_listed_internal_has_product_name() -> None:
    for k in INTERNAL_TO_PRODUCT:
        assert product_name(k) == INTERNAL_TO_PRODUCT[k]
    assert "Tension" in product_name("contradiction_score")
