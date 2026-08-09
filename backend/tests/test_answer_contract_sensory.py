import asyncio

from guancha_api.application.answer_contract import _decision_uncertainty, build_sensory_interpretations
from guancha_api.providers.merchant_reply import FakeMerchantReplyReasoningProvider


def _evidence(field: str, value: object, *, status: str = "explicit") -> dict[str, object]:
    return {"field_name": field, "normalized_value": value, "information_status": status, "source_type": "product-claim"}


def test_qingxiang_and_light_roast_have_bounded_interpretations() -> None:
    hints = build_sensory_interpretations([_evidence("aroma_style", "qingxiang"), _evidence("roast_level", "light")])
    assert hints[0]["source_field"] == "aroma_style"
    assert "如果商品页的清香型描述准确" in hints[0]["interpretation"]
    assert "清鲜、轻扬" in hints[0]["interpretation"]
    assert "火味存在感通常较低" in hints[1]["interpretation"]
    assert "不代表具体商品已经验证没有火味" in hints[1]["boundary"]


def test_legacy_roast_or_style_keeps_explicit_aroma_direction() -> None:
    hints = build_sensory_interpretations([_evidence("roast_or_style", "浓香型")])
    assert len(hints) == 1
    assert hints[0]["source_field"] == "roast_or_style"
    assert "熟香、醇厚方向" in hints[0]["interpretation"]
    assert "实际浓度已被验证" in hints[0]["boundary"]


def test_heavy_roast_is_not_a_quality_judgement() -> None:
    hints = build_sensory_interpretations([_evidence("roast_level", "heavy")])
    assert "熟香和焙火存在感通常会更明显" in hints[0]["interpretation"]
    assert "品质高低" in hints[0]["boundary"]
    assert "品质差" not in hints[0]["interpretation"]


def test_marketing_or_unknown_never_becomes_verified_taste() -> None:
    marketing = build_sensory_interpretations([_evidence("marketing_claims", "兰花香")])
    assert "不能确认实际喝到的香气强度" in marketing[0]["interpretation"]
    assert "有明显兰花香" not in marketing[0]["interpretation"]
    assert build_sensory_interpretations([_evidence("aroma_style", "qingxiang", status="unknown")]) == []
    assert build_sensory_interpretations([_evidence("season", "spring")]) == []


def test_legacy_style_hint_does_not_make_the_aroma_question_look_duplicate() -> None:
    uncertainty = _decision_uncertainty("aroma_style", [_evidence("roast_or_style", "清香型")])
    assert uncertainty["label"] == "页面已有香型/焙火描述，仍需确认具体香型"
    assert "不能区分具体香型与焙火程度" in uncertainty["why_it_matters"]
    assert "风味方向" in uncertainty["change_if"]


def test_known_decision_fields_have_specific_labels() -> None:
    uncertainty = _decision_uncertainty("price", [])
    assert uncertainty["label"] == "实际到手价格"


def test_short_merchant_roast_answers_use_a_closed_mapping() -> None:
    provider = FakeMerchantReplyReasoningProvider()
    light = asyncio.run(provider.parse_merchant_reply(field_key="roast_level", raw_text="浅", product_evidence=()))
    heavy = asyncio.run(provider.parse_merchant_reply(field_key="roast_level", raw_text="深", product_evidence=()))
    assert light.claims[0]["normalized_value"] == "light"
    assert heavy.claims[0]["normalized_value"] == "heavy"
