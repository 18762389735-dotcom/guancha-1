from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict


class ApiErrorDetail(BaseModel):
    """Stable error payload consumed by the frontend adapter."""

    model_config = ConfigDict(populate_by_name=True)

    code: str
    message: str
    retryable: bool = False
    resource_id: UUID | None = None
    request_id: UUID


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail
