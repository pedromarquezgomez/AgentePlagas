from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import Channel, HumanReviewReason, HumanReviewStatus, IncidentPriority


class HumanReviewItem(BaseModel):
    id: str | None = None
    trace_id: str
    conversation_id: str
    incident_id: str | None = None
    decision_record_id: str | None = None
    channel: Channel
    reason: HumanReviewReason
    priority: IncidentPriority = "medium"
    status: HumanReviewStatus = "open"
    summary: str | None = None
    created_at: Any | None = None
    updated_at: Any | None = None
    resolved_at: Any | None = None
    assigned_to: str | None = None
    resolution_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanReviewItemCreate(BaseModel):
    trace_id: str
    conversation_id: str
    incident_id: str | None = None
    decision_record_id: str | None = None
    channel: Channel
    reason: HumanReviewReason
    priority: IncidentPriority = "medium"
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanReviewItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HumanReviewStatus | None = None
    assigned_to: str | None = None
    resolution_notes: str | None = None
