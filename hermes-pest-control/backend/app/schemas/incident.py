from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import Channel, IncidentPriority, IncidentStatus


class IncidentDraft(BaseModel):
    conversation_id: str | None = None
    channel: Channel
    pest_type: str | None = None
    location: str | None = None
    affected_area: str | None = None
    priority: IncidentPriority = "medium"
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    id: str | None = None
    conversation_id: str | None = None
    channel: Channel
    pest_type: str | None = None
    location: str | None = None
    affected_area: str | None = None
    priority: IncidentPriority = "medium"
    status: IncidentStatus
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
