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
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, "商品信息")


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
        unknowns = [{"label": _label(str(field)), "why_it_matters": "这项信息可能影响本次比较", "change_if": "补充后可能改变当前结论"} for field in decision["missing_critical_fields"][:3]]
        question = question_by_candidate.get(decision["candidate_id"])
        items.append({
            "candidate_id": decision["candidate_id"], "position": decision["overall_order"],
            "display_name": candidate["display_name"] or candidate["display_label"] or f"候选茶 {decision['overall_order']}",
            "verdict": _action(str(decision["action_bucket"]), decision["candidate_id"] == version["top_candidate_id"]),
            "why_it_fits": list(decision["reasons"])[:3], "known_facts": facts[:5],
            "decision_uncertainties": unknowns, "risks": list(decision["risk_flags"])[:3],
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
