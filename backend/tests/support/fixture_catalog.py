from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from guancha_api.schemas.contracts import (
    EvidenceSourceType,
    EvidenceStrength,
    InformationStatus,
    VerificationStatus,
)


FIXTURE_SCHEMA_VERSION = "prd-fixture-v1"
CORE_FIELDS = frozenset(
    {
        "tea_type",
        "aroma_style",
        "roast_level",
        "season",
        "origin_text",
        "year_or_batch",
        "process_text",
        "price",
        "weight_grams",
        "unit_price",
        "sample_available",
        "return_policy",
        "marketing_claims",
        "missing_fields",
        "conflicts",
    }
)
_SECRET_PATTERN = re.compile(r"(?:api[_-]?key|authorization|bearer\s+|sk-[a-z0-9])", re.IGNORECASE)
_WINDOWS_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|\\\\)")


class FixtureCatalogError(ValueError):
    """Fixture files are malformed, unsafe, or absent from the manifest."""


class FixtureEvidence(BaseModel):
    """Test DTO preserving the frozen Evidence enums without database identifiers."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=100)
    raw_text: str | None = Field(default=None, max_length=4000)
    normalized_value: str | None = Field(default=None, max_length=2000)
    information_status: InformationStatus
    source_type: EvidenceSourceType
    verification_status: VerificationStatus
    evidence_strength: EvidenceStrength
    source_image_id: str | None = Field(default=None, max_length=120)
    source_location: str = Field(min_length=1, max_length=200)


class ExtractionFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    schema_version: Literal["prd-fixture-v1"]
    fixture_kind: Literal["extraction"] = "extraction"
    fields: dict[str, Any]
    evidence: tuple[FixtureEvidence, ...]

    @field_validator("fields")
    @classmethod
    def require_exact_prd_core_fields(cls, value: dict[str, Any]) -> dict[str, Any]:
        if set(value) != CORE_FIELDS:
            missing = sorted(CORE_FIELDS - set(value))
            unexpected = sorted(set(value) - CORE_FIELDS)
            raise ValueError(f"fields must equal PRD core fields; missing={missing}, unexpected={unexpected}")
        return value

    @model_validator(mode="after")
    def require_product_evidence_to_remain_unverified(self) -> "ExtractionFixture":
        for evidence in self.evidence:
            if evidence.source_type == EvidenceSourceType.PRODUCT_CLAIM and (
                evidence.verification_status != VerificationStatus.UNVERIFIED
            ):
                raise ValueError("product screenshot evidence must remain unverified")
        return self


class MerchantReplyFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    schema_version: Literal["prd-fixture-v1"]
    fixture_kind: Literal["merchant-reply"] = "merchant-reply"
    original_question: str = Field(min_length=1, max_length=500)
    merchant_text: str = Field(min_length=1, max_length=4000)
    expected_reply_status: Literal["answered", "partial", "evasive", "conflicting"]
    expected_claims: tuple[FixtureEvidence, ...]
    unresolved_fields: tuple[str, ...]
    expected_conflicts: tuple[str, ...]
    should_trigger_rejudgement: bool

    @model_validator(mode="after")
    def require_merchant_claims_to_remain_unverified(self) -> "MerchantReplyFixture":
        for evidence in self.expected_claims:
            if evidence.source_type != EvidenceSourceType.MERCHANT_CLAIM:
                raise ValueError("merchant reply fixture claims must use merchant-claim")
            if evidence.verification_status != VerificationStatus.UNVERIFIED:
                raise ValueError("merchant claims must remain unverified")
        return self


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    fixture_type: Literal["extraction", "merchant-reply"]
    path: str = Field(pattern=r"^[a-z0-9_./-]+$")
    prd_section: str = Field(min_length=1)
    legacy_source_file: str = Field(min_length=1)
    legacy_case_id: str = Field(min_length=1)
    conversion_notes: str = Field(min_length=1)
    schema_version: Literal["prd-fixture-v1"]
    expected_use: tuple[str, ...] = Field(min_length=1)
    contains_original_image: Literal[False] = False


class FixtureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["prd-fixture-v1"]
    fixtures: tuple[ManifestEntry, ...]
    demo_images: tuple["DemoImageFixture", ...] = ()
    demo_image_sets: tuple["DemoImageSetFixture", ...] = ()

    @model_validator(mode="after")
    def require_unique_fixture_ids(self) -> "FixtureManifest":
        ids = [entry.fixture_id for entry in self.fixtures]
        if len(ids) != len(set(ids)):
            raise ValueError("fixture_id values must be globally unique")
        return self


class DemoImageFixture(BaseModel):
    """A project-owned, privacy-safe image approved for demo fallback.

    ``sha256`` is the hash of the sanitized pixels, not a filename or visual
    similarity signal.  The original bytes are retained only as a second
    integrity check in the manifest.
    """

    model_config = ConfigDict(extra="forbid")

    fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    candidate_fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    image_role: Literal["product-screenshot"]
    display_order: int = Field(ge=1, le=2)
    path: str = Field(pattern=r"^[a-z0-9_./\-\u4e00-\u9fff]+$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mime_type: Literal["image/jpeg", "image/png"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fixture_schema_version: Literal["prd-fixture-v1"]
    extraction_fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    decision_expectation_id: str = Field(min_length=1)
    approved_for_cache_fallback: bool = False
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class DemoImageSetFixture(BaseModel):
    """Approved two-image product set and its complete fallback contract."""
    model_config = ConfigDict(extra="forbid")

    candidate_fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    image_fixture_ids: tuple[str, str]
    image_set_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_schema_version: Literal["prd-fixture-v1"]
    extraction_schema_version: Literal["phase3-joint-images-v1"]
    prompt_version: Literal["openai-responses-v1"]
    domain: Literal["tieguanyin"]
    extraction_fixture_id: str = Field(pattern=r"^[a-z0-9-]+$")
    approved_for_cache_fallback: bool = False


class FixtureCatalog:
    """Read-only catalog for project-owned fixtures; it never reads legacy assets."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3] / "test-fixtures"
        self._manifest: FixtureManifest | None = None

    def manifest(self) -> FixtureManifest:
        if self._manifest is None:
            self._manifest = self._validate_manifest(self._load_json(self.root / "manifest.yaml"))
        return self._manifest

    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(entry.fixture_id for entry in self.manifest().fixtures)

    def demo_image_fixtures(self) -> tuple[DemoImageFixture, ...]:
        """Return only project-owned image fixtures declared by the manifest."""
        return self.manifest().demo_images

    def demo_image_set_fixtures(self) -> tuple[DemoImageSetFixture, ...]:
        return self.manifest().demo_image_sets

    def load(self, fixture_id: str) -> ExtractionFixture | MerchantReplyFixture:
        entry = next((item for item in self.manifest().fixtures if item.fixture_id == fixture_id), None)
        if entry is None:
            raise FixtureCatalogError(f"unknown fixture_id: {fixture_id}")
        document = self._load_json(self.root / entry.path)
        try:
            fixture = ExtractionFixture.model_validate(document) if entry.fixture_type == "extraction" else MerchantReplyFixture.model_validate(document)
        except ValidationError as error:
            raise FixtureCatalogError(f"invalid fixture {fixture_id}: {error}") from error
        if fixture.fixture_id != entry.fixture_id or fixture.schema_version != entry.schema_version:
            raise FixtureCatalogError(f"fixture {fixture_id} does not match manifest metadata")
        self._assert_safe(document)
        return fixture

    def _validate_manifest(self, document: Any) -> FixtureManifest:
        try:
            manifest = FixtureManifest.model_validate(document)
        except ValidationError as error:
            raise FixtureCatalogError(f"invalid fixture manifest: {error}") from error
        self._assert_safe(document)
        for entry in manifest.fixtures:
            path = (self.root / entry.path).resolve()
            if self.root.resolve() not in path.parents or not path.is_file():
                raise FixtureCatalogError(f"manifest references missing or unsafe path: {entry.path}")
        for image in manifest.demo_images:
            # Demo images are committed, project-owned fixture artwork.  The
            # allow-list deliberately excludes historical desktop asset trees.
            path = (self.root.parent / image.path).resolve()
            demo_root = (self.root / "demo-images").resolve()
            if demo_root not in path.parents or not path.is_file():
                raise FixtureCatalogError(f"manifest references missing or unsafe demo image: {image.path}")
            if sha256(path.read_bytes()).hexdigest() != image.source_sha256:
                raise FixtureCatalogError(f"demo image source hash mismatch: {image.fixture_id}")
        images = {item.fixture_id: item for item in manifest.demo_images}
        for image_set in manifest.demo_image_sets:
            try:
                members = tuple(images[item_id] for item_id in image_set.image_fixture_ids)
            except KeyError as error:
                raise FixtureCatalogError("demo image set references an unknown image") from error
            if any(member.candidate_fixture_id != image_set.candidate_fixture_id for member in members):
                raise FixtureCatalogError("demo image set mixes candidate fixtures")
            canonical = "|".join(f"{item.display_order}:{item.sha256}" for item in sorted(members, key=lambda item: item.display_order))
            if sha256(canonical.encode("ascii")).hexdigest() != image_set.image_set_fingerprint:
                raise FixtureCatalogError("demo image set fingerprint mismatch")
        return manifest

    @staticmethod
    def _load_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise FixtureCatalogError(f"cannot read fixture document {path.name}: {error}") from error

    @staticmethod
    def _assert_safe(value: Any) -> None:
        rendered = json.dumps(value, ensure_ascii=False)
        if _WINDOWS_PATH_PATTERN.search(rendered):
            raise FixtureCatalogError("fixtures must not contain absolute Windows paths")
        if _SECRET_PATTERN.search(rendered):
            raise FixtureCatalogError("fixtures must not contain API keys or authorization data")
