from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    internal_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus | None = None
    priority: IncidentPriority | None = None
    internal_notes: str | None = None
