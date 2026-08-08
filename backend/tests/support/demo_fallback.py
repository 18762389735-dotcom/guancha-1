"""Exact, auditable fallback for the three project-owned demo images.

This is deliberately not image recognition: it compares the normalized image
set fingerprint to an approved manifest entry after the provider has failed.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable
from uuid import UUID

from tests.support.fixture_catalog import FixtureCatalog, ExtractionFixture


EXTRACTION_CONTRACT_VERSION = "phase3-joint-images-v1"
DOMAIN = "tieguanyin"
PROMPT_VERSION = "openai-responses-v1"


def image_set_fingerprint(images: Iterable[tuple[int, str]]) -> str:
    """Hash a canonical order/hash sequence; no filename or perceptual match."""
    canonical = "|".join(f"{order}:{digest.lower()}" for order, digest in sorted(images))
    return sha256(canonical.encode("ascii")).hexdigest()


def fixture_cache_key(*, candidate_id: UUID, image_fingerprint: str) -> str:
    """Candidate-scoped fallback key.

    Two candidates may upload byte-identical images, but must never share a
    cache resource or an ExtractionVersion.  The candidate UUID is therefore
    part of the cache identity, while ``image_set_fingerprint`` remains a
    reusable integrity description of the ordered sanitized pixels.
    """
    material = "|".join((DOMAIN, "prd-fixture-v1", EXTRACTION_CONTRACT_VERSION, str(candidate_id), image_fingerprint))
    return sha256(material.encode("ascii")).hexdigest()


class DemoFallbackCatalog:
    def __init__(self, catalog: FixtureCatalog | None = None) -> None:
        self.catalog = catalog or FixtureCatalog()

    def match(self, *, candidate_id: UUID, images: Iterable[tuple[int, str]]) -> ExtractionFixture | None:
        actual = tuple(images)
        actual_fingerprint = image_set_fingerprint(actual)
        # Compute the full cache identity before checking its fixture payload.
        # It is intentionally candidate-scoped even where only a single
        # project fixture hash can match semantic data.
        cache_key = fixture_cache_key(candidate_id=candidate_id, image_fingerprint=actual_fingerprint)
        if not cache_key:
            return None
        for item in self.catalog.demo_image_set_fixtures():
            if not item.approved_for_cache_fallback:
                continue
            if (
                actual_fingerprint != item.image_set_fingerprint
                or item.fixture_schema_version != "prd-fixture-v1"
                or item.extraction_schema_version != EXTRACTION_CONTRACT_VERSION
                or item.prompt_version != PROMPT_VERSION
                or item.domain != DOMAIN
            ):
                continue
            # Bind the result to all schema/contract dimensions.  A stale
            # fixture is never silently reinterpreted under a new provider DTO.
            if item.extraction_fixture_id not in self.catalog.fixture_ids():
                continue
            fixture = self.catalog.load(item.extraction_fixture_id)
            if isinstance(fixture, ExtractionFixture):
                return fixture
        return None
