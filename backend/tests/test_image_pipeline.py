from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from guancha_api.infrastructure.image_pipeline import (
    ImageSafetyLimits,
    UnsafeImageError,
    sanitize_image_upload,
)
from guancha_api.schemas.contracts import ErrorCode


def _make_image_bytes(
    *, image_format: str, width: int = 80, height: int = 80, with_exif: bool = False
) -> bytes:
    image = Image.new("RGB", (width, height), color=(32, 96, 48))
    output = BytesIO()
    options: dict[str, object] = {}
    if with_exif:
        exif = Image.Exif()
        exif[274] = 3
        options["exif"] = exif
    image.save(output, format=image_format, **options)
    return output.getvalue()


def test_sanitize_jpeg_reencodes_and_removes_exif() -> None:
    original = _make_image_bytes(image_format="JPEG", with_exif=True)

    sanitized = sanitize_image_upload(data=original, declared_content_type="image/jpeg")

    assert sanitized.content_type == "image/jpeg"
    assert sanitized.width == 80
    assert sanitized.height == 80
    assert sanitized.source_sha256 != sanitized.sanitized_sha256
    assert sanitized.data != original
    with Image.open(BytesIO(sanitized.data)) as image:
        assert image.format == "JPEG"
        assert image.getexif() == {}
        assert not image.info.get("exif")


def test_sanitize_png_returns_clean_private_storage_payload() -> None:
    sanitized = sanitize_image_upload(
        data=_make_image_bytes(image_format="PNG"), declared_content_type="image/png"
    )

    assert sanitized.content_type == "image/png"
    assert sanitized.size_bytes == len(sanitized.data)
    with Image.open(BytesIO(sanitized.data)) as image:
        assert image.format == "PNG"
        assert image.info == {}


def test_rejects_invalid_or_mismatched_image_data() -> None:
    with pytest.raises(UnsafeImageError) as invalid:
        sanitize_image_upload(data=b"not an image", declared_content_type="image/png")
    assert invalid.value.error_code is ErrorCode.UNSAFE_OR_CORRUPT_IMAGE

    with pytest.raises(UnsafeImageError) as mismatch:
        sanitize_image_upload(
            data=_make_image_bytes(image_format="JPEG"), declared_content_type="image/png"
        )
    assert mismatch.value.error_code is ErrorCode.UNSAFE_OR_CORRUPT_IMAGE


def test_rejects_unsupported_type_oversize_and_extreme_pixel_limit() -> None:
    with pytest.raises(UnsafeImageError) as type_error:
        sanitize_image_upload(data=b"x", declared_content_type="image/webp")
    assert type_error.value.error_code is ErrorCode.INVALID_IMAGE_TYPE

    with pytest.raises(UnsafeImageError) as size_error:
        sanitize_image_upload(
            data=b"x" * 11,
            declared_content_type="image/png",
            limits=ImageSafetyLimits(max_input_bytes=10),
        )
    assert size_error.value.error_code is ErrorCode.IMAGE_TOO_LARGE

    with pytest.raises(UnsafeImageError) as pixel_limit:
        sanitize_image_upload(
            data=_make_image_bytes(image_format="PNG", width=80, height=80),
            declared_content_type="image/png",
            limits=ImageSafetyLimits(max_pixels=1_000),
        )
    assert pixel_limit.value.error_code is ErrorCode.IMAGE_PIXEL_LIMIT_EXCEEDED


def test_rejects_highly_compressed_pixel_bomb_before_pixel_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A 5000x5000 solid PNG compresses far below 5 MB but exceeds the 20M
    # pixel budget. ``load`` must never run before the header-size guard.
    payload = _make_image_bytes(image_format="PNG", width=5_000, height=5_000)
    assert len(payload) < 5_242_880

    def fail_if_loaded(self: Image.Image) -> None:
        raise AssertionError("pixel data must not be decoded before the limit check")

    monkeypatch.setattr(Image.Image, "load", fail_if_loaded)
    with pytest.raises(UnsafeImageError) as pixel_limit:
        sanitize_image_upload(data=payload, declared_content_type="image/png")
    assert pixel_limit.value.error_code is ErrorCode.IMAGE_PIXEL_LIMIT_EXCEEDED


def test_low_resolution_is_warning_and_normal_large_image_is_scaled() -> None:
    low = sanitize_image_upload(data=_make_image_bytes(image_format="PNG", width=100, height=400), declared_content_type="image/png")
    assert low.warnings == ("low_resolution",)
    large = sanitize_image_upload(data=_make_image_bytes(image_format="JPEG", width=3000, height=1000), declared_content_type="image/jpeg")
    assert (large.width, large.height) == (2048, 683)
