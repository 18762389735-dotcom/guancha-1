from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from uuid import UUID

from guancha_api.infrastructure.storage.interfaces import (
    TemporaryImageCleanupError,
    TemporaryImageObject,
    TemporaryPrivateStorage,
)


def temporary_image_object_key(image_id: UUID) -> str:
    """Single private-key convention shared by upload, retry, deletion and workers."""
    return f"temporary/{image_id}"


async def delete_temporary_private_image(
    storage: TemporaryPrivateStorage, *, object_key: str
) -> None:
    try:
        await storage.delete(object_key=object_key)
    except Exception as exc:
        raise TemporaryImageCleanupError(object_key) from exc


@asynccontextmanager
async def temporary_private_image(
    storage: TemporaryPrivateStorage,
    *,
    object_key: str,
    content_type: str,
    data: bytes,
) -> AsyncIterator[TemporaryImageObject]:
    """Store a private image only for the lifetime of a processing operation.

    The ``finally`` block runs for success, provider errors and cancellation/timeouts.
    It deliberately does not expose a URL or persist an object path in any DTO.
    """

    stored = await storage.put_private(
        object_key=object_key,
        content_type=content_type,
        data=data,
    )
    try:
        yield stored
    finally:
        await delete_temporary_private_image(storage, object_key=stored.object_key)
