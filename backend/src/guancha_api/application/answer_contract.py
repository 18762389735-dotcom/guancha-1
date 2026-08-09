"""Presentation-only mapper for the competition answer contract.

This module deliberately consumes immutable Decision/Evidence records and does
not call a provider, mutate persistence, or invent absent product facts.
"""
from __future__ import annotations

from uuid import UUID


FIELD_LABELS = {
    "product_name": "商品名称", "tea_category": "茶类", "tea_subtype": "具体茶类",
    "origin": "产地", "roast_or_style": "香型或焙火", "price": "价格",
    "weight": "净含量", "weight_grams": "净含量", "season": "采摘季节",
    "sample_available": "是否可试饮", "return_policy": "退换说明",
    "tea_type": "茶类", "origin_text": "产地", "aroma_style": "香型",
    "roast_level": "焙火程度", "process_text": "加工工艺",
    "year_or_batch": "年份或批次",
}

_UNCERTAINTY_EXPLANATIONS = {
    "price": "需要核对是否落在本次预算内。",
    "weight": "需要结合净含量判断价格是否合适。",
    "weight_grams": "需要结合净含量判断价格是否合适。",
    "sample_available": "是否可试饮会影响送礼前的试错成本。",
    "roast_level": "焙火程度会影响香气与入口风格，和本次口味需求直接相关。",
    "aroma_style": "香型会影响和“清爽花香”等口味需求的匹配程度。",
    "origin": "若在意产区，需要先核对具体产地。",
    "origin_text": "若在意产区，需要先核对具体产地。",
    "year_or_batch": "年份或批次会影响对新茶与风格的判断。",
    "return_policy": "退换说明会影响购买后的风险。",
}


def _text_values(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return [item.strip().lower() for item in str(value or "").replace("|", ",").split(",") if item.strip()]


def _source_prefix(evidence: dict[str, object]) -> str:
    return "商家补充的" if evidence.get("source_type") == "merchant-claim" else "商品页的"


def build_sensory_interpretations(evidence_items: list[dict[str, object]]) -> list[dict[str, str]]:
    """Build bounded, traceable presentation hints from explicit evidence only.

    These are general knowledge relations, not claims that the user has already
    tasted the specific product.  The return shape keeps the evidence field and
    value available to tests and the presentation mapper, while the user-facing
    answer below exposes only natural-language labels, text, and boundaries.
    """
    hints: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(item: dict[str, object], *, label: str, text: str, boundary: str, kind: str) -> None:
        field = str(item.get("field_name") or "")
        value = str(item.get("normalized_value") or "")
        key = (field, text)
        if key in seen or len(hints) >= 3:
            return
        seen.add(key)
        hints.append({
            "source_field": field,
            "source_value": value,
            "label": label,
            "interpretation": text,
            "boundary": boundary,
            "kind": kind,
        })

    explicit = [
        item for item in evidence_items
        if item.get("information_status") == "explicit" and item.get("normalized_value") not in (None, "")
    ]
    # Keep the order deterministic and put high-value style signals before
    # action/marketing explanations.
    priorities = {"aroma_style": 0, "roast_level": 1, "roast_or_style": 1, "sample_available": 2, "marketing_claims": 3}
    for item in sorted(explicit, key=lambda row: priorities.get(str(row.get("field_name")), 9)):
        field = str(item.get("field_name") or "")
        values = _text_values(item.get("normalized_value"))
        prefix = _source_prefix(item)
        if field in {"aroma_style", "roast_or_style"}:
            if any(token in value for value in values for token in ("qingxiang", "清香")):
                add(item, label="清香型线索", text=f"如果{prefix}清香型描述准确，整体风格通常更偏清鲜、轻扬。", boundary="这不代表已验证这款茶一定有某种花香。", kind="sensory")
            elif any(token in value for value in values for token in ("nongxiang", "浓香")):
                add(item, label="浓香型线索", text=f"如果{prefix}浓香型描述准确，风格通常更偏熟香、醇厚方向。", boundary="这不代表更高级，也不等于实际浓度已被验证。", kind="sensory")
        elif field in {"roast_level", "roast_or_style"}:
            if any(token in value for value in values for token in ("light", "轻焙", "低焙", "轻火")):
                add(item, label="焙火方向", text="从这种焙火方向看，火味存在感通常较低，更容易保留清鲜方向。", boundary="不代表具体商品已经验证没有火味。", kind="sensory")
            elif any(token in value for value in values for token in ("medium", "中焙", "足火", "heavy", "重焙", "高焙", "浓焙")):
                add(item, label="焙火方向", text="从这种焙火方向看，熟香和焙火存在感通常会更明显。", boundary="不代表品质高低，也不等于实际喝感已被验证。", kind="sensory")
        elif field == "sample_available" and item.get("normalized_value") is True:
            add(item, label="试饮方式", text="可以先通过小样确认真实香气、入口和火味，试错成本更低。", boundary="小样降低试错成本，不代表一定适合。", kind="action")
        elif field == "marketing_claims" and any("兰花香" in value for value in values):
            add(item, label="商品页香气描述", text=f"{prefix}强调兰花香方向，但仅凭页面描述还不能确认实际喝到的香气强度。", boundary="营销描述不能替代真实饮用体验。", kind="marketing-claim")
    return hints


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, "商品信息")


