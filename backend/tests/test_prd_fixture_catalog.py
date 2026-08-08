from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.support.fixture_catalog import (
    CORE_FIELDS,
    FixtureCatalog,
    FixtureCatalogError,
    MerchantReplyFixture,
)
from guancha_api.domain.tieguanyin.rules import load_approved_rules, load_rules
from guancha_api.schemas.contracts import (
    ActionBucket,
    EvidenceSourceType,
    InformationStatus,
    VerificationStatus,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "test-fixtures"


def test_manifest_references_existing_unique_project_owned_fixtures() -> None:
    catalog = FixtureCatalog(FIXTURE_ROOT)

    assert len(catalog.fixture_ids()) == 12
    assert len(set(catalog.fixture_ids())) == 12
    for fixture_id in catalog.fixture_ids():
        assert catalog.load(fixture_id).fixture_id == fixture_id


def test_unknown_fixture_is_rejected() -> None:
    with pytest.raises(FixtureCatalogError, match="unknown fixture_id"):
        FixtureCatalog(FIXTURE_ROOT).load("not-in-manifest")


def test_three_prd_fixed_candidates_preserve_required_semantics() -> None:
    catalog = FixtureCatalog(FIXTURE_ROOT)
    candidate_a = catalog.load("candidate-a-complete-qingxiang")
    candidate_b = catalog.load("candidate-b-nongxiang-unknown-roast")
    candidate_c = catalog.load("candidate-c-marketing-heavy")

    assert set(candidate_a.fields) == CORE_FIELDS
    assert candidate_a.fields["tea_type"] == "tieguanyin"
    assert candidate_a.fields["aroma_style"] == "qingxiang"
    assert candidate_a.fields["season"] == "spring"
    assert candidate_a.fields["roast_level"] == "light"
    assert candidate_a.fields["price"] is not None
    assert candidate_a.fields["weight_grams"] is not None
    assert candidate_a.fields["sample_available"] is True

    assert candidate_b.fields["tea_type"] == "tieguanyin"
    assert candidate_b.fields["aroma_style"] == "nongxiang"
    assert candidate_b.fields["roast_level"] == "unknown"

    assert candidate_c.fields["marketing_claims"] == ["高山", "兰花香", "大师", "核心产区", "老客户复购"]
    for field in ("aroma_style", "season", "roast_level", "sample_available"):
        assert candidate_c.fields[field] in {"unknown", None}


def test_extraction_boundaries_keep_unknown_conflict_and_unit_price_guardrails() -> None:
    catalog = FixtureCatalog(FIXTURE_ROOT)
    missing_price = catalog.load("boundary-missing-price")
    missing_weight = catalog.load("boundary-missing-weight")
    unknown_roast = catalog.load("boundary-unknown-roast")
    conflicting = catalog.load("boundary-conflicting-fields")

    assert missing_price.fields["price"] is None
    assert missing_price.fields["unit_price"] is None
    assert missing_weight.fields["weight_grams"] is None
    assert missing_weight.fields["unit_price"] is None
    assert unknown_roast.fields["roast_level"] == "unknown"
    assert conflicting.fields["conflicts"] == ["season"]
    seasons = [item for item in conflicting.evidence if item.field_name == "season"]
    assert len(seasons) == 2
    assert {item.source_type for item in seasons} == {
        EvidenceSourceType.PRODUCT_CLAIM,
        EvidenceSourceType.MERCHANT_CLAIM,
    }
    assert any(item.information_status == InformationStatus.CONFLICT for item in seasons)


def test_screenshot_evidence_is_unverified_product_claim() -> None:
    catalog = FixtureCatalog(FIXTURE_ROOT)
    for fixture_id in catalog.fixture_ids():
        fixture = catalog.load(fixture_id)
        if isinstance(fixture, MerchantReplyFixture):
            continue
        for evidence in fixture.evidence:
            if evidence.source_type == EvidenceSourceType.PRODUCT_CLAIM:
                assert evidence.verification_status == VerificationStatus.UNVERIFIED


def test_merchant_reply_fixtures_preserve_append_only_claim_semantics() -> None:
    catalog = FixtureCatalog(FIXTURE_ROOT)
    answered = catalog.load("merchant-answered")
    partial = catalog.load("merchant-partially-answered")
    evasive = catalog.load("merchant-evasive")
    conflicting = catalog.load("merchant-conflicting")

    assert isinstance(answered, MerchantReplyFixture)
    assert answered.expected_reply_status == "answered"
    assert partial.expected_reply_status == "partial"
    assert partial.unresolved_fields == ("season",)
    assert evasive.expected_reply_status == "evasive"
    assert evasive.expected_claims == ()
    assert conflicting.expected_reply_status == "conflicting"
    assert conflicting.expected_conflicts == ("season",)
    for fixture in (answered, partial, conflicting):
        for claim in fixture.expected_claims:
            assert claim.source_type == EvidenceSourceType.MERCHANT_CLAIM
            assert claim.verification_status == VerificationStatus.UNVERIFIED


def test_decision_rules_are_safely_loaded_and_only_approved_rules_execute() -> None:
    rules = load_rules()

    assert [rule.rule_id for rule in rules] == [
        "RULE-PRICE-001",
        "RULE-ROAST-001",
        "RULE-STYLE-001",
        "RULE-MARKETING-001",
        "RULE-INFO-TRANSPARENCY-001",
    ]
    assert {rule.status for rule in rules} == {"approved"}
    assert {rule.action_bucket for rule in rules} <= set(ActionBucket)
    assert load_approved_rules() == rules


def test_fixture_data_has_no_paths_keys_or_legacy_database_dependencies() -> None:
    for path in FIXTURE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            # Binary fixture artwork is checked by the manifest/hash test;
            # treating it as UTF-8 would hide image fixtures from the catalog.
            continue
        value = path.read_text(encoding="utf-8")
        assert not re.search(r"(?:[A-Za-z]:\\\\|\\\\\\\\)", value)
        assert not re.search(r"(?:sk-[A-Za-z0-9]|OPENAI_API_KEY|Authorization|Bearer\\s+)", value, re.IGNORECASE)
        assert "legacy_database_id" not in value
        assert '"verification_status":"verified"' not in value
