"""Presentation-only mapper for the competition answer contract.

This module deliberately consumes immutable Decision/Evidence records and does
not call a provider, mutate persistence, or invent absent product facts.
"""
from __future__ import annotations

from uuid import UUID


FIELD_LABELS = {
    "product_name": "商品名称", "tea_category": "茶类", "tea_subtype": "具体茶类",
    "tea_type": "茶类", "origin": "产地", "origin_text": "具体产地",
    "roast_or_style": "页面标注的香型或焙火方向", "aroma_style": "具体香型",
    "roast_level": "具体焙火程度", "price": "实际到手价格",
    "aroma_claims": "页面香气描述", "taste_claims": "页面滋味描述",
    "weight": "净含量", "weight_grams": "净含量", "season": "采摘季节",
    "year_or_batch": "年份或批次", "process_text": "制作工艺说明",
    "sample_available": "是否可试饮", "return_policy": "试饮或退换规则",
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


def _display_value(field: str, value: object) -> str:
    """Keep internal normalized enums out of the user-facing answer."""
    text = str(value)
    if field == "roast_level":
        return {"light": "轻火", "medium": "中火", "heavy": "足火"}.get(text, text)
    if field == "sample_available":
        return {"true": "提供小样或试饮", "false": "暂不提供小样或试饮"}.get(text.lower(), text)
    return text


def _decision_uncertainty(field: str, evidence: list[dict[str, object]]) -> dict[str, str]:
    """Explain a decision-critical unknown without promoting an ambiguous fact.

    ``roast_or_style`` is a legacy page field: a value such as “清香型” is a
    useful page clue, but it does not reliably say whether the seller means a
    specific aroma style or a roast description.  Keep that distinction plain
    for the user instead of asking a seemingly duplicate question.
    """
    has_legacy_style = any(
        item.get("field_name") == "roast_or_style"
        and item.get("information_status") in {"explicit", "inferred"}
        and item.get("normalized_value") not in (None, "", "unknown")
        for item in evidence
    )
    if field == "aroma_style" and has_legacy_style:
        return {
            "label": "页面已有香型/焙火描述，仍需确认具体香型",
            "why_it_matters": "页面的合并描述还不能区分具体香型与焙火程度。",
            "change_if": "确认具体香型后，才能更可靠地判断是否接近你这次想要的风味方向。",
        }
    if field == "roast_level" and has_legacy_style:
        return {
            "label": "页面已有香型/焙火描述，仍需确认具体焙火程度",
            "why_it_matters": "页面的合并描述还不能说明火味和熟香会处于什么程度。",
            "change_if": "确认焙火程度后，才能更可靠地判断是否符合你这次的口感方向。",
        }
    return {
        "label": _label(field),
        "why_it_matters": "这项信息可能影响本次比较。",
        "change_if": "补充后可能改变当前结论。",
    }


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
        merchant_facts = []
        for evidence in candidate["evidence"]:
            if evidence["information_status"] != "explicit" or evidence["normalized_value"] in (None, ""):
                continue
            field = str(evidence["field_name"])
            source = evidence.get("source_type") or "product-claim"
            fact = {"label": _label(field), "value": _display_value(field, evidence["normalized_value"])}
            if source == "merchant-claim":
                if not any(item["label"] == fact["label"] for item in merchant_facts):
                    merchant_facts.append({**fact, "basis": "商家回复声明，尚未实物核验"})
                continue
            if source == "product-claim" and not any(item["label"] == fact["label"] for item in facts):
                facts.append({**fact, "basis": "商品页明确标注"})
        unknowns = [_decision_uncertainty(str(field), candidate["evidence"]) for field in decision["missing_critical_fields"][:3]]
        question = question_by_candidate.get(decision["candidate_id"])
        sensory = build_sensory_interpretations(candidate["evidence"])
        items.append({
            "candidate_id": decision["candidate_id"], "position": decision["overall_order"],
            "display_name": candidate["display_name"] or candidate["display_label"] or f"候选茶 {decision['overall_order']}",
            "verdict": _action(str(decision["action_bucket"]), decision["candidate_id"] == version["top_candidate_id"]),
            "why_it_fits": list(decision["reasons"])[:3], "known_facts": facts[:5], "merchant_facts": merchant_facts[:3],
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
