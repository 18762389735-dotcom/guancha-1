from __future__ import annotations

from .interfaces import TemporaryImageObject


class InMemoryTemporaryPrivateStorage:
    """Test-only private storage adapter; it never generates accessible URLs."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[str, bytes]] = {}
        self.deleted_keys: list[str] = []

    async def put_private(
        self, *, object_key: str, content_type: str, data: bytes
    ) -> TemporaryImageObject:
        self.objects[object_key] = (content_type, data)
        return TemporaryImageObject(
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(data),
        )

    async def delete(self, *, object_key: str) -> None:
        self.objects.pop(object_key, None)
        self.deleted_keys.append(object_key)

    async def read_private(self, *, object_key: str) -> bytes:
        return self.objects[object_key][1]
