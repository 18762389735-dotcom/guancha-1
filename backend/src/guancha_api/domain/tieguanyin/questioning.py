from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guancha_api.domain.tieguanyin.decision import evaluate_candidate, rank_within_buckets
from guancha_api.domain.tieguanyin.rules.rule_schema import DecisionRule


ANSWER_BRANCHES: dict[str, tuple[str, ...]] = {
    "roast_level": ("light", "medium", "heavy", "still-unknown", "conflicting"),
    "aroma_style": ("qingxiang", "nongxiang", "chenxiang", "still-unknown", "conflicting"),
    "season": ("spring", "autumn", "other", "still-unknown", "conflicting"),
    "sample_available": ("yes", "no", "still-unknown"),
    "price": ("within-budget", "over-budget", "still-unknown"),
    "return_policy": ("trial-friendly", "restricted", "still-unknown"),
    "origin_text": ("known", "still-unknown", "conflicting"),
    "year_or_batch": ("known", "still-unknown", "conflicting"),
    "weight_grams": ("known", "still-unknown"),
    "process_text": ("known", "still-unknown", "conflicting"),
}


@dataclass(frozen=True)
class BranchImpact:
    action_bucket_changed: bool
    top_candidate_changed: bool
    high_risk_changed: bool
    explanation_changed: bool
    old_action_bucket: str
    new_action_bucket: str
    old_top_candidate_id: object | None
    new_top_candidate_id: object | None
    resolved_risks: tuple[str, ...]
    added_risks: tuple[str, ...]
    impact_level: int


def simulate_decision_branch(*, need: dict[str, Any], inputs: list[dict[str, Any]], original_decisions: list[dict[str, Any]], target_candidate_id: object, field_key: str, assumed_value: str, rules: tuple[DecisionRule, ...]) -> BranchImpact:
    """Evaluate one whitelisted answer branch without mutating persisted evidence."""
    if field_key not in ANSWER_BRANCHES or assumed_value not in ANSWER_BRANCHES[field_key]:
        raise ValueError("unsupported question branch")
    changed_inputs = [_replace_field(item, field_key, assumed_value) if item["candidate_id"] == target_candidate_id else item for item in inputs]
    drafts = [evaluate_candidate(candidate_id=item["candidate_id"], extraction_version_id=item["extraction_version_id"], need=need, evidence=item["evidence"], rules=rules) for item in changed_inputs]
    ranked = rank_within_buckets(drafts)
    old = next(item for item in original_decisions if item["candidate_id"] == target_candidate_id)
    new = next(item for item in ranked if item.candidate_id == target_candidate_id)
    old_top = min(original_decisions, key=lambda item: item["overall_order"])["candidate_id"]
    new_top = ranked[0].candidate_id if ranked else None
    resolved = tuple(flag for flag in old["risk_flags"] if flag not in new.risk_flags)
    added = tuple(flag for flag in new.risk_flags if flag not in old["risk_flags"])
    action_changed = old["action_bucket"] != new.action_bucket.value
    top_changed = old_top != new_top
    risk_changed = bool(resolved or added)
    explanation_changed = tuple(old["reasons"]) != new.reasons
    level = 4 if action_changed else 3 if top_changed else 2 if risk_changed else 1 if explanation_changed else 0
    return BranchImpact(action_changed, top_changed, risk_changed, explanation_changed, old["action_bucket"], new.action_bucket.value, old_top, new_top, resolved, added, level)


def _replace_field(item: dict[str, Any], field_key: str, value: str) -> dict[str, Any]:
    evidence = [dict(row) for row in item["evidence"]]
    normalized = _normalized(field_key, value)
    for row in evidence:
        if row.get("field_name") == field_key:
            row["normalized_value"] = normalized
            row["information_status"] = "unknown" if value == "still-unknown" else "conflict" if value == "conflicting" else "explicit"
            break
    else:
        evidence.append({"field_name": field_key, "normalized_value": normalized, "information_status": "unknown" if value == "still-unknown" else "explicit"})
    return {**item, "evidence": evidence}


def _normalized(field_key: str, value: str) -> str | None:
    if value == "still-unknown": return None
    if field_key == "sample_available": return "true" if value == "yes" else "false"
    if field_key == "price": return "999999" if value == "over-budget" else "0" if value == "within-budget" else None
    return value
