"""Phase 9 deterministic Decision regression properties.

The cases are structured decision fixtures only.  They never invoke Vision,
providers, images, or evaluation identifiers from production code.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from guancha_api.domain.tieguanyin.decision import evaluate_candidate, rank_within_buckets
from guancha_api.domain.tieguanyin.rules import load_approved_rules
from guancha_api.application.question_service import QuestionGenerationService, _question_text
from guancha_api.schemas.contracts import ActionBucket


RULES = load_approved_rules()
FULL = {"tea_type": "tieguanyin", "aroma_style": "qingxiang", "roast_level": "light", "season": "spring"}


def _evidence(**values: object) -> list[dict[str, object]]:
    return [
        {
            "field_name": field,
            "normalized_value": value,
            "information_status": "unknown" if value is None else "explicit",
        }
        for field, value in values.items()
    ]


def _draft(
    *,
    need: dict[str, object] | None = None,
    evidence: list[dict[str, object]] | None = None,
    recent: list[dict[str, object]] | None = None,
):
    return evaluate_candidate(
        candidate_id=uuid4(),
        extraction_version_id=uuid4(),
        need=need or {},
        evidence=evidence or _evidence(**FULL),
        rules=RULES,
        recent_preference_evidence=recent,
    )


@pytest.mark.parametrize("budget", [20, 50, 100, 200, 500])
@pytest.mark.parametrize("style", ["qingxiang", "nongxiang", "chenxiang"])
@pytest.mark.parametrize("purpose", ["self", "gift", "office", "explore"])
def test_persona_baselines_are_deterministic(budget: int, style: str, purpose: str) -> None:
    need = {"budget_text": str(budget), "taste_text": style, "purpose_text": purpose}
    first = _draft(need=need, evidence=_evidence(**FULL, price="88"))
    second = _draft(need=need, evidence=_evidence(**FULL, price="88"))
    assert first.action_bucket is second.action_bucket
    assert first.score_components == second.score_components


def test_m1_budget_monotonicity() -> None:
    evidence = _evidence(**FULL, price="100")
    low = _draft(need={"budget_text": "50"}, evidence=evidence)
    high = _draft(need={"budget_text": "150"}, evidence=evidence)
    assert high.score_components["budget_fit"] >= low.score_components["budget_fit"]
    assert high.action_bucket is not ActionBucket.NOT_RECOMMENDED_NOW


def test_m2_aroma_preference_shift() -> None:
    qing = _draft(need={"taste_text": "qingxiang"}, evidence=_evidence(**FULL))
    qing_as_nong = _draft(need={"taste_text": "nongxiang"}, evidence=_evidence(**FULL))
    nong = _draft(need={"taste_text": "nongxiang"}, evidence=_evidence(**{**FULL, "aroma_style": "nongxiang"}))
    assert qing.score_components["need_match"] > qing_as_nong.score_components["need_match"]
    assert nong.score_components["need_match"] > qing_as_nong.score_components["need_match"]


def test_m3_roast_preference_shift() -> None:
    evidence = _evidence(**{**FULL, "roast_level": "heavy"})
    avoid = _draft(need={"taste_text": "avoid roast"}, evidence=evidence)
    accept = _draft(need={"taste_text": "accept heavy roast"}, evidence=evidence)
    assert accept.score_components["need_match"] > avoid.score_components["need_match"]


def test_m4_explore_values_explicit_trial_evidence_without_erasing_risk() -> None:
    evidence = _evidence(**FULL, sample_available="true")
    explore = _draft(need={"risk_attitude_text": "\u5c1d\u8bd5"}, evidence=evidence)
    assert explore.action_bucket is ActionBucket.SAMPLE_FIRST
    conflict = _draft(
        need={"risk_attitude_text": "\u5c1d\u8bd5"},
        evidence=evidence + [{"field_name": "season", "normalized_value": "autumn", "information_status": "conflict"}],
    )
    assert conflict.action_bucket is ActionBucket.NOT_RECOMMENDED_NOW


def test_m5_marketing_claims_do_not_raise_sufficiency_or_lower_risk() -> None:
    baseline = _draft(evidence=_evidence(tea_type="tieguanyin", aroma_style=None, roast_level=None, season=None))
    marketed = _draft(evidence=_evidence(tea_type="tieguanyin", aroma_style=None, roast_level=None, season=None, marketing_claims="master high-mountain"))
    assert marketed.score_components["evidence_sufficiency"] == baseline.score_components["evidence_sufficiency"]
    assert marketed.action_bucket is baseline.action_bucket


def test_m6_known_to_unknown_never_increases_certainty() -> None:
    known = _draft(evidence=_evidence(**FULL))
    unknown = _draft(evidence=_evidence(**{**FULL, "aroma_style": None}))
    assert unknown.score_components["evidence_sufficiency"] <= known.score_components["evidence_sufficiency"]
    assert unknown.internal_score <= known.internal_score


def test_unknown_status_with_a_value_is_not_treated_as_known() -> None:
    known = _draft(evidence=_evidence(**FULL))
    unknown_value = _draft(evidence=_evidence(tea_type="tieguanyin", aroma_style="qingxiang", roast_level="light") + [{"field_name": "season", "normalized_value": "spring", "information_status": "unknown"}])
    assert unknown_value.score_components["evidence_sufficiency"] < known.score_components["evidence_sufficiency"]


def test_explicit_legacy_tea_and_style_fields_satisfy_only_the_matching_core_fields() -> None:
    draft = _draft(evidence=_evidence(
        tea_subtype="铁观音", tea_category="乌龙茶", roast_or_style="清香型", season="spring",
    ))
    assert "tea_type" not in draft.missing_critical_fields
    assert "aroma_style" not in draft.missing_critical_fields
    # 清香型 is a style direction, never a fabricated roast-level fact.
    assert "roast_level" in draft.missing_critical_fields


def test_m7_conflict_never_improves_risk_or_bucket() -> None:
    plain = _draft(evidence=_evidence(**FULL))
    conflict = _draft(evidence=_evidence(**FULL) + [{"field_name": "season", "normalized_value": "autumn", "information_status": "conflict"}])
    assert conflict.score_components["risk_penalty"] <= plain.score_components["risk_penalty"]
    assert conflict.action_bucket is ActionBucket.NOT_RECOMMENDED_NOW


def test_m8_current_need_dominates_low_confidence_preference() -> None:
    recent = [{"confidence": "low", "issue_source": "tea", "target_type": "aroma", "target_value": "nongxiang", "polarity": "positive"}]
    qing = _draft(need={"taste_text": "qingxiang"}, evidence=_evidence(**FULL), recent=recent)
    nong = _draft(need={"taste_text": "qingxiang"}, evidence=_evidence(**{**FULL, "aroma_style": "nongxiang"}), recent=recent)
    ranked = rank_within_buckets([nong, qing])
    assert ranked[0].candidate_id == qing.candidate_id


def test_m9_price_removal_cannot_become_budget_fit() -> None:
    priced = _draft(need={"budget_text": "50"}, evidence=_evidence(**FULL, price="100"))
    unknown = _draft(need={"budget_text": "50"}, evidence=_evidence(**FULL, price=None))
    assert unknown.score_components["budget_fit"] <= 0
    assert unknown.action_bucket is ActionBucket.ASK_BEFORE_BUYING
    assert priced.action_bucket is ActionBucket.NOT_RECOMMENDED_NOW


def test_m10_sample_unknown_is_not_yes() -> None:
    yes = _draft(need={"risk_attitude_text": "\u5c1d\u8bd5"}, evidence=_evidence(**FULL, sample_available="true"))
    unknown = _draft(need={"risk_attitude_text": "\u5c1d\u8bd5"}, evidence=_evidence(**FULL, sample_available=None))
    assert yes.score_components["trial_friendliness"] == 1
    assert unknown.score_components["trial_friendliness"] == 0


@pytest.mark.parametrize(
    "expected,evidence,need",
    [
        (ActionBucket.CURRENTLY_SELECTABLE, _evidence(**FULL), {}),
        (ActionBucket.SAMPLE_FIRST, _evidence(**FULL, sample_available="true"), {"risk_attitude_text": "\u5c1d\u8bd5"}),
        (ActionBucket.ASK_BEFORE_BUYING, _evidence(**FULL, price=None), {"budget_text": "50"}),
        (ActionBucket.INSUFFICIENT_INFORMATION, _evidence(tea_type=None, aroma_style=None, roast_level=None, season=None), {}),
        (ActionBucket.NOT_RECOMMENDED_NOW, _evidence(**{**FULL, "aroma_style": "nongxiang"}), {"taste_text": "qingxiang"}),
    ],
)
def test_all_five_action_buckets_are_reachable(expected: ActionBucket, evidence: list[dict[str, object]], need: dict[str, object]) -> None:
    assert _draft(need=need, evidence=evidence).action_bucket is expected


@pytest.mark.parametrize(
    "need,evidence,expected",
    [
        ({"risk_attitude_text": "try", "budget_text": "50"}, _evidence(**FULL, sample_available="true", price="100") + [{"field_name": "season", "normalized_value": "autumn", "information_status": "conflict"}], ActionBucket.NOT_RECOMMENDED_NOW),
        ({"risk_attitude_text": "try", "budget_text": "50"}, _evidence(tea_type=None, aroma_style=None, roast_level=None, season=None, sample_available="true", price=None), ActionBucket.INSUFFICIENT_INFORMATION),
        ({"risk_attitude_text": "try", "budget_text": "50"}, _evidence(**FULL, sample_available="true", price=None), ActionBucket.ASK_BEFORE_BUYING),
    ],
)
def test_bucket_priority_is_stable_when_multiple_rules_apply(need: dict[str, object], evidence: list[dict[str, object]], expected: ActionBucket) -> None:
    assert _draft(need=need, evidence=evidence).action_bucket is expected


def test_questions_only_offer_unknown_or_decision_relevant_fields() -> None:
    service = QuestionGenerationService(repository=object())
    candidate_id = uuid4()
    version = {"need_snapshot": {"taste_text": "qingxiang"}, "rule_version": RULES[0].rule_version}
    decisions = [{"candidate_id": candidate_id, "missing_critical_fields": ["roast_level"], "action_bucket": "ask-before-buying", "overall_order": 1, "risk_flags": [], "reasons": []}]
    inputs = [{"candidate_id": candidate_id, "extraction_version_id": uuid4(), "evidence": _evidence(tea_type="tieguanyin", aroma_style="qingxiang", roast_level=None, season="spring", price=None)}]
    candidates = service._candidates(version=version, decisions=decisions, inputs=inputs)
    assert candidates
    assert all(item.field_key not in {"tea_type", "aroma_style", "season"} for item in candidates)
    assert all(item.field_key in {"roast_level", "price", "sample_available", "return_policy", "origin_text", "year_or_batch", "weight_grams", "process_text"} for item in candidates)


def test_boolean_merchant_questions_do_not_use_a_double_question_form() -> None:
    assert _question_text("sample_available") == "请问这款茶是否提供小样或试饮装？"
