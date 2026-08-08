from __future__ import annotations

from uuid import uuid4

from tests.support.demo_fallback import DemoFallbackCatalog, fixture_cache_key, image_set_fingerprint
from tests.support.fixture_catalog import FixtureCatalog, ExtractionFixture
from guancha_api.infrastructure.image_pipeline import sanitize_image_upload


def test_demo_images_are_safe_and_hash_stable() -> None:
    catalog = FixtureCatalog()
    for image in catalog.demo_image_fixtures():
        data = (catalog.root.parent / image.path).read_bytes()
        sanitized = sanitize_image_upload(data=data, declared_content_type=image.mime_type)
        assert sanitized.sanitized_sha256 == image.sha256
        assert (sanitized.width, sanitized.height) == (image.width, image.height)


def test_image_set_fingerprint_is_exact_and_order_canonical() -> None:
    a = "a" * 64
    b = "b" * 64
    assert image_set_fingerprint(((1, a), (2, b))) == image_set_fingerprint(((2, b), (1, a)))
    assert image_set_fingerprint(((1, a),)) != image_set_fingerprint(((1, a), (2, b)))


def test_only_approved_exact_demo_images_match_fallback() -> None:
    catalog = FixtureCatalog()
    fallback = DemoFallbackCatalog(catalog)
    images = {image.fixture_id: image for image in catalog.demo_image_fixtures()}
    for image_set in catalog.demo_image_set_fixtures():
        pair = tuple((images[image_id].display_order, images[image_id].sha256) for image_id in image_set.image_fixture_ids)
        result = fallback.match(candidate_id=uuid4(), images=pair)
        assert isinstance(result, ExtractionFixture)
        assert result.fixture_id == image_set.extraction_fixture_id
        assert fallback.match(candidate_id=uuid4(), images=pair[:1]) is None
    assert fallback.match(candidate_id=uuid4(), images=((1, "0" * 64),)) is None


def test_cache_key_binds_current_candidate_context() -> None:
    fingerprint = image_set_fingerprint(((1, "a" * 64),))
    assert fixture_cache_key(candidate_id=uuid4(), image_fingerprint=fingerprint) != fixture_cache_key(candidate_id=uuid4(), image_fingerprint=fingerprint)
