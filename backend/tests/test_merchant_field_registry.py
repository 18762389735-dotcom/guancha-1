from guancha_api.domain.tieguanyin.merchant_fields import MERCHANT_FIELDS, merchant_field_label


def test_competition_merchant_field_registry_covers_all_p0_questions() -> None:
    required = {"price", "weight_grams", "tea_subtype", "aroma_style", "roast_level", "season", "origin_text", "sample_available", "return_policy"}
    assert required.issubset(MERCHANT_FIELDS)
    assert all(merchant_field_label(field) != field for field in required)
