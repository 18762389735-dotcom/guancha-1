from guancha_api.application.answer_contract import build_sensory_interpretations


def _evidence(field: str, value: object, *, status: str = "explicit") -> dict[str, object]:
    return {"field_name": field, "normalized_value": value, "information_status": status, "source_type": "product-claim"}


def test_qingxiang_and_light_roast_have_bounded_interpretations() -> None:
    hints = build_sensory_interpretations([_evidence("aroma_style", "qingxiang"), _evidence("roast_level", "light")])
    assert hints[0]["source_field"] == "aroma_style"
    assert "如果商品页的清香型描述准确" in hints[0]["interpretation"]
    assert "清鲜、轻扬" in hints[0]["interpretation"]
    assert "火味存在感通常较低" in hints[1]["interpretation"]
    assert "不代表具体商品已经验证没有火味" in hints[1]["boundary"]


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
