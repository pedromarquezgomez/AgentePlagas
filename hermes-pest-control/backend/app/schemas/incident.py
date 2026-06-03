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
    confidence: str | None = None
    severity: str | None = None
    operational_priority: str | None = None
    response_hours: int | None = None
    assessment_reason: str | None = None
    visit_type: str | None = None
    technician_level: str | None = None
    dispatch_bucket: str | None = None
    sla_hours: int | None = None
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
    confidence: str | None = None
    severity: str | None = None
    operational_priority: str | None = None
    response_hours: int | None = None
    assessment_reason: str | None = None
    visit_type: str | None = None
    technician_level: str | None = None
    dispatch_bucket: str | None = None
    sla_hours: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentRead(BaseModel):
    id: str | None = None
    conversation_id: str | None = None
    channel: Channel
    pest_type: str | None = None
    location: str | None = None
    affected_area: str | None = None
    priority: str = "medium"
    operational_priority: str | None = None
    status: IncidentStatus
    summary: str | None = None
    internal_notes: str | None = None
    confidence: str | None = None
    severity: str | None = None
    response_hours: int | None = None
    assessment_reason: str | None = None
    visit_type: str | None = None
    technician_level: str | None = None
    dispatch_bucket: str | None = None
    sla_hours: int | None = None
    sla_status: str | None = None
    elapsed_hours: float | None = None
    remaining_hours: float | None = None
    breach_hours: float | None = None
    created_at: Any | None = None
    updated_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus | None = None
    priority: IncidentPriority | None = None
    internal_notes: str | None = None
