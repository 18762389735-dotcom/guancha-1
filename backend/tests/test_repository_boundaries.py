from guancha_api.repositories.postgres import _explicit_product_conflict


def test_only_explicit_known_product_claims_can_conflict_with_merchant_values() -> None:
    assert not _explicit_product_conflict(None, "true")
    assert not _explicit_product_conflict({"source_type": "product-claim", "information_status": "unknown", "normalized_value": "false"}, "true")
    assert not _explicit_product_conflict({"source_type": "product-claim", "information_status": "inferred", "normalized_value": "false"}, "true")
    assert not _explicit_product_conflict({"source_type": "product-claim", "information_status": "explicit", "normalized_value": ""}, "true")
    assert not _explicit_product_conflict({"source_type": "product-claim", "information_status": "explicit", "normalized_value": "unknown"}, "true")
    assert not _explicit_product_conflict({"source_type": "merchant-claim", "information_status": "explicit", "normalized_value": "false"}, "true")
    assert not _explicit_product_conflict({"source_type": "product-claim", "information_status": "explicit", "normalized_value": "true"}, "true")
    assert _explicit_product_conflict({"source_type": "product-claim", "information_status": "explicit", "normalized_value": "false"}, "true")
