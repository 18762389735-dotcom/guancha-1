"""Offline Phase 9 Decision validation artifact generator.

This script uses the frozen Decision domain only.  It makes no provider or
network call, never loads images, and stores no raw user image material.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID, uuid5

from guancha_api.domain.tieguanyin.decision import evaluate_candidate, rank_within_buckets
from guancha_api.domain.tieguanyin.rules import load_approved_rules


NAMESPACE = UUID("07f10ea6-0f39-4513-bd32-4bb7c3a327a1")
RULES = load_approved_rules()
FULL = {"tea_type": "tieguanyin", "aroma_style": "qingxiang", "roast_level": "light", "season": "spring"}


def evidence(values: dict[str, object]) -> list[dict[str, object]]:
    return [
        {"field_name": field, "normalized_value": value, "information_status": "unknown" if value is None else "explicit"}
        for field, value in values.items()
    ]


def draft(case_id: str, need: dict[str, object], values: dict[str, object]):
    return evaluate_candidate(
        candidate_id=uuid5(NAMESPACE, f"candidate:{case_id}"),
        extraction_version_id=uuid5(NAMESPACE, f"version:{case_id}"),
        need=need,
        evidence=evidence(values),
        rules=RULES,
    )


def serialize(case_id: str, source: str, need: dict[str, object], values: dict[str, object]) -> dict[str, object]:
    result = draft(case_id, need, values)
    return {
        "case_id": case_id,
        "source": source,
        "candidate_id": str(result.candidate_id),
        "extraction_version_id": str(result.extraction_version_id),
        "need": need,
        "evidence_version": "phase2-frozen-contract",
        "actual": {
            "action_bucket": result.action_bucket.value,
            "score_components": result.score_components,
            "internal_score": str(result.internal_score),
            "missing_critical_fields": list(result.missing_critical_fields),
        },
    }


def serialize_real_extraction(case_id: str, prediction: dict[str, object]) -> dict[str, object]:
    """Adapt frozen extraction Evidence to existing Decision input names.

    This is an evaluation-only field-name adapter, not a normalizer: values and
    information statuses come directly from the frozen real output.
    """
    extraction = prediction.get("extraction", {})
    source_rows = extraction.get("evidence", []) if isinstance(extraction, dict) else []
    by_field = {str(row.get("field_name")): row for row in source_rows if isinstance(row, dict)}
    aliases = {
        "tea_type": "tea_subtype",
        "aroma_style": "roast_or_style",
        "season": "season",
        "price": "price",
        "sample_available": "sample_available",
    }
    adapted = []
    for target, source in aliases.items():
        row = by_field.get(source)
        if row:
            adapted.append({"field_name": target, "normalized_value": row.get("normalized_value"), "information_status": row.get("information_status")})
    result = evaluate_candidate(
        candidate_id=uuid5(NAMESPACE, f"candidate:{case_id}"),
        extraction_version_id=uuid5(NAMESPACE, f"version:{case_id}"),
        need={},
        evidence=adapted,
        rules=RULES,
    )
    return {
        "case_id": case_id,
        "source": "real_frozen_extraction",
        "candidate_id": str(result.candidate_id),
        "extraction_version_id": str(result.extraction_version_id),
        "need": {},
        "evidence_version": str(prediction.get("schema_version", "unknown")),
        "real_evidence_fields": [row["field_name"] for row in adapted],
        "actual": {"action_bucket": result.action_bucket.value, "score_components": result.score_components, "internal_score": str(result.internal_score), "missing_critical_fields": list(result.missing_critical_fields)},
    }


def run(output: Path, real_holdout: Path | None) -> int:
    output.mkdir(parents=True, exist_ok=True)
    personas: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    budgets = [20, 50, 100, 200, 500]
    styles = ["qingxiang", "nongxiang", "chenxiang"]
    purposes = ["self", "gift", "office", "explore"]
    for budget in budgets:
        for style in styles:
            for purpose in purposes:
                for price in ("88", "288"):
                    case_id = f"PERSONA-{budget}-{style}-{purpose}-{price}"
                    personas.append(serialize(case_id, "synthetic_decision_fixture", {"budget_text": str(budget), "taste_text": style, "purpose_text": purpose}, {**FULL, "price": price}))

    # The real holdout is read only as a provenance count.  It remains frozen;
    # no extraction field is rewritten and no image is copied into evaluation output.
    real_ids: list[str] = []
    if real_holdout and real_holdout.exists():
        payload = json.loads(real_holdout.read_text(encoding="utf-8"))
        predictions = payload.get("predictions", [])
        real_ids = [str(item.get("asset_id")) for item in predictions if isinstance(item, dict)]
        for prediction in predictions:
            if isinstance(prediction, dict):
                personas.append(serialize_real_extraction(f"REAL-{prediction.get('asset_id')}", prediction))

    pairwise: list[dict[str, object]] = []
    for budget in budgets:
        for style in ("qingxiang", "nongxiang"):
            good = draft(f"PAIR-good-{budget}-{style}", {"budget_text": str(budget), "taste_text": style}, {**FULL, "aroma_style": style, "price": str(min(budget, 88))})
            bad = draft(f"PAIR-bad-{budget}-{style}", {"budget_text": str(budget), "taste_text": style}, {**FULL, "aroma_style": "nongxiang" if style == "qingxiang" else "qingxiang", "price": "999"})
            ordered = rank_within_buckets([bad, good])
            passed = ordered[0].candidate_id == good.candidate_id
            item = {"case_id": f"PAIR-{budget}-{style}", "classification": "ranking_direction_violation", "passed": passed, "winner_candidate_id": str(ordered[0].candidate_id)}
            pairwise.append(item)
            if not passed:
                failures.append(item)

    metamorphic: list[dict[str, object]] = []
    checks = {
        "M1_budget_monotonicity": lambda: draft("m1a", {"budget_text": "150"}, {**FULL, "price": "100"}).score_components["budget_fit"] >= draft("m1b", {"budget_text": "50"}, {**FULL, "price": "100"}).score_components["budget_fit"],
        "M2_aroma_preference": lambda: draft("m2a", {"taste_text": "qingxiang"}, FULL).score_components["need_match"] > draft("m2b", {"taste_text": "nongxiang"}, FULL).score_components["need_match"],
        "M3_roast_preference": lambda: draft("m3a", {"taste_text": "accept heavy roast"}, {**FULL, "roast_level": "heavy"}).score_components["need_match"] > draft("m3b", {"taste_text": "avoid roast"}, {**FULL, "roast_level": "heavy"}).score_components["need_match"],
        "M4_trial_boundary": lambda: draft("m4", {"risk_attitude_text": "try"}, {**FULL, "sample_available": "true"}).action_bucket.value == "sample-first",
        "M5_marketing_invariance": lambda: draft("m5a", {}, {"tea_type": "tieguanyin", "aroma_style": None, "roast_level": None, "season": None}).action_bucket == draft("m5b", {}, {"tea_type": "tieguanyin", "aroma_style": None, "roast_level": None, "season": None, "marketing_claims": "master high-mountain"}).action_bucket,
        "M6_unknown_safety": lambda: draft("m6a", {}, FULL).score_components["evidence_sufficiency"] > draft("m6b", {}, {**FULL, "aroma_style": None}).score_components["evidence_sufficiency"],
        "M7_conflict_risk": lambda: draft(
            "m7", {}, {**FULL}
        ).internal_score > evaluate_candidate(
            candidate_id=uuid5(NAMESPACE, "candidate:m7-conflict"),
            extraction_version_id=uuid5(NAMESPACE, "version:m7-conflict"),
            need={},
            evidence=evidence(FULL) + [{"field_name": "season", "normalized_value": "autumn", "information_status": "conflict"}],
            rules=RULES,
        ).internal_score,
        "M8_need_priority": lambda: rank_within_buckets([draft("m8a", {"taste_text": "qingxiang"}, {**FULL, "aroma_style": "nongxiang"}), draft("m8b", {"taste_text": "qingxiang"}, FULL)])[0].candidate_id == draft("m8b", {"taste_text": "qingxiang"}, FULL).candidate_id,
        "M9_unknown_price": lambda: draft("m9", {"budget_text": "50"}, {**FULL, "price": None}).action_bucket.value == "ask-before-buying",
        "M10_unknown_sample": lambda: draft("m10", {"risk_attitude_text": "try"}, {**FULL, "sample_available": None}).score_components["trial_friendliness"] == 0,
    }
    classification = {
        "M1_budget_monotonicity": "budget_monotonicity_violation", "M2_aroma_preference": "aroma_preference_violation", "M3_roast_preference": "roast_preference_violation", "M4_trial_boundary": "sample_boundary_violation", "M5_marketing_invariance": "marketing_claim_leak", "M6_unknown_safety": "unknown_as_known", "M7_conflict_risk": "conflict_risk_violation", "M8_need_priority": "preference_priority_violation", "M9_unknown_price": "budget_monotonicity_violation", "M10_unknown_sample": "sample_boundary_violation",
    }
    for name, check in checks.items():
        passed = bool(check())
        item = {"case_id": name, "classification": classification[name], "passed": passed}
        metamorphic.append(item)
        if not passed:
            failures.append(item)

    (output / "decision-persona-cases-v0.1.json").write_text(json.dumps({"case_count": len(personas), "real_holdout_ids": real_ids, "cases": personas}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "decision-pairwise-results-v0.1.json").write_text(json.dumps({"case_count": len(pairwise), "results": pairwise}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "decision-metamorphic-results-v0.1.json").write_text(json.dumps({"case_count": len(metamorphic), "results": metamorphic}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "decision-failures-v0.1.json").write_text(json.dumps({"failure_count": len(failures), "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    total = len(personas) + len(pairwise) + len(metamorphic)
    summary = f"# Decision Eval v0.1\n\n- Total cases: {total}\n- Persona cases: {len(personas)}\n- Pairwise cases: {len(pairwise)}\n- Metamorphic checks: {len(metamorphic)}\n- Frozen real extraction cases: {len(real_ids)} ({', '.join(real_ids) or 'none'})\n- Failures: {len(failures)}\n- Vision/provider calls: 0\n\nThe real cases are driven by frozen `predictions[].extraction.evidence` through an evaluation-only field-name adapter. The remaining cases are deterministic Decision fixtures. No images are stored here.\n"
    (output / "decision-eval-summary-v0.1.md").write_text(summary, encoding="utf-8")
    return len(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-holdout", type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.real_holdout))
