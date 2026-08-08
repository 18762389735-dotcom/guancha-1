from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from guancha_api.schemas.contracts import ErrorCode


_CONTENT_TYPE_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png"}
_SAVE_FORMAT_BY_CONTENT_TYPE = {"image/jpeg": "JPEG", "image/png": "PNG"}


class UnsafeImageError(ValueError):
    """An image was rejected before it could enter temporary storage."""

    def __init__(self, error_code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class ImageSafetyLimits:
    max_input_bytes: int = 5_242_880
    max_pixels: int = 20_000_000
    max_dimension: int = 16_384
    output_max_dimension: int = 2_048
    unusable_min_dimension: int = 64


@dataclass(frozen=True, slots=True)
class SanitizedImage:
    """The only image payload eligible for temporary private storage."""

    content_type: str
    data: bytes
    width: int
    height: int
    source_sha256: str
    sanitized_sha256: str
    warnings: tuple[str, ...] = ()

    @property
    def size_bytes(self) -> int:
        return len(self.data)


def sanitize_image_upload(
    *,
    data: bytes,
    declared_content_type: str,
    limits: ImageSafetyLimits = ImageSafetyLimits(),
) -> SanitizedImage:
    """Decode, inspect and re-encode one JPEG/PNG without EXIF or metadata.

    The client MIME is never trusted: it must agree with the decoded format and
    file signature handled by Pillow. Metadata is removed by copying pixels into a
    fresh image and writing a new encoded byte stream.
    """

    if declared_content_type not in _SAVE_FORMAT_BY_CONTENT_TYPE:
        raise UnsafeImageError(ErrorCode.INVALID_IMAGE_TYPE, "Only JPEG and PNG are allowed.")
    if not data:
        raise UnsafeImageError(ErrorCode.UNSAFE_OR_CORRUPT_IMAGE, "Image data is empty.")
    if len(data) > limits.max_input_bytes:
        raise UnsafeImageError(ErrorCode.IMAGE_TOO_LARGE, "Image exceeds the size limit.")
    expected_signature = (
        b"\xff\xd8\xff" if declared_content_type == "image/jpeg" else b"\x89PNG\r\n\x1a\n"
    )
    if not data.startswith(expected_signature):
        raise UnsafeImageError(
            ErrorCode.UNSAFE_OR_CORRUPT_IMAGE,
            "Image signature does not match the declared content type.",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                decoded_format = probe.format
                actual_content_type = _CONTENT_TYPE_BY_FORMAT.get(decoded_format or "")
                if actual_content_type != declared_content_type:
                    raise UnsafeImageError(
                        ErrorCode.UNSAFE_OR_CORRUPT_IMAGE,
                        "Declared content type does not match decoded image format.",
                    )
                # ``size`` comes from image headers. Enforce both dimension
                # and total-pixel limits before Pillow is allowed to decode
                # the complete pixel buffer.
                width, height = probe.size
                image_warnings = _validate_dimensions(
                    width=width, height=height, limits=limits
                )
                probe.verify()

            with Image.open(BytesIO(data)) as source:
                actual_content_type = _CONTENT_TYPE_BY_FORMAT.get(source.format or "")
                if actual_content_type != declared_content_type:
                    raise UnsafeImageError(
                        ErrorCode.UNSAFE_OR_CORRUPT_IMAGE,
                        "Decoded image format changed during verification.",
                    )
                # Limits were checked using the verified header above; only
                # now is it safe to allocate/decode pixels.
                source.load()
                oriented = ImageOps.exif_transpose(source)
                clean = _copy_pixels_without_metadata(oriented, declared_content_type)
                clean.thumbnail((limits.output_max_dimension, limits.output_max_dimension), Image.Resampling.LANCZOS)
    except UnsafeImageError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise UnsafeImageError(
            ErrorCode.IMAGE_PIXEL_LIMIT_EXCEEDED, "Image pixel count exceeds the safety limit."
        ) from error
    except (OSError, SyntaxError, UnidentifiedImageError) as error:
        raise UnsafeImageError(
            ErrorCode.UNSAFE_OR_CORRUPT_IMAGE, "Image cannot be safely decoded."
        ) from error

    encoded = _encode_clean_image(clean, declared_content_type)
    if len(encoded) > limits.max_input_bytes:
        raise UnsafeImageError(
            ErrorCode.IMAGE_TOO_LARGE, "Sanitized image exceeds the size limit."
        )
    return SanitizedImage(
        content_type=declared_content_type,
        data=encoded,
        width=clean.width,
        height=clean.height,
        source_sha256=sha256(data).hexdigest(),
        # Encoded PNG bytes can differ across supported Pillow/zlib builds
        # although their normalized pixels are identical. The persistence and
        # idempotency identity therefore binds canonical RGB pixels rather
        # than an encoder-specific byte stream.
        sanitized_sha256=_canonical_pixel_sha256(clean),
        warnings=tuple(image_warnings),
    )


def _validate_dimensions(*, width: int, height: int, limits: ImageSafetyLimits) -> list[str]:
    if width < limits.unusable_min_dimension or height < limits.unusable_min_dimension:
        raise UnsafeImageError(
            ErrorCode.IMAGE_TOO_LOW_RESOLUTION, "Image resolution is below the minimum."
        )
    if width > limits.max_dimension or height > limits.max_dimension:
        raise UnsafeImageError(
            ErrorCode.IMAGE_PIXEL_LIMIT_EXCEEDED, "Image dimensions exceed the safety limit."
        )
    if width * height > limits.max_pixels:
        raise UnsafeImageError(
            ErrorCode.IMAGE_PIXEL_LIMIT_EXCEEDED, "Image pixel count exceeds the safety limit."
        )
    return ["low_resolution"] if width < 480 or height < 480 else []


def _copy_pixels_without_metadata(source: Image.Image, content_type: str) -> Image.Image:
    # New pixel buffers discard EXIF, ICC profiles, comments and arbitrary image.info.
    mode = "RGB"
    normalized = source.convert(mode)
    clean = Image.new(mode, normalized.size)
    clean.paste(normalized)
    return clean


def _encode_clean_image(image: Image.Image, content_type: str) -> bytes:
    output = BytesIO()
    if content_type == "image/jpeg":
        image.save(output, format="JPEG", quality=90, optimize=True, progressive=False)
    else:
        image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _canonical_pixel_sha256(image: Image.Image) -> str:
    """Return a cross-platform digest for the normalized image identity."""
    digest = sha256()
    digest.update(image.mode.encode("ascii"))
    digest.update(b"\0")
    digest.update(image.width.to_bytes(8, "big"))
    digest.update(image.height.to_bytes(8, "big"))
    digest.update(image.tobytes())
    return digest.hexdigest()
