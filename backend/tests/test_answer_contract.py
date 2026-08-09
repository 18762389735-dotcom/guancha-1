from uuid import uuid4

from guancha_api.application.answer_contract import build_selection_answer


def test_answer_contract_uses_user_facing_labels_and_specific_uncertainty_reasons() -> None:
    client_id = uuid4()
    candidate_id = uuid4()
    version_id = uuid4()
    answer = build_selection_answer(
        version={"id": version_id, "selection_session_id": uuid4(), "top_candidate_id": candidate_id},
        candidates=[{
            "candidate_id": candidate_id,
            "display_name": "安溪铁观音",
            "display_label": "候选茶 A",
            "evidence": [{
                "information_status": "explicit",
                "normalized_value": "清香型",
                "field_name": "aroma_style",
            }],
        }],
        decisions=[{
            "candidate_id": candidate_id,
            "overall_order": 1,
            "action_bucket": "ask-before-buying",
            "reasons": ["清香型与本次需求更接近"],
            "missing_critical_fields": ["roast_level", "price", "sample_available"],
            "risk_flags": [],
        }],
        questions=[],
    )

    item = answer["candidates"][0]
    assert item["known_facts"] == [{"label": "具体香型", "value": "清香型", "basis": "商品页明确标注"}]
    assert [unknown["label"] for unknown in item["decision_uncertainties"]] == ["具体焙火程度", "实际到手价格", "是否可试饮"]
    assert all(unknown["why_it_matters"] for unknown in item["decision_uncertainties"])
    assert all(unknown["change_if"] for unknown in item["decision_uncertainties"])