def _why_it_matters(field: str) -> str:
    return _UNCERTAINTY_EXPLANATIONS.get(field, "这项信息可能影响本次比较，补充后再决定会更稳妥。")


def _action(bucket: str, is_top: bool) -> str:
    if bucket == "currently-selectable": return "当前可优先考虑" if is_top else "可作为备选"
    if bucket == "sample-first": return "方向可继续考虑，建议先试饮"
    if bucket == "ask-before-buying": return "暂时更接近你的需求，先问清再买" if is_top else "建议问清再比较"
    if bucket == "not-recommended-now": return "当前不建议直接购买"
    return "目前还不能可靠地区分"


def build_selection_answer(*, version: dict[str, object], decisions: list[dict[str, object]], candidates: list[dict[str, object]], questions: list[dict[str, object]]) -> dict[str, object]:
    """Build natural-language display data without exposing engineering enums."""
    candidate_by_id = {row["candidate_id"]: row for row in candidates}
    question_by_candidate: dict[UUID, dict[str, object]] = {}
    for question in questions:
        question_by_candidate.setdefault(question["candidate_id"], question)
    items = []
    for decision in decisions:
        candidate = candidate_by_id[decision["candidate_id"]]
        facts = []
        for evidence in candidate["evidence"]:
            if evidence["information_status"] not in {"explicit", "inferred"} or evidence["normalized_value"] in (None, ""):
                continue
            field = str(evidence["field_name"])
            if any(item["label"] == _label(field) for item in facts):
                continue
            facts.append({"label": _label(field), "value": str(evidence["normalized_value"]), "basis": "商品页明确标注" if evidence["information_status"] == "explicit" else "根据页面内容推测"})
        unknowns = [
            {
                "label": _label(str(field)),
                "why_it_matters": _why_it_matters(str(field)),
                "change_if": "补充后可能改变当前结论",
            }
            for field in decision["missing_critical_fields"][:3]
        ]
        question = question_by_candidate.get(decision["candidate_id"])
        sensory = build_sensory_interpretations(candidate["evidence"])
        items.append({
            "candidate_id": decision["candidate_id"], "position": decision["overall_order"],
            "display_name": candidate["display_name"] or candidate["display_label"] or f"候选茶 {decision['overall_order']}",
            "verdict": _action(str(decision["action_bucket"]), decision["candidate_id"] == version["top_candidate_id"]),
            "why_it_fits": list(decision["reasons"])[:3], "known_facts": facts[:5],
            "decision_uncertainties": unknowns, "risks": list(decision["risk_flags"])[:3],
            "sensory_interpretations": [
                {"label": hint["label"], "text": hint["interpretation"], "boundary": hint["boundary"]}
                for hint in sensory
            ],
            "next_step": None if question is None else {"kind": "ask_merchant", "text": question["question_text"], "question_id": question["id"]},
        })
    top = items[0] if items else None
    return {
        "answer_version": "v2", "selection_session_id": version["selection_session_id"], "decision_version_id": version["id"],
        "status": "ready" if top and top["verdict"] != "目前还不能可靠地区分" else "needs_follow_up",
        "headline": "目前还不能可靠地区分这几款茶" if top is None or top["verdict"] == "目前还不能可靠地区分" else f"当前相对更适合{top['display_name']}",
        "qualification": "结论基于当前商品页与商家补充信息，仍有关键项待确认。" if top and top["decision_uncertainties"] else "结论基于当前可核对的信息。",
        "candidates": items,
    }
