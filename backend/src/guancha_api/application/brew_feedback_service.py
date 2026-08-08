from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from guancha_api.schemas.contracts import BrewAdjustment, BrewFeedbackAnalysisRequest, BrewFeedbackAnalysisResponse, PreferenceEvidence

SAFE_ADJUSTMENTS = {
    "water_temperature": {"direction": "decrease", "suggested_delta": -5},
    "steep_time": {"direction": "decrease", "suggested_delta": -3},
    "tea_amount": {"direction": "decrease", "suggested_delta": -1},
    "water_volume": {"direction": "increase", "suggested_delta": 10},
}

def analyze_feedback(request: BrewFeedbackAnalysisRequest) -> BrewFeedbackAnalysisResponse:
    actual, recommended, feedback = request.actual_brew_parameters, request.system_recommended_parameters, request.structured_feedback
    bitter = any(value in " ".join(filter(None, (feedback.bitterness, feedback.astringency, feedback.free_text_note))).lower() for value in ("bitter", "astringent", "strong", "明显", "苦", "涩"))
    hot = actual.water_temperature and recommended.water_temperature and actual.water_temperature > recommended.water_temperature + 3
    cold = actual.water_temperature and recommended.water_temperature and actual.water_temperature < recommended.water_temperature - 3
    long = actual.steep_time and recommended.steep_time and actual.steep_time > recommended.steep_time + 3
    short = actual.steep_time and recommended.steep_time and actual.steep_time < recommended.steep_time - 3
    heavy_leaf = actual.tea_amount and recommended.tea_amount and actual.tea_amount > recommended.tea_amount * 1.15
    low_water = actual.water_volume and recommended.water_volume and actual.water_volume < recommended.water_volume * 0.85
    now = datetime.now(timezone.utc)
    if bitter and (hot or long or heavy_leaf or low_water):
        parameter = "water_temperature" if hot else "steep_time" if long else "tea_amount" if heavy_leaf else "water_volume"
        direction = SAFE_ADJUSTMENTS[parameter]["direction"]
        delta = SAFE_ADJUSTMENTS[parameter]["suggested_delta"]
        return BrewFeedbackAnalysisResponse(attribution="brewing", attribution_reasons=("实际冲泡参数偏离建议，且反馈出现苦涩。",), next_brew_adjustment=BrewAdjustment(parameter=parameter, direction=direction, suggested_delta=delta, reason="下一泡只调整一个变量，先降低苦涩风险。", confidence="low"), preference_evidence=(), impact_explanation="本次更可能受泡法影响，不把它归为茶本身偏好。", warnings=("单次记录仅供下次试泡参考。",))
    tea_issue = any(value in " ".join(filter(None, (feedback.aroma, feedback.mouthfeel, feedback.free_text_note))).lower() for value in ("heavy roast", "burnt", "焙火", "焦"))
    repeated = (actual.infusion_number or 0) >= 2
    if tea_issue and repeated and not any((hot, cold, long, short, heavy_leaf, low_water)):
        evidence = PreferenceEvidence(id=uuid4(), target_type="roast", target_value="heavy-roast", polarity="negative", confidence="low", issue_source="tea", source_brew_session_id=request.brew_session_id, created_at=now)
        return BrewFeedbackAnalysisResponse(attribution="tea", attribution_reasons=("Reasonable repeated brews consistently indicate an unwanted roast impression.",), next_brew_adjustment=BrewAdjustment(reason="Keep the same parameters for now; this remains a low-confidence experience record.", confidence="low"), preference_evidence=(evidence,), impact_explanation="This does not change the taste card or establish a permanent preference.", warnings=("Incomplete or single-infusion feedback remains uncertain.",))
    if feedback.overall_rating and feedback.overall_rating >= 4 and repeated and not any((hot, cold, long, short, heavy_leaf, low_water)):
        evidence = PreferenceEvidence(id=uuid4(), target_type="mouthfeel", target_value="positive-experience", polarity="positive", confidence="low", issue_source="tea", source_brew_session_id=request.brew_session_id, created_at=now)
        return BrewFeedbackAnalysisResponse(attribution="tea", attribution_reasons=("参数基本处于建议范围，且反馈整体积极。",), next_brew_adjustment=BrewAdjustment(reason="下一泡先保持本次参数，继续观察。", confidence="low"), preference_evidence=(evidence,), impact_explanation="形成一条低置信度体验证据，不会修改口味卡。", warnings=("单次体验不足以形成长期偏好。",))
    return BrewFeedbackAnalysisResponse(attribution="uncertain", attribution_reasons=("参数或反馈信息不足，暂时无法区分茶与泡法影响。",), next_brew_adjustment=BrewAdjustment(reason="补充下一泡的实际参数和具体感受后再判断。", confidence="low"), preference_evidence=(), impact_explanation="不确定反馈不参与强排序，也不改写口味卡。", warnings=("本次证据不足。",))
