from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import VisitStatus


class Visit(BaseModel):
    id: str | None = None
    incident_id: str
    technician_id: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: VisitStatus = "draft"
    address: str | None = None
    notes: str | None = None
    external_calendar_provider: str | None = None
    external_calendar_event_id: str | None = None
    external_calendar_sync_status: str | None = None
    external_calendar_last_synced_at: Any | None = None
    external_calendar_error: str | None = None
    created_at: Any | None = None
    updated_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisitCreate(BaseModel):
    incident_id: str
    technician_id: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: VisitStatus = "draft"
    address: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technician_id: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: VisitStatus | None = None
    address: str | None = None
    notes: str | None = None
