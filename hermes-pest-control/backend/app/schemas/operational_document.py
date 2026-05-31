from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import (
    OperationalDocumentGeneratedBy,
    OperationalDocumentStatus,
    OperationalDocumentType,
)


class OperationalDocument(BaseModel):
    id: str | None = None
    document_type: OperationalDocumentType
    incident_id: str | None = None
    visit_id: str | None = None
    title: str
    content: str
    status: OperationalDocumentStatus = "draft"
    generated_by: OperationalDocumentGeneratedBy = "system"
    created_at: Any | None = None
    updated_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalDocumentCreate(BaseModel):
    document_type: OperationalDocumentType
    incident_id: str | None = None
    visit_id: str | None = None
    title: str
    content: str
    status: OperationalDocumentStatus = "draft"
    generated_by: OperationalDocumentGeneratedBy = "admin"
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    content: str | None = None
    status: OperationalDocumentStatus | None = None
    metadata: dict[str, Any] | None = None
