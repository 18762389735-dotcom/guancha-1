from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from guancha_api.domain.tieguanyin.rules.rule_schema import DecisionRule
from guancha_api.schemas.contracts import ActionBucket, InformationStatus


_BUCKET_ORDER = {
    ActionBucket.CURRENTLY_SELECTABLE: 0,
    ActionBucket.SAMPLE_FIRST: 1,
    ActionBucket.ASK_BEFORE_BUYING: 2,
    ActionBucket.INSUFFICIENT_INFORMATION: 3,
    ActionBucket.NOT_RECOMMENDED_NOW: 4,
}


@dataclass(frozen=True)
class CandidateDecisionDraft:
    candidate_id: object
    extraction_version_id: object
    action_bucket: ActionBucket
    reasons: tuple[str, ...]
    risk_flags: tuple[str, ...]
    missing_critical_fields: tuple[str, ...]
    score_components: dict[str, int]
    internal_score: Decimal


def evaluate_candidate(
    *,
    candidate_id: object,
    extraction_version_id: object,
    need: dict[str, Any],
    evidence: list[dict[str, Any]],
    rules: tuple[DecisionRule, ...],
    recent_preference_evidence: list[dict[str, Any]] | None = None,
) -> CandidateDecisionDraft:
    values = _evidence_values(evidence)
    missing = _missing_core(values)
    reasons: list[str] = []
    risks: list[str] = []
    buckets: list[ActionBucket] = []

    for rule in rules:
        if _rule_matches(rule.condition, values, need, missing, evidence):
            buckets.append(rule.action_bucket)
            reasons.append(rule.reason)
            risks.append(rule.risk)

    if any(item.get("information_status") == InformationStatus.CONFLICT.value for item in evidence):
        buckets.append(ActionBucket.NOT_RECOMMENDED_NOW)
        reasons.append("\u5173\u952e\u6765\u6e90\u5b58\u5728\u51b2\u7a81")
        risks.append("\u51b2\u7a81\u4e0d\u80fd\u88ab\u6b63\u5411\u4fe1\u606f\u62b5\u6d88")

    if values.get("sample_available") is True and _is_exploratory(need.get("risk_attitude_text")):
        buckets.append(ActionBucket.SAMPLE_FIRST)
        reasons.append("\u652f\u6301\u4f4e\u6210\u672c\u8bd5\u996e\uff0c\u9002\u5408\u5148\u786e\u8ba4\u4f53\u9a8c")
        risks.append("\u8bd5\u996e\u524d\u4ecd\u9700\u4fdd\u7559\u4f53\u9a8c\u4e0d\u786e\u5b9a\u6027")

    # A missing price cannot silently be treated as budget-compatible.
    if need.get("budget_text") and "price" not in values:
        buckets.append(ActionBucket.ASK_BEFORE_BUYING)
        reasons.append("\u4ef7\u683c\u672a\u77e5\uff0c\u65e0\u6cd5\u786e\u8ba4\u9884\u7b97\u662f\u5426\u5339\u914d")
        risks.append("\u672a\u77e5\u4ef7\u683c\u4e0d\u80fd\u89c6\u4e3a\u7b26\u5408\u9884\u7b97")

    if not buckets:
        buckets.append(ActionBucket.CURRENTLY_SELECTABLE)
        reasons.append("\u672c\u6b21\u9700\u6c42\u4e0e\u53ef\u8bfb\u53d6\u4fe1\u606f\u6ca1\u6709\u660e\u786e\u51b2\u7a81")
    bucket = max(buckets, key=lambda item: _BUCKET_ORDER[item])

    confidence = max(0, 4 - len(missing))
    explicit_sensory_need = _explicit_sensory_need_match(need.get("taste_text"), evidence)
    match = (
        _text_match(need.get("taste_text"), values.get("aroma_style"))
        + _roast_match(need.get("taste_text"), values.get("roast_level"))
        + _purpose_match(need.get("purpose_text"), values)
    )
    if explicit_sensory_need > 0:
        reasons.append("当前明确的感官方向与页面已标注的风格线索更接近")
    elif explicit_sensory_need < 0:
        reasons.append("页面已标注的风格线索与当前明确的感官方向存在偏离")
    budget = _budget_fit(need.get("budget_text"), values.get("price"))
    trial = 1 if values.get("sample_available") is True else 0
    risk_penalty = _BUCKET_ORDER[bucket]
    personal = _low_confidence_preference_delta(values, recent_preference_evidence or [])
    score = Decimal(explicit_sensory_need + match + budget + confidence + trial - risk_penalty + personal)
    return CandidateDecisionDraft(
        candidate_id,
        extraction_version_id,
        bucket,
        tuple(dict.fromkeys(reasons))[:3],
        tuple(dict.fromkeys(risks))[:3],
        tuple(missing),
        {
            "explicit_sensory_need_match": explicit_sensory_need,
            "need_match": match,
            "budget_fit": budget,
            "evidence_sufficiency": confidence,
            "trial_friendliness": trial,
            "risk_penalty": -risk_penalty,
            "personal_low_confidence": personal,
        },
        score,
    )


def rank_within_buckets(drafts: list[CandidateDecisionDraft]) -> list[CandidateDecisionDraft]:
    return sorted(
        drafts,
        key=lambda item: (
            _BUCKET_ORDER[item.action_bucket],
            -item.score_components["explicit_sensory_need_match"],
            -item.score_components["need_match"],
            -item.score_components["budget_fit"],
            -item.score_components["trial_friendliness"],
            -item.score_components["personal_low_confidence"],
            -item.score_components["evidence_sufficiency"],
            str(item.candidate_id),
        ),
    )


def _evidence_values(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in evidence:
        field = item.get("field_name")
        value = item.get("normalized_value")
        if field and value not in (None, "", "unknown") and item.get("information_status") in {
            InformationStatus.EXPLICIT.value,
            InformationStatus.INFERRED.value,
        }:
            values[str(field)] = _coerce(value)
    # The frozen extraction contract predates the decision contract.  A page
    # can explicitly identify a tea as “铁观音” or “乌龙茶” under the legacy
    # subtype/category fields; it must count as a known tea type rather than
    # making the user ask a merchant to repeat the page.  This is a derived
    # read-time alias only: no Evidence record is rewritten.
    if "tea_type" not in values:
        for field in ("tea_subtype", "tea_category"):
            if values.get(field):
                values["tea_type"] = values[field]
                break
    # 清香型、浓香型与陈香型 are style designations, not roast levels.  The
    # legacy combined field may therefore satisfy aroma direction, while the
    # distinct roast_level remains unknown and can still be asked explicitly.
    if "aroma_style" not in values:
        legacy_style = str(values.get("roast_or_style") or "").strip().lower()
        style_aliases = {
            "qingxiang": "qingxiang", "清香": "qingxiang", "清香型": "qingxiang",
            "nongxiang": "nongxiang", "浓香": "nongxiang", "浓香型": "nongxiang",
            "chenxiang": "chenxiang", "陈香": "chenxiang", "陈香型": "chenxiang",
        }
        if legacy_style in style_aliases:
            values["aroma_style"] = style_aliases[legacy_style]
    return values


def _low_confidence_preference_delta(values: dict[str, Any], recent: list[dict[str, Any]]) -> int:
    """Bounded tie-breaker only: it cannot mutate a safety bucket."""
    field_by_target = {"roast": "roast_level", "aroma": "aroma_style", "tea-style": "tea_type", "mouthfeel": "taste_claims"}
    for item in recent:
        if item.get("confidence") != "low" or item.get("issue_source") != "tea":
            continue
        field = field_by_target.get(str(item.get("target_type")))
        if field and values.get(field) and (
            item.get("target_type") == "mouthfeel"
            or str(item.get("target_value", "")).replace("-", " ") in str(values[field]).lower().replace("-", " ")
        ):
            return 1 if item.get("polarity") == "positive" else -1 if item.get("polarity") == "negative" else 0
    return 0


def _missing_core(values: dict[str, Any]) -> list[str]:
    return [field for field in ("tea_type", "aroma_style", "roast_level", "season") if field not in values]


def _rule_matches(condition: str, values: dict[str, Any], need: dict[str, Any], missing: list[str], evidence: list[dict[str, Any]]) -> bool:
    if condition == "core_information_insufficient":
        return len(missing) >= 3 or "tea_type" in missing
    if condition == "marketing_with_missing_core":
        return bool(values.get("marketing_claims")) and len(missing) >= 2
    if condition == "roast_unknown":
        return "roast_level" in missing and bool(need.get("taste_text") or need.get("risk_attitude_text"))
    if condition == "style_conflict":
        return _text_match(need.get("taste_text"), values.get("aroma_style")) < 0
    if condition == "budget_mismatch_without_sample":
        return _budget_fit(need.get("budget_text"), values.get("price")) < 0 and values.get("sample_available") is not True
    return False


def _coerce(value: Any) -> Any:
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return Decimal(str(value))
    except Exception:
        return value


def _budget_fit(text: Any, price: Any) -> int:
    if not text or not isinstance(price, Decimal):
        return 0
    amounts = [Decimal(value) for value in re.findall(r"\d+(?:\.\d+)?", str(text))]
    if not amounts:
        return 0
    # A budget range describes an allowed ceiling, not its first number.
    # ``150–300``, ``150-300`` and ``300以内`` therefore all cap at 300.
    ceiling = max(amounts)
    return 1 if price <= ceiling else -1


def _text_match(text: Any, style: Any) -> int:
    if not text or not style:
        return 0
    wanted, actual = str(text).lower(), str(style).lower()
    qing = ("qingxiang", "\u6e05\u9999")
    nong = ("nongxiang", "\u6d53\u9999")
    wants_qing = any(token in wanted for token in qing)
    wants_nong = any(token in wanted for token in nong)
    is_qing = actual in qing
    is_nong = actual in nong
    if (wants_qing and is_qing) or (wants_nong and is_nong):
        return 1
    if (wants_qing and is_nong) or (wants_nong and is_qing):
        return -1
    return 0


def _explicit_sensory_need_match(text: Any, evidence: list[dict[str, Any]]) -> int:
    """Return a bounded same-bucket signal from current need and explicit style facts.

    This is deliberately separate from ``_text_match`` because the latter also
    feeds frozen hard-conflict rules.  Everyday wording such as ``清爽`` should
    break a same-tier tie when the page explicitly gives a style direction, but
    must not silently promote or demote an action bucket.
    """
    wanted = str(text or "").lower()
    if not wanted:
        return 0
    explicit: dict[str, str] = {}
    for item in evidence:
        field = str(item.get("field_name") or "")
        value = item.get("normalized_value")
        if field in {"aroma_style", "roast_level"} and item.get("information_status") == InformationStatus.EXPLICIT.value and value not in (None, "", "unknown"):
            explicit[field] = str(value).lower()

    style = explicit.get("aroma_style", "")
    roast = explicit.get("roast_level", "")
    score = 0
    wants_qing = any(token in wanted for token in ("qingxiang", "清香", "清爽", "清鲜"))
    wants_rich = any(token in wanted for token in ("nongxiang", "浓香", "熟香", "浓郁"))
    style_direction = _style_direction(style)
    roast_direction = _roast_direction(roast)
    if wants_qing:
        if style_direction == "qing":
            score += 1
        elif style_direction == "nong":
            score -= 1
    elif wants_rich:
        if style_direction == "nong":
            score += 1
        elif style_direction == "qing":
            score -= 1

    avoids_fire = any(token in wanted for token in ("怕火", "怕明显火味", "火味少", "低火", "轻焙", "不想火味", "不希望火味"))
    wants_fire = any(token in wanted for token in ("喜欢焙火", "焙火感明显", "火味明显", "重焙", "浓焙", "高焙", "熟香", "浓郁"))
    if avoids_fire:
        if roast_direction == "light":
            score += 1
        elif roast_direction in {"medium", "heavy"}:
            score -= 1
    elif wants_fire:
        if roast_direction in {"medium", "heavy"}:
            score += 1
        elif roast_direction == "light":
            score -= 1
    return max(-2, min(2, score))


def _style_direction(value: str) -> str:
    if "qingxiang" in value or "清香" in value:
        return "qing"
    if "nongxiang" in value or "浓香" in value:
        return "nong"
    return ""


def _roast_direction(value: str) -> str:
    if any(token in value for token in ("light", "轻焙", "低焙", "轻火")):
        return "light"
    if any(token in value for token in ("heavy", "重焙", "高焙", "浓焙", "足火")):
        return "heavy"
    if any(token in value for token in ("medium", "中焙", "中火")):
        return "medium"
    return ""


def _roast_match(text: Any, roast: Any) -> int:
    if not text or not roast:
        return 0
    wanted, actual = str(text).lower(), str(roast).lower()
    strong = any(token in actual for token in ("heavy", "strong", "\u91cd\u7119", "\u6d53\u7119", "\u9ad8\u7119"))
    light = any(token in actual for token in ("light", "\u8f7b\u7119", "\u4f4e\u7119"))
    avoids_strong = any(token in wanted for token in ("avoid roast", "avoid fire", "\u6015\u706b", "\u4e0d\u63a5\u53d7\u7119", "\u4e0d\u559c\u6b22\u7119", "\u8f7b\u7119", "\u4f4e\u706b", "\u4f4e\u706b\u5473", "\u706b\u5473\u5c11"))
    accepts_strong = any(token in wanted for token in ("accept heavy roast", "accept roast", "\u63a5\u53d7\u7119\u706b", "\u559c\u6b22\u7119\u706b", "\u91cd\u7119", "\u6d53\u7119", "\u706b\u5473"))
    if strong:
        return -1 if avoids_strong else 1 if accepts_strong else 0
    if light and avoids_strong:
        return 1
    return 0


def _purpose_match(purpose: Any, values: dict[str, Any]) -> int:
    if not purpose:
        return 0
    wanted = str(purpose).lower()
    if any(token in wanted for token in ("\u9001\u793c", "\u793c\u54c1", "gift")):
        return 1 if values.get("gift_packaging") is True else 0
    if any(token in wanted for token in ("\u529e\u516c", "\u516c\u53f8", "office")):
        return 1 if values.get("office_suitable") is True else 0
    if any(token in wanted for token in ("\u81ea\u996e", "\u81ea\u5df1\u559d", "self")):
        return 1 if values.get("self_drink") is True else 0
    if _is_exploratory(wanted):
        return 1 if values.get("sample_available") is True else 0
    return 0


def _is_exploratory(value: Any) -> bool:
    text = str(value or "").lower()
    return any(token in text for token in ("explore", "try", "\u63a2\u7d22", "\u5c1d\u8bd5", "\u8bd5\u996e"))
